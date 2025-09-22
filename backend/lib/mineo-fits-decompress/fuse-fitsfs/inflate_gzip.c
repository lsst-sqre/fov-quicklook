#include "inflate_gzip.h"

#include <zlib.h>


/* These implementations are plagiarized from zlib's "uncompress()"
*/

int inflate_gzip_32(
    uint8_t       * restrict dest,
    int32_t       * restrict destlen,
    uint8_t const * restrict source,
    int32_t        sourcelen
){
    z_stream stream = {0};
    int err;
    uint32_t left;
    Byte buf[1];    /* for detection of incomplete stream when *destlen == 0 */

    if (*destlen) {
        left = *destlen;
        *destlen = 0;
    }
    else {
        left = 1;
        dest = buf;
    }

    stream.next_in = (z_const Bytef *)source;
    stream.avail_in = sourcelen;
    stream.next_out = dest;
    stream.avail_out = left;

    err = inflateInit2(&stream, 31);
    if (err != Z_OK) return err;

    err = inflate(&stream, Z_FINISH);

    if (dest != buf){
        *destlen = stream.total_out;
    }
    else if (stream.total_out && err == Z_BUF_ERROR){
        left = 1;
    }

    inflateEnd(&stream);
    return err == Z_STREAM_END ? Z_OK :
           err == Z_NEED_DICT ? Z_DATA_ERROR  :
           err == Z_BUF_ERROR && left + stream.avail_out ? Z_DATA_ERROR :
           err;
}


int inflate_gzip_64(
    uint8_t       * restrict dest,
    int64_t       * restrict destlen,
    uint8_t const * restrict source,
    int64_t        sourcelen
){
    z_stream stream = {0};
    int err;
    const uInt max = (uInt)-1;
    uint64_t len, left;
    Byte buf[1];    /* for detection of incomplete stream when *destlen == 0 */

    len = sourcelen;
    if (*destlen) {
        left = *destlen;
        *destlen = 0;
    }
    else {
        left = 1;
        dest = buf;
    }

    stream.next_in = (z_const Bytef *)source;
    stream.avail_in = 0;

    err = inflateInit2(&stream, 31);
    if(err != Z_OK) return err;

    stream.next_out = dest;
    stream.avail_out = 0;

    do{
        if (stream.avail_out == 0) {
            stream.avail_out = left > (uint64_t)max ? max : (uInt)left;
            left -= stream.avail_out;
        }
        if (stream.avail_in == 0) {
            stream.avail_in = len > (uint64_t)max ? max : (uInt)len;
            len -= stream.avail_in;
        }
        err = inflate(&stream, Z_NO_FLUSH);
    }
    while (err == Z_OK);

    if(dest != buf){
        *destlen = stream.total_out;
    }
    else if(stream.total_out && err == Z_BUF_ERROR){
        left = 1;
    }

    inflateEnd(&stream);
    return err == Z_STREAM_END ? Z_OK :
           err == Z_NEED_DICT ? Z_DATA_ERROR  :
           err == Z_BUF_ERROR && left + stream.avail_out ? Z_DATA_ERROR :
           err;
}
