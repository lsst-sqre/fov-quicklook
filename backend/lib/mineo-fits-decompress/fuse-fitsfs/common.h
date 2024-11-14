#ifndef uuid_2e1b9ed2_ed51_4c93_b5f1_66bb2453ba2e
#define uuid_2e1b9ed2_ed51_4c93_b5f1_66bb2453ba2e

#include <stdlib.h>

/** Declares a pointer and set a newly allocated instance to it.

    Parameters
    ----------
    varname
        Variable name.
    reftype
        Dereferenced type. (e.g. `char` for `char*`).
*/
#define NEW_PTR(varname, reftype)  reftype* varname = (reftype*)malloc(sizeof(reftype))

/** Declare a pointer and set a newly allocated array to it.

    Parameters
    ----------
    varname
        Variable name.
    elemtype
        Element type.
    nelem
        Number of elements.
*/
#define NEW_ARRAY(varname, elemtype, nelem)  elemtype* varname = (elemtype*)malloc((nelem) * sizeof(elemtype))

#endif /* uuid_2e1b9ed2_ed51_4c93_b5f1_66bb2453ba2e */
