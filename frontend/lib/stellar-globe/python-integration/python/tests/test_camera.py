import math
from typing import cast

import pytest

from hscmap import Window
from hscmap.comm.mock import MockComm


def test_camera_params_get(w: Window):
    assert w.camera.params is not None


def test_camera_center_get(w: Window):
    assert w.camera.center is not None


def test_camera_fov_get(w: Window):
    assert w.camera.fov is not None


def test_camera_center_set(w: Window):
    comm = cast(MockComm, w._comm)
    w.camera.center = (150, 2)
    assert comm.last_outgoing_message()['type'] == 'JumpTo'
    assert math.isclose(comm.last_outgoing_message()['ra'], 150 * math.pi / 180)
    assert math.isclose(comm.last_outgoing_message()['dec'], 2 * math.pi / 180)


def test_camera_fov_set(w: Window):
    comm = cast(MockComm, w._comm)
    w.camera.fov = 0.1
    assert math.isclose(comm.last_outgoing_message()['fov'], 0.1 * math.pi / 180)
