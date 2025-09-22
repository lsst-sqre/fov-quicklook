#ifndef uuid_60f5aeb3_e51c_47e9_8b6d_31aeed12a224
#define uuid_60f5aeb3_e51c_47e9_8b6d_31aeed12a224

#include <dirent.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>

#include <stdlib.h>


/** File (including Directory) interface
*/
struct IFile_vtbl;
struct IFile
{
    struct IFile_vtbl const *vtbl;
};

struct IFile_vtbl
{
    /** Closes the file and destructs self.
    */
    void (*close)(struct IFile *self);

    /** Calls posix fstat().

        Parameters
        ----------
        statbuf
            Pointer to an instance of struct `stat`.

        Returns
        -------
        status
            The return value of posix fstat().
    */
    int (*fstat)(struct IFile *self, struct stat *statbuf);
};


/** Regular file interface, inheriting IFile.
*/
struct IRegFile_vtbl;
struct IRegFile
{
    struct IRegFile_vtbl const *vtbl;
};

struct IRegFile_vtbl
{
    /* IFile members */

    /** Closes the file and destructs self.
    */
    void (*close)(struct IRegFile *self);

    /** Calls posix fstat().

        Parameters
        ----------
        statbuf
            Pointer to an instance of struct `stat`.

        Returns
        -------
        status
            The return value of posix fstat().
    */
    int (*fstat)(struct IRegFile *self, struct stat *statbuf);

    /* IRegFile members */

    /** Reads `size` bytes from the `offset`-th byte (zero-indexed).
        This function does not return until it reads exactly `size` bytes,
        except when EOF or an error is met.

        Parameters
        ----------
        buf
            Buffer to which to store bytes.
        size
            Size to read, in bytes
        offset
            File offset of the 0-th byte to read.

        Returns
        -------
        nread
            Number of bytes read.

        Errors
        ------
        This function sets `errno` to non-zero value before it returns
        with fewer bytes read, due to an error. This function does not set
        `errno` when it finds EOF.
    */
    size_t (*read)(struct IRegFile *self, void* buf, size_t size, size_t offset);
};

struct IDirectory;

/** Opens a regular file.

    Parameters
    ----------
    path
        File path.
    directory
        Directory. This argument may be NULL.

    Returns
    -------
    regfile
        Regular file.
*/
struct IRegFile* regfile_open(char const* path, struct IDirectory *directory);


/** Directory interface, inheriting IFile.
*/
struct IDirectory_vtbl;
struct IDirectory
{
    struct IDirectory_vtbl const *vtbl;
};

struct IDirectory_vtbl
{
    /* IFile members */

    /** Closes the file and destructs self.
    */
    void (*close)(struct IDirectory *self);

    /** Calls posix fstat().

        Parameters
        ----------
        statbuf
            Pointer to an instance of struct `stat`.

        Returns
        -------
        status
            The return value of posix fstat().
    */
    int (*fstat)(struct IDirectory *self, struct stat *statbuf);

    /* IDirectory members */

    /** Reads one `dirent` from the directory.

        Parameters
        ----------
        offset
            Offset of the `dirent` to read.
            It must be 0 for the first call to this function.

        Returns
        -------
        dirent
            Directory item.
    */
    struct dirent* (*read)(struct IDirectory *self, size_t offset);

    /** Calls posix fstatat().

        Parameters
        ----------
        pathname
            File path.
        statbuf
            Pointer to an instance of struct `stat`.

        Returns
        -------
        status
            The return value of posix fstatat().
    */
    int (*fstatat)(struct IDirectory *self, const char *pathname, struct stat *statbuf);

    /** Calls posix openat() in read mode.

        Parameters
        ----------
        pathname
            File path.

        Returns
        -------
        descriptor
            The return value of posix openat().
    */
    int (*openat)(struct IDirectory *self, const char *pathname);
};


/** Opens a directory.

    Parameters
    ----------
    path
        Directory path.

    Returns
    -------
    directory
        Directory.
*/

struct IDirectory* directory_open(char const* path);

#endif /* uuid_60f5aeb3_e51c_47e9_8b6d_31aeed12a224 */
