from typing import Any

from quicklook.datasets import get_dataset
from quicklook.datasource.types import VisitEntry
from quicklook.types import VisitName


def sort_visit_entries(
    entries: list[VisitEntry],
    *,
    dataset_type: str,
    order_by: str | None,
    reverse: bool | None,
) -> list[VisitEntry]:
    default = get_dataset(dataset_type).default_order_by[0]
    selected_field = order_by or default.removeprefix('-')
    selected_reverse = default.startswith('-') if selected_field == default.removeprefix('-') else False
    if reverse:
        selected_reverse = not selected_reverse
    return sorted(
        entries,
        key=lambda entry: (_visit_entry_sort_value(entry, selected_field), entry.display_id),
        reverse=selected_reverse,
    )


def _visit_entry_sort_value(entry: VisitEntry, field: str) -> Any:
    match field:
        case 'exposure' | 'visit':
            visit = VisitName(entry.id)
            value = visit.dimensions.get(field)
            return -1 if value is None else int(value)
        case _:
            return getattr(entry, field)
