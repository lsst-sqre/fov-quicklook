from quicklook.types import BBox, GeneratorPod
from quicklook.types import Visit, CcdId


def test_bbox_union():
    bbox1 = BBox(miny=1.0, maxy=5.0, minx=2.0, maxx=6.0)
    bbox2 = BBox(miny=3.0, maxy=7.0, minx=4.0, maxx=8.0)
    result = bbox1.union(bbox2)
    assert result.miny == 1.0
    assert result.maxy == 7.0
    assert result.minx == 2.0
    assert result.maxx == 8.0


def test_generatorpod_name():
    pod = GeneratorPod(host="localhost", port=8080)
    assert pod.name == "localhost:8080"
