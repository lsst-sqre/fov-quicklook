from __future__ import annotations

import io
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import numpy
from astropy.io import fits
from PIL import Image

from quicklook.tileinfo import ccds_by_name
from quicklook.types import CcdName

ASSET_DIR = Path(__file__).parent / "assets"
CENTRAL_REVIEW_CCD_NAMES: tuple[CcdName, ...] = (
    CcdName("R22_S00"),
    CcdName("R22_S01"),
    CcdName("R22_S02"),
    CcdName("R22_S10"),
    CcdName("R22_S11"),
    CcdName("R22_S12"),
    CcdName("R22_S20"),
    CcdName("R22_S21"),
    CcdName("R22_S22"),
)
CENTRAL_REVIEW_CCD_SET = frozenset(CENTRAL_REVIEW_CCD_NAMES)


class LSSTCam:
    """Minimal instrument placeholder for Butler review-app fixtures."""


@dataclass(frozen=True)
class FilterChannelMapping:
    image_name: str
    channel_index: int
    signal_scale: float
    bias_level: float


FILTER_CHANNEL_MAPPINGS: dict[str, FilterChannelMapping] = {
    "u": FilterChannelMapping("haru.jpeg", 2, 180.0, 1180.0),
    "g": FilterChannelMapping("haru.jpeg", 1, 190.0, 1195.0),
    "r": FilterChannelMapping("IMG_9685.jpeg", 0, 185.0, 1210.0),
    "i": FilterChannelMapping("IMG_9685.jpeg", 1, 175.0, 1205.0),
    "z": FilterChannelMapping("IMG_9685.jpeg", 2, 165.0, 1190.0),
    "y": FilterChannelMapping("haru.jpeg", 0, 170.0, 1185.0),
}

NOISE_TILE_SIZE = 512


def render_virtual_raw_fits_bytes(
    *,
    ccd_name: CcdName,
    exposure_id: int,
    day_obs: int,
    physical_filter: str,
    obs_id: str,
) -> bytes:
    science_pixels = render_virtual_science_pixels(
        ccd_name=ccd_name,
        exposure_id=exposure_id,
        physical_filter=physical_filter,
    )
    height, width = science_pixels.shape
    mapping = filter_channel_mapping(physical_filter)
    overscan = mapping.bias_level + _overscan_pattern(
        height=height + 1,
        width=width + 1,
        ccd_name=ccd_name,
        exposure_id=exposure_id,
        suffix="overscan",
    )

    raw = overscan.astype(numpy.float32, copy=True)
    raw[:height, :width] = mapping.bias_level + science_pixels

    raft, slot = str(ccd_name).split("_")
    bbox = ccds_by_name()[ccd_name].bbox

    primary = fits.PrimaryHDU()
    primary.header["RAFTBAY"] = raft
    primary.header["CCDSLOT"] = slot
    primary.header["OBSID"] = obs_id
    primary.header["DAYOBS"] = day_obs
    primary.header["FILTER"] = physical_filter

    segment = fits.ImageHDU(data=raw, name="Segment00")
    segment.header["DATASEC"] = f"[1:{width},1:{height}]"
    segment.header["PC1_1E"] = 1.0
    segment.header["PC1_2E"] = 0.0
    segment.header["PC2_1E"] = 0.0
    segment.header["PC2_2E"] = 1.0
    segment.header["CRVAL1E"] = float(bbox.minx - 1)
    segment.header["CRVAL2E"] = float(bbox.miny - 1)

    with io.BytesIO() as buf:
        fits.HDUList([primary, segment]).writeto(buf)
        return buf.getvalue()


def render_virtual_science_pixels(
    *,
    ccd_name: CcdName,
    exposure_id: int,
    physical_filter: str,
) -> numpy.ndarray:
    bbox = ccds_by_name()[ccd_name].bbox
    height = int(bbox.maxy - bbox.miny) + 1
    width = int(bbox.maxx - bbox.minx) + 1
    base_signal = _project_attachment_channel(
        ccd_name=ccd_name,
        physical_filter=physical_filter,
    )
    shift_y, shift_x = _exposure_roll_offsets(exposure_id)
    signal = numpy.roll(base_signal, shift=(shift_y, shift_x), axis=(0, 1))
    noise = _science_noise(
        height=height,
        width=width,
        ccd_name=ccd_name,
        exposure_id=exposure_id,
        physical_filter=physical_filter,
    )
    return signal + noise


def filter_channel_mapping(physical_filter: str) -> FilterChannelMapping:
    return FILTER_CHANNEL_MAPPINGS.get(physical_filter, FILTER_CHANNEL_MAPPINGS["r"])


def review_projection_ccd_names() -> tuple[CcdName, ...]:
    return CENTRAL_REVIEW_CCD_NAMES


def _exposure_roll_offsets(exposure_id: int) -> tuple[int, int]:
    return (
        ((exposure_id * 17) % 29) - 14,
        ((exposure_id * 23) % 31) - 15,
    )


def _project_attachment_channel(*, ccd_name: CcdName, physical_filter: str) -> numpy.ndarray:
    bbox = ccds_by_name()[ccd_name].bbox
    mapping = filter_channel_mapping(physical_filter)
    channel = _attachment_channel(mapping.image_name, mapping.channel_index)
    width = int(bbox.maxx - bbox.minx) + 1
    height = int(bbox.maxy - bbox.miny) + 1
    projection_minx, projection_maxx, projection_miny, projection_maxy = _projection_bounds_for_ccd(ccd_name)
    src_height, src_width = channel.shape
    x_scale = (src_width - 1) / max(projection_maxx - projection_minx, 1.0)
    y_scale = (src_height - 1) / max(projection_maxy - projection_miny, 1.0)
    x0 = (bbox.minx - projection_minx) * x_scale
    x1 = (bbox.maxx - projection_minx) * x_scale
    y0 = (bbox.miny - projection_miny) * y_scale
    y1 = (bbox.maxy - projection_miny) * y_scale
    sampled = _resample_channel_region(channel, x0=x0, x1=x1, y0=y0, y1=y1, width=width, height=height)
    centered = sampled - sampled.mean(dtype=numpy.float64)
    return centered.astype(numpy.float32) * (mapping.signal_scale / 255.0)


def _projection_bounds_for_ccd(ccd_name: CcdName) -> tuple[float, float, float, float]:
    if ccd_name in CENTRAL_REVIEW_CCD_SET:
        return _central_projection_bounds()

    bbox = ccds_by_name()[ccd_name].bbox
    return float(bbox.minx), float(bbox.maxx), float(bbox.miny), float(bbox.maxy)


@cache
def _central_projection_bounds() -> tuple[float, float, float, float]:
    bboxes = [ccds_by_name()[ccd_name].bbox for ccd_name in CENTRAL_REVIEW_CCD_NAMES]
    return (
        float(min(bbox.minx for bbox in bboxes)),
        float(max(bbox.maxx for bbox in bboxes)),
        float(min(bbox.miny for bbox in bboxes)),
        float(max(bbox.maxy for bbox in bboxes)),
    )


def _resample_channel_region(
    channel: numpy.ndarray,
    *,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    width: int,
    height: int,
) -> numpy.ndarray:
    src_height, src_width = channel.shape
    x_coords = numpy.clip(numpy.linspace(x0, x1, num=width, dtype=numpy.float32), 0, src_width - 1)
    y_coords = numpy.clip(numpy.linspace(y0, y1, num=height, dtype=numpy.float32), 0, src_height - 1)

    x_floor = numpy.floor(x_coords).astype(numpy.int32)
    y_floor = numpy.floor(y_coords).astype(numpy.int32)
    x_ceil = numpy.clip(x_floor + 1, 0, src_width - 1)
    y_ceil = numpy.clip(y_floor + 1, 0, src_height - 1)
    x_weight = (x_coords - x_floor).astype(numpy.float32)
    y_weight = (y_coords - y_floor).astype(numpy.float32)

    top_left = channel[y_floor[:, None], x_floor[None, :]]
    top_right = channel[y_floor[:, None], x_ceil[None, :]]
    bottom_left = channel[y_ceil[:, None], x_floor[None, :]]
    bottom_right = channel[y_ceil[:, None], x_ceil[None, :]]

    top = top_left * (1.0 - x_weight[None, :]) + top_right * x_weight[None, :]
    bottom = bottom_left * (1.0 - x_weight[None, :]) + bottom_right * x_weight[None, :]
    return top * (1.0 - y_weight[:, None]) + bottom * y_weight[:, None]


@cache
def _attachment_channel(image_name: str, channel_index: int) -> numpy.ndarray:
    path = ASSET_DIR / image_name
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        arr = numpy.asarray(rgb, dtype=numpy.float32)
    return _rotate_channel_180(arr[:, :, channel_index])


def _rotate_channel_180(channel: numpy.ndarray) -> numpy.ndarray:
    return numpy.flip(channel, axis=(0, 1)).copy()


def _science_noise(
    *,
    height: int,
    width: int,
    ccd_name: CcdName,
    exposure_id: int,
    physical_filter: str,
) -> numpy.ndarray:
    tile = _noise_tile(physical_filter)
    offset_y = (exposure_id * 13 + len(str(ccd_name)) * 5) % NOISE_TILE_SIZE
    offset_x = (exposure_id * 19 + sum(ord(ch) for ch in str(ccd_name))) % NOISE_TILE_SIZE
    y_index = (numpy.arange(height) + offset_y) % NOISE_TILE_SIZE
    x_index = (numpy.arange(width) + offset_x) % NOISE_TILE_SIZE
    return tile[y_index[:, None], x_index[None, :]]


def _overscan_pattern(
    *,
    height: int,
    width: int,
    ccd_name: CcdName,
    exposure_id: int,
    suffix: str,
) -> numpy.ndarray:
    tile = _noise_tile(f"{ccd_name}:{suffix}")
    offset_y = (exposure_id * 7 + sum(ord(ch) for ch in str(ccd_name))) % NOISE_TILE_SIZE
    offset_x = (exposure_id * 11 + len(suffix) * 17) % NOISE_TILE_SIZE
    y_index = (numpy.arange(height) + offset_y) % NOISE_TILE_SIZE
    x_index = (numpy.arange(width) + offset_x) % NOISE_TILE_SIZE
    return tile[y_index[:, None], x_index[None, :]] * 0.15


@cache
def _noise_tile(key: str) -> numpy.ndarray:
    seed = sum((index + 1) * ord(char) for index, char in enumerate(key))
    rng = numpy.random.default_rng(seed)
    return rng.normal(loc=0.0, scale=8.0, size=(NOISE_TILE_SIZE, NOISE_TILE_SIZE)).astype(numpy.float32)
