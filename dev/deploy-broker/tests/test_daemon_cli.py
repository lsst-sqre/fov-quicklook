from __future__ import annotations

import sys
from pathlib import Path

from deploy_broker.config import Settings
from deploy_broker.daemon_cli import main


def test_main_prints_bearer_token_on_startup(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    settings = Settings(
        api_token="secret-broker-token",
        state_dir=tmp_path / "state",
        token_command="fetch-broker-tokens",
    )
    app = object()
    captured: dict[str, object] = {}

    monkeypatch.setattr("deploy_broker.daemon_cli.get_settings", lambda: settings)
    monkeypatch.setattr("deploy_broker.daemon_cli.create_app", lambda resolved: app)

    def _run(app: object, host: str, port: int) -> None:
        captured["app"] = app
        captured["host"] = host
        captured["port"] = port

    monkeypatch.setattr("deploy_broker.daemon_cli.uvicorn.run", _run)
    monkeypatch.setattr(sys, "argv", ["deploy-broker-daemon"])

    main()

    output = capsys.readouterr()
    assert "Broker bearer token: secret-broker-token" in output.err
    assert captured == {"app": app, "host": "127.0.0.1", "port": 8010}


def test_main_exits_when_token_command_is_missing(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    settings = Settings(
        api_token="secret-broker-token",
        state_dir=tmp_path / "state",
        token_command=None,
    )

    monkeypatch.setattr("deploy_broker.daemon_cli.get_settings", lambda: settings)
    monkeypatch.setattr(sys, "argv", ["deploy-broker-daemon"])

    def _run(*args, **kwargs) -> None:
        raise AssertionError("uvicorn.run must not be called")

    monkeypatch.setattr("deploy_broker.daemon_cli.uvicorn.run", _run)

    try:
        main()
    except SystemExit as exc:
        assert exc.code == 1
    else:
        raise AssertionError("main() should exit when token command is missing")

    output = capsys.readouterr()
    assert "DEPLOY_BROKER_TOKEN_COMMAND must be configured" in output.err
