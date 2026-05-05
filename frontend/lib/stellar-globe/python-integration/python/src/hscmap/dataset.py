from typing import List
from .models.actions.hipsLayers.baseUrlChanged import Model as BaseUrlChanged
from typing import Optional, Dict, Tuple
from functools import cached_property, lru_cache
from dataclasses import dataclass
from .window import Window
from .models.actions.tractTileLayers.layerToggled import Model as LayerToggled


@dataclass
class DatasetManager:
    _w: Window

    def _sync(self):
        self._w.sync()

    @property
    def tile_layers(self) -> Dict[str, 'TileLayer']:
        self._sync()
        return {layer['name']: TileLayer(layer['name'], self._w) for layer in self._w._store_state['tractTileLayers']['layers']}

    @cached_property
    def hips(self) -> 'HipsDatasetManager':
        return HipsDatasetManager(self._w)


@dataclass
class TileLayer:
    name: str
    _w: Window

    def _state(self):
        for layer in self._w._store_state['tractTileLayers']['layers']:  # pragma: no branch
            if layer['name'] == self.name:
                return layer
        raise ValueError(f'Layer {self.name} not found')  # pragma: no coverķ

    def _sync(self):
        self._w.sync()

    @property
    def visible(self) -> bool:
        self._sync()
        return self._state()['visible']

    @visible.setter
    def visible(self, value) -> None:
        action = LayerToggled(
            type='tractTileLayers/layerToggled',
            payload={
                'name': self.name,
                'visible': value,
            },
        )
        self._w._dispatch(action)


@dataclass
class HipsDatasetManager:
    _w: Window

    def _sync(self):
        self._w.sync()

    @property
    def base_url(self) -> Optional[str]:
        self._sync()
        return self._w._store_state['hipsLayers'].get('baseUrl')

    @base_url.setter
    def base_url(self, value: Optional[str]) -> None:
        action = BaseUrlChanged(
            type='hipsLayers/baseUrlChanged',
            payload={
                'baseUrl': value,
            },
        )
        self._w._dispatch(action)

    def clear(self) -> None:
        self.base_url = None

    @property
    def properties(self) -> Optional[List[Tuple[str, str]]]:
        if self.base_url:
            return get_hips_properties(self.base_url)

    def find_by_name(self, name: str) -> List['HipsSearchResponse']:
        import requests
        import urllib.parse as parse_url

        url = f'https://alasky.cds.unistra.fr/MocServer/query?hips_service_url=*&casesensitive=false&obs_title=*{ parse_url.quote(name) }*&dataproduct_type=image&dataproduct_subtype=*&get=record&fields=ID,obs_title,hips_service*,hips_status*&fmt=json'
        response: List = requests.get(url).json()
        return [
            HipsSearchResponse(
                ID=item.get('ID', ''),
                obs_title=item.get('obs_title', ''),
                hips_service_url=item.get('hips_service_url', ''),
            )
            for item in response
        ]


@dataclass
class HipsSearchResponse:
    ID: str
    obs_title: str
    hips_service_url: str


@lru_cache
def get_hips_properties(base_url: str) -> List[Tuple[str, str]]:
    import requests

    url = f'{base_url}/properties'
    response = requests.get(url).text
    return parse_hips_properties(response)


def parse_hips_properties(raw_properties: str) -> List[Tuple[str, str]]:
    # 次のようなstrをパースしlist[tuple[str, str]]に変換する
    # '#' で始まる行はコメントだが、その場合は ('', 値) として返す

    # hips_doi             = 10.26093/cds/aladin/598a-0e
    # ...
    # obs_copyright_url    = http://panstarrs.stsci.edu/
    # # PanSTARRS filters are described at http://svo2.cab.inta-csic.es/svo/theory/fps/index.php?mode=browse&gname=PAN-STARRS
    # em_min               = 3.94340e-7
    # em_max               = 8.430e-7
    # ...
    #

    lines = raw_properties.split('\n')
    result = []
    for line in lines:
        if len(line) > 1:
            if line.startswith('#'):
                result.append(('', line[2:]))
            else:
                if '=' in line:  # pragma: no branch
                    key, value = line.split('=', 1)
                    result.append((key.strip(), value.strip()))
                else:  # pragma: no cover
                    result.append(('', line))

    return result
