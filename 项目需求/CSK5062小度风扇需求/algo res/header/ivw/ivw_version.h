//#ifndef __IVW_VERSION__
//#define __IVW_VERSION__
//#define IVW_VERSION  "4.1.1.0.3.1"
//#endif


#ifndef __IVW_VERSION__
#define __IVW_VERSION__
#include "w_res/res_mgr.h"
 
#define VE_TO_STR1(R)  #R
#define VE_TO_STR(R)  VE_TO_STR1(R)

#define IVW_ENGINE_NAME  "mini-esr-"

#define IVW_VERSION  "5.1.2.1.7.2"

#ifndef IVW_RELEASE
#define IVW_RELEASE			"beta"
#endif

#define  IVW_VERSION_STR		IVW_ENGINE_NAME PLATFORM_SET " Tag" IVW_VERSION "_%d"  \
	"," __DATE__  "," __TIME__

#endif
