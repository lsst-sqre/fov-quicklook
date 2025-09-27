from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal, cast

from quicklook.config import config
from quicklook.generator.job import Job
from quicklook.types import CcdName, Progress

JobPhase = Literal['generate_single_fits_tiles', 'merge_tiles', 'transfer_tiles']

GeneratorId = str


@dataclass
class JobStatus:
    job: Job

    generate_single_fits_tiles: dict[CcdName, Progress] = field(default_factory=dict)
    merge_tiles: dict[GeneratorId, Progress] = field(default_factory=dict)
    transfer_tiles: dict[GeneratorId, Progress] = field(default_factory=dict)

    @classmethod
    @lru_cache(config.max_job)
    def from_job(cls, job: Job) -> 'JobStatus':
        return cls(job)

    def notify(self):
        # display_status(self)
        ...


def display_status(status: JobStatus):
    from shutil import get_terminal_size
    import sys

    # Clear the terminal and move the cursor to the top-left corner.
    sys.stdout.write('\033[2J\033[H')
    sys.stdout.flush()

    terminal_width = get_terminal_size(fallback=(120, 24)).columns
    bar_width = min(60, max(10, terminal_width - 36))

    def format_progress(label: str, progress: Progress) -> list[str]:
        total = progress.total
        count = progress.count
        clamped_total = total if total > 0 else 0
        ratio = 0.0 if clamped_total == 0 else min(1.0, max(0.0, count / clamped_total))
        filled = int(bar_width * ratio)
        bar = f"[{'#' * filled}{'.' * (bar_width - filled)}]"

        if clamped_total == 0:
            percent_text = '  N/A '
            total_text = f'({count}/-)'
        else:
            percent_text = f'{ratio * 100:6.2f}%'
            total_text = f'({count}/{clamped_total})'

        return [
            f'{label}',
            f'  {bar} {percent_text} {total_text}',
        ]

    def section(title: str, data: Mapping[str, Progress]) -> list[str]:
        output: list[str] = [title, '-' * len(title)]
        if not data:
            output.append('  (no entries)')
            return output

        total_sum = sum(progress.total for progress in data.values())
        count_sum = sum(progress.count for progress in data.values())
        if total_sum > 0:
            ratio = min(1.0, max(0.0, count_sum / total_sum))
            percent_text = f'{ratio * 100:6.2f}%'
            summary = f'  summary: {percent_text} ({count_sum}/{total_sum})'
        else:
            summary = f'  summary:  N/A  ({count_sum}/-)'
        output.append(summary)

        for key, progress in sorted(data.items(), key=lambda item: str(item[0])):
            output.extend(format_progress(f'• {key}', progress))
        return output

    lines: list[str] = []
    header = f'Job Status for {status.job.id}'
    visit_line = f'Visit: {status.job.visit}'
    separator = '=' * min(terminal_width, max(len(header), len(visit_line)))

    lines.append(header)
    lines.append(visit_line)
    lines.append(separator)

    sections = (
        ('Generate FITS tiles', status.generate_single_fits_tiles),
        ('Merge tiles', status.merge_tiles),
        ('Transfer tiles', status.transfer_tiles),
    )

    for title, data in sections:
        lines.extend(section(title, cast(Mapping[str, Progress], data)))
        lines.append('')

    sys.stdout.write('\n'.join(lines).rstrip() + '\n')
    sys.stdout.flush()
