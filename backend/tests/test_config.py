from quicklook.config import config


def test_coordinator_port():
    assert config.coordinator_base_url == 'http://localhost:19501'
    assert config.coordinator_port == 19501


def test_coordinator_ws_base_url():
    assert config.coordinator_base_url == 'http://localhost:19501'
    assert config.coordinator_ws_base_url == 'ws://localhost:19501'
