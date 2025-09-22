#include "common.h"
#include "inflate_gzip.h"
#include "file.h"
#include "fitsfile.h"
#include "parallel_for.h"

#include <pthread.h>

/* gcc extension: brings BYTE_ORDER */
#include <endian.h>

#include <assert.h>
#include <errno.h>
#include <stdatomic.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>


/** Allocates memory and returns an "untracked" pointer to it.

    gcc-11's `-fanalyzer` emits -Wanalyzer-malloc-leak false-positively
    when there are such lines as:

        int* _Atomic ap;  // global variable

        void f(){
            int* p = (int*)malloc(sizeof(int));
            ... (Do many things with `*p`) ...
            ap = p;
        }

    True, the code above is overly simplified so that the allocated memory
    may actually leak. But no matter how careful code we write, the warning
    inevitably comes out.

    We can prevent `-fanalyzer` from tracking the pointer, by putting the
    return value of `malloc` directly into an atomic variable:

        void f(){
            int* _Atomic p = (int*)malloc(sizeof(int));
            // `-fanalyzer` totally neglects `p`.
            // We can even return immediately after this line, leaving `p` behind.
            ... (Do many things with `*p`) ...
            ap = p;
        }

    But we don't want `p` to be atomic unnecessarily. This function solves
    this problem (at least for gcc-11).

    Parameters
    ----------
    size
        Size in bytes.

    Returns
    -------
    p
        Pointer to allocated memory.
*/
void* malloc_untracked_by_fanalyzer(size_t size)
{
    void* _Atomic p = malloc(size);
    return p;
}


/** Tests whether an array is filled with zero.

    Parameters
    ----------
    buf
        Array.
    size
        Size of `buf` in bytes

    Returns
    -------
    test
        True if `buf` is filled with zero.
*/
static _Bool is_filled_with_zero(void* buf, size_t size)
{
    for(size_t i = 0; i < size; ++i){
        if(((char*)buf)[i]) return 0;
    }
    return 1;
}


/** Tests whether a string contains a character.

    Parameters
    ----------
    s
        Null-terminated string.
    c
        Character.

    Returns
    -------
    test
        True if `s` contains `c`.
*/
static _Bool str_contains(char const* s, char c)
{
    for(; *s != 0; ++s){
        if(*s == c) return 1;
    }
    return 0;
}


/** Swaps bytes (if necessary) so that the elements of the returned array will
    be in the host byte order.

    Parameters
    ----------
    arr
        Array, whose elements are in network byte order.
    n
        Number of elements in `arr`.
*/
static void to_host_byte_order64(uint64_t* arr, size_t n);


/** Swaps bytes (if necessary) so that the elements of the returned array will
    be in the host byte order.

    Parameters
    ----------
    arr
        Array, whose elements are in network byte order.
    n
        Number of elements in `arr`.
*/
static void to_host_byte_order32(uint32_t* arr, size_t n);


#if BYTE_ORDER == LITTLE_ENDIAN
static void to_host_byte_order64(uint64_t* arr, size_t n)
{
    for(size_t i = 0; i < n; ++i){
        /* __builtin_bswap64 is not faster than the following pure C code
            when the latter is translated into SIMD instructions.
        */
        uint64_t x = arr[i];
        arr[i] = (
            ((x >> 56))
        |   ((x >> 40) & (uint64_t)0x000000000000ff00)
        |   ((x >> 24) & (uint64_t)0x0000000000ff0000)
        |   ((x >>  8) & (uint64_t)0x00000000ff000000)
        |   ((x <<  8) & (uint64_t)0x000000ff00000000)
        |   ((x << 24) & (uint64_t)0x0000ff0000000000)
        |   ((x << 40) & (uint64_t)0x00ff000000000000)
        |   ((x << 56))
        );
    }
}


static void to_host_byte_order32(uint32_t* arr, size_t n)
{
    for(size_t i = 0; i < n; ++i){
        /* __builtin_bswap32 is not faster than the following pure C code
            when the latter is translated into SIMD instructions.
        */
        uint32_t x = arr[i];
        arr[i] = (
            ((x >> 24))
        |   ((x >>  8) & (uint32_t)0x0000ff00)
        |   ((x <<  8) & (uint32_t)0x00ff0000)
        |   ((x << 24))
        );
    }
}
#else
static void to_host_byte_order64(uint64_t net)
{
    /* do nothing */
    return;
}


static void to_host_byte_order32(uint32_t net)
{
    /* do nothing */
    return;
}
#endif


/** Decodes (uncompressed) gzip2 cipher.

    Decryption goes as follows when `element_size` is 4:

    If the ciphertext is:
        A1 A2 ... An; B1 B2 ... Bn; C1 C2 ... Cn; D1 D2 ... Dn
    where each of Ai, Bi, Ci and Di is a byte, the plaintext is:
        A1 B1 C1 D1; A2 B2 C2 D2; ...; An Bn Cn Dn

    Parameters
    ----------
    input
        Input cipher.
    output
        Deciphered output.
    element_size
        Element size in bytes.
    num_elements
        Number of elements.
*/
static void gzip2_decode(char* input, char* output, size_t element_size, size_t num_elements)
{
    for(size_t i = 0; i < element_size; ++i){
        for(size_t j = 0; j < num_elements; ++j){
            output[j * element_size + i] = input[i * num_elements + j];
        }
    }
}


/** Key part of a FITS header card.

    The last byte (key[8]) of the key is usually '='.
    The last byte is ' ' for only a few keywords like "END      ".
*/
struct __attribute__((__packed__)) FitsCardKey
{
    /** Key. *Not* null-terminated. */
    char key[9];
};


/** Value part of a FITS header card.
*/
struct __attribute__((__packed__)) FitsCardValue
{
    /** Value. *Not* null-terminated. */
    char value[71];
};


/** FITS header card.
*/
struct __attribute__((__packed__)) FitsCard
{
    struct FitsCardKey      key;
    struct FitsCardValue    value;
};


/** Parses a boolean value field of a FITS header card.

    `output` argument must be a pointer to intptr_t.

    Parameters
    ----------
    input
        FITS header card.
    output
        Pointer to a buffer in which to store the result.

    Returns
    -------
    success
        True if succeeds.
*/
static _Bool fits_parse_bool(struct FitsCardValue const* input, void* output)
{
    intptr_t* result = (intptr_t*)output;

    size_t const n = sizeof(input->value);
    size_t i = 0;

    for(; i < n; ++i){
        if(input->value[i] != ' ') break;
    }
    if(!(i < n)) return 0;

    if(input->value[i] == 'T'){
        ++i;
        *result = 1;
    }
    else if(input->value[i] == 'F'){
        ++i;
        *result = 0;
    }
    else{
        return 0;
    }

    for(; i < n; ++i){
        if(input->value[i] != ' ') break;
    }
    if(!(i < n)) return 1;

    return input->value[i] == '/';
}


/** Parses an integer value field of a FITS header card.

    `output` argument must be a pointer to intptr_t.

    Parameters
    ----------
    input
        FITS header card.
    output
        Pointer to a buffer in which to store the result.

    Returns
    -------
    success
        True if succeeds.
*/
static _Bool fits_parse_int(struct FitsCardValue const* input, void* output)
{
    intptr_t* result = (intptr_t*)output;

    size_t const n = sizeof(input->value);
    size_t i = 0;

    for(; i < n; ++i){
        if(input->value[i] != ' ') break;
    }
    if(!(i < n)) return 0;

    intptr_t sign = 1;
    if(input->value[i] == '+'){
        ++i;
    }
    else if(input->value[i] == '-'){
        sign = -1;
        ++i;
    }

    size_t i_start = i;
    intptr_t absvalue = 0;
    for(; i < n; ++i){
        char c = input->value[i];
        if(!('0' <= c && c <= '9')) break;
        absvalue = absvalue * 10 + (intptr_t)(c - '0');
    }

    if(i <= i_start) return 0;

    *result = sign * absvalue;

    for(; i < n; ++i){
        if(input->value[i] != ' ') break;
    }
    if(!(i < n)) return 1;

    return input->value[i] == '/';
}


/** Parses a string value field of a FITS header card.

    `output` argument must be a pointer to a buffer of at least 72 characters
    including the terminating null character.

    Parameters
    ----------
    input
        FITS header card.
    output
        Pointer to a buffer in which to store the result.

    Returns
    -------
    success
        True if succeeds.
*/
static _Bool fits_parse_str(struct FitsCardValue const* input, void* output)
{
    char* outptr = (char*)output;

    size_t const n = sizeof(input->value);
    size_t i = 0;

    for(; i < n; ++i){
        if(input->value[i] != ' ') break;
    }
    if(!(i < n)) return 0;

    if(input->value[i] != '\'') return 0;
    ++i;

    for(; i < n; ++i){
        char c = input->value[i];
        if(c == '\''){
            if(i + 1 < n && input->value[i + 1] == '\''){
                *(outptr++) = c;
                ++i;
            }
            else{
                break;
            }
        }
        else{
            *(outptr++) = c;
        }
    }
    if(!(i < n)) return 0; /* no closing quote */
    ++i;

    *(outptr--) = 0;
    /* This inequity is not '<=' because the first space is significant. */
    while((char*)output < outptr){
        if(*outptr != ' ') break;
        *(outptr--) = 0;
    }

    for(; i < n; ++i){
        if(input->value[i] != ' ') break;
    }
    if(!(i < n)) return 1;

    return input->value[i] == '/';
}


/** Writes a string value to a FITS header card.

    Parameters
    ----------
    value
        String. Long string will be truncated.
    output
        FITS header card in which to store `value`.
*/
static void fits_write_str(char const* value, struct FitsCardValue* output)
{
    memset(output->value, ' ', sizeof(output->value));

    if(*value == 0){
        output->value[1] = '\'';
        output->value[2] = '\'';
        return;
    }

    output->value[1] = '\'';
    int i = 2;

    for(; i < sizeof(output->value) - 1; ++i){
        char c = *(value++);
        if(c == '\''){
            if(i < sizeof(output->value) - 2){
                output->value[i] = '\'';
                output->value[i+1] = '\'';
                ++i;
            }
            else{
                break;
            }
        }
        else if(c){
            output->value[i] = c;
        }
        else{
            break;
        }
    }

    if(i < 10){
        i = 10;
    }

    output->value[i++] = '\'';
}


/** Writes an integer value to a FITS header card.

    Parameters
    ----------
    value
        Integer.
    output
        FITS header card in which to store `value`.
*/
static void fits_write_int(int64_t value, struct FitsCardValue* output)
{
    /* The FITS standard requires to put an integer from
        output->value[1] through output->value[20] (inclusive).
        The longest 64bits integer (in string representation) is
        -9223372036854775808. The length of this is 20.
        So, if the argument type is int64_t, we don't have to fear
        that the string representation may be too long.
    */

    memset(output->value, ' ', sizeof(output->value));

    size_t i = 20;

    if(value == 0){
        output->value[i] = '0';
        return;
    }

    char sign;
    uint64_t u;
    if(value >= 0){
        sign = ' ';
        u = (uint64_t)value;
    }
    else{
        sign = '-';
        u = (uint64_t)((-1) * value);
    }

    for(; i > 0; --i){
        if(u == 0) break;

        output->value[i] = '0' + (u % 10);
        u /= 10;
    }

    output->value[i] = sign;
}


/** FITS header.

    This structure represents only a single chunk (2880 bytes).
    The entire header is realized as a linked list.
*/
struct FitsHeader
{
    /** Next chunk. NULL if this chunk is the last chunk. */
    struct FitsHeader    *next;
    /** FITS header cards */
    struct FitsCard      cards[36];
};


/** Creates an instance of `FitsHeader`.

    The returned instance is initialized to the extent that it is ready to be
    destroyed with `FitsHeader_destroy()`.

    Returns
    -------
    instance
        New instance. NULL if failed.
*/
static struct FitsHeader* FitsHeader_new()
{
    NEW_PTR(chunk, struct FitsHeader);
    if(!chunk){
        errno = ENOMEM;
        return NULL;
    }

    chunk->next = NULL;
    return chunk;
}


/** Destroys an instance of `FitsHeader`.

    The entire linked list is deleted.

    Parameters
    -------
    header
        FITS header.
*/
static void FitsHeader_destroy(struct FitsHeader *header)
{
    while(header){
        struct FitsHeader *next = header->next;
        free(header);
        header = next;
    }
}


/** Copies a part of a FITS header to a contiguous buffer.

    Parameters
    ----------
    header
        FITS header.
    buf
        Output contiguous buffer.
    size
        Number of bytes to copy.
    offset
        Offset of the data, in the FITS header, to copy.
*/
static void FitsHeader_copy_to_buffer(
    struct FitsHeader   *header,
    void                *buf,
    size_t              size,
    size_t              offset
){
    size_t const block_size = sizeof(header->cards);
    size_t const offset_of_end = size + offset;

    size_t block_offset = 0;

    while(size > 0 && header){
        size_t block_end = block_offset + block_size;
        if(block_end <= offset){
            header = header->next;
            block_offset += block_size;
            continue;
        }

        size_t copy_start = offset;
        size_t copy_end = (block_end < offset_of_end) ? block_end : offset_of_end;

        size_t offset_in_block = copy_start - block_offset;
        size_t copy_size = copy_end - copy_start;

        memcpy(buf, (char*)header->cards + offset_in_block, copy_size);

        offset = copy_end;
        size -= copy_size;
        buf = (char*)buf + copy_size;

        header = header->next;
        block_offset += block_size;
    }

    assert(size == 0);
}


/** Read file to get a FITS header.

    On return, *poffset_of_body is set to the file offset of the body.

    Parameters
    ----------
    file
        File to read.
    offset
        File offset of the 0th byte to read.
    poffset_of_body
        (Output) File offset of the body.
    reading_errno
        (output) errno.

    Returns
    -------
    header
        FITS header. The return value may be NULL.
        It being NULL and `*reading_errno` being 0 imply end of file.
        It being NULL and `*reading_errno` being non-0 imply a read error.
*/
static
struct FitsHeader*
FitsHeader_read_file(
    struct IRegFile *file,
    size_t          offset,
    size_t          *poffset_of_body,
    int             *reading_errno
){
    struct FitsHeader* header = NULL;
    struct FitsHeader** prevlink = &header;

    size_t const ncards_per_chunk = sizeof(header->cards) / sizeof(header->cards[0]);

    *reading_errno = 0;

    while(1){
        struct FitsHeader* chunk = FitsHeader_new();
        if(!chunk){
            FitsHeader_destroy(header);
            *reading_errno = ENOMEM;
            return NULL;
        }

        errno = 0;
        size_t nread = file->vtbl->read(file, chunk->cards, sizeof(chunk->cards), offset);
        if(nread != sizeof(chunk->cards)){
            if(errno == 0){
                /* C standard permits that a number of null bytes may appear
                    past the end of a binary file content */
                if(!header /* first chunk*/
                && is_filled_with_zero(chunk->cards, nread)
                ){
                    /* OK */;
                }
                else{
                    *reading_errno = EILSEQ;
                }
            }
            else{
                *reading_errno = errno;
            }

            FitsHeader_destroy(chunk);
            FitsHeader_destroy(header);
            return NULL;
        }

        if(!header){ /* first chunk */
            if(0 != memcmp("XTENSION=", &chunk->cards[0].key, sizeof(chunk->cards[0].key))
            && 0 != memcmp("SIMPLE  =", &chunk->cards[0].key, sizeof(chunk->cards[0].key))
            ){
                FitsHeader_destroy(chunk);
                FitsHeader_destroy(header);
                *reading_errno = EILSEQ;
                return NULL;
            }
        }

        *prevlink = chunk;
        prevlink = &chunk->next;
        offset += sizeof(chunk->cards);

        _Bool isend = 0;
        for(size_t i = 0; i < ncards_per_chunk; ++i){
            if(0 == memcmp("END      ", &chunk->cards[i].key, sizeof(chunk->cards[i].key))){
                isend = 1;
                break;
            }
        }

        if(isend) break;
    }

    *poffset_of_body = offset;
    return header;
}


/** Essential cards in a FITS header.
    The members of this structure are ready to use by the program,
    unlike `FitsCard`
*/
struct FitsEssentialCards
{
    char        xtension[72];
    intptr_t    bitpix;
    intptr_t    naxis;
    intptr_t    naxes[2];
    intptr_t    pcount;
    intptr_t    gcount;

    intptr_t    zimage;
    char        zcmptype[72];
    char        zquantiz[72];
    intptr_t    zbitpix;
    intptr_t    znaxis;
    intptr_t    znaxes[2];
    intptr_t    ztile[2];
    intptr_t    tfields;
    char        tform1[72];
    char        ttype1[72];
    intptr_t    theap;
};


/** Parses a FITS header.

    Parameters
    ----------
    header
        FITS header to parse.
    output
        Result of the parsing.

    Returns
    -------
    success
        True if succeeded.
*/
static _Bool fits_parse_header(struct FitsHeader *header, struct FitsEssentialCards* output)
{
    struct Parser
    {
        size_t                      offset;
        struct FitsCardKey const    key;
        _Bool                       (*parsefunc)(struct FitsCardValue const* input, void* output);
    };

    static struct Parser const parsers[] = {
        {offsetof(struct FitsEssentialCards, xtension ), {"XTENSION="}, fits_parse_str  },
        {offsetof(struct FitsEssentialCards, bitpix   ), {"BITPIX  ="}, fits_parse_int  },
        {offsetof(struct FitsEssentialCards, naxis    ), {"NAXIS   ="}, fits_parse_int  },
        {offsetof(struct FitsEssentialCards, naxes[0] ), {"NAXIS1  ="}, fits_parse_int  },
        {offsetof(struct FitsEssentialCards, naxes[1] ), {"NAXIS2  ="}, fits_parse_int  },
        {offsetof(struct FitsEssentialCards, pcount   ), {"PCOUNT  ="}, fits_parse_int  },
        {offsetof(struct FitsEssentialCards, gcount   ), {"GCOUNT  ="}, fits_parse_int  },

        {offsetof(struct FitsEssentialCards, zimage   ), {"ZIMAGE  ="}, fits_parse_bool },
        {offsetof(struct FitsEssentialCards, zcmptype ), {"ZCMPTYPE="}, fits_parse_str  },
        {offsetof(struct FitsEssentialCards, zquantiz ), {"ZQUANTIZ="}, fits_parse_str  },
        {offsetof(struct FitsEssentialCards, zbitpix  ), {"ZBITPIX ="}, fits_parse_int  },
        {offsetof(struct FitsEssentialCards, znaxis   ), {"ZNAXIS  ="}, fits_parse_int  },
        {offsetof(struct FitsEssentialCards, znaxes[0]), {"ZNAXIS1 ="}, fits_parse_int  },
        {offsetof(struct FitsEssentialCards, znaxes[1]), {"ZNAXIS2 ="}, fits_parse_int  },
        {offsetof(struct FitsEssentialCards, ztile[0] ), {"ZTILE1  ="}, fits_parse_int  },
        {offsetof(struct FitsEssentialCards, ztile[1] ), {"ZTILE2  ="}, fits_parse_int  },
        {offsetof(struct FitsEssentialCards, tfields  ), {"TFIELDS ="}, fits_parse_int  },
        {offsetof(struct FitsEssentialCards, tform1   ), {"TFORM1  ="}, fits_parse_str  },
        {offsetof(struct FitsEssentialCards, ttype1   ), {"TTYPE1  ="}, fits_parse_str  },
        {offsetof(struct FitsEssentialCards, theap    ), {"THEAP   ="}, fits_parse_int  },
    };

    size_t const nparsers = sizeof(parsers) / sizeof(parsers[0]);
    size_t const ncards_per_chunk = sizeof(header->cards) / sizeof(header->cards[0]);

    memset(output, 0, sizeof(struct FitsEssentialCards));
    output->gcount = 1;

    while(header){
        for(size_t i = 0; i < ncards_per_chunk; ++i){
            struct FitsCard* card = &header->cards[i];

            for(size_t j = 0; j < nparsers; ++j){
                struct Parser const *parser = &parsers[j];

                if(0 == memcmp(&card->key, &parser->key, sizeof(card->key))){
                    if(!parser->parsefunc(&card->value, (char*)output + parser->offset)){
                        return 0;
                    }
                    break;
                }
            }
        }

        header = header->next;
    }

    return 1;
}


/** Gets the gross size of a constituent whose net size is `netsize` bytes,
    when it is stored in a FITS file.

    Parameters
    ----------
    netsize
        Net size in bytes.

    Returns
    -------
    grosssize
        Gross size, paddings included.
*/
static size_t fits_get_aligned_size(
    size_t netsize
){
    size_t const blocksize = sizeof(((struct FitsHeader*)NULL)->cards);
    return ((netsize + (blocksize - 1)) / blocksize) * blocksize;
}


/** Gets the physical size of the body part of an HDU.

    Parameters
    ----------
    essential_cards
        Essential cards in the header part of the HDU.

    Returns
    -------
    size
        Body size in bytes, paddings included.
*/
static size_t fits_get_physical_body_size(
    struct FitsEssentialCards const* essential_cards
){
    size_t nelem = 0;
    if(essential_cards->naxis > 0){
        nelem = 1;
        for(intptr_t i = 0; i < essential_cards->naxis; ++i){
            nelem *= essential_cards->naxes[i];
        }
    }

    size_t bytes_per_elem = (
        (essential_cards->bitpix > 0) ? essential_cards->bitpix : -essential_cards->bitpix
    ) / 8;

    size_t netsize = bytes_per_elem * essential_cards->gcount * (essential_cards->pcount + nelem);
    return fits_get_aligned_size(netsize);
}


/** HDU decoder (abstract interface)

    An HDU decoder decodes a "physical" (or compressed, in-file) HDU
    into a "logical" (or uncompressed, in-memory) HDU.
*/
struct IFitsHduDecoder_vtbl;
struct IFitsHduDecoder
{
    struct IFitsHduDecoder_vtbl const* vtbl;
};

struct IFitsHduDecoder_vtbl
{
    /** Destructor.
    */
    void (*destroy)(
        struct IFitsHduDecoder  *self
    );

    /** Gets the logical size of the body part of the HDU.

        Parameters
        ----------
        essential_cards
            Essential cards in the header part of the HDU.

        Returns
        -------
        size
            Body size in bytes, paddings included.
    */
    size_t (*get_logical_body_size)(
        struct IFitsHduDecoder          *self,
        struct FitsEssentialCards const *essential_cards
    );

    /** Decodes the header part.

        Parameters
        ----------
        essential_cards
            Essential cards in the header part of the HDU.
        header
            Header part of the HDU. This will get modified directly.
    */
    void (*decode_header)(
        struct IFitsHduDecoder          *self,
        struct FitsEssentialCards const *essential_cards,
        struct FitsHeader               *header
    );

    /** Decodes the body part.

        The caller must not try to read outside the logical boundaries of
        the body.

        This member function is called in parallel.

        Parameters
        ----------
        file
            File to read.
        buf
            Buffer to store the plaintext in.
        size
            Size of `buf`. It is the logical size to read.
        logical_offset_in_body
            Logical offset, in the body part of the HDU, of the 0-th byte to read.

        Returns
        -------
        nbytes
            Number of logical bytes read.
            The return value being different from `size` implies an error.
    */
    size_t (*decode_body)(
        struct IFitsHduDecoder          *self,
        struct IRegFile                 *file,
        void                            *buf,
        size_t                          size,
        size_t                          logical_offset_in_body
    );

    /** Decodes the entire body part at once.

        If you ever call this function, you must call it before the first call
        to decode_body().

        This member function is called in parallel.

        Parameters
        ----------
        file
            File to read.
        num_threads
            Number of threads to use.
        mutex
            Mutex, used if required by this function.

        Returns
        -------
        nbytes
            Number of logical bytes read.
            The return value being different from `size` implies an error.
    */
    void (*predecode_all_body)(
        struct IFitsHduDecoder          *self,
        struct IRegFile                 *file,
        size_t                          num_threads,
        pthread_mutex_t                 *mutex
    );
};


/** HDU decoder for plain (uncompressed) fits file.
*/
struct CFitsPlainHduDecoder
{
    struct IFitsHduDecoder iface;

    /** Physical file offset of the body part of this HDU */
    size_t physical_offset_of_body;
};


static void CFitsPlainHduDecoder_destroy(
    struct IFitsHduDecoder  *self
);
static size_t CFitsPlainHduDecoder_get_logical_body_size(
    struct IFitsHduDecoder          *self,
    struct FitsEssentialCards const *essential_cards
);
static void CFitsPlainHduDecoder_decode_header(
    struct IFitsHduDecoder          *self,
    struct FitsEssentialCards const *essential_cards,
    struct FitsHeader               *header
);
static size_t CFitsPlainHduDecoder_decode_body(
    struct IFitsHduDecoder          *self,
    struct IRegFile                 *file,
    void                            *buf,
    size_t                          size,
    size_t                          logical_offset_in_body
);
static void CFitsPlainHduDecoder_predecode_all_body(
    struct IFitsHduDecoder          *self,
    struct IRegFile                 *file,
    size_t                          num_threads,
    pthread_mutex_t                 *mutex
);

static struct IFitsHduDecoder_vtbl const CFitsPlainHduDecoder_vtbl = {
    .destroy               = CFitsPlainHduDecoder_destroy,
    .get_logical_body_size = CFitsPlainHduDecoder_get_logical_body_size,
    .decode_header         = CFitsPlainHduDecoder_decode_header,
    .decode_body           = CFitsPlainHduDecoder_decode_body,
    .predecode_all_body    = CFitsPlainHduDecoder_predecode_all_body,
};


/** Creates an instance of CFitsPlainHduDecoder.

    Parameters
    ----------
    physical_offset_of_body
        File offset of the body data.

    Returns
    -------
    instance
        An instance of CFitsPlainHduDecoder.
*/
static struct IFitsHduDecoder* CFitsPlainHduDecoder_new(
    size_t physical_offset_of_body
){
    NEW_PTR(selfc, struct CFitsPlainHduDecoder);
    if(!selfc){
        errno = ENOMEM;
        return NULL;
    }

    selfc->iface.vtbl = &CFitsPlainHduDecoder_vtbl;
    selfc->physical_offset_of_body = physical_offset_of_body;

    return (struct IFitsHduDecoder*)selfc;
}


static void CFitsPlainHduDecoder_destroy(
    struct IFitsHduDecoder* self
){
    struct CFitsPlainHduDecoder* selfc = (struct CFitsPlainHduDecoder*)self;

    if(!selfc) return;

    free(selfc);
}


static size_t CFitsPlainHduDecoder_get_logical_body_size(
    struct IFitsHduDecoder          *self,
    struct FitsEssentialCards const *essential_cards
){
    return fits_get_physical_body_size(essential_cards);
}


static void CFitsPlainHduDecoder_decode_header(
    struct IFitsHduDecoder          *self,
    struct FitsEssentialCards const *essential_cards,
    struct FitsHeader               *header
){
    /* Do nothing. */
    return;
}


static size_t CFitsPlainHduDecoder_decode_body(
    struct IFitsHduDecoder          *self,
    struct IRegFile                 *file,
    void                            *buf,
    size_t                          size,
    size_t                          logical_offset_in_body
){
    struct CFitsPlainHduDecoder* selfc = (struct CFitsPlainHduDecoder*)self;

    return file->vtbl->read(
        file,
        buf,
        size,
        selfc->physical_offset_of_body + logical_offset_in_body
    );
}


static void CFitsPlainHduDecoder_predecode_all_body(
    struct IFitsHduDecoder          *self,
    struct IRegFile                 *file,
    size_t                          num_threads,
    pthread_mutex_t                 *mutex
){
    /* Do nothing. */
    return;
}


/** HDU decoder for tiled fits file.
*/
struct CFitsTiledHduDecoder
{
    struct IFitsHduDecoder  iface;
    size_t                  physical_offset_of_body;
    size_t                  element_size;
    size_t                  image_width;
    size_t                  image_height;
    size_t                  pointer_size;
    size_t                  tile_width;
    size_t                  tile_height;
    size_t                  num_tiles_along_x;
    size_t                  num_tiles_along_y;
    size_t                  num_tiles;
    size_t                  physical_offset_of_heap;
    size_t *_Atomic         tile_entries;
    char *_Atomic *_Atomic  tiles;
};


static void CFitsTiledHduDecoder_destruct(
    struct IFitsHduDecoder  *self
);
static size_t CFitsTiledHduDecoder_get_logical_body_size(
    struct IFitsHduDecoder          *self,
    struct FitsEssentialCards const *essential_cards
);
static void CFitsTiledHduDecoder_decode_header(
    struct IFitsHduDecoder          *self,
    struct FitsEssentialCards const *essential_cards,
    struct FitsHeader               *header
);
static size_t CFitsTiledHduDecoder_decode_body(
    struct IFitsHduDecoder          *self,
    struct IRegFile                 *file,
    void                            *buf,
    size_t                          size,
    size_t                          logical_offset_in_body
);
void CFitsTiledHduDecoder_predecode_all_body(
    struct IFitsHduDecoder          *self,
    struct IRegFile                 *file,
    size_t                          num_threads,
    pthread_mutex_t                 *mutex
);

static struct IFitsHduDecoder_vtbl const CFitsTiledHduDecoder_vtbl = {
    .destroy               = CFitsTiledHduDecoder_destruct,
    .get_logical_body_size = CFitsTiledHduDecoder_get_logical_body_size,
    .decode_header         = CFitsTiledHduDecoder_decode_header,
    .decode_body           = CFitsTiledHduDecoder_decode_body,
    .predecode_all_body    = CFitsTiledHduDecoder_predecode_all_body,
};


/** Creates an instance of CFitsTiledHduDecoder.

    Parameters
    ----------
    physical_offset_of_body
        File offset of the body data.
    essential_cards
        Essential cards in the FITS header.

    Returns
    -------
    instance
        An instance of CFitsTiledHduDecoder.
*/
static struct IFitsHduDecoder* CFitsTiledHduDecoder_new(
    size_t                          physical_offset_of_body,
    struct FitsEssentialCards const *essential_cards
){
    if(!essential_cards->zimage
    || 2 != essential_cards->znaxis
    || 0 != strcmp(essential_cards->xtension, "BINTABLE")
    || 0 != strcmp(essential_cards->zcmptype, "GZIP_2")
    || !(essential_cards->bitpix >= 0 || 0 == strcmp(essential_cards->zquantiz, "NONE"))
    ){
        errno = EILSEQ;
        return NULL;
    }

    struct CFitsTiledHduDecoder* selfc = (struct CFitsTiledHduDecoder*)
        malloc_untracked_by_fanalyzer(sizeof(struct CFitsTiledHduDecoder));
    if(!selfc){
        errno = ENOMEM;
        return NULL;
    }

    selfc->iface.vtbl = &CFitsTiledHduDecoder_vtbl;

    selfc->physical_offset_of_body = physical_offset_of_body;

    selfc->element_size = (
        (essential_cards->zbitpix > 0) ? essential_cards->zbitpix : -essential_cards->zbitpix
    ) / 8;

    selfc->image_width = essential_cards->znaxes[0];
    selfc->image_height = essential_cards->znaxes[1];

    if(str_contains(essential_cards->tform1, 'Q')){
        selfc->pointer_size = 8;
    }
    else{
        selfc->pointer_size = 4;
    }

    size_t ztile_x = essential_cards->ztile[0];
    size_t ztile_y = essential_cards->ztile[1];
    if(ztile_x == 0 && ztile_y == 0){
        ztile_x = essential_cards->znaxes[0];
        ztile_y = 1;
    }
    else{
        if(ztile_x == 0) ztile_x = 1;
        if(ztile_y == 0) ztile_y = 1;
    }

    selfc->tile_width = ztile_x;
    selfc->tile_height = ztile_y;
    selfc->num_tiles_along_x = (essential_cards->znaxes[0] + (ztile_x - 1)) / ztile_x;
    selfc->num_tiles_along_y = (essential_cards->znaxes[1] + (ztile_y - 1)) / ztile_y;
    selfc->num_tiles = essential_cards->naxes[1];

    if(selfc->num_tiles_along_x * selfc->num_tiles_along_y != selfc->num_tiles){
        errno = EILSEQ;
        return NULL;
    }

    size_t offset_of_heap_in_body = 0;
    if(essential_cards->theap){
        offset_of_heap_in_body = essential_cards->theap;
    }
    else{
        size_t bytes_per_elem = (
            (essential_cards->bitpix > 0) ? essential_cards->bitpix : -essential_cards->bitpix
        ) / 8;
        offset_of_heap_in_body = bytes_per_elem * essential_cards->naxes[0] * essential_cards->naxes[1];
    }

    selfc->physical_offset_of_heap = physical_offset_of_body + offset_of_heap_in_body;

    selfc->tile_entries = NULL;
    selfc->tiles = NULL;

    return (struct IFitsHduDecoder*)selfc;
}


static void CFitsTiledHduDecoder_destruct(
    struct IFitsHduDecoder  *self
){
    struct CFitsTiledHduDecoder* selfc = (struct CFitsTiledHduDecoder*)self;

    if(!selfc) return;

    if(selfc->tile_entries){
        free(selfc->tile_entries);
    }

    if(selfc->tiles){
        size_t const num_tiles = selfc->num_tiles;
        for(size_t i = 0; i < num_tiles; ++i){
            if(selfc->tiles[i]){
                free(selfc->tiles[i]);
            }
        }

        free(selfc->tiles);
    }

    free(selfc);
}


static size_t CFitsTiledHduDecoder_get_logical_body_size(
    struct IFitsHduDecoder          *self,
    struct FitsEssentialCards const *essential_cards
){
    size_t nelem = 0;
    if(essential_cards->znaxis > 0){
        nelem = 1;
        for(intptr_t i = 0; i < essential_cards->znaxis; ++i){
            nelem *= essential_cards->znaxes[i];
        }
    }

    size_t bytes_per_elem = (
        (essential_cards->zbitpix > 0) ? essential_cards->zbitpix : -essential_cards->zbitpix
    ) / 8;

    size_t netsize = bytes_per_elem * nelem;
    return fits_get_aligned_size(netsize);
}


static void CFitsTiledHduDecoder_decode_header(
    struct IFitsHduDecoder          *self,
    struct FitsEssentialCards const *essential_cards,
    struct FitsHeader               *header
){
    static struct FitsCardKey const keys_to_delete[] = {
        {"ZIMAGE  ="},
        {"ZCMPTYPE="},
        {"ZBITPIX ="},
        {"ZNAXIS  ="},
        {"ZNAXIS1 ="},
        {"ZNAXIS2 ="},
        {"ZTILE1  ="},
        {"ZTILE2  ="},
        {"ZQUANTIZ="},
        {"ZSIMPLE ="},
        {"ZTENSION="},
        {"TFIELDS ="},
        {"TFORM1  ="},
        {"TTYPE1  ="},
        {"THEAP   ="},
    };

    size_t const nkeys_to_delete = sizeof(keys_to_delete) / sizeof(keys_to_delete[0]);
    size_t const ncards_per_chunk = sizeof(header->cards) / sizeof(header->cards[0]);

    if(!essential_cards->zimage){
        return;
    }

    while(header){
        for(size_t i = 0; i < ncards_per_chunk; ++i){
            struct FitsCard* card = &header->cards[i];

            _Bool found = 0;
            for(size_t j = 0; j < nkeys_to_delete; ++j){
                if(0 == memcmp(&card->key, &keys_to_delete[j], sizeof(card->key))){
                    memcpy(&card->key, "COMMENT  ", sizeof(card->key));
                    memset(&card->value, ' ', sizeof(card->value));
                    found = 1;
                    break;
                }
            }
            if(found){
                /* OK */;
            }
            else if(0 == memcmp(&card->key, "XTENSION=", sizeof(card->key))){
                fits_write_str("IMAGE", &card->value);
            }
            else if(0 == memcmp(&card->key, "BITPIX  =", sizeof(card->key))){
                fits_write_int(essential_cards->zbitpix, &card->value);
            }
            else if(0 == memcmp(&card->key, "NAXIS   =", sizeof(card->key))){
                fits_write_int(essential_cards->znaxis, &card->value);
            }
            else if(0 == memcmp(&card->key, "NAXIS1  =", sizeof(card->key))){
                fits_write_int(essential_cards->znaxes[0], &card->value);
            }
            else if(0 == memcmp(&card->key, "NAXIS2  =", sizeof(card->key))){
                fits_write_int(essential_cards->znaxes[1], &card->value);
            }
            else if(0 == memcmp(&card->key, "PCOUNT  =", sizeof(card->key))){
                fits_write_int(0, &card->value);
            }
            else if(0 == memcmp(&card->key, "GCOUNT  =", sizeof(card->key))){
                fits_write_int(1, &card->value);
            }
        }

        header = header->next;
    }
}


/** Loads `tile_entries`
    (interleaved list of (size[i], offset[i]) of the compressed tiles).

    This function may be called in parallel.

    Parameters
    ----------
    file
        File to read.

    Returns
    -------
    success
        True if succeeded.
*/
static _Bool CFitsTiledHduDecoder_load_tile_entries(
    struct CFitsTiledHduDecoder *selfc,
    struct IRegFile             *file
){
    if(selfc->tile_entries){
        return 1;
    }

    size_t nelems = 2 * selfc->num_tiles; /* (size, offset) for each tiles */
    size_t* tile_entries = (size_t*)malloc_untracked_by_fanalyzer(nelems * sizeof(size_t));
    if(!tile_entries){
        errno = ENOMEM;
        return 0;
    }

    assert(sizeof(size_t) == sizeof(uint64_t));

    if(selfc->pointer_size == 8){
        size_t nread = nelems * sizeof(tile_entries[0]);
        if(nread != file->vtbl->read(
            file,
            tile_entries,
            nread,
            selfc->physical_offset_of_body
        )){
            free(tile_entries);
            errno = EILSEQ;
            return 0;
        }

        to_host_byte_order64((uint64_t*)tile_entries, nelems);
    }
    else{
        size_t nread = nelems * sizeof(uint32_t);
        uint32_t* tile_entries32 = (uint32_t*)malloc(nread);
        if(!tile_entries32){
            free(tile_entries);
            errno = ENOMEM;
            return 0;
        }

        if(nread != file->vtbl->read(
            file,
            tile_entries32,
            nread,
            selfc->physical_offset_of_body
        )){
            free(tile_entries32);
            free(tile_entries);
            errno = EILSEQ;
            return 0;
        }

        to_host_byte_order32(tile_entries32, nelems);

        uint32_t reduced_or = 0;
        for(size_t i = 0; i < nelems; ++i){
            reduced_or |= tile_entries32[i];
        }
        if(reduced_or & (uint32_t)0x80000000){
            /* FITS standard says that the elements in `tile_entries` are signed
                (though we declared them uint32_t). The standard also says that
                the meaning of minus values are undefined. We just refuse to decode
                a FITS file containing such things.
            */
            free(tile_entries32);
            free(tile_entries);
            errno = EILSEQ;
            return 0;
        }

        for(size_t i = 0; i < nelems; ++i){
            tile_entries[i] = (size_t)tile_entries32[i];
        }

        free(tile_entries32);
    }

    size_t* nil = NULL;
    if(!atomic_compare_exchange_strong(&selfc->tile_entries, &nil, tile_entries)){
        /* Another thread won the race. We throw away ours. */
        free(tile_entries);
    }

    return 1;
}


/** Initialize `tiles`

    This function may be called in parallel.

    Returns
    -------
    success
        True if succeeded.
*/
static _Bool CFitsTiledHduDecoder_initialize_tiles(
    struct CFitsTiledHduDecoder *selfc
){
    if(selfc->tiles){
        return 1;
    }

    size_t nb_tiles = selfc->num_tiles * sizeof(selfc->tiles[0]);
    char* _Atomic* tiles = (char* _Atomic*)malloc_untracked_by_fanalyzer(nb_tiles);
    if(!tiles){
        errno = ENOMEM;
        return 0;
    }

    memset(tiles, 0, nb_tiles);

    char* _Atomic* nil = NULL;
    if(!atomic_compare_exchange_strong(&selfc->tiles, &nil, tiles)){
        /* Another thread won the race. We throw away ours. */
        free(tiles);
    }

    return 1;
}


/** Gets decoded tile (y, x).

    This function may be called in parallel.

    Parameters
    ----------
    file
        File to read.
    y
        vertical index of the tile to get.
    x
        horizontal index of the tile to get.

    Returns
    -------
    tile
        Decoded tile image.
*/
static char* CFitsTiledHduDecoder_get_tile(
    struct CFitsTiledHduDecoder *selfc,
    struct IRegFile             *file,
    size_t                      y,
    size_t                      x
){
    if(!selfc->tiles){
        if(!CFitsTiledHduDecoder_load_tile_entries(selfc, file)){
            return NULL;
        }
        if(!CFitsTiledHduDecoder_initialize_tiles(selfc)){
            return NULL;
        }
    }

    size_t tilepos = selfc->num_tiles_along_x * y + x;

    {
        char* tile = selfc->tiles[tilepos];
        if(tile){
            return tile;
        }
    }

    size_t nread = selfc->tile_entries[2*tilepos];
    size_t offset = selfc->tile_entries[2*tilepos + 1] + selfc->physical_offset_of_heap;
    size_t tilesize = selfc->element_size * selfc->tile_width * selfc->tile_height;

    /* In `tile` buffer, compressed data will be stored first.
        Then, it will be decompressed into `tile_uncompressed`,
        and then it will be decoded back into `tile`.
        Therefore, the length of `tile` buffer must be
        max((size of compressed data), (size of uncompressed data))
    */
    char* tile = (char*)malloc((nread > tilesize) ? nread : tilesize);
    if(!tile){
        errno = ENOMEM;
        return NULL;
    }
    char* tile_uncompressed = (char*)malloc(tilesize);
    if(!tile_uncompressed){
        free(tile);
        errno = ENOMEM;
        return NULL;
    }

    if(nread != file->vtbl->read(
        file,
        tile,
        nread,
        offset
    )){
        free(tile);
        free(tile_uncompressed);
        errno = EILSEQ;
        return NULL;
    }

    int64_t ndecoded = (int64_t)tilesize;
    if(Z_OK != inflate_gzip_64((uint8_t*)tile_uncompressed, &ndecoded, (uint8_t*)tile, nread)){
        free(tile);
        free(tile_uncompressed);
        errno = EILSEQ;
        return NULL;
    }

    gzip2_decode(tile_uncompressed, tile, selfc->element_size, tilesize / selfc->element_size);

    free(tile_uncompressed);

    char* nil = NULL;
    if(!atomic_compare_exchange_strong(&selfc->tiles[tilepos], &nil, tile)){
        /* Another thread won the race. We throw away ours. */
        free(tile);
        tile = nil; /* `nil` has the value of `selfc->tiles[tilepos]` */
    }

    return tile;
}


static size_t CFitsTiledHduDecoder_decode_body(
    struct IFitsHduDecoder          *self,
    struct IRegFile                 *file,
    void                            *buf,
    size_t                          size,
    size_t                          logical_offset_in_body
){
    struct CFitsTiledHduDecoder* selfc = (struct CFitsTiledHduDecoder*)self;

    if(size == 0) return 0;

    size_t image_width_in_bytes = selfc->image_width * selfc->element_size;
    size_t tile_width_in_bytes = selfc->tile_width * selfc->element_size;
    size_t xtile_max = selfc->num_tiles_along_x - 1;

    size_t i_start = logical_offset_in_body;
    size_t i_end = logical_offset_in_body + size;

    size_t i_true_end = i_end;

    size_t image_size_in_bytes = image_width_in_bytes * selfc->image_height;
    if(i_end > image_size_in_bytes){
        i_end = image_size_in_bytes;
        /* The interval [i_end, i_true_end) is out of image area,
            filled with padding bytes for alignment */
    }

    if(i_end <= i_start){
        /* all bytes are padding */
        memset((char*)buf, 0, size);
        return size;
    }

    size_t y_start = i_start / image_width_in_bytes;
    size_t x_start = i_start % image_width_in_bytes;

    size_t y_last = (i_end - 1) / image_width_in_bytes;
    size_t x_last = (i_end - 1) % image_width_in_bytes;

    size_t ytile_start = y_start / selfc->tile_height;
    size_t xtile_start = x_start / tile_width_in_bytes;

    size_t ytile_last = y_last / selfc->tile_height;
    size_t xtile_last = x_last / tile_width_in_bytes;

    for(size_t ytile = ytile_start; ytile <= ytile_last; ++ytile){
        size_t xtile_start_in_this_row = (ytile == ytile_start) ? xtile_start : 0;
        size_t xtile_last_in_this_row = (ytile == ytile_last) ? xtile_last : xtile_max;
        size_t offset_of_tile_y = ytile * selfc->tile_height * image_width_in_bytes;

        for(size_t xtile = xtile_start_in_this_row; xtile <= xtile_last_in_this_row; ++xtile){
            size_t rowoffset_of_tile_x = xtile * tile_width_in_bytes;
            size_t rowoffset_of_tile_x_end = rowoffset_of_tile_x + tile_width_in_bytes;
            if(rowoffset_of_tile_x_end > image_width_in_bytes){
                rowoffset_of_tile_x_end = image_width_in_bytes;
            }
            size_t this_tile_width_in_bytes = rowoffset_of_tile_x_end - rowoffset_of_tile_x;

            size_t offset_of_tile_yx = offset_of_tile_y + rowoffset_of_tile_x;

            char* tile = CFitsTiledHduDecoder_get_tile(
                selfc,
                file,
                ytile,
                xtile
            );
            if(!tile){
                if(!errno) errno = EILSEQ;
                return 0;
            }

            for(size_t q = 0; q < selfc->tile_height; ++q){
                size_t offset_of_q = offset_of_tile_yx + q * image_width_in_bytes;
                size_t offset_of_q_end = offset_of_q + this_tile_width_in_bytes;

                if(offset_of_q_end <= i_start) continue;
                if(i_end <= offset_of_q) break;

                size_t copy_start = (offset_of_q < i_start) ? i_start : offset_of_q;
                size_t copy_end = (offset_of_q_end < i_end) ? offset_of_q_end : i_end;

                memcpy(
                    (char*)buf + (copy_start - i_start),
                    tile + q * this_tile_width_in_bytes + (copy_start - offset_of_q),
                    copy_end - copy_start
                );
            }
        }
    }

    memset((char*)buf + (i_end - i_start), 0, i_true_end - i_end);

    return size;
}


/** Parameters used by threads in CFitsTiledHduDecoder_predecode_all_body().
*/
struct CFitsTiledHduDecoder_PredecodeAllBody_ThreadProc_Params
{
    struct CFitsTiledHduDecoder *selfc;
    struct IRegFile             *file;
    size_t                      num_tiles_along_x;
};


/** Thread procedure in CFitsTiledHduDecoder_predecode_all_body().

    Parameters
    ----------
    i
        For-index. It is the ID of a tile.
    params
        `CFitsTiledHduDecoder_PredecodeAllBody_ThreadProc_Params`.
*/
void CFitsTiledHduDecoder_predecode_all_body_threadproc(
    size_t i,
    void* params
){
    struct CFitsTiledHduDecoder_PredecodeAllBody_ThreadProc_Params* args
        = (struct CFitsTiledHduDecoder_PredecodeAllBody_ThreadProc_Params*)params;

    CFitsTiledHduDecoder_get_tile(
        args->selfc,
        args->file,
        i / args->num_tiles_along_x,
        i % args->num_tiles_along_x
    );
}


void CFitsTiledHduDecoder_predecode_all_body(
    struct IFitsHduDecoder          *self,
    struct IRegFile                 *file,
    size_t                          num_threads,
    pthread_mutex_t                 *mutex
){
    struct CFitsTiledHduDecoder* selfc = (struct CFitsTiledHduDecoder*)self;

    size_t const num_tiles = selfc->num_tiles;
    if(num_tiles == 0) return;  /* No tiles */

    if(selfc->tile_entries) return;  /* Already decoded */

    pthread_mutex_lock(mutex);
    do{
        if(selfc->tile_entries) break;

        if(!CFitsTiledHduDecoder_load_tile_entries(selfc, file)){
            break;
        }
        if(!CFitsTiledHduDecoder_initialize_tiles(selfc)){
            break;
        }

        size_t const num_tiles_along_x = selfc->num_tiles_along_x;

        if(num_threads <= 1){
            for(size_t i = 0; i < num_tiles; ++i){
                CFitsTiledHduDecoder_get_tile(
                    selfc,
                    file,
                    i / num_tiles_along_x,
                    i % num_tiles_along_x
                );
            }
        }
        else{
            struct CFitsTiledHduDecoder_PredecodeAllBody_ThreadProc_Params params = {
                .selfc = selfc,
                .file = file,
                .num_tiles_along_x = num_tiles_along_x,
            };
            parallel_for_zu(
                num_threads,
                0,
                num_tiles,
                CFitsTiledHduDecoder_predecode_all_body_threadproc,
                &params
            );
        }
    }
    while(0);
    pthread_mutex_unlock(mutex);
}


/** FITS HDU (header-data unit).

    The entire FITS file is represented by a linked list of this structure.
*/
struct FitsHdu
{
    struct FitsHdu * _Atomic next;

    struct FitsHeader *header;
    struct IFitsHduDecoder* decoder;

    _Bool   next_is_filled;
    int     next_reading_errno; /* error that happened while reading `next` */

    size_t  logical_offset_of_header; /* logical file offset of the header */
    size_t  logical_offset_of_body; /* logical file offset of the body */

    size_t  physical_offset_of_next_hdu; /* physical file offset of the next hdu */
    size_t  logical_offset_of_next_hdu; /* logical file offset of the next hdu */
};


/** Creates an instance of `FitsHdu`.

    The returned instance is initialized to the extent that it is ready to be
    destroyed with `FitsHdu_destroy()`.

    Returns
    -------
    instance
        New instance. NULL if failed.
*/
static struct FitsHdu* FitsHdu_new()
{
    NEW_PTR(block, struct FitsHdu);
    if(!block){
        errno = ENOMEM;
        return NULL;
    }

    block->next = NULL;
    block->header = NULL;
    block->decoder = NULL;

    block->next_is_filled = 0;
    block->next_reading_errno = 0;
    return block;
}


/** Destroys an instance of `FitsHeader`.

    The entire linked list is deleted.

    Parameters
    -------
    hdu
        The first HDU to be destroyed. All subsequent HDUs are also destroyed.
*/
static void FitsHdu_destroy(struct FitsHdu *hdu)
{
    while(hdu != NULL){
        struct FitsHdu *next = hdu->next;

        FitsHeader_destroy(hdu->header);
        if(hdu->decoder){
            hdu->decoder->vtbl->destroy(hdu->decoder);
        }

        free(hdu);
        hdu = next;
    }
}


/** Creates an HDU by reading a file.

    Parameters
    ----------
    file
        File to read.
    physical_offset
        File offset of the header part of the HDU.
    logical_offset
        Logical offset of the header part of the HDU.
        This may be different from `physical_offset` because of compression.
    reading_errno
        (Output) `errno` will be stored.

    Returns
    -------
    hdu
        HDU.
        It being NULL and `*reading_errno` being 0 imply end of file.
        It being NULL and `*reading_errno` being non-0 imply an error.
*/
static struct FitsHdu* FitsHdu_load_from_file(
    struct IRegFile *file,
    size_t          physical_offset,
    size_t          logical_offset,
    int             *reading_errno
){
    *reading_errno = 0;

    size_t physical_offset_of_body = 0;
    struct FitsHeader *header = FitsHeader_read_file(file, physical_offset, &physical_offset_of_body, reading_errno);
    if(!header){
        /* We must not modify *reading_errno here. */
        return NULL;
    }

    struct FitsHdu* hdu = FitsHdu_new();
    if(!hdu){
        FitsHeader_destroy(header);
        *reading_errno = ENOMEM;
        return NULL;
    }

    hdu->header = header;
    /* Hereafter, destruction of `hdu` will lead to destruction of `header` */

    struct FitsEssentialCards essential_cards;
    if(!fits_parse_header(hdu->header, &essential_cards)){
        FitsHdu_destroy(hdu);
        *reading_errno = EILSEQ;
        return NULL;
    }

    errno = EILSEQ;
    if(!hdu->decoder && errno == EILSEQ){
        errno = 0;
        hdu->decoder = CFitsTiledHduDecoder_new(physical_offset_of_body, &essential_cards);
    }
    if(!hdu->decoder && errno == EILSEQ){
        errno = 0;
        hdu->decoder = CFitsPlainHduDecoder_new(physical_offset_of_body);
    }
    if(!hdu->decoder){
        FitsHdu_destroy(hdu);
        *reading_errno = errno;
        return NULL;
    }

    hdu->decoder->vtbl->decode_header(hdu->decoder, &essential_cards, hdu->header);

    size_t physical_body_size = fits_get_physical_body_size(&essential_cards);
    size_t logical_body_size = hdu->decoder->vtbl->get_logical_body_size(hdu->decoder, &essential_cards);
    size_t header_size = physical_offset_of_body - physical_offset;

    hdu->logical_offset_of_header  = logical_offset;
    hdu->logical_offset_of_body = logical_offset + header_size;
    hdu->physical_offset_of_next_hdu = physical_offset_of_body + physical_body_size;
    hdu->logical_offset_of_next_hdu = hdu->logical_offset_of_body + logical_body_size;

    return hdu;
}


/** CFitsFile: FITS file class
*/
struct CFitsFile
{
    struct IRegFile         iface;  /* Interface of this class */
    struct IRegFile         *file; /* regfile class opened by this class */
    struct FitsHdu *_Atomic hdu;
    _Bool                   hdu_is_filled;
    int                     hdu_reading_errno;

    pthread_mutex_t         mutex;

    /* If positive, the entire image will be decoded on the first call to read()
        with this number of threads.
        If zero or negative, only necessary parts will be decoded
        on every call to read() with a single thread
    */
    intptr_t                num_threads;
};


static void CFitsFile_close(struct IRegFile *self);
static int CFitsFile_fstat(struct IRegFile *self, struct stat *statbuf);
static size_t CFitsFile_read(struct IRegFile *self, void* buf, size_t size, size_t offset);

static struct IRegFile_vtbl const CFitsFile_vtbl = {
    .close = CFitsFile_close,
    .fstat = CFitsFile_fstat,
    .read  = CFitsFile_read,
};


struct IRegFile* fitsfile_open(
    char const                          *path,
    struct IDirectory                   *directory,
    struct FitsFileOpenOptions const    *options
){
    NEW_PTR(selfc, struct CFitsFile);
    if(!selfc){
        errno = ENOMEM;
        return NULL;
    }

    selfc->iface.vtbl = &CFitsFile_vtbl;
    selfc->file = regfile_open(path, directory);
    if(!selfc->file){
        free(selfc);
        if(!errno) errno = ENOENT;
        return NULL;
    }

    selfc->hdu = NULL;
    selfc->hdu_is_filled = 0;
    selfc->hdu_reading_errno = 0;

    pthread_mutex_init(&selfc->mutex, NULL);

    selfc->num_threads = options->num_threads;

    return (struct IRegFile*)selfc;
}


static void CFitsFile_close(struct IRegFile *self)
{
    struct CFitsFile* selfc = (struct CFitsFile*)self;

    if(!selfc) return;

    pthread_mutex_destroy(&selfc->mutex);

    struct IRegFile *file = selfc->file;
    selfc->file = NULL;
    if(file){
        file->vtbl->close(file);
    }

    struct FitsHdu *hdu = selfc->hdu;
    selfc->hdu = NULL;
    if(hdu){
        FitsHdu_destroy(hdu);
    }

    free(selfc);
}


int fitsfile_stat(const char *pathname, struct stat *statbuf, struct IDirectory *directory)
{
    struct FitsFileOpenOptions options = {
        .num_threads = 0,
    };
    struct IRegFile* file = fitsfile_open(pathname, directory, &options);
    if(!file){
        if(!errno) errno = EILSEQ;
        return -1;
    }

    int ret = file->vtbl->fstat(file, statbuf);
    int copied_errno = errno;

    file->vtbl->close(file);

    errno = copied_errno;
    return ret;
}


/** Gets the HDU next to `prev`.

    This function may be called in parallel.

    Parameters
    ----------
    prev
        Current HDU.
        This argument may be NULL, in which case the primary HDU is returned.
    reading_errno
        (Output) `errno` will be stored.

    Returns
    -------
    hdu
        HDU next to `prev`.
        It being NULL and `*reading_errno` being 0 imply end of file.
        It being NULL and `*reading_errno` being non-0 imply an error.
*/
static struct FitsHdu* CFitsFile_get_next_hdu(
    struct CFitsFile    *selfc,
    struct FitsHdu      *prev,
    int                 *reading_errno
){
    *reading_errno = 0;
    struct FitsHdu* returned_hdu = NULL;

    if(!prev){
        /* The caller wants the primary HDU */
        returned_hdu = selfc->hdu;
    }
    else{
        /* The caller wants the HDU next to `prev` */
        returned_hdu = prev->next;
    }

    if(returned_hdu){
        return returned_hdu;
    }

    pthread_mutex_lock(&selfc->mutex);
    do{
        if(!prev){ /* The caller wants the primary HDU */
            if(!selfc->hdu){
                if(selfc->hdu_is_filled){
                    *reading_errno = selfc->hdu_reading_errno;
                }
                else{
                    size_t physical_offset = 0;
                    size_t logical_offset = 0;
                    selfc->hdu = FitsHdu_load_from_file(selfc->file, physical_offset, logical_offset, reading_errno);
                    selfc->hdu_is_filled = 1;
                    selfc->hdu_reading_errno = *reading_errno;
                }
            }

            returned_hdu = selfc->hdu;
            break;
        }

        /* The caller wants the HDU next to `prev` */

        if(prev->next_is_filled){
            *reading_errno = prev->next_reading_errno;
        }
        else{
            size_t physical_offset = prev->physical_offset_of_next_hdu;
            size_t logical_offset = prev->logical_offset_of_next_hdu;
            prev->next = FitsHdu_load_from_file(selfc->file, physical_offset, logical_offset, reading_errno);
            prev->next_is_filled = 1;
            prev->next_reading_errno = *reading_errno;
        }

        returned_hdu = prev->next;
        break;
    }
    while(0);
    pthread_mutex_unlock(&selfc->mutex);

    return returned_hdu;
}


static int CFitsFile_fstat(struct IRegFile *self, struct stat *statbuf)
{
    struct CFitsFile* selfc = (struct CFitsFile*)self;

    struct FitsHdu* hdu = NULL;
    struct FitsHdu* last_hdu = hdu;

    int reading_errno = 0;

    do{
        last_hdu = hdu;
        hdu = CFitsFile_get_next_hdu(selfc, last_hdu, &reading_errno);
    }
    while(hdu != NULL);

    if(reading_errno){
        errno = reading_errno;
        return -1;
    }

    int ret = selfc->file->vtbl->fstat(selfc->file, statbuf);
    if(ret != 0){
        return ret;
    }

    if(last_hdu != NULL){
        statbuf->st_size = last_hdu->logical_offset_of_next_hdu;
    }

    return 0;
}


static size_t CFitsFile_read(struct IRegFile *self, void* buf, size_t size, size_t offset)
{
    struct CFitsFile* selfc = (struct CFitsFile*)self;

    size_t const original_size = size;
    size_t const offset_of_end = offset + size;

    struct FitsHdu* hdu = NULL;
    int reading_errno = 0;

    while(size > 0){
        hdu = CFitsFile_get_next_hdu(selfc, hdu, &reading_errno);
        if(!hdu){
            break;
        }

        size_t logical_hdu_end = hdu->logical_offset_of_next_hdu;
        if(logical_hdu_end <= offset){
            continue;
        }

        assert(hdu->logical_offset_of_header <= offset); /* loop invariance */

        if(offset < hdu->logical_offset_of_body){
            /* header must be copied */
            size_t copy_start = offset;
            size_t copy_end = (hdu->logical_offset_of_body < offset_of_end) ? hdu->logical_offset_of_body : offset_of_end;

            size_t logical_offset_in_header = copy_start - hdu->logical_offset_of_header;
            size_t logical_size = copy_end - copy_start;

            FitsHeader_copy_to_buffer(hdu->header, buf, logical_size, logical_offset_in_header);

            offset = copy_end;
            size -= logical_size;
            buf = (char*)buf + logical_size;

            if(size == 0) break;
        }

        assert(hdu->logical_offset_of_body <= offset);

        /* body must be copied */

        if(selfc->num_threads > 0){
            hdu->decoder->vtbl->predecode_all_body(
                hdu->decoder,
                selfc->file,
                selfc->num_threads,
                &selfc->mutex
            );
        }

        size_t copy_start = offset;
        size_t copy_end = (logical_hdu_end < offset_of_end) ? logical_hdu_end : offset_of_end;

        size_t logical_offset_in_body = copy_start - hdu->logical_offset_of_body;
        size_t logical_size = copy_end - copy_start;

        size_t ndecoded = hdu->decoder->vtbl->decode_body(
            hdu->decoder,
            selfc->file,
            buf,
            logical_size,
            logical_offset_in_body
        );

        if(ndecoded != logical_size){
            reading_errno = EILSEQ;
            break;
        }

        offset = copy_end;
        size -= logical_size;
        buf = (char*)buf + logical_size;
    }

    if(reading_errno == 0){
        return original_size - size;
    }
    else{
        return -reading_errno;
    }
}
