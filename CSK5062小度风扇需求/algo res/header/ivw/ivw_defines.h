#ifndef __IVW_DEFINES_H__
#define __IVW_DEFINES_H__

#include "ivw_log.h"
#include "stack_defines.h"

#if !((defined _WIN32) || (defined _WIN64) || (defined __LINUX__))
#include <stdint.h>
#endif

#ifdef __GNUC__
#define WIVW_API __attribute__((visibility ("default")))
#elif defined(_MSC_VER) && defined(_DLL)
#define WIVW_API __declspec(dllexport)
#else
#define WIVW_API
#endif

#define  _In
#define  _Out
#define  _Inout

typedef	char				ivBool;		

typedef unsigned long long	ivULongLong;
typedef signed long long	ivLongLong;


#if ((defined _WIN32) || (defined _WIN64) || (defined __LINUX__))
typedef	signed char			int8_t;		/* 8-bit */
typedef	unsigned char		uint8_t;	/* 8-bit */
typedef	signed short		int16_t;	/* 16-bit */
typedef	unsigned short		uint16_t;	/* 16-bit */
typedef	signed int			int32_t;	/* 32-bit */
typedef	unsigned int		uint32_t;	/* 32-bit */
#endif


typedef	signed char			ivInt8;		/* 8-bit */
typedef	unsigned char		ivUInt8;	/* 8-bit */
typedef	char				ivChar;		/* 8-bit */
typedef	unsigned char		ivUChar;	/* 8-bit */


typedef	signed short		ivInt16;	/* 16-bit */
typedef	unsigned short		ivUInt16;	/* 16-bit */
typedef	signed short		ivShort;	/* 16-bit */
typedef	unsigned short		ivUShort;	/* 16-bit */

typedef	signed int			ivInt32;	/* 32-bit */
typedef	unsigned int		ivUInt32;	/* 32-bit */
typedef	signed int			ivInt;	/* 32-bit */
typedef	unsigned int		ivUInt;	/* 32-bit */
typedef void				ivVoid;

typedef float               ivFloat;  /* 32-bit */

#ifdef IV_TYPE_INT64
typedef	signed long long	ivInt64;	/* 64-bit */
typedef	unsigned long long 	ivUInt64;	/* 64-bit */
#endif

#endif
