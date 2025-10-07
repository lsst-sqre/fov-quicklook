import sys
from collections.abc import Mapping
from dataclasses import dataclass
from shutil import get_terminal_size
from typing import cast

from quicklook.job.status import JobStatus
from quicklook.job.watcher import JobWatcher
from quicklook.types import Progress
from quicklook.utils.throttle import throttle


@dataclass
class JobStatusPrinter:  # pragma: no cover
    n_columns: int = 4

    @throttle(0.5)
    def __call__(self, status: JobStatus | JobWatcher, *, columns: int | None = None):
        self._display_status(status, columns=columns)

    def flush(self):
        """Flush any pending throttled calls."""
        self.__call__.flush()  # type: ignore

    def _display_status(self, status: JobStatus | JobWatcher, *, columns: int | None = None):
        n_columns = self.n_columns

        # Clear the terminal and move the cursor to the top-left corner.
        sys.stdout.write('\033[2J\033[H')
        sys.stdout.flush()

        terminal_width = get_terminal_size(fallback=(120, 24)).columns
        indent = '  '
        requested_columns = columns if columns and columns > 0 else n_columns
        requested_columns = max(1, requested_columns)
        minimal_column_width = 28

        available_width = max(1, terminal_width - len(indent))

        def format_progress(label: str, progress: Progress, width: int) -> str:
            total = progress.total
            count = progress.count
            clamped_total = total if total > 0 else 0
            ratio = 0.0 if clamped_total == 0 else min(1.0, max(0.0, count / clamped_total))

            if clamped_total == 0:
                percent_text = '  N/A '
                total_text = f'({count}/-)'
            else:
                percent_text = f'{ratio * 100:6.2f}%'
                total_text = f'({count}/{clamped_total})'

            label_text = f'• {label}'

            other_width = len(percent_text) + len(total_text) + 5
            available = max(1, width - other_width)

            min_label_reserved = 4
            available_for_bar = max(1, available - min_label_reserved)
            preferred_bar = min(24, max(8, available * 2 // 3))
            bar_width = max(1, min(preferred_bar, available_for_bar))
            label_width = max(1, available - bar_width)

            if len(label_text) > label_width:
                ellipsis_reserved = 1 if label_width > 1 else 0
                label_text = label_text[: label_width - ellipsis_reserved]
                if ellipsis_reserved:
                    label_text += '…'

            label_field = label_text.ljust(label_width)

            bar_fill = min(bar_width, max(0, int(bar_width * ratio)))
            bar_empty = bar_width - bar_fill
            bar = f"[{'#' * bar_fill}{'.' * bar_empty}]"

            return f"{label_field} {bar} {percent_text} {total_text}".ljust(width)

        def determine_layout(entry_count: int) -> tuple[int, list[int]]:
            if entry_count <= 0:
                return 0, []

            columns_to_use = min(entry_count, requested_columns)
            while columns_to_use > 1 and available_width // columns_to_use < minimal_column_width:
                columns_to_use -= 1

            columns_to_use = max(1, columns_to_use)
            base_width = max(1, available_width // columns_to_use)
            column_widths = [base_width] * columns_to_use
            leftover = available_width - base_width * columns_to_use
            for index in range(leftover):
                column_widths[index] += 1

            return columns_to_use, column_widths

        def render_section_rows(items: list[tuple[str, Progress]]) -> list[str]:
            entry_count = len(items)
            if entry_count == 0:
                return []

            columns_to_use, column_widths = determine_layout(entry_count)
            rows: list[str] = []
            buffer: list[str] = []
            for index, (label, progress) in enumerate(items):
                column_index = index % columns_to_use
                width = column_widths[column_index]
                buffer.append(format_progress(label, progress, width))
                if column_index == columns_to_use - 1:
                    rows.append(indent + ''.join(buffer))
                    buffer = []

            if buffer:
                start_column = len(buffer)
                for column_index in range(start_column, columns_to_use):
                    width = column_widths[column_index]
                    buffer.append(' ' * width)
                rows.append(indent + ''.join(buffer))

            return rows

        def section(title: str, data: Mapping[str, Progress]) -> list[str]:
            output: list[str] = [title, '-' * len(title)]
            if not data:
                output.append(f'{indent}(no entries)')
                return output

            total_sum = sum(progress.total for progress in data.values())
            count_sum = sum(progress.count for progress in data.values())
            if total_sum > 0:
                ratio = min(1.0, max(0.0, count_sum / total_sum))
                percent_text = f'{ratio * 100:6.2f}%'
                summary = f'{indent}summary: {percent_text} ({count_sum}/{total_sum})'
            else:
                summary = f'{indent}summary:  N/A  ({count_sum}/-)'
            output.append(summary)

            sorted_entries = sorted(((str(key), progress) for key, progress in data.items()), key=lambda item: item[0])
            output.extend(render_section_rows(sorted_entries))
            return output

        lines: list[str] = []
        job_status = status if isinstance(status, JobStatus) else status.job.status
        header = f'Job Status for {job_status.job.id}'
        visit_line = f'Visit: {job_status.job.visit}'
        separator = '=' * min(terminal_width, max(len(header), len(visit_line)))

        lines.append(header)
        lines.append(visit_line)
        lines.append(separator)

        sections = (
            ('Generate FITS tiles', job_status.generate_single_fits_tiles),
            ('Merge tiles', job_status.merge_tiles),
            ('Transfer tiles', job_status.transfer_tiles),
        )

        for title, data in sections:
            lines.extend(section(title, cast(Mapping[str, Progress], data)))
            lines.append('')

        sys.stdout.write('\n'.join(lines).rstrip() + '\n')
        sys.stdout.flush()


display_status = JobStatusPrinter()
