#include "common.h"
#include "parallel_for.h"

#include <pthread.h>

#include <stdlib.h>


/** Parameters of `parallel_for_threadproc_zu` function.
*/
struct ParallelFor_ThreadProcParam_zu
{
    size_t begin;
    size_t end;
    size_t stride;
    void (*body)(size_t i, void* params);
    void  *body_params;
};


/** `pthread_create()`-type thread procedure
    used by `parallel_for_zu()`

    This function does this:

        for(i = begin; i < end; i += stride){
            body(body_params);
        }

    Parameters
    ----------
    params
        `struct ParallelFor_ThreadProcParam_zu`.

    Returns
    -------
    null
        Always null.
*/
void* parallel_for_threadproc_zu(void* params)
{
    struct ParallelFor_ThreadProcParam_zu* args
        = (struct ParallelFor_ThreadProcParam_zu*)params;

    size_t i      = args->begin ;
    size_t end    = args->end   ;
    size_t stride = args->stride;
    void (*body)(size_t i, void* params) = args->body;
    void  *body_params = args->body_params;

    for(; i < end; i += stride){
        body(i, body_params);
    }

    return NULL;
}


_Bool parallel_for_zu(
    size_t num_threads,
    size_t begin,
    size_t end,
    void (*body)(size_t i, void* params),
    void  *params
){
    if(num_threads > end - begin){
        num_threads = end - begin;
    }

    if(num_threads <= 1){
        for(size_t i = begin; i < end; ++i){
            body(i, params);
        }
        return 1;
    }

    NEW_ARRAY(threads, pthread_t, num_threads);
    if(!threads){
        return 0;
    }

    NEW_ARRAY(threadparams, struct ParallelFor_ThreadProcParam_zu, num_threads);
    if(!threadparams){
        free(threads);
        return 0;
    }

    size_t i;
    for(i = 0; i < num_threads; ++i){
        threadparams[i].stride      = num_threads;
        threadparams[i].begin       = begin + i  ;
        threadparams[i].end         = end        ;
        threadparams[i].body        = body       ;
        threadparams[i].body_params = params     ;

        if(0 != pthread_create(
            &threads[i],
            NULL,
            parallel_for_threadproc_zu,
            &(threadparams[i])
        )){
            break;
        }
    }

    size_t num_created_threads = i;

    for(i = 0; i < num_created_threads; ++i){
        pthread_join(threads[i], NULL);
    }

    free(threadparams);
    free(threads);

    return num_threads == num_created_threads;
}
