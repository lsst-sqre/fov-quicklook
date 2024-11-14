#ifndef uuud_f27eedab_0ee0_4e1b_b607_03e409e60c2c
#define uuud_f27eedab_0ee0_4e1b_b607_03e409e60c2c

#include <stdint.h>

/* This header file brings us Z_OK, Z_DATA_ERROR, etc. */
#include <zlib.h>

/** Uncompresses gzip stream (32bit).

    Parameters
    ----------
    dest
        Destination buffer.
    destlen
        `*destlen` must be set to the size of `dest` buffer before calling
        this function. `*destlen`  will be set to the size of the uncompressed
        data on return.
    source
        Compressed data.
    sourcelen
        Length of the compressed data.

    Returns
    -------
    status
        Z_OK on success.
*/
int inflate_gzip_32(
    uint8_t       * restrict dest,
    int32_t       * restrict destlen,
    uint8_t const * restrict source,
    int32_t        sourcelen
);

/** Uncompresses gzip stream (64bit).

    Parameters
    ----------
    dest
        Destination buffer.
    destlen
        `*destlen` must be set to the size of `dest` buffer before calling
        this function. `*destlen`  will be set to the size of the uncompressed
        data on return.
    source
        Compressed data.
    sourcelen
        Length of the compressed data.

    Returns
    -------
    status
        Z_OK on success.
*/
int inflate_gzip_64(
    uint8_t       * restrict dest,
    int64_t       * restrict destlen,
    uint8_t const * restrict source,
    int64_t        sourcelen
);

#endif /* uuud_f27eedab_0ee0_4e1b_b607_03e409e60c2c */
