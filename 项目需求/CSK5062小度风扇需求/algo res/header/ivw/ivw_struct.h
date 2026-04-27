#ifndef __IVW_STRUCT_H__
#define __IVW_STRUCT_H__

#include "ivw_type.h"

#define _IN_VAR_
#define _OUT_VAR_
#define _IN_OUT_VAR_

typedef struct _WakeUpResult
{
	int32_t iFrameStart_;
	int32_t nFrameDuration_;
	int32_t nFillerScore_;
	int32_t nKeyWordScore_;

	int32_t nCM_Thresh_;
	int32_t nCM_;
	int32_t iResID_;
	char  pSzLabel_[64];
}TWakeUpResult;

typedef struct _TIvwInfo
{
	_OUT_VAR_ int32_t share_mem_size;				// 共享内存大小，必须在sharemem中分配 
	_OUT_VAR_ int32_t inst_mem_size;				// 实例内存大小，可以在psram、sram或者sharemem中分配

	_OUT_VAR_ int32_t input_pcm_channel;			// 输入音频通道数
	_OUT_VAR_ int32_t input_pcm_frame_count;		// 输入音频帧数
	_OUT_VAR_ int32_t input_pcm_frame_ms;			// 输入音频每帧的时长(单位ms)
	_OUT_VAR_ int32_t input_pcm_bit;				// 输入音频采样精度
	_OUT_VAR_ int32_t input_pcm_sample_rate;		// 输入音频采样率

	_OUT_VAR_ int32_t output_frame_ms;		        // 输出结果帧长(单位ms)

	_OUT_VAR_ int32_t main_word_count;			// 主唤醒词数量
	_OUT_VAR_ int32_t asr_word_count;			// 命令词数量

	_OUT_VAR_ int32_t mlp_res_type;			// 声学模型类型

	_OUT_VAR_ char  version[64];					// 版本描述

	_IN_OUT_VAR_ int32_t max_regist_num;				// 输入参数，最大注册数量
}TIvwInfo, *PIvwInfo;

typedef struct _TRegistRes
{
	char weight[64];
	short salt;
	short threshold_main;
	short threshold_asr;
	char type;
	char weight_q;
	char keyword[4];
	unsigned int intent_crc32;
	//char reserved[4];

}TRegistRes, *PRegistRes;

typedef struct _TRegistTmp
{
	char weight_t[12 * 64];
	short weight_t_num;
	short salt;
	short threshold_main;
	short threshold_asr;
	char type;
	char weight_q;
	char keyword[4];
	unsigned int intent_crc32;

}TRegistTmp, *PRegistTmp;


typedef struct TagIvwRegistResHeader
{
	int	header[RES_HEADER_SIZE / 4];

}tIvwRegistResHeader, *pIvwRegistResHeader;

typedef struct TagIvwRegistResMgr
{
	tIvwRegistResHeader res_head_param;
	short count;
	short fill[15];
	TRegistRes     *ivw_regist_res;
}tIvwRegistResMgr, *pIvwRegistResMgr;

typedef struct TagIvwRegistInfo
{
	const char *intentStr;
	char intentStrLen;
	char type;
	char sensitivity;
	char maxWords;
	char minWords;
}tIvwRegistInfo, *pIvwRegistInfo;

typedef struct _TIvwRes
{
	uint32_t		res_size_arr_[MAX_RES_NUMS];   // 唤醒资源大小
	char*   		res_buf_arr_[MAX_RES_NUMS];	   // 唤醒资源存放地址
}TIvwRes, *PIvwRes;

typedef struct _TIvwInitParam
{
	char *		share_mem_addr;			// 共享内存起始地址
	char *		inst_mem_addr;			// psram起始地址
	int32_t		share_mem_size;			// 外部申请的共享内存大小
	int32_t       inst_mem_size;			// 外部申请的psram内存大小
	int32_t       share_mem_size_used;	// 唤醒库中实际使用的sharemem内存大小
	int32_t       inst_mem_size_used;		// 唤醒库中实际使用的psram内存大小
	TIvwRes		ivw_res;				// 资源(包括mlp、keywod_main、keyword_asr)
	PIvwInfo	info;					// 唤醒信息（调用wIvwwIvwGetInfo接口获取的)
}TIvwInitParam, *PIvwInitParam;

#define MAX_EXTRA_DATA (2)
typedef struct _TIvwExtraData
{
	EDataType   data_type;				// 数据类型
	int32_t		frame;					// 帧数
	int32_t		dim;					// 维度
	void *		data[MAX_EXTRA_DATA];	// 数据地址
}TIvwExtraData, *PIvwExtraData;
#endif
