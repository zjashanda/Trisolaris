#ifndef __STACK_DEFINES_H__
#define __STACK_DEFINES_H__

#include <stdio.h>
#include <stdlib.h>

#define STACK_CHECK_ON (0)
#define PRINT_STACK_FUN (0)

#if STACK_CHECK_ON


typedef struct tagStackInst
{
	char stack_tag[128];
	char* __stack_base__;
	int __stack_current_max_used__;
	int __stack_total_max_used__;
}TStackInst;

extern TStackInst gStackInst;

#define STACK_CHECK_INIT()         \
    do {                                       \
        char __stack_init_local__;             \
        gStackInst.__stack_base__ = &__stack_init_local__; \
        gStackInst.__stack_current_max_used__ = 0;                \
		memset(gStackInst.stack_tag, 0, sizeof(gStackInst.stack_tag)); \
    } while (0)

#define STACK_CHECK_UPDATE()                               \
    do {                                                   \
        if (gStackInst.__stack_base__) {                   \
            char __stack_curr__;                           \
            int __used__ = (int)(gStackInst.__stack_base__ - &__stack_curr__); \
            if (__used__ > gStackInst.__stack_current_max_used__)               \
                gStackInst.__stack_current_max_used__ = __used__;               \
				strcpy(gStackInst.stack_tag, __FUNCTION__); \
				if (PRINT_STACK_FUN) {						\
					printf("%s, stack:%d\n", __FUNCTION__, __used__); \
				}													\
        }                                                  \
    } while (0)

#define STACK_GET_MAX_USED()  \
	if (gStackInst.__stack_current_max_used__ > gStackInst.__stack_total_max_used__) { \
		gStackInst.__stack_total_max_used__ = gStackInst.__stack_current_max_used__;	\
		printf("[%s][%s] MAX_STACK:%d\n", __FUNCTION__, gStackInst.stack_tag, gStackInst.__stack_current_max_used__); \
	}

#else
#define STACK_CHECK_INIT()
#define STACK_CHECK_UPDATE() 
#define STACK_GET_MAX_USED()
#endif

#endif
