#ifndef __W_IVW_H__
#define __W_IVW_H__
#include "ivw_defines.h"
#include "ivw_type.h"

typedef void *WIVW_INST;
#include "ivw_struct.h"

#ifdef __cplusplus
extern "C" {
#endif /* __cplusplus */


WIVW_API ivInt wIvwGetInfo(_Out const PIvwInfo pInfo, _In PIvwRes pIvwRes);

WIVW_API int32_t wIvwCreate(_Out WIVW_INST *wIvwInst, _Inout const PIvwInitParam pInitParam);

WIVW_API int32_t wIvwDestroy(_In WIVW_INST wIvwInst);

WIVW_API int32_t wIvwSetParameter(_In WIVW_INST wIvwInst, _In int32_t param, _In int32_t value);

WIVW_API int32_t wIvwGetParameter(_In WIVW_INST wIvwInst, _In int32_t param, _Out int32_t *value);

WIVW_API int32_t wIvwSetDebugDir(_In WIVW_INST wIvwInst, _In const ivChar *dir, _In const ivChar *name);

WIVW_API int32_t wIvwRegisterCallBacks(_In WIVW_INST wIvwInst, _In ECallBackType FuncType, _In const PIVWCallBack pFunc, _In void *pUserParam);

WIVW_API int32_t wIvwUnRegisterCallBacks(_In WIVW_INST wIvwInst, _In ECallBackType FuncType);

WIVW_API int32_t wIvwStart(_In WIVW_INST wIvwInst, _In EResetType reset_type);

WIVW_API int32_t wIvwStop(_In WIVW_INST wIvwInst);

WIVW_API int32_t wIvwWrite(_In WIVW_INST wIvwInst, _In const short *samples, _In int32_t nSamplesInChar);

WIVW_API int32_t wIvwRegistWrite(_In WIVW_INST wIvwInst, _In const short *samples, _In int32_t nSamplesInChar, _In tIvwRegistInfo *pRegistInfo, _Out int8_t *flag, _Out TRegistTmp *pIvwRegistTmp);

WIVW_API int32_t wIvwRegistArbitrate(WIVW_INST wIvwInst, TRegistTmp *pIvwRegistReses, int32_t nNumRegistRes, TRegistRes *pOutRes);
#if 0
WIVW_API int32_t wIvwRegistDelete(_In WIVW_INST wIvwInst, _In tIvwRegistInfo *pRegistInfo, _Out pIvwRegistResMgr pRegistResMgr);
#endif
WIVW_API int32_t wIvwGetStatus(_In WIVW_INST wIvwInst, _In EStatusID eStatusId, _Out void *rst, _Inout int32_t *nBufLen);


#ifdef __cplusplus
}
#endif /* __cplusplus */

#endif //__W_IVW_H__

