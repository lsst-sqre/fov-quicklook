from typing import List
from hscmap import Window
from hscmap.regions import RegionBase, TextRegion
from hscmap.comm.mock import MockComm


def test_watch(w: Window):
    comm: MockComm = w._comm  # type: ignore

    def watch_on():
        return len(w.regions.members)

    history: List[RegionBase] = []

    def on_change():
        history.append(w.regions.members[-1])

    w.watch(watch_on=watch_on, on_change=on_change)
    assert len(w.watchers.members) == 1

    assert len(history) == 0

    w.dataset.tile_layers['PDR3 DUD'].visible = False
    comm.pull_all_messages()
    assert len(history) == 0  # on_change is not called if the value of watch_on does not change

    t = w.regions.new_text(text='test', position=(0, 0))
    comm.pull_all_messages()

    assert len(history) == 1
    assert history[0].id == t.id

    w.watchers.clear()

    assert len(w.watchers.members) == 0
