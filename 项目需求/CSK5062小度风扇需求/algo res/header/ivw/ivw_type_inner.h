#ifndef __IVW_TYPE_INNER_H__
#define __IVW_TYPE_INNER_H__
#include "ivw_defines.h"
typedef enum
{
	CHANNEL0 = 0,
	CHANNEL1,
	CHANNEL2,
	DUAL_CHANNEL,
	NONE
}ChannelId;

typedef struct WakeUpEndStateInfo_
{
	int8_t		bOpenWakeUpEndStateDelay;
	int8_t		nDefaultJudgeMentTopN;
	int8_t		nDefaultContinueFrame;
	int8_t		nDefaultMaxDelayFrame;

	int8_t		bWakeUp;
	int16_t		nWakeUpId;
	int16_t		nWakeUpEndState;
	int8_t		wake_up_rlt_buf[IVW_MAX_STR_BUF_LEN];
	int32_t		nUpDateWakeFrame;
	int32_t		nWakeUpFinalAddFrame;
	int32_t		nContinueWakeUpEndStateFrame;
}WakeUpEndStateInfo;

typedef struct nBestStateScore_
{
	int16_t likelyHood;
	int16_t index;
}nBestStateScore;


#endif
