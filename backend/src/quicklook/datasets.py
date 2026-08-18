from collections.abc import Iterable, Mapping
from typing import Literal

from pydantic import BaseModel


class Dataset(BaseModel):
    dataset_type: str
    quicklook_dimension: str
    default_order_by: list[str]
    order_by_fields: list[str]
    partial: bool
    preprocess_kind: Literal['raw', 'image']
    exclude_corner_rafts: bool = False

    def quicklook_dimensions(self, required_dimensions: Iterable[str] | None = None) -> list[str]:
        if required_dimensions is None:
            return [self.quicklook_dimension]
        dimensions = sorted(set(required_dimensions) - {'detector', 'instrument'})
        if not dimensions:
            raise ValueError(f'{self.dataset_type} must include at least one quicklook dimension')
        return dimensions

    def build_visit_dimensions(
        self,
        data_id: Mapping[str, object],
        *,
        required_dimensions: Iterable[str] | None = None,
    ) -> dict[str, str]:
        return {
            key: str(data_id[key])
            for key in self.quicklook_dimensions(required_dimensions)
            if key in data_id and data_id[key] is not None
        }


COMMON_ORDER_BY_FIELDS = [
    'day_obs',
    'exposure',
    'visit',
    'obs_id',
    'physical_filter',
    'exposure_time',
    'science_program',
    'observation_type',
    'observation_reason',
    'target_name',
]


DEFAULT_DATASETS = {
    'raw': Dataset(
        dataset_type='raw',
        quicklook_dimension='exposure',
        default_order_by=['-exposure'],
        order_by_fields=COMMON_ORDER_BY_FIELDS,
        partial=False,
        preprocess_kind='raw',
    ),
    'post_isr_image': Dataset(
        dataset_type='post_isr_image',
        quicklook_dimension='exposure',
        default_order_by=['-exposure'],
        order_by_fields=COMMON_ORDER_BY_FIELDS,
        partial=True,
        preprocess_kind='image',
        exclude_corner_rafts=True,
    ),
    'difference_image': Dataset(
        dataset_type='difference_image',
        quicklook_dimension='visit',
        default_order_by=['-visit'],
        order_by_fields=COMMON_ORDER_BY_FIELDS,
        partial=True,
        preprocess_kind='image',
        exclude_corner_rafts=True,
    ),
    'preliminary_visit_image': Dataset(
        dataset_type='preliminary_visit_image',
        quicklook_dimension='visit',
        default_order_by=['-visit'],
        order_by_fields=COMMON_ORDER_BY_FIELDS,
        partial=True,
        preprocess_kind='image',
    ),
    'calexp': Dataset(
        dataset_type='calexp',
        quicklook_dimension='exposure',
        default_order_by=['-exposure'],
        order_by_fields=COMMON_ORDER_BY_FIELDS,
        partial=True,
        preprocess_kind='image',
    ),
}


def get_dataset(dataset_type: str) -> Dataset:
    if dataset_type in DEFAULT_DATASETS:
        return DEFAULT_DATASETS[dataset_type]
    return Dataset(
        dataset_type=dataset_type,
        quicklook_dimension='exposure',
        default_order_by=['-exposure'],
        order_by_fields=COMMON_ORDER_BY_FIELDS,
        partial=True,
        preprocess_kind='image',
    )
