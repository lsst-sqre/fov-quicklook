from __future__ import annotations

from quicklook.dev.debug_jupyter import (
    EXIT_CODE_SENTINEL,
    ExecutionBuffers,
    build_bash_wrapper,
    handle_message,
    normalize_token,
    strip_exit_code_sentinel,
)


def test_normalize_token_decodes_json_quoted_string() -> None:
    assert normalize_token('"abc123"') == "abc123"


def test_strip_exit_code_sentinel_returns_cleaned_stdout() -> None:
    cleaned, exit_code = strip_exit_code_sentinel(
        f"hello\n{EXIT_CODE_SENTINEL}7\n"
    )
    assert cleaned == "hello\n"
    assert exit_code == 7


def test_build_bash_wrapper_embeds_exit_code_sentinel() -> None:
    wrapper = build_bash_wrapper("echo hello")
    assert "echo hello" not in wrapper
    assert EXIT_CODE_SENTINEL in wrapper


def test_handle_message_records_system_exit_code() -> None:
    buffers = ExecutionBuffers()
    done = handle_message(
        {
            "parent_header": {"msg_id": "target"},
            "header": {"msg_type": "error"},
            "content": {"ename": "SystemExit", "evalue": "3", "traceback": ["trace"]},
        },
        request_id="target",
        buffers=buffers,
    )
    assert done is False
    assert buffers.exit_code == 3
    assert "trace" in buffers.stderr
