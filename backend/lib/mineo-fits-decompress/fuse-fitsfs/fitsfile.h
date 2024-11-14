#ifndef uuid_44549561_6d1b_425c_b4f2_8ed44a47f376
#define uuid_44549561_6d1b_425c_b4f2_8ed44a47f376

#include "file.h"

#include <stdint.h>


/** Options of fitsfile_open.
*/
struct FitsFileOpenOptions
{
    /** If positive, the entire image will be decoded on the first call to read()
        with this number of threads.
        If zero or negative, only necessary parts will be decoded
        on every call to read() with a single thread.
    */
    intptr_t num_threads;
};


/** Opens a FITS file.

    Parameters
    ----------
    path
        File path.
    directory
        Directory. This argument may be NULL.
    options
        Options.

    Returns
    -------
    fitsfile
        FITS file.
*/
struct IRegFile* fitsfile_open(
    char const                          *path,
    struct IDirectory                   *directory,
    struct FitsFileOpenOptions const    *options
);

/** Pseudo-posix stat() and fstatat() for FITS file.
    `stat::st_size` field is set to its uncompressed size.

    Parameters
    ----------
    pathname
        File path.
    statbuf
        Pointer to a `struct stat` instance.
    directory
        Directory. This argument may be NULL.
*/
int fitsfile_stat(const char *pathname, struct stat *statbuf, struct IDirectory *directory);

#endif /* uuid_44549561_6d1b_425c_b4f2_8ed44a47f376 */
