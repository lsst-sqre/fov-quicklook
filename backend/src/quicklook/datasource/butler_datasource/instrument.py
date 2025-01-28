from dataclasses import dataclass
from functools import cache
from pathlib import Path


@dataclass
class Instrument:
    name: str
    detector_2_ccd: dict[int, str]
    ccd_2_detector: dict[str, int]

    @classmethod
    def get(cls, instrument_name: str):
        return cls._load_instruments()[instrument_name]

    @classmethod
    @cache
    def _load_instruments(cls) -> dict[str, 'Instrument']:
        # ccd-name-map.txt は
        # butler query-dimension-records embargo detector > ccd-name-map.txt
        # で作成できる。

        @dataclass
        class Line:
            instrument: str
            id: str
            full_name: str
            name_in_raft: str
            raft: str
            purpose: str

            @property
            def ccd_name(self):
                return f'{self.raft}_{self.name_in_raft}'

            @classmethod
            def from_line(cls, line: str) -> 'Line':
                return cls(*line.split())

        map_def = Path(__file__).parent / "ccd-name-map.txt"
        lines = map_def.read_text().splitlines()
        assert lines[0].split() == 'instrument   id full_name name_in_raft raft  purpose'.split()
        instruments: dict[str, Instrument] = {}

        entries = (Line.from_line(line) for line in lines[2:])
        for entry in entries:
            if entry.instrument not in instruments:
                instruments[entry.instrument] = Instrument(
                    name=entry.instrument,
                    detector_2_ccd={},
                    ccd_2_detector={},
                )
            instruments[entry.instrument].detector_2_ccd[int(entry.id)] = entry.ccd_name
            instruments[entry.instrument].ccd_2_detector[entry.ccd_name] = int(entry.id)

        return instruments
