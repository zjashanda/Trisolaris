/** 
 * @file	htk_define.h
 * @brief	
 * 
 * some definitions of struct and function when dealing with htk format files
 * 
 * @author	ptshi@iflytek.com
 * @version	1.0
 * @date	2015/8/19
 * 
 * @see		
 * 
 * <b>History:</b><br>
 * <table>
 *  <tr> <th>Version	<th>Date		<th>Author	<th>Notes</tr>
 *  <tr> <td>1.0		<td>2015/8/19	<td>ptshi@iflytek.com	<td>Create this file</tr>
 * </table>
 * 
 */
#pragma once

//#include "log/glog.h"
#include "util/sutil.h"
#include "util/suconf.h"
#include "boost/shared_array.hpp"

#define HTK_HEAD_SIZE	(sizeof(htk::HTK_Header))	// 12

namespace htk {
	enum
	{
		HTK_TYPE_CHAR   = 0,
		HTK_TYPE_SHORT  = 1,
		HTK_TYPE_INT    = 2,
		HTK_TYPE_INT64  = 3,
		HTK_TYPE_FLOAT  = 4,
		HTK_TYPE_DOUBLE = 5,
		HTK_TYPE_UCHAR  = 6,
		HTK_TYPE_USHORT = 7,
		HTK_TYPE_UINT   = 8,
		HTK_TYPE_UINT64 = 9,
		HTK_TYPE_COUNT  = 10,
	};
	static int parse_htk_data_bytes(int t)
	{
		int siz = -1;
		switch(t)
		{
		case HTK_TYPE_CHAR:
		case HTK_TYPE_UCHAR:
			{
				siz = 1;
			}
			break;
		case HTK_TYPE_SHORT:
		case HTK_TYPE_USHORT:
			{
				siz = 2;
			}
			break;
		case HTK_TYPE_INT:
		case HTK_TYPE_UINT:
		case HTK_TYPE_FLOAT:
			{
				siz = 4;
			}
			break;
		case HTK_TYPE_INT64:
		case HTK_TYPE_UINT64:
		case HTK_TYPE_DOUBLE:
			{
				siz = 8;
			}
			break;
		default:
			break;
		}
		return siz;
	}
	struct HTK_Header
	{
		HTK_Header()
		{
			memset(this, 0, sizeof(*this));
			sampKind =9;
		}
		~HTK_Header()
		{

		}
		union 
		{
			int		nSamples;
			int		blockNumber;
		};
		union
		{
			int		sampPeriod;
			int		dataType;
		};
		union
		{
			unsigned short	sampSize;
			unsigned short	blockSize;
		};
		union
		{
			unsigned short	sampKind;
		};
	};

	struct HTK_File_Info
	{
		HTK_File_Info()
		{
			memset(this, 0, sizeof(this));
			htk_head.sampKind =9;
		}
		~HTK_File_Info()
		{
			//delete [] pfData;
		}
		HTK_Header	htk_head;
		int			nDataCount;
		void*		pfData;
	};

	template<typename BaseType>
	static void swap32(BaseType *ptr_32)
	{
		char temp, *ptr_q;
		ptr_q = (char*)ptr_32;
		temp  = *ptr_q;				*ptr_q		 = *(ptr_q + 3);	*(ptr_q + 3) = temp;
		temp  = *(ptr_q + 1);		*(ptr_q + 1) = *(ptr_q + 2);	*(ptr_q + 2) = temp;
	}

	template<typename BaseType>
	static void swap16(BaseType *ptr_16)
	{
		char temp, *ptr_q;
		ptr_q  = (char*)ptr_16;		temp = *ptr_q;
		*ptr_q = *(ptr_q + 1);		*(ptr_q + 1) = temp;
	}

	/** 
	 * @brief 	HTK_parse
	 * 
	 * 	get HTK file information into struct HTK_File_Info
	 *	HTK_File_Info.pfData need be deleted outside
	 * 
	 * @author	ptshi@iflytek.com
	 * @date	2015/8/19
	 * @return	static int	- Return 0 in success, otherwise return error code.
	 * @param	const char* htkFileName	- [in] 
	 * @param	HTK_File_Info* pHTKFileInfo	- [out] 
	 * @see		
	 */

	static int HTK_parse(const char* htkFileName, HTK_Header& htk_head)
	{
		int nBytes = 0;
		size_t file_size = spIvw::get_file_size(htkFileName);
		FILE* fp = fopen(htkFileName, "rb");
		if (fp != NULL)
		{
			fread(&htk_head, sizeof(HTK_Header), 1, fp);
			swap32<int>(&(htk_head.nSamples));
			swap32<int>(&(htk_head.sampPeriod));
			swap16<unsigned short>(&(htk_head.sampSize));
			swap16<unsigned short>(&(htk_head.sampKind));
			//if (htk_head.sampKind == 9)
			{
				nBytes = (((file_size - sizeof(HTK_Header))/ htk_head.sampSize)*htk_head.sampSize);
			}
			fclose(fp);
		}
		return nBytes;
	}

#ifdef CE_DEC
	static int HTK_parse(const char* htkFileName, HTK_File_Info* pHTKFileInfo)
	{
		FILE* fp = fopen(htkFileName, "rb");
		//sglog_error_assert_return(fp != NULL, "Open file error", -1);
		HTK_Header htk_head;
		int nread = fread(&htk_head, sizeof(HTK_Header), 1, fp);
		swap32<int>(&(htk_head.nSamples));
		swap32<int>(&(htk_head.sampPeriod));
		swap16<unsigned short>(&(htk_head.sampSize));
		swap16<unsigned short>(&(htk_head.sampKind));

		pHTKFileInfo->htk_head	= htk_head;
		//pHTKFileInfo->nDataCount = (htk_head.nSamples*htk_head.sampSize)/sizeof(float);
		//htk_head.dataType=4;
		//int bytes_data_element  = parse_htk_data_bytes(htk_head.dataType);
		////sglog_error_assert_return(bytes_data_element >0 ,"htk data type error", -1);
		//pHTKFileInfo->pfData	= new char[pHTKFileInfo->nDataCount*bytes_data_element];		 
		//fread(pHTKFileInfo->pfData, bytes_data_element, pHTKFileInfo->nDataCount, fp);		
		//if (htk_head.dataType ==HTK_TYPE_FLOAT )
		//{
		//	float *pBuf = (float*)pHTKFileInfo->pfData;
		//	for ( int k = 0; k < pHTKFileInfo->nDataCount; k++ )
		//	{
		//		swap32<float>(&(pBuf[k]));
		//	}
		//}

		pHTKFileInfo->nDataCount = (htk_head.blockNumber * htk_head.blockSize);
		pHTKFileInfo->pfData = new char[pHTKFileInfo->nDataCount];
		fread(pHTKFileInfo->pfData, pHTKFileInfo->nDataCount, 1, fp);
		
		fclose(fp);

		return 0;
	}
#else
	static int HTK_parse(const char* htkFileName, HTK_File_Info* pHTKFileInfo)
	{
		FILE* fp = fopen(htkFileName, "rb");
		//sglog_error_assert_return(fp != NULL, "Open file error", -1);
		HTK_Header htk_head;
		int nread = fread(&htk_head, sizeof(HTK_Header), 1, fp);
		swap32<int>(&(htk_head.nSamples));
		swap32<int>(&(htk_head.sampPeriod));
		swap16<unsigned short>(&(htk_head.sampSize));
		swap16<unsigned short>(&(htk_head.sampKind));

		pHTKFileInfo->htk_head = htk_head;
		pHTKFileInfo->nDataCount = (htk_head.nSamples*htk_head.sampSize) / sizeof(float);
		htk_head.dataType = 4;
		int bytes_data_element = parse_htk_data_bytes(htk_head.dataType);
		//sglog_error_assert_return(bytes_data_element >0 ,"htk data type error", -1);
		pHTKFileInfo->pfData = new char[pHTKFileInfo->nDataCount*bytes_data_element];
		fread(pHTKFileInfo->pfData, bytes_data_element, pHTKFileInfo->nDataCount, fp);
		if (htk_head.dataType == HTK_TYPE_FLOAT)
		{
			float *pBuf = (float*)pHTKFileInfo->pfData;
			for (int k = 0; k < pHTKFileInfo->nDataCount; k++)
			{
				swap32<float>(&(pBuf[k]));
			}
		}

		fclose(fp);

		return 0;
	}
#endif


	static void HTK_read(const char* htkFileName, char* dst, int nMaxBytes)
	{
		FILE* fp = fopen(htkFileName, "rb");
		if (fp != 0)
		{
			HTK_Header htk_head;
			fread(&htk_head, sizeof(HTK_Header), 1, fp);
			swap32<int>(&(htk_head.nSamples));
			swap32<int>(&(htk_head.sampPeriod));
			swap16<unsigned short>(&(htk_head.sampSize));
			swap16<unsigned short>(&(htk_head.sampKind));
			int nbytes_element = parse_htk_data_bytes(sizeof(float));
			int nDataCount = std::max<int>(htk_head.nSamples*htk_head.sampSize, nMaxBytes) / nbytes_element;
			int nread = fread(dst, nbytes_element, nDataCount, fp);
			if (sizeof(float) == HTK_TYPE_FLOAT)
			{
				float *pfdata = (float*)dst;
				for (int k = 0; k < nDataCount; k++)
				{
					swap32<float>(&(pfdata[k]));
				}
			}
			fclose(fp);
		}
	}

	static int HTK_parse_head(const char* data,int &nBlocks,int &iType, bool isatomfea = false)
	{	
		HTK_Header htk_head = *(HTK_Header*)data;		
		swap32<int>(&(htk_head.nSamples));
		swap32<int>(&(htk_head.sampPeriod));
		swap16<unsigned short>(&(htk_head.sampSize));
		swap16<unsigned short>(&(htk_head.sampKind));

		if (isatomfea)
		{
			htk_head.dataType = 4;//when use atom fea,should add this line
		}

		nBlocks  = htk_head.blockNumber;
		iType	 = htk_head.dataType;
		return 0;
	}

	static int HTK_parse_head(const char* data, int &nDim,int &nBlocks,int &iType, bool isatomfea = false)
	{	
		HTK_Header htk_head = *(HTK_Header*)data;		
		swap32<int>(&(htk_head.nSamples));
		swap32<int>(&(htk_head.sampPeriod));
		swap16<unsigned short>(&(htk_head.sampSize));
		swap16<unsigned short>(&(htk_head.sampKind));

		nBlocks  = htk_head.blockNumber;
		iType	 = htk_head.dataType;
		nDim	 = htk_head.blockSize/parse_htk_data_bytes(iType);			
		return 0;
	}

	static int HTK_parse_body(char* data, int nDim,int nBlocks,int iType)
	{	
		if (iType ==HTK_TYPE_FLOAT )
		{
			float *pBuf = (float*)data;
			for ( int k = 0; k < nDim * nBlocks; k++ )
			{
				swap32<float>(&(pBuf[k]));
			}
		}		
		return 0;
	}

	

	static int HTK_write_buff(const char* fileName, const char* buff, int buff_size, int data_type, int data_dim, const char* format="wb")
	{
		int bytes_data_element = parse_htk_data_bytes(data_type);
		//sglog_error_assert_return(bytes_data_element > 0 ,"try htk write data type error",-1);
		//sglog_error_assert_return(buff_size % bytes_data_element ==0 ,"HTK_write_buff| buffsize is not mod dataytpe", -1);
		FILE* fp = fopen(fileName, format);

		HTK_Header htk_head;
		int data_number = buff_size/bytes_data_element;
		htk_head.blockNumber = data_number/data_dim;
		htk_head.dataType = data_type;	// force to float
		htk_head.blockSize = (unsigned short) data_dim * bytes_data_element;

		swap32<int>(&(htk_head.nSamples));
		swap32<int>(&(htk_head.sampPeriod));
		swap16<unsigned short>(&(htk_head.sampSize));
		swap16<unsigned short>(&(htk_head.sampKind));
		fwrite(&htk_head, sizeof(HTK_Header), 1, fp);

		boost::shared_array<char> sa_pfBuf(new char[ buff_size]);
		char* pfBuf = sa_pfBuf.get();
		memcpy(pfBuf, buff, buff_size);		

		if (data_type == HTK_TYPE_FLOAT)
		{
			float *pdstBuf = (float*) pfBuf;
			const float* buff_conv = (float*)buff;
			for (int i = 0; i < data_number; i++)
			{
				pdstBuf[i] = buff_conv[i];
				swap32<float>(&pdstBuf[i]);
			}
		}		

		fwrite(pfBuf, bytes_data_element, data_number, fp);
		fclose(fp);

		return 0;
	}
	/** 
	 * @brief 	HTK_compare
	 * 
	 * 	compare two HTK format files, header skipped
	 * 
	 * @author	ptshi@iflytek.com
	 * @date	2015/8/19
	 * @return	static int	- Return 0 in success, otherwise return error code.
	 * @param	const char* oriFile	- [in] 
	 * @param	const char* desFile	- [in] 
	 * @see		
	 */
	static int HTK_compare(const char* oriFile, const char* desFile)
	{
		//sglog_error_assert_return( spIvw::is_file_exist(oriFile), "Open file err", -1);
		//sglog_error_assert_return( spIvw::is_file_exist(desFile), "Open file err", -1);

		size_t oriFileSize = spIvw::get_file_size(oriFile);
		boost::shared_array<char> oriDataBuf(new char[oriFileSize]);
		memset(oriDataBuf.get(), 0, oriFileSize);
		spIvw::read_bin_file(oriFile, oriDataBuf.get(), oriFileSize);

		size_t desFileSize = spIvw::get_file_size(desFile);
		boost::shared_array<char> desDataBuf(new char[desFileSize]);
		memset(desDataBuf.get(), 0, desFileSize);
		spIvw::read_bin_file(desFile, desDataBuf.get(), desFileSize);
		//sglog_error_assert_return(oriFileSize == desFileSize, "Different file size", -1);
		int headOffset =  sizeof(HTK_Header);
		int cmpValue = memcmp(oriDataBuf.get()+headOffset, desDataBuf.get()+headOffset, oriFileSize-headOffset);
		//sglog_error_assert_return(0 == cmpValue, "Memory compare err", -1);
		return 0;
	}

}