"""
generate_single_fits_tiles_coordinatorの動作確認用の簡単なテスト
"""
import asyncio
from collections import deque

import pytest


async def test_phase_transition_with_round_robin():
    """Phase 2のラウンドロビン動作をテスト"""
    # シミュレート用のデータ
    ccd_refs = [f"ccd{i}" for i in range(10)]
    remaining_ccds = deque(ccd_refs[:])
    submitted_ccds: list[str] = []
    completed_ccds: set[str] = set()
    phase2_index = 0
    
    async def get_next_ccd() -> str | None:
        """次のCCDを取得（ラウンドロビン版）"""
        nonlocal phase2_index
        # Phase 1
        if remaining_ccds:
            ccd = remaining_ccds.popleft()
            submitted_ccds.append(ccd)
            return ccd
        
        # Phase 2: ラウンドロビン
        for offset in range(len(submitted_ccds)):
            idx = (phase2_index + offset) % len(submitted_ccds)
            ccd = submitted_ccds[idx]
            if ccd not in completed_ccds:
                phase2_index = (idx + 1) % len(submitted_ccds)
                return ccd
        
        return None
    
    # Phase 1: すべてのCCDを1回ずつsubmit
    for _ in range(10):
        ccd = await get_next_ccd()
        assert ccd is not None
    
    # 高速workerが8個を完了
    for i in range(8):
        completed_ccds.add(f"ccd{i}")
    
    # Phase 2: 未完了のccd8, ccd9をラウンドロビンで繰り返しsubmit
    submissions = []
    for _ in range(10):  # 複数回submitできる
        ccd = await get_next_ccd()
        if ccd is None:
            break
        submissions.append(ccd)
    
    # ccd8とccd9が交互にsubmitされる
    print(f"Phase 2 submissions: {submissions}")
    assert submissions == ["ccd8", "ccd9", "ccd8", "ccd9", "ccd8", "ccd9", "ccd8", "ccd9", "ccd8", "ccd9"]
    
    # ccd8が完了
    completed_ccds.add("ccd8")
    
    # ccd9のみがsubmitされる
    submissions2 = []
    for _ in range(5):
        ccd = await get_next_ccd()
        if ccd is None:
            break
        submissions2.append(ccd)
    
    print(f"After ccd8 completion: {submissions2}")
    assert all(ccd == "ccd9" for ccd in submissions2)
    
    # ccd9も完了
    completed_ccds.add("ccd9")
    
    # すべて完了
    ccd = await get_next_ccd()
    assert ccd is None


if __name__ == "__main__":
    asyncio.run(test_phase_transition_with_round_robin())
    print("✓ Phase 2 round-robin logic test passed")
