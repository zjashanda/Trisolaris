#ifndef __BASIC_DEFINES_H__
#define __BASIC_DEFINES_H__

#define  MD5_LEN				     (32)
#define  MAX_STATE_COUNT_ARC		 (2)
#define  W_LOG_ZERO					(-0x3FFFFFFF)
#define  W_LOG_ZERO_SHORT			(-0xFFFF)
#define  W_MAX_WORD_SCORE			(0xFFFF)

#define ivMax(a,b)  (((a)>(b))?(a):(b))
#define ivMin(a,b)  (((a)<(b))?(a):(b))

#ifdef _WIN32
#include <assert.h>
//#define IV_ASSERT(exp)			_ASSERT(exp)
#define IV_ASSERT(exp)			assert(exp)
#if _MSC_VER<1900
#define snprintf _snprintf
#endif
#else
#define IV_ASSERT(exp)			
#define HMODULE	void*
#endif


#define STRING2(x) #x
#define STRING(x) STRING2(x)
#define MLP_ALIGN_SIZE_32			(32)

#ifdef _MSC_VER
// For The Compile Infomation
#define To_msg(msg)	__FILE__ "(" STRING(__LINE__) ") : "##msg
#define CompileMsg(msg) 	__pragma(message(To_msg("#######"##msg##"######")))
#else
#define CompileMsg(msg)
#endif

#define RDeclareApi(func)		extern Proc_##func  func##_;
#define DeclareApi(func)		Proc_##func  func##_;

//sglog_error_assert_return(0, ("GetProcAddress | err, %s = NULL", #func), -1); 
#ifdef __GNUC__
#define GetProcAddress dlsym
#endif

#define GetProcApi(func)\
	{\
	func##_ = (Proc_##func)GetProcAddress(hand, #func);\
	if(func##_ == NULL)\
		{\
			printf("GetProcAddress | err, %s = NULL", #func); \
			return -1; \
		}\
	}
#define GetProcApiVar(func)\
	{\
	func##_ = (Proc_##func)( func);\
	}

#ifdef __cplusplus

#define DISALLOW_COPY_AND_ASSIGN(T)   T(T const&);   T& operator=(T const&){ return *this;}
#define MAKE_SINGLETON_NO_CONSTRUCT(T)   static T& get_inst(){	static T inst;	return inst;}
#define MAKE_SINGLETON(T)   T(){} static T& get_inst(){	static T inst;	return inst;}

#else

#ifdef _MSC_VER
typedef unsigned char bool;
#	define true		1
#	define false	0
#else
#	include	<stdbool.h>
#endif

#endif

#endif
