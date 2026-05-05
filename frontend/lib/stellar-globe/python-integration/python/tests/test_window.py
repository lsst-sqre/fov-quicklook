import math
import re
from typing import cast

import pytest
import requests
from requests.exceptions import HTTPError

from hscmap.comm.mock import MockComm
from hscmap.window import Window


# Dummy Serverが動いていることを確認
def test_dummy_server(w: Window):
    comm: MockComm = cast(MockComm, w._comm)
    r = requests.get(comm._base_url + "/healthz")
    assert r.status_code == 200


# ウィンドウを作成できる
def test_Window(w: Window):
    pass


# 不正なメッセージにはエラーが出る
def test_send_invalid_message(w: Window):
    with pytest.raises(HTTPError) as e:
        w._post_message({"type": "invalid"})
    assert e.value.response.status_code == 400


# 正しいメッセージはエラーが出ない
def test_send_valid_message(w: Window):
    w.sync()


def test_window_repr(w: Window):
    s = repr(w)
    assert re.search(r"<Window .*>", s)


def test_window_sync(w: Window):
    pdr3_dud = w.dataset.tile_layers['PDR3 DUD']
    assert pdr3_dud.visible
    pdr3_dud.visible = False
    assert w._synced is False
    w.sync()
    assert pdr3_dud.visible is False


def test_window_patch(w: Window):
    comm = cast(MockComm, w._comm)
    assert w._store_revision == 0
    pdr3_dud = w.dataset.tile_layers['PDR3 DUD']
    assert pdr3_dud.visible
    pdr3_dud.visible = False
    assert w._store_revision == 0
    comm.pull_message()
    assert pdr3_dud.visible is False


def test_window_close(w: Window):
    comm = cast(MockComm, w._comm)
    w.close()
    comm.pull_all_messages()


def test_window_action_on_closed_window(w: Window):
    comm = cast(MockComm, w._comm)
    w.close()
    assert w._connection_status == 'connected'
    comm.pull_all_messages()
    assert w._connection_status == 'disconnected'
    w.sync(force=True)
    comm.pull_all_messages()
    assert w._connection_status == 'connected'


def test_window_title(w: Window):
    w.title = 'x'
    assert w.title == 'x'


def test_window_snapshot_bytes(w: Window):
    b = w.snapshot_bytes()
    assert isinstance(b, bytes)
    assert b[:4] == b'\x89PNG'


def test_window_lock(w: Window):
    unlock = w.lock()
    unlock()


def test_window_jump_to(w: Window):
    comm = cast(MockComm, w._comm)
    w.jump_to(150, 2, fov=1, duration=0)
    assert math.isclose(comm.last_outgoing_message()['ra'], 150 * math.pi / 180)
    assert comm.last_outgoing_message()['duration'] == 0
