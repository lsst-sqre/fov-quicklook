#include "file.h"
#include "common.h"

#include <pthread.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>

#include <errno.h>
#include <stdint.h>
#include <stdio.h>


/* CRegFile: Regular file class
*/

struct CRegFile
{
    struct IRegFile iface;
    int             fd;
};


static void CRegFile_close(struct IRegFile *self);
static int CRegFile_fstat(struct IRegFile *self, struct stat *statbuf);
static size_t CRegFile_read(struct IRegFile *self, void* buf, size_t size, size_t offset);

static struct IRegFile_vtbl const CRegFile_vtbl = {
    .close = CRegFile_close,
    .fstat = CRegFile_fstat,
    .read =  CRegFile_read,
};


struct IRegFile* regfile_open(char const* path, struct IDirectory *directory)
{
    NEW_PTR(selfc, struct CRegFile);
    if(!selfc){
        errno = ENOMEM;
        return NULL;
    }

    selfc->iface.vtbl = &CRegFile_vtbl;
    if(directory){
        selfc->fd = directory->vtbl->openat(directory, path);
    }
    else{
        selfc->fd = open(path, O_RDONLY | O_CLOEXEC);
    }
    if(-1 == selfc->fd){
        free(selfc);
        if(!errno) errno = ENOENT;
        return NULL;
    }

    return (struct IRegFile*)selfc;
}


static void CRegFile_close(struct IRegFile *self)
{
    struct CRegFile* selfc = (struct CRegFile*)self;

    if(!selfc) return;

    int fd = selfc->fd;
    selfc->fd = -1;
    if(-1 != fd){
        close(fd);
    }

    free(selfc);
}


static int CRegFile_fstat(struct IRegFile *self, struct stat *statbuf)
{
    struct CRegFile* selfc = (struct CRegFile*)self;

    return fstat(selfc->fd, statbuf);
}


static size_t CRegFile_read(struct IRegFile *self, void* buf, size_t size, size_t offset)
{
    struct CRegFile* selfc = (struct CRegFile*)self;

    size_t const msb = ~((size_t)SIZE_MAX >> (size_t)1);
    if(msb & (size | offset | (offset + size))){
        errno = EINVAL;
        return 0;
    }

    size_t nread = 0;

    while(size > 0){
        errno = 0;
        ssize_t len = pread(selfc->fd, buf, size, offset);
        if(len == 0){
            break;
        }
        else if(len == -1){
            if(errno == EINTR){
                continue;
            }
            else{
                break;
            }
        }
        else{
            offset += len;
            buf = (char*)buf + len;
            nread += len;
            size -= len;
        }
    }

    return nread;
}


/* CDirectory: Directory class
*/

struct CDirectory
{
    struct IDirectory   iface;
    DIR                 *dirp;
    /* Previous entry */
    struct dirent       *entry;
    /* Offset of self->entry.
        Because self->entry->d_off is the offset of its next entry,
        we have to keep track of this for ourselves.
    */
    size_t              offset;

    pthread_mutex_t     mutex;
};


static void CDirectory_close(struct IDirectory *self);
static int CDirectory_fstat(struct IDirectory *self, struct stat *statbuf);
static struct dirent* CDirectory_read(struct IDirectory *self, size_t offset);
static int CDirectory_fstatat(struct IDirectory *self, const char *pathname, struct stat *statbuf);
static int CDirectory_openat(struct IDirectory *self, const char *pathname);

static struct IDirectory_vtbl const CDirectory_vtbl = {
    .close = CDirectory_close,
    .fstat = CDirectory_fstat,
    .read = CDirectory_read,
    .fstatat = CDirectory_fstatat,
    .openat = CDirectory_openat,
};


struct IDirectory* directory_open(char const* path)
{
    NEW_PTR(selfc, struct CDirectory);
    if(!selfc){
        errno = ENOMEM;
        return NULL;
    }

    selfc->iface.vtbl = &CDirectory_vtbl;

    selfc->dirp = opendir(path);
    if(!selfc->dirp){
        free(selfc);
        if(!errno) errno = ENOENT;
        return NULL;
    }

    selfc->entry = NULL;
    selfc->offset = 0;

    pthread_mutex_init(&selfc->mutex, NULL);

    return (struct IDirectory*)selfc;
}


static void CDirectory_close(struct IDirectory *self)
{
    struct CDirectory* selfc = (struct CDirectory*)self;

    if(!selfc) return;

    pthread_mutex_destroy(&selfc->mutex);

    DIR* dirp = selfc->dirp;
    selfc->dirp = NULL;
    if(dirp){
        closedir(dirp);
    }

    free(selfc);
}


static int CDirectory_fstat(struct IDirectory *self, struct stat *statbuf)
{
    struct CDirectory* selfc = (struct CDirectory*)self;

    return fstat(dirfd(selfc->dirp), statbuf);
}


static struct dirent* CDirectory_read(struct IDirectory *self, size_t offset)
{
    struct CDirectory* selfc = (struct CDirectory*)self;

    pthread_mutex_lock(&selfc->mutex);
    do {
        if(selfc->entry && selfc->offset == offset){
            /* Just use the current selfc->entry */
            break;
        }

        if(selfc->entry && selfc->entry->d_off == offset){
            /* Need not seeking */;
        }
        else if(offset){
            seekdir(selfc->dirp, offset) /* -> void */;
        }
        else if(selfc->entry){
            rewinddir(selfc->dirp) /* -> void */;
        }

        selfc->offset = offset;
        selfc->entry = readdir(selfc->dirp);
    }
    while(0);
    pthread_mutex_unlock(&selfc->mutex);

    return selfc->entry;
}


static int CDirectory_fstatat(struct IDirectory *self, const char *pathname, struct stat *statbuf)
{
    struct CDirectory* selfc = (struct CDirectory*)self;

    return fstatat(dirfd(selfc->dirp), pathname, statbuf, 0);
}


static int CDirectory_openat(struct IDirectory *self, const char *pathname)
{
    struct CDirectory* selfc = (struct CDirectory*)self;

    return openat(dirfd(selfc->dirp), pathname, O_RDONLY | O_CLOEXEC);
}
