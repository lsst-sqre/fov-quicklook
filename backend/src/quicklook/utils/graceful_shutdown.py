"""
プロセスの graceful shutdown ユーティリティ。

SIGINT → sleep → SIGKILL の共通パターンを提供する。
"""

import asyncio
import os
import signal

import quicklook.mylogging

logger = quicklook.mylogging.getLogger(__name__)


async def graceful_shutdown(
    *,
    sigint_delay: float = 1.0,
    sigkill_delay: float = 5.0,
    reason: str = "",
) -> None:  # pragma: no cover
    """
    現在のプロセスを graceful に停止する。

    1. sigint_delay 秒待機
    2. SIGINT を送信（uvicornなどのシグナルハンドラによる graceful shutdown を開始）
    3. sigkill_delay 秒待機
    4. SIGKILL で強制終了（SIGINT で終了しなかった場合のフォールバック）

    Args:
        sigint_delay: SIGINT 送信前の待機秒数。再起動ループ防止に使う。
        sigkill_delay: SIGINT 後 SIGKILL までの猶予秒数。
        reason: ログ出力用の終了理由。
    """
    if reason:
        logger.warning(f"Initiating shutdown: {reason}")
    await asyncio.sleep(sigint_delay)
    os.kill(os.getpid(), signal.SIGINT)
    await asyncio.sleep(sigkill_delay)
    os.kill(os.getpid(), signal.SIGKILL)
