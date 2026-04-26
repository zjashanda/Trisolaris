#pragma once

#include <stdint.h>

#if defined(_MSC_VER)                 /* Microsoft Visual C++ */
#	if !defined(SPARK_BIND_API_FOR_IVW)
#		define SPARK_BIND_API_FOR_IVW __stdcall
#	endif
#	pragma pack(push, 8)
#else                                          /* Any other including Unix */
#	if !defined(SPARK_BIND_API_FOR_IVW) 
#		define SPARK_BIND_API_FOR_IVW  __attribute__ ((visibility("default")))
#	endif
#endif

typedef  void* SPARK_BIND_HANDLE;

struct  SparkBindParams
{
    const char *key;
    const char *value;
};


struct SparkBindBuffer
{
    const static int32_t MAX_DATA = 16;
    const static int32_t MAX_PARAMS = 64;
    int32_t data_num;
    int32_t params_num;
    void * data[MAX_DATA];
    int32_t data_len[MAX_DATA];
    SparkBindParams params[MAX_PARAMS];
};

struct SparkResultBuffer
{
    const static int32_t MAX_DATA = 16;
    int32_t data_num;
    void * data[MAX_DATA];
    int32_t data_len[MAX_DATA];
};

#ifdef __cplusplus
extern "C" {
#endif
    SPARK_BIND_HANDLE SPARK_BIND_API_FOR_IVW spark_bind_init(int32_t argc,const SparkBindParams* params);

    int32_t SPARK_BIND_API_FOR_IVW spark_bind_do_jobs(SPARK_BIND_HANDLE handle,const SparkBindBuffer *bufs,int32_t jobs_num,SparkResultBuffer **rlt);

    void SPARK_BIND_API_FOR_IVW spark_bind_uninit(SPARK_BIND_HANDLE handle);
#ifdef __cplusplus
};
#endif

/* Reset the structure packing alignments for different compilers. */
#if defined(_MSC_VER)                /* Microsoft Visual C++ */
#	pragma pack(pop)
#endif

