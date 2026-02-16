"""CcdDispatcherの単体テスト

Phase 1（初期ディスパッチ）とPhase 2（再割り当て）の両方をテストする。
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from quicklook.comm.types import GeneratorId
from quicklook.generator.generate_single_fits_tiles import CcdMetadata
from quicklook.types import CcdDataRef, CcdName, VisitName
from quicklook.utils.geom import BBox

from .ccd_dispatcher import CcdDispatcher, CcdSubmission


def make_ccd_ref(ccd_name: str) -> CcdDataRef:
    """テスト用のCcdDataRefを作成"""
    return CcdDataRef(VisitName(f"dummy:raw:{ccd_name}"), CcdName(ccd_name))


def make_ccd_metadata(ccd_name: str) -> CcdMetadata:
    """テスト用のCcdMetadataを作成"""
    return CcdMetadata(
        ccd_name=CcdName(ccd_name),
        image_stat=None,  # type: ignore
        amps=[],
        bbox=BBox(0, 0, 100, 100),
    )


class TestCcdDispatcherPhase1:
    """Phase 1（初期ディスパッチ）のテスト"""

    @pytest.mark.asyncio
    async def test_get_next_ccd_returns_ccds_in_order(self):
        """CCDが順番に返されることを確認"""
        ccd_refs = [make_ccd_ref(f"R{i:02d}") for i in range(5)]
        dispatcher = CcdDispatcher(ccd_refs)
        generator_id = GeneratorId("g-test")

        results = []
        for _ in range(5):
            ccd = await dispatcher.get_next_ccd(generator_id)
            if ccd is None:
                break
            results.append(ccd.ccd)

        assert len(results) == 5
        assert results == [CcdName(f"R{i:02d}") for i in range(5)]

    @pytest.mark.asyncio
    async def test_get_next_ccd_returns_none_when_all_completed(self):
        """全CCD完了後はNoneを返す"""
        ccd_refs = [make_ccd_ref("R00")]
        dispatcher = CcdDispatcher(ccd_refs)
        generator_id = GeneratorId("g-test")

        # CCDを取得
        ccd = await dispatcher.get_next_ccd(generator_id)
        assert ccd is not None

        # 完了を記録
        await dispatcher.on_ccd_completed(
            CcdName("R00"),
            make_ccd_metadata("R00"),
            generator_id,
        )

        # 次のCCDを要求するとNone
        ccd = await dispatcher.get_next_ccd(generator_id)
        assert ccd is None

    @pytest.mark.asyncio
    async def test_all_completed_event_is_set_when_all_done(self):
        """全CCD完了時にall_completedイベントがセットされる"""
        ccd_refs = [make_ccd_ref("R00"), make_ccd_ref("R01")]
        dispatcher = CcdDispatcher(ccd_refs)
        generator_id = GeneratorId("g-test")

        assert not dispatcher.all_completed.is_set()

        # 最初のCCDを取得して完了
        await dispatcher.get_next_ccd(generator_id)
        await dispatcher.on_ccd_completed(CcdName("R00"), make_ccd_metadata("R00"), generator_id)
        assert not dispatcher.all_completed.is_set()

        # 2番目のCCDを取得して完了
        await dispatcher.get_next_ccd(generator_id)
        await dispatcher.on_ccd_completed(CcdName("R01"), make_ccd_metadata("R01"), generator_id)
        assert dispatcher.all_completed.is_set()


class TestCcdDispatcherPhase2:
    """Phase 2（再割り当て）のテスト"""

    @pytest.mark.asyncio
    async def test_resubmit_after_all_submitted(self):
        """全CCDが提出された後、未完了CCDが再割り当てされる"""
        ccd_refs = [make_ccd_ref("R00"), make_ccd_ref("R01")]
        # 再submitの最小経過時間を0にしてテストを高速化
        dispatcher = CcdDispatcher(
            ccd_refs,
            resubmit_min_age_seconds=0.0,
            resubmit_max_attempts_per_ccd=2,
        )
        gen1 = GeneratorId("g-1")
        gen2 = GeneratorId("g-2")

        # Phase 1: 全CCD提出
        ccd1 = await dispatcher.get_next_ccd(gen1)
        ccd2 = await dispatcher.get_next_ccd(gen2)
        assert ccd1 is not None and ccd2 is not None

        # gen2のCCDを完了
        await dispatcher.on_ccd_completed(ccd2.ccd, make_ccd_metadata(str(ccd2.ccd)), gen2)

        # Phase 2: gen2が再度CCDを要求 → gen1の未完了CCDが再割り当て
        resubmitted = await dispatcher.get_next_ccd(gen2)
        assert resubmitted is not None
        assert resubmitted.ccd == ccd1.ccd  # gen1に割り当てられていたCCDが再割り当て

    @pytest.mark.asyncio
    async def test_resubmit_respects_min_age(self):
        """再submitはmin_age_seconds以上経過したCCDのみ対象"""
        ccd_refs = [make_ccd_ref("R00"), make_ccd_ref("R01")]
        dispatcher = CcdDispatcher(
            ccd_refs,
            resubmit_min_age_seconds=60.0,  # 60秒
            resubmit_max_attempts_per_ccd=2,
        )
        gen1 = GeneratorId("g-1")
        gen2 = GeneratorId("g-2")

        # Phase 1: 全CCD提出
        ccd1 = await dispatcher.get_next_ccd(gen1)
        ccd2 = await dispatcher.get_next_ccd(gen2)
        assert ccd1 is not None and ccd2 is not None

        # gen2のCCDを完了
        await dispatcher.on_ccd_completed(ccd2.ccd, make_ccd_metadata(str(ccd2.ccd)), gen2)

        # まだ60秒経過していないので再割り当てされない
        resubmitted = await dispatcher.get_next_ccd(gen2)
        assert resubmitted is None

    @pytest.mark.asyncio
    async def test_resubmit_respects_max_attempts(self):
        """再submitは最大回数を超えない"""
        ccd_refs = [make_ccd_ref("R00")]
        dispatcher = CcdDispatcher(
            ccd_refs,
            resubmit_min_age_seconds=0.0,
            resubmit_max_attempts_per_ccd=1,  # 最大1回の再submit
        )
        gen1 = GeneratorId("g-1")
        gen2 = GeneratorId("g-2")

        # Phase 1: CCDを提出（1回目）
        ccd = await dispatcher.get_next_ccd(gen1)
        assert ccd is not None

        # Phase 2: 再割り当て（2回目）
        resubmitted = await dispatcher.get_next_ccd(gen2)
        assert resubmitted is not None

        # 3回目は上限に達しているのでNone
        resubmitted = await dispatcher.get_next_ccd(gen1)
        assert resubmitted is None

    @pytest.mark.asyncio
    async def test_first_completion_wins(self):
        """最初に完了したGeneratorのメタデータのみ採用"""
        ccd_refs = [make_ccd_ref("R00")]
        dispatcher = CcdDispatcher(
            ccd_refs,
            resubmit_min_age_seconds=0.0,
            resubmit_max_attempts_per_ccd=2,
        )
        gen1 = GeneratorId("g-1")
        gen2 = GeneratorId("g-2")

        # Phase 1: gen1がCCDを取得
        ccd = await dispatcher.get_next_ccd(gen1)
        assert ccd is not None

        # Phase 2: gen2が同じCCDを再割り当てで取得
        await dispatcher.get_next_ccd(gen2)

        # gen2が先に完了
        metadata_gen2 = make_ccd_metadata("R00")
        await dispatcher.on_ccd_completed(CcdName("R00"), metadata_gen2, gen2)

        # gen2のメタデータが採用
        assert dispatcher.ccd_metadata_dict[CcdName("R00")] == metadata_gen2
        assert dispatcher.ccd_generator_map[CcdName("R00")] == gen2

        # gen1が後から完了しても無視
        metadata_gen1 = make_ccd_metadata("R00")
        await dispatcher.on_ccd_completed(CcdName("R00"), metadata_gen1, gen1)

        # まだgen2のメタデータ
        assert dispatcher.ccd_metadata_dict[CcdName("R00")] == metadata_gen2
        assert dispatcher.ccd_generator_map[CcdName("R00")] == gen2

    @pytest.mark.asyncio
    async def test_resubmit_disabled_when_max_attempts_zero(self):
        """max_attempts=0の場合、再submitは無効"""
        ccd_refs = [make_ccd_ref("R00"), make_ccd_ref("R01")]
        dispatcher = CcdDispatcher(
            ccd_refs,
            resubmit_min_age_seconds=0.0,
            resubmit_max_attempts_per_ccd=0,  # 再submit無効
        )
        gen1 = GeneratorId("g-1")
        gen2 = GeneratorId("g-2")

        # Phase 1: 全CCD提出
        await dispatcher.get_next_ccd(gen1)
        ccd2 = await dispatcher.get_next_ccd(gen2)
        assert ccd2 is not None

        # gen2のCCDを完了
        await dispatcher.on_ccd_completed(ccd2.ccd, make_ccd_metadata(str(ccd2.ccd)), gen2)

        # 再submitは無効なのでNone
        resubmitted = await dispatcher.get_next_ccd(gen2)
        assert resubmitted is None


class TestCcdDispatcherConcurrency:
    """並行処理のテスト"""

    @pytest.mark.asyncio
    async def test_concurrent_get_next_ccd(self):
        """複数のworkerが同時にget_next_ccdを呼んでも重複しない"""
        num_ccds = 100
        num_workers = 4
        ccd_refs = [make_ccd_ref(f"R{i:03d}") for i in range(num_ccds)]
        dispatcher = CcdDispatcher(
            ccd_refs,
            resubmit_min_age_seconds=1000.0,  # 再submitを無効化
        )

        results: list[tuple[GeneratorId, CcdName | None]] = []
        lock = asyncio.Lock()

        async def worker(gen_id: GeneratorId):
            while True:
                ccd = await dispatcher.get_next_ccd(gen_id)
                async with lock:
                    results.append((gen_id, ccd.ccd if ccd else None))
                if ccd is None:
                    break
                # 完了を記録
                await dispatcher.on_ccd_completed(
                    ccd.ccd,
                    make_ccd_metadata(str(ccd.ccd)),
                    gen_id,
                )

        # 複数workerを並行実行
        workers = [
            asyncio.create_task(worker(GeneratorId(f"g-{i}")))
            for i in range(num_workers)
        ]
        await asyncio.gather(*workers)

        # 重複なく全CCD処理
        processed_ccds = [r[1] for r in results if r[1] is not None]
        assert len(processed_ccds) == num_ccds
        assert len(set(processed_ccds)) == num_ccds  # 重複なし
