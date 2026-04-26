#ifndef __IVW_DEFINES_INNER_H__
#define __IVW_DEFINES_INNER_H__

#define SIZEOF_CHAR					(1)
#define SIZEOF_SHORT				(2)
#define SIZEOF_INT					(4)

#define FA_FOLDER_PATH "fa_folder_path"
#define WKAEUP_MLP_POSTERIOR_PATH "confidence_posterior_rlt"
#define WKAEUP_SYLLABLE_PATH "syllable_posterior_rlt"

#define IVW_ONCE_FRAME_SIZE         (8)

#define IVW_MAX_STR_BUF_LEN	(512)

#define MAX_REF_CHANNEL (0)

#define IVW_FIXED_WRITE_BUF_LEN_N_FRAMES        (160 * IVW_ONCE_FRAME_SIZE) 
#define IVW_FIXED_WRITE_BUF_LEN_1_FRAMES		(160)

#define IVW_FIXED_WRITE_BUF_LEM_NCHANNEL        (IVW_FIXED_WRITE_BUF_LEN_1_FRAMES * MAX_CHANNEL_COUNT * sizeof(short))
#define IVW_MULTITASK_FRAME_COUNT               (4)

#define MAX_E2E_SCORE_CACHE_SIZE				(15 + 2) //15(e2e_score_buffer_size) + 2(win)
#define MAX_REGIST_CACHE_SIZE					(13 + 2)

#define CONV_OUT_CACHE_NUM						(8) //切命令词模式时解码爆发计算缓存后验帧数
#define MAX_CHANNEL_COUNT						(1)
#define MAX_SYLLABLE_INFO_TOPN					(10)
#define MAX_SYLLABLE_POS_SIZE					(16)//(420)

#define USE_PCEN_FEATURE						(1)

#define DEC_FEA_CACHE_NUM						(64) //子词置信度计算缓存后验帧数
#define CONV_OUT_DIM							(178) //3003
#define ALIGN_OFFSET(OFFSET, ALIGN)				((OFFSET + ALIGN - 1) & ~(ALIGN - 1))

#define VOICE_REGIST_UES_CONSONANT				 (0)

#if ((defined _WIN32) || (defined _WIN64) || (defined __LINUX__))
#define ATTRIBUTE_DATA
#else
#define ATTRIBUTE_DATA //__attribute__ ((section (".data")))
#endif

#define UNET_DELAY_FRAME							(1)
#define FFT_DELAY									(0)
#define TOTAL_DELAY									(UNET_DELAY_FRAME + FFT_DELAY)

/***********param for e2e_syl mlp**************/
#define PRELOAD_WEIGHT_SIZE (32*1024)
#define PRELOAD_BIAS_SIZE (2 * 1024)
#define RES_COPY_OPT (1)

#define LOG_FILE_OPEN								(0)

/***********************************************/
typedef enum
{
	MULTITASK_LEVEL_1 = 0,
	MULTITASK_LEVEL_1TO2 = 1,
	MULTITASK_LEVEL_2TO1 = 2,
	MULTITASK_LEVEL_2 = 3,
}MULTITASK_LEVEL_STATE;

typedef enum
{
	STATE_E2E_PRE_NOT_WAKEUP = 0,//
	STATE_E2E_PRE_WAKEUP = 1,
}E2E_PRE_WAKEUP_STATE;

#endif
