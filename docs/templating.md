# Templating System

`fov-quicklook` provides a templating feature that performs text substitution based on metadata. This functionality allows easy generation of URLs, scripts, and other text outputs.

## Basic Syntax

When `%(field_name)` is written in a template, it is replaced with the corresponding metadata value.

Examples:
```
%(uuid)       → "919c991d-706d-50f1-bd8a-aee69b457ba4"
%(ccd_name)   → "R13_S01"
%(exposure)   → 2025051500271
```

## Available Fields

Fields from the `DataSourceCcdMetadata` class are available in templates:

| Field | Type | Description | Example |
|------------|------|------|------|
| ccd_name | string | CCD name | "R20_S00" |
| detector | number | Detector ID | 127 |
| exposure | number | Exposure number | 2025052000278 |
| day_obs | number | Observation date (YYYYMMDD format) | 20250521 |
| uuid | string | Unique identifier | "919c991d-706d-50f1-bd8a-aee69b457ba4" |
| dataType | string | Legacy scope identifier derived from visit.id | "embargo:LSSTCam!-raw!-all:raw" |

## Pipeline Feature

A pipeline feature is available for processing values. Use the format `%(field_name|transformation_function)`.

### Available Transformation Functions

#### iso8601
Converts dates to ISO8601 format.

```
%(day_obs|iso8601)  → 2025-05-16  (original value: 20250516)
```

#### sequence
Gets the last 5 digits of a number (modulo 100000).

```
%(exposure|sequence)  → 271  (original value: 2025051500271)
```

#### zeropadding(width)
Zero-pads a number to the specified width.

```
%(exposure|sequence|zeropadding(8))  → 00000271
```

## Pipeline Chaining

Multiple pipelines can be chained together.

```
%(day_obs|iso8601)                      → 2025-05-16
%(exposure|sequence)                    → 271
%(exposure|sequence|zeropadding(8))     → 00000271
```

## Usage Examples

### Basic Example
```
UUID: %(uuid)
CCD: %(ccd_name), ID: %(detector)
```

### Butler Script Generation
```
from lsst.daf.butler import Butler
butler = Butler('reviewapp-ci')
ref = butler.get_dataset('%(uuid)')
if ref is None:
    raise LookupError('Dataset was not found')
data = butler.get(ref)
```

The UUID-based form selects the exact CCD dataset and does not depend on the
dataset type or on whether its quicklook dimension is `exposure` or `visit`.

### URL Generation
```
https://usdf-rsp.slac.stanford.edu/rubintv/summit-usdf/lsstcam/event?channel_name=calexp_mosaic&date_str=%(day_obs|iso8601)&seq_num=%(exposure|sequence)
```

This would generate a URL with the date `2025-05-21` and sequence number `278` (based on day_obs: 20250521 and exposure: 2025052000278):
```
https://usdf-rsp.slac.stanford.edu/rubintv/summit-usdf/lsstcam/event?channel_name=calexp_mosaic&date_str=2025-05-21&seq_num=278
```
