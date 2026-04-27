#ifndef __IVW_TYPE_H__
#define __IVW_TYPE_H__

#include "ivw_defines.h"

#define MAX_CHANNEL_COUNT (1)

typedef enum
{
	CallBackFuncNameWakeUpChannel0 = 0,
	CallBackFuncNameWakeUpChannel1,
	CallBackFuncNameWakeUpChannel2,
	CallBackFuncNamePreWakeUpChannel0 = MAX_CHANNEL_COUNT,
	CallBackFuncNamePreWakeUpChannel1,
	CallBackFuncNamePreWakeUpChannel2,
	CallBackFuncNameGetResult = 2 * MAX_CHANNEL_COUNT,
	CallBackFuncNameVadBegin,
	CallBackFuncNameVadEnd,
	CallBackFuncNameWavProcessd,
	CallBackFuncNameOrigWakeUpChannel0 = 2 * MAX_CHANNEL_COUNT + 4,
	CallBackFuncNameOrigWakeUpChannel1,
	CallBackFuncNameOrigWakeUpChannel2,
	CallBackFuncNameLogPcmChannel0 = 3 * MAX_CHANNEL_COUNT + 4,
	CallBackFuncNameLogPcmChannel1,
	CallBackFuncNameLogPcmChannel2,
	CallBackFuncNameWakeUpEndPointDelay = 4 * MAX_CHANNEL_COUNT + 4, 
	CallBackFuncPreIntentChannel0 = 5 * MAX_CHANNEL_COUNT + 4,
	CallBackFuncPreIntentChannel1,
	CallBackFuncPreIntentChannel2,
#ifdef RESEARCHER_MODE
	//WDEC_WAKEUP_TOPN
	CallBackFuncNameTopNWakeUp = 4 * MAX_CHANNEL_COUNT + 5,
	//HTK_DUMP_MLP_POSTERIOR
	CallBackFuncHtkDumpMlpFea,
	CallBackFuncHtkDumpMlpFeaMultitask,
	//HTK_DUMP_FEA
	CallBackFuncHtkDumpFea,
	CallBackFuncNameCount = 4 * MAX_CHANNEL_COUNT + 9
#else
	CallBackFuncNameCount = 5 * MAX_CHANNEL_COUNT + 5
#endif
}ECallBackType;

typedef enum
{
	DEFAULT_RESET = 0, // 仅重置解码模块
	ALL_RESET		   // 重置所有功能模块
}EResetType;

typedef int32_t (*PIVWCallBack)(const char* pIvwParam, void *pUserParam);

typedef enum
{
	SID_LAST_WAKE_RLT = 0,		// 最后一次唤醒结果
	SID_PRIOR_DATA				// 模型中的先验信息
}EStatusID;

#define MAX_RES_NUMS (8)
#define MIN_REGIST_WORD (2)
#define MAX_REGIST_WORD (10)
#define MIN_REGIST_STATES (MIN_REGIST_WORD * 2)
#define MAX_REGIST_STATES (MAX_REGIST_WORD * 2)
#define MAX_REGIST_STATES_TEMP (MAX_REGIST_STATES + 9) // foor(MAX_REGIST_STATES * 0.45 + 0.5)
#define MAX_REGIST_STRING (48)
#define RES_HEADER_SIZE (96)

typedef enum
{
	E_HIGH = 0,
	E_MID,
	E_LOW
}ESensitivity;

typedef enum
{
	E_DATA_FEA_NO_NORM = 0,				// 特征数据
	E_DATA_FEA_NORM,
	E_DATA_FEA_POSTER
}EDataType;

typedef enum
{
	ASR_MODE = 0,
	WAKEUP_MODE,
}WakeupMode;

typedef enum
{
	MAIN = 0,
	ASR,
}KeywordType;

typedef enum {
	E_BRANCH_NROMAL = 0,	// T+16唤醒分支
	E_BRANCH_MULTITASK,		// Multitask唤醒分支(T分支)
	E_BRANCH_FREESP,		// 自由说分支
	E_BRANCH_E2E,			// 主唤醒端到端分支
	E_BRANCH_MLC_E2E,		// 命令词端到端分支
	E_BRANCH_MAIN_SLOT,		// SLOT分支
	E_BRANCH_MLC_SLOT,		// SLOT分支
	E_BRANCH_REJECT_SLOT,		// SLOT分支
	E_BRANCH_RECALL_SLOT,		// SLOT分支
	E_BRANCH_RECORRECT_SLOT,	// SLOT分支
	E_BRANCH_MLC_REGIST_E2E,		// 命令词端到端分支
}EIvwBranchType;

typedef enum
{
	INDEX_MLP_CONFIDENCE = 0,
	INDEX_WFSA,
	INDEX_KEYWORD_MAIN,
	INDEX_KEYWORD_ASR,
	INDEX_MLP_CNN,
	INDEX_MLP_UNET,
	INDEX_KEYWORD_CUSTOM,
	INDEX_KEYWORD_VOICE,
}EIvwResIndex;

typedef enum
{
	THRESHOLD_GRADE_Normal = 0,//Normal
	THRESHOLD_GRADE_Hard,	//hard
}ThresholdGrade;


#endif
