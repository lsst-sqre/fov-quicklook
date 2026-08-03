#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import re
import sys
import textwrap
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urljoin

import requests
import websockets

DEFAULT_BASE_URL = "https://usdf-rsp-dev.slac.stanford.edu/fov-quicklook/debug"
DEFAULT_TOKEN_FILE = Path(__file__).resolve().parents[4] / "dev" / ".gafaelfawr-token"
DEFAULT_BROKER_URL_FILE = Path.home() / ".fov-quicklook2" / "broker-url"
DEFAULT_BROKER_TOKEN_FILE = Path.home() / ".fov-quicklook2" / "broker-token"
EXIT_CODE_SENTINEL = "__DEBUG_JUPYTER_EXIT_CODE__="


@dataclass(slots=True)
class ExecutionBuffers:
    stdout_parts: list[str] = field(default_factory=list)
    stderr_parts: list[str] = field(default_factory=list)
    exit_code: int | None = None

    @property
    def stdout(self) -> str:
        return "".join(self.stdout_parts)

    @property
    def stderr(self) -> str:
        return "".join(self.stderr_parts)


@dataclass(slots=True)
class JupyterSession:
    base_url: str
    cookie_header: str
    xsrf_token: str | None

    def api_url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def ws_url(self, path: str, query: dict[str, str]) -> str:
        scheme = "wss" if self.base_url.startswith("https://") else "ws"
        rest = self.base_url.removeprefix("https://").removeprefix("http://")
        return f"{scheme}://{rest}{path}?{urlencode(query)}"

    @property
    def api_headers(self) -> dict[str, str]:
        headers = {"Cookie": self.cookie_header}
        if self.xsrf_token:
            headers["X-XSRFToken"] = self.xsrf_token
        return headers


def normalize_token(token: str) -> str:
    token = token.strip()
    if len(token) >= 2 and token[0] == token[-1] == '"':
        try:
            decoded = json.loads(token)
        except json.JSONDecodeError:
            return token
        if isinstance(decoded, str):
            return decoded.strip()
    return token


def load_text_argument(code: str | None, file_path: str | None) -> str:
    if bool(code) == bool(file_path):
        raise ValueError("--code か --file のどちらか一方だけを指定してください。")
    if code is not None:
        return code
    path = Path(file_path or "")
    if not path.exists():
        raise ValueError(f"ファイルが見つかりません: {path}")
    return path.read_text(encoding="utf-8")


def make_cookie_header(token: str, xsrf_token: str | None = None) -> str:
    pairs = [f'gafaelfawr="{token}"']
    if xsrf_token:
        pairs.append(f"_xsrf={xsrf_token}")
    return "; ".join(pairs)


def build_bash_wrapper(script: str) -> str:
    encoded = base64.b64encode(script.encode("utf-8")).decode("ascii")
    return textwrap.dedent(
        f"""
        import base64
        import os
        import stat
        import subprocess
        import sys
        import tempfile

        script = base64.b64decode({encoded!r}).decode("utf-8")
        with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False, encoding="utf-8") as handle:
            handle.write("set -euo pipefail\\n")
            handle.write(script)
            script_path = handle.name
        os.chmod(script_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        try:
            completed = subprocess.run(["bash", script_path], text=True, capture_output=True)
            sys.stdout.write(completed.stdout)
            sys.stderr.write(completed.stderr)
            sys.stdout.write("\\n{EXIT_CODE_SENTINEL}" + str(completed.returncode) + "\\n")
        finally:
            os.unlink(script_path)
        """
    ).strip()


def strip_exit_code_sentinel(stdout: str) -> tuple[str, int | None]:
    match = None
    for candidate in re.finditer(rf"(?:^|\n){re.escape(EXIT_CODE_SENTINEL)}(\d+)\n?$", stdout):
        match = candidate
    if match is None:
        return stdout, None
    cleaned = stdout[: match.start()]
    if match.group(0).startswith("\n"):
        cleaned += "\n"
    cleaned += stdout[match.end() :]
    return cleaned, int(match.group(1))


def fetch_app_token(
    broker_url: str,
    broker_token: str,
    *,
    refresh: bool,
    timeout: float,
) -> str:
    response = requests.get(
        f"{broker_url.rstrip('/')}/v1/tokens/app",
        headers={"Authorization": f"Bearer {broker_token}"},
        params={"refresh": "true"} if refresh else None,
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    token = payload.get("token")
    if not isinstance(token, str) or not token.strip():
        raise ValueError("broker get-app-token のレスポンスに token がありません。")
    return normalize_token(token)


def load_token(args: argparse.Namespace) -> str:
    if args.token:
        return normalize_token(args.token)

    if args.broker:
        broker_url = args.broker_url or read_optional_text(args.broker_url_file)
        broker_token = args.broker_token or read_optional_text(args.broker_token_file)
        if not broker_url or not broker_token:
            raise ValueError("broker token 取得には broker URL と broker token が必要です。")
        return fetch_app_token(
            broker_url,
            broker_token,
            refresh=args.refresh_broker_token,
            timeout=args.http_timeout,
        )

    if env_token := os.environ.get("GAFAELFAWR_TOKEN"):
        return normalize_token(env_token)

    if token_file := args.token_file:
        path = Path(token_file)
        if path.exists():
            return normalize_token(path.read_text(encoding="utf-8"))

    raise ValueError(
        "gafaelfawr token が見つかりません。"
        " --token / --broker / GAFAELFAWR_TOKEN / dev/.gafaelfawr-token のいずれかを使ってください。"
    )


def read_optional_text(path: str | Path | None) -> str | None:
    if path is None:
        return None
    file_path = Path(path)
    if not file_path.exists():
        return None
    return file_path.read_text(encoding="utf-8").strip()


def bootstrap_session(base_url: str, token: str, *, timeout: float) -> JupyterSession:
    normalized_base = base_url.rstrip("/")
    current_url = normalized_base
    cookie_header = make_cookie_header(token)
    for _ in range(10):
        response = requests.get(
            current_url,
            headers={"Cookie": cookie_header},
            timeout=timeout,
            allow_redirects=False,
        )
        if response.status_code not in {301, 302, 303, 307, 308}:
            break
        location = response.headers.get("Location")
        if not location:
            break
        current_url = urljoin(current_url, location)
    else:
        raise ValueError("debug Jupyter への redirect が多すぎます。")
    response.raise_for_status()
    if not response.url.startswith(normalized_base):
        raise ValueError(
            "debug Jupyter に到達できませんでした。"
            " gafaelfawr token の期限切れや ingress redirect を確認してください。"
        )
    xsrf_token = response.cookies.get("_xsrf")
    return JupyterSession(
        base_url=normalized_base,
        cookie_header=make_cookie_header(token, xsrf_token),
        xsrf_token=xsrf_token,
    )


def create_kernel(
    session: JupyterSession,
    *,
    kernel_name: str,
    timeout: float,
) -> str:
    response = requests.post(
        session.api_url("/api/kernels"),
        headers=session.api_headers,
        json={"name": kernel_name},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    kernel_id = payload.get("id")
    if not isinstance(kernel_id, str) or not kernel_id:
        raise ValueError("Jupyter kernel 作成結果に id がありません。")
    return kernel_id


def shutdown_kernel(session: JupyterSession, kernel_id: str, *, timeout: float) -> None:
    response = requests.delete(
        session.api_url(f"/api/kernels/{kernel_id}"),
        headers=session.api_headers,
        timeout=timeout,
    )
    if response.status_code not in {204, 404}:
        response.raise_for_status()


def message_type(message: dict[str, Any]) -> str:
    direct = message.get("msg_type")
    if isinstance(direct, str) and direct:
        return direct
    header = message.get("header")
    if isinstance(header, dict):
        nested = header.get("msg_type")
        if isinstance(nested, str):
            return nested
    return ""


def append_text_result(buffers: ExecutionBuffers, content: dict[str, Any]) -> None:
    data = content.get("data")
    if not isinstance(data, dict):
        return
    text_plain = data.get("text/plain")
    if isinstance(text_plain, str) and text_plain:
        buffers.stdout_parts.append(text_plain)
        if not text_plain.endswith("\n"):
            buffers.stdout_parts.append("\n")


def handle_message(
    message: dict[str, Any],
    *,
    request_id: str,
    buffers: ExecutionBuffers,
) -> bool:
    parent_header = message.get("parent_header")
    if isinstance(parent_header, dict):
        parent_msg_id = parent_header.get("msg_id")
        if parent_msg_id and parent_msg_id != request_id:
            return False

    content = message.get("content")
    if not isinstance(content, dict):
        content = {}

    current_type = message_type(message)
    if current_type == "stream":
        text = content.get("text")
        if not isinstance(text, str):
            return False
        if content.get("name") == "stderr":
            buffers.stderr_parts.append(text)
        else:
            buffers.stdout_parts.append(text)
        return False
    if current_type in {"display_data", "execute_result"}:
        append_text_result(buffers, content)
        return False
    if current_type == "error":
        traceback = content.get("traceback")
        if isinstance(traceback, list) and traceback:
            buffers.stderr_parts.append("\n".join(str(line) for line in traceback) + "\n")
        else:
            buffers.stderr_parts.append(
                f"{content.get('ename', 'Error')}: {content.get('evalue', '')}\n"
            )
        if content.get("ename") == "SystemExit":
            try:
                buffers.exit_code = int(str(content.get("evalue", "")).strip())
            except ValueError:
                buffers.exit_code = 1
        else:
            buffers.exit_code = 1
        return False
    return current_type == "status" and content.get("execution_state") == "idle"


async def execute_code(
    session: JupyterSession,
    *,
    kernel_id: str,
    code: str,
    timeout: float,
) -> ExecutionBuffers:
    client_session_id = uuid.uuid4().hex
    request_id = uuid.uuid4().hex
    ws_url = session.ws_url(
        f"/api/kernels/{kernel_id}/channels",
        {"session_id": client_session_id},
    )
    buffers = ExecutionBuffers()
    async with websockets.connect(
        ws_url,
        additional_headers={"Cookie": session.cookie_header},
        max_size=10 * 1024 * 1024,
    ) as websocket:
        request = {
            "channel": "shell",
            "header": {
                "msg_id": request_id,
                "msg_type": "execute_request",
                "session": client_session_id,
                "username": "debug-jupyter",
                "version": "5.3",
            },
            "parent_header": {},
            "metadata": {},
            "content": {
                "code": code,
                "silent": False,
                "store_history": False,
                "user_expressions": {},
                "allow_stdin": False,
                "stop_on_error": True,
            },
            "buffers": [],
        }
        await websocket.send(json.dumps(request))
        while True:
            raw_message = await asyncio.wait_for(websocket.recv(), timeout=timeout)
            message = json.loads(raw_message)
            if handle_message(message, request_id=request_id, buffers=buffers):
                return buffers


def print_output(buffers: ExecutionBuffers) -> int:
    stdout, bash_exit_code = strip_exit_code_sentinel(buffers.stdout)
    if stdout:
        print(stdout, end="" if stdout.endswith("\n") else "\n")
    if buffers.stderr:
        print(buffers.stderr, end="" if buffers.stderr.endswith("\n") else "\n", file=sys.stderr)
    if bash_exit_code is not None:
        return bash_exit_code
    if buffers.exit_code is not None:
        return buffers.exit_code
    return 0


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="debug Jupyter の base URL")
    parser.add_argument("--token", help="gafaelfawr token を直接指定")
    parser.add_argument(
        "--token-file",
        default=str(DEFAULT_TOKEN_FILE),
        help="token file のパス (既定: dev/.gafaelfawr-token)",
    )
    parser.add_argument(
        "--broker",
        action="store_true",
        help="deploy broker から app token を取得する",
    )
    parser.add_argument("--broker-url", help="deploy broker の URL")
    parser.add_argument("--broker-token", help="deploy broker の bearer token")
    parser.add_argument(
        "--broker-url-file",
        default=str(DEFAULT_BROKER_URL_FILE),
        help="broker URL file のパス",
    )
    parser.add_argument(
        "--broker-token-file",
        default=str(DEFAULT_BROKER_TOKEN_FILE),
        help="broker token file のパス",
    )
    parser.add_argument(
        "--refresh-broker-token",
        action="store_true",
        help="broker の token cache を refresh してから app token を取得する",
    )
    parser.add_argument(
        "--kernel-name",
        default="python3",
        help="Jupyter kernel 名 (既定: python3)",
    )
    parser.add_argument(
        "--http-timeout",
        type=float,
        default=30.0,
        help="HTTP request timeout 秒数",
    )
    parser.add_argument(
        "--execute-timeout",
        type=float,
        default=120.0,
        help="kernel execute timeout 秒数",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="fov-quicklook debug Jupyter で Python / bash を実行する",
    )
    add_common_arguments(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    python_parser = subparsers.add_parser("python", help="Python code を実行")
    python_parser.add_argument("--code", help="実行する Python code")
    python_parser.add_argument("--file", help="実行する Python file")

    bash_parser = subparsers.add_parser("bash", help="bash script を実行")
    bash_parser.add_argument("--code", help="実行する bash script")
    bash_parser.add_argument("--file", help="実行する bash file")

    return parser.parse_args()


def command_to_code(args: argparse.Namespace) -> str:
    text = load_text_argument(getattr(args, "code", None), getattr(args, "file", None))
    if args.command == "python":
        return text
    if args.command == "bash":
        return build_bash_wrapper(text)
    raise ValueError(f"未対応コマンドです: {args.command}")


def main() -> None:
    args = parse_args()
    token = load_token(args)
    session = bootstrap_session(args.base_url, token, timeout=args.http_timeout)
    code = command_to_code(args)
    kernel_id = create_kernel(session, kernel_name=args.kernel_name, timeout=args.http_timeout)
    try:
        buffers = asyncio.run(
            execute_code(
                session,
                kernel_id=kernel_id,
                code=code,
                timeout=args.execute_timeout,
            )
        )
    finally:
        shutdown_kernel(session, kernel_id, timeout=args.http_timeout)
    raise SystemExit(print_output(buffers))


if __name__ == "__main__":
    main()
