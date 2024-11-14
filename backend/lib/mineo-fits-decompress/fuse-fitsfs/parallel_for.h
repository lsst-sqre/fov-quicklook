#ifndef uuid_3ac472d8_7f86_4b3e_803f_874243f63559
#define uuid_3ac472d8_7f86_4b3e_803f_874243f63559

#include <stddef.h>


/** Execute the following construction in parallel:

    for(i = begin; i < end; ++i){
        body(i, params);
    }

    This is size_t (zu) version.

    Parameters
    ----------
    num_threads
        Number of threads.
    begin
        The first `i`.
    end
        One past the last `i`.
    body
        Function to be executed.
    params
        Parameters passed to `body`.

    Returns
    -------
    success
        True if succeeded.
*/
_Bool parallel_for_zu(
    size_t num_threads,
    size_t begin,
    size_t end,
    void (*body)(size_t i, void* params),
    void  *params
);

#endif /* uuid_3ac472d8_7f86_4b3e_803f_874243f63559 */
