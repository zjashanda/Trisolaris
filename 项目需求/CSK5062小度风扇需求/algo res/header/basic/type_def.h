#pragma once

/* data type */
typedef char str64[64];

/* macro */
#ifdef WIN32
#include <crtdbg.h>
#define W_ASSERT						_ASSERT
#define W_INLINE						__inline
#define W_ASSERT_EQUAL(x, y, epsion)	_ASSERT( fabs(x-y) < epsion)
#else
#define W_ASSERT						assert
#define W_INLINE						inline
#define W_ASSERT_EQUAL(x, y, epsion)	assert(fabs(x-y) < epsion)
#endif

#ifdef __USE_CASTOR_MVA__
#define mva_relu mva_relu_q15_int8
#endif

typedef struct __Q_Fix
{
	int Q_Mat;
	int Q_In;
}Q_Fix, *pQ_Fix;
