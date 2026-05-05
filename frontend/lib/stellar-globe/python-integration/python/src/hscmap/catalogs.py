from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Literal, Optional, Tuple, Iterable

from .models.actions.catalogs.catalogAdded import Marker
from .models.actions.catalogs.catalogAdded import Model as CatalogAdded
from .models.actions.catalogs.catalogDeleted import Model as CatalogDeleted
from .models.actions.catalogs.catalogUpdated import Model as CatalogUpdated
from .tinyid import tinyid
from .vec3 import SkyCoord
from .window import Window

MarkerType = Literal['asterisk', 'circle', 'circledHollowAsterisk', 'circledHollowPlus', 'circledHollowX', 'diamond', 'dot', 'hollowAsterisk', 'hollowPlus', 'hollowX', 'pentagon', 'plus', 'square', 'triangle', 'x']

Color = List[float]
V3 = List[float]

if TYPE_CHECKING:  # pragma: no cover
    from pandas import DataFrame as pdDataFrame
else:
    pdDataFrame = None


@dataclass
class CatalogManager:
    _w: Window

    @property
    def members(self) -> List['Catalog']:
        self._w.sync()
        return [Catalog(c['id'], self._w) for c in self._w._store_state['catalogs']['catalogs']]

    def clear(self) -> None:
        for catalog in self.members:
            catalog.delete()

    def _new(
        self,
        *,
        name: Optional[str] = None,
        table: Dict[str, List[str]],
        xyz: List[V3],
        color: Optional[List[Optional[Color]]] = None,
        type: Optional[Optional[List[MarkerType]]] = None,
        base_color: Optional[Color] = None,
        default_marker_type: MarkerType = 'circle',
        open_catalog_table=False,
    ) -> 'Catalog':
        id = tinyid()
        fields = [*table.keys()]
        name = name or f'Catalog {len(self.members) + 1}'

        # attributesの全ての値が同じ長さであることを確認
        for values in table.values():
            if len(values) != len(xyz):  # pragma: no cover
                raise ValueError('All attributes must have the same length as coords')

        # colors, typesも同じ長さであることを確認
        if color is not None and len(color) != len(xyz):  # pragma: no cover
            raise ValueError('All colors must have the same length as coords')
        if type is not None and len(type) != len(xyz):  # pragma: no cover
            raise ValueError('All types must have the same length as coords')

        markers: List[Marker] = [
            Marker(
                position=xyz[i],
                color=color[i] if color else None,
                type=type[i] if type else None,
            )
            for i in range(len(xyz))
        ]
        attributes = [[table[f][i] for f in table.keys()] for i in range(len(xyz))]

        action = CatalogAdded(
            type='catalogs/catalogAdded',
            payload={
                'id': id,
                'name': name,
                'attributes': attributes,
                'baseColor': base_color,
                'defaultType': default_marker_type,
                'fields': fields,
                'markers': markers,
            },
        )
        self._w._dispatch(action)
        return Catalog(id, self._w)

    def from_pandas(
        self,
        df: pdDataFrame,
        *,
        name: Optional[str] = None,
        coord_column: Optional[Tuple[str, str]] = None,
        color_column: Optional[str] = None,
        type_column: Optional[str] = None,
        base_color: Optional[Color] = None,
        default_marker_type: MarkerType = 'circle',
        open_catalog_table=False,
    ) -> 'Catalog':
        w = self._w

        if coord_column is None:  # pragma: no branch
            coord_column = ('ra', 'dec')

        ras = df[coord_column[0]]
        decs = df[coord_column[1]]

        xyz = [
            SkyCoord(
                w._angle_input(ra),
                w._angle_input(dec),
            )
            .as_vec3()
            .as_list()
            for ra, dec in zip(ras, decs)
        ]

        color = df[color_column].tolist() if color_column else None
        type = df[type_column].tolist() if type_column else None
        table = {k: [str(value) for value in df[k].tolist()] for k in df.columns}

        return self._new(
            name=name,
            table=table,
            xyz=xyz,
            color=color,
            type=type,
            base_color=base_color,
            default_marker_type=default_marker_type,
            open_catalog_table=open_catalog_table,
        )

    def new(
        self,
        ra: List[float],
        dec: List[float],
        *,
        name: Optional[str] = None,
        color: Optional[List[Optional[Color]]] = None,
        type: Optional[Optional[List[MarkerType]]] = None,
        base_color: Optional[Color] = None,
        default_marker_type: MarkerType = 'circle',
        open_catalog_table=False,
    ) -> 'Catalog':
        # Check that the length of ra and dec is the same
        if len(ra) != len(dec):  # pragma: no cover
            raise ValueError('ra and dec must have the same length')

        return self._new(
            name=name,
            table={},
            xyz=[SkyCoord(self._w._angle_input(r), self._w._angle_input(d)).as_vec3().as_list() for r, d in zip(ra, dec)],
            color=color,
            type=type,
            base_color=base_color,
            default_marker_type=default_marker_type,
            open_catalog_table=open_catalog_table,
        )


@dataclass
class Catalog:
    id: str
    _w: Window

    def delete(self) -> None:
        self._w.sync()
        self._w._dispatch(
            CatalogDeleted(
                type='catalogs/catalogDeleted',
                payload={'id': self.id},
            )
        )

    def _sync(self):
        self._w.sync()

    def _state(self):
        self._sync()
        for catalog in self._w._store_state['catalogs']['catalogs']:
            if catalog['id'] == self.id:  # pragma: no branch
                return catalog
        raise ValueError(f'Catalog {self.id} not found')  # pragma: no cover

    def _update(self, **kwargs):
        self._w._dispatch(
            CatalogUpdated(
                type='catalogs/catalogUpdated',
                payload={**kwargs, 'id': self.id},  # type: ignore
            )
        )

    @property
    def name(self) -> str:
        self._sync()
        return self._state()['name']

    @name.setter
    def name(self, new_name: str) -> None:
        self._update(name=new_name)

    @property
    def color(self) -> Color:
        self._sync()
        return self._state()['baseColor']

    @color.setter
    def color(self, new_color: Color) -> None:
        self._update(baseColor=new_color)

    @property
    def marker(self) -> MarkerType:
        self._sync()
        return self._state()['defaultType']

    @marker.setter
    def marker(self, new_marker: MarkerType) -> None:
        self._update(defaultType=new_marker)

    @property
    def column_names(self) -> List[str]:
        self._sync()
        return self._state()['fields']

    @property
    def visible(self) -> bool:
        self._sync()
        return self._state()['visible']

    @visible.setter
    def visible(self, new_visible: bool) -> None:
        self._update(visible=new_visible)

    @property
    def selected_indices(self) -> List[int]:
        self._sync()
        return [*map(int, self._state()['selectedRecords'].keys())]

    @selected_indices.setter
    def selected_indices(self, indicse: Iterable[int]) -> None:
        from hscmap.models.actions.catalogs.recordsBatchSelected import Model as RecordBatchSelected

        self._w._dispatch(
            RecordBatchSelected(
                type='catalogs/recordsBatchSelected',
                payload={
                    'id': self.id,
                    'indices': [*indicse],
                },
            ),
        )

    def as_pandas_dataframe(self) -> 'pdDataFrame':
        import pandas

        fields = self._state()['fields']
        rows = self._state()['attributes']
        return pandas.DataFrame(rows, columns=fields)  # type: ignore


def sample_pandas_data(n_rows: int = 500):
    import numpy
    import pandas

    # pandasでサンプル用のカタログデータを作る
    # カラムは ID, ra, dec, mag
    # 行数はn_rows
    # 内容は適当に乱数で埋める
    # 乱数の範囲は
    # ID: [0, nrows)
    # ra: [-0.5, 0.5]
    # dec: [-0.5, 0.5]
    # mag: [15, 25]
    # とする
    # w.catalogs.from_pandas(df) でカタログを作成できるようにする

    df = pandas.DataFrame(
        {
            'ID': range(n_rows),
            'ra': (numpy.random.rand(n_rows) - 0.5) * 1,
            'dec': (numpy.random.rand(n_rows) - 0.5) * 1,
            'mag': (numpy.random.rand(n_rows) * 10) + 15,
        }
    )
    return df
