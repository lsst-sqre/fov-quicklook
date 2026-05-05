import pytest

from hscmap import Window
from hscmap.catalogs import sample_pandas_data, Catalog


def test_catalogs(w: Window):
    w.catalogs


def test_catalogs_from_pandas(w: Window):
    sample = sample_pandas_data(50)
    w.catalogs.from_pandas(sample)


def test_catalogs_clear(w: Window):
    w.catalogs.clear()
    sample = sample_pandas_data()
    w.catalogs.from_pandas(sample)
    assert len(w.catalogs.members) == 1
    w.catalogs.clear()
    assert len(w.catalogs.members) == 0


def test_catalogs_new(w: Window):
    w.catalogs.clear()
    w.catalogs.new([0, 1, 2], [0, 1, 2])
    assert len(w.catalogs.members) == 1
    assert w.catalogs.members[0].name == 'Catalog 1'


@pytest.fixture
def sample_catalog(w: Window):
    sample = sample_pandas_data()
    w.catalogs.clear()
    return w.catalogs.from_pandas(sample)


def test_catalog_delete(sample_catalog: Catalog):
    w = sample_catalog._w
    assert len(w.catalogs.members) == 1
    sample_catalog.delete()
    assert len(w.catalogs.members) == 0


def test_catalog_name_get(sample_catalog: Catalog):
    assert sample_catalog.name == 'Catalog 1'


def test_catalog_name_set(sample_catalog: Catalog):
    sample_catalog.name = 'New Name'
    assert sample_catalog.name == 'New Name'


def test_catalog_color(sample_catalog: Catalog):
    assert sample_catalog.color != [1, 0, 0, 1]
    sample_catalog.color = [1, 0, 0, 1]
    assert sample_catalog.color == [1, 0, 0, 1]


def test_catalog_markers(sample_catalog: Catalog):
    assert sample_catalog.marker == 'circle'
    sample_catalog.marker = 'asterisk'
    assert sample_catalog.marker == 'asterisk'


def test_catalog_column_names(sample_catalog: Catalog):
    assert sample_catalog.column_names == ['ID', 'ra', 'dec', 'mag']


def test_catalog_visible(sample_catalog: Catalog):
    assert sample_catalog.visible is True
    sample_catalog.visible = False
    assert sample_catalog.visible is False


def test_catalog_selected_indices(sample_catalog: Catalog):
    assert sample_catalog.selected_indices == []
    sample_catalog.selected_indices = [1, 2, 3]
    assert sample_catalog.selected_indices == [1, 2, 3]
    sample_catalog.selected_indices = [2, 3, 4]
    assert sample_catalog.selected_indices == [2, 3, 4]


def test_catalog_as_pandas_dataframe(sample_catalog: Catalog):
    import pandas

    df = sample_catalog.as_pandas_dataframe()
    assert isinstance(df, pandas.DataFrame)
    assert df.columns.tolist() == ['ID', 'ra', 'dec', 'mag']
    assert len(df) == 500
    assert df.columns.tolist() == ['ID', 'ra', 'dec', 'mag']
    assert len(df['ID']) == 500
    assert df['ID'][10] == '10'
