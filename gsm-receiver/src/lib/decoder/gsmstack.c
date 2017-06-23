/*
 * Invoke gsmstack() with any kind of burst. Automaticly decode and retrieve
 * information.
 *
 *Modified by Paul Kinsella <> to dump tmsi's for linking tmsi to phone number via silent sms.
 *Coding Help from Piotr https://github.com/gr-gsm
 *Code is modified version of tmsi dumper to work on gsm-receiver on kali linux.
 */
#include "system.h"
#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#include <unistd.h>
#include <string.h>
#include "gsmstack.h"
//#include "gsm_constants.h"
#include "interleave.h"
//#include "sch.h"
#include "cch.h"

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#include <osmocom/core/msgb.h>
#include <osmocom/core/gsmtap.h>
#include <osmocom/core/gsmtap_util.h>

#include <time.h>

FILE* tmsiFile;

static const int USEFUL_BITS = 142;

static void out_gsmdecode(char type, int arfcn, int ts, int fn, char *data, int len);

static void filter_tmsi(char *data, int len);

void write_tmsi(char *tmsi, unsigned int tmsi_index);

void write_imsi(char *imsi, unsigned int imsi_index);

void writetimestamp(FILE* filename, int page_type);

time_t rawtime;
struct tm * timeinfo;

/* encode a decoded burst (1 bit per byte) into 8-bit-per-byte */
static void burst_octify(unsigned char *dest, 
			 const unsigned char *data, int length)
{
	int bitpos = 0;

	while (bitpos < USEFUL_BITS) {
		unsigned char tbyte;
		int i; 

		tbyte = 0;
		for (i = 0; (i < 8) && (bitpos < length); i++) {
			tbyte <<= 1;
			tbyte |= data[bitpos++];
		}
		if (i < 8)
			tbyte <<= 8 - i;
		*dest++ = tbyte;
	}	
}


#if 0
static void
diff_decode(char *dst, char *src, int len)
{
	const char *end = src + len;
	unsigned char last;

	src += 3;
	last = 0;
	memset(dst, 0, 3);
	dst += 3;

	while (src < end)
	{
		*dst = !*src ^ last;
		last = *dst;
		src++;
		dst++;
	}
}
#endif

/* TODO: handle mapping in a more elegant way or simplify the function */

uint8_t
get_chan_type(enum TIMESLOT_TYPE type, int fn, uint8_t *ss)
{
  uint8_t chan_type = GSMTAP_CHANNEL_BCCH;
  *ss = 0;
  int mf51 = fn % 51;

  if(type == TST_FCCH_SCH_BCCH_CCCH_SDCCH4)
  {
      if(mf51 == 22) /* SDCCH */
      {
          chan_type = GSMTAP_CHANNEL_SDCCH4;
          *ss = 0;
      }
      else if(mf51 == 26) /* SDCCH */
      {
          chan_type = GSMTAP_CHANNEL_SDCCH4;
          *ss = 1;
      }
      else if(mf51 == 32) /* SDCCH */
      {
          chan_type = GSMTAP_CHANNEL_SDCCH4;
          *ss = 2;
      }
      else if(mf51 == 36) /* SDCCH */
      {
          chan_type = GSMTAP_CHANNEL_SDCCH4;
          *ss = 3;
      }
      else if(mf51 == 42) /* SAACH */
      {
          chan_type = GSMTAP_CHANNEL_SDCCH4 | GSMTAP_CHANNEL_ACCH;
          *ss = ((fn % 102) > 51) ? 2 :  0;
      }
      else if(mf51 == 46) /* SAACH */
      {
          chan_type = GSMTAP_CHANNEL_SDCCH4 | GSMTAP_CHANNEL_ACCH;
          *ss = ((fn % 102) > 51) ? 3 :  1;
      }
  }
  else if(type == TST_FCCH_SCH_BCCH_CCCH)
  {
      if(mf51 != 2) /* BCCH */
      {
          chan_type = GSMTAP_CHANNEL_CCCH;
          *ss = 0;
      }
  }
  else if(type == TST_SDCCH8)
  {
      if(mf51 == 0) /* SDCCH */
      {
          chan_type = GSMTAP_CHANNEL_SDCCH8;
          *ss = 0;
      }
      else if(mf51 == 4) /* SDCCH */
      {
          chan_type = GSMTAP_CHANNEL_SDCCH8;
          *ss = 1;
      }
      else if(mf51 == 8) /* SDCCH */
      {
          chan_type = GSMTAP_CHANNEL_SDCCH8;
          *ss = 2;
      }
      else if(mf51 == 12) /* SDCCH */
      {
          chan_type = GSMTAP_CHANNEL_SDCCH8;
          *ss = 3;
      }
      else if(mf51 == 16) /* SDCCH */
      {
          chan_type = GSMTAP_CHANNEL_SDCCH8;
          *ss = 4;
      }
      else if(mf51 == 20) /* SDCCH */
      {
          chan_type = GSMTAP_CHANNEL_SDCCH8;
          *ss = 5;
      }
      else if(mf51 == 24) /* SDCCH */
      {
          chan_type = GSMTAP_CHANNEL_SDCCH8;
          *ss = 6;
      }
      else if(mf51 == 28) /* SDCCH */
      {
          chan_type = GSMTAP_CHANNEL_SDCCH8;
          *ss = 7;
      }
      else if(mf51 == 32) /* SAACH */
      {
          chan_type = GSMTAP_CHANNEL_SDCCH8 | GSMTAP_CHANNEL_ACCH;
          *ss = ((fn % 102) > 51) ? 4 :  0;
      }
      else if(mf51 == 36) /* SAACH */
      {
          chan_type = GSMTAP_CHANNEL_SDCCH8 | GSMTAP_CHANNEL_ACCH;
          *ss = ((fn % 102) > 51) ? 5 :  1;
      }
      else if(mf51 == 40) /* SAACH */
      {
          chan_type = GSMTAP_CHANNEL_SDCCH8 | GSMTAP_CHANNEL_ACCH;
          *ss = ((fn % 102) > 51) ? 6 :  2;
      }
      else if(mf51 == 44) /* SAACH */
      {
          chan_type = GSMTAP_CHANNEL_SDCCH8 | GSMTAP_CHANNEL_ACCH;
          *ss = ((fn % 102) > 51) ? 7 :  3;
      }
  }
  else if (type == TST_TCHF) {
    chan_type = GSMTAP_CHANNEL_TCH_F | GSMTAP_CHANNEL_ACCH;
  }

  return chan_type;
}

/*
 * Initialize a new GSMSTACK context.
 */
int
GS_new(GS_CTX *ctx)
{
	struct sockaddr_in sin;

	sin.sin_family = AF_INET;
	sin.sin_port = htons(GSMTAP_UDP_PORT);
	inet_aton("127.0.0.1", &sin.sin_addr);

	memset(ctx, 0, sizeof *ctx);
	interleave_init(&ctx->interleave_ctx, 456, 114);
	interleave_init_facch_f(&ctx->interleave_facch_f1_ctx, 456, 114, 0);
	interleave_init_facch_f(&ctx->interleave_facch_f2_ctx, 456, 114, 4);
	ctx->fn = -1;
	ctx->bsic = -1;

	ctx->gsmtap_inst = gsmtap_source_init("127.0.0.1", GSMTAP_UDP_PORT, 0);
	if (!ctx->gsmtap_inst) {
		perror("creating gsmtap socket\n");
		return -EIO;
	}
	/* Add a local sink to the existing GSMTAP source */
	gsmtap_source_add_sink(ctx->gsmtap_inst);

	return 0;
}

#define BURST_BYTES	((USEFUL_BITS/8)+1)
/*
 * 142 bit
 */
int
GS_process(GS_CTX *ctx, int ts, int type, const unsigned char *src, int fn, int first_burst)
{
	int bsic;
	int ret;
	unsigned char *data;
	int len;
	struct gs_ts_ctx *ts_ctx = &ctx->ts_ctx[ts];

	memset(ctx->msg, 0, sizeof(ctx->msg));

	if (ts_ctx->type == TST_TCHF && type == NORMAL &&
	    (fn % 26) != 12 && (fn % 26) != 25) {
		/* Dieter: we came here because the burst might contain FACCH bits */
		ctx->fn = fn;

		/* get burst index to TCH bursts only */
		ts_ctx->burst_count2 = fn % 26;

		if (ts_ctx->burst_count2 >= 12)
			ts_ctx->burst_count2--;
		ts_ctx->burst_count2 = ts_ctx->burst_count2 % 8;

		/* copy data bits and stealing flags to buffer */
		memcpy(ts_ctx->burst2 + (116 * ts_ctx->burst_count2), src, 58);
		memcpy(ts_ctx->burst2 + (116 * ts_ctx->burst_count2) + 58, src + 58 + 26, 58);

		/* Return if not enough bursts for a full gsm message */
		if ((ts_ctx->burst_count2 % 4) != 3)
			return 0;

		data = decode_facch(ctx, ts_ctx->burst2, &len, (ts_ctx->burst_count2 == 3) ? 1 : 0);
		if (data == NULL) {
			DEBUGF("cannot decode FACCH fnr=%d ts=%d\n", ctx->fn, ts);
			return -1;
		}

		//filter_tmsi(data,len);//uncomment to activate
		out_gsmdecode(0, 0, ts, ctx->fn, data, len);

		if (ctx->gsmtap_inst) {
			struct msgb *msg;
			uint8_t chan_type = GSMTAP_CHANNEL_TCH_F;
			uint8_t ss = 0;
			int fn = (ctx->fn - 3); /*  "- 3" for start of frame */

			msg = gsmtap_makemsg(0, ts, chan_type, ss, ctx->fn, 0, 0, data, len);
			if (msg)
				gsmtap_sendmsg(ctx->gsmtap_inst, msg);
		}
		return 0;
	}

	/* normal burst processing */
	if (first_burst) /* Dieter: it is important to start with the correct burst */
		ts_ctx->burst_count = 0;

	ctx->fn = fn;
	if (type == NORMAL) {
		/* Interested in these frame numbers (cch)
 		 * 2-5, 12-15, 22-25, 23-35, 42-45
 		 * 6-9, 16-19, 26-29, 36-39, 46-49
 		 */
		/* Copy content data into new array */
		//DEBUGF("burst count %d\n", ctx->burst_count);
		memcpy(ts_ctx->burst + (116 * ts_ctx->burst_count), src, 58);
		memcpy(ts_ctx->burst + (116 * ts_ctx->burst_count) + 58, src + 58 + 26, 58);
		ts_ctx->burst_count++;
		/* Return if not enough bursts for a full gsm message */
		if (ts_ctx->burst_count < 4)
			return 0;

		ts_ctx->burst_count = 0;
		data = decode_cch(ctx, ts_ctx->burst, &len);
		if (data == NULL) {
			DEBUGF("cannot decode fnr=0x%06x (%6d) ts=%d\n", ctx->fn, ctx->fn, ts);
			return -1;
		}
		//DEBUGF("OK TS %d, len %d\n", ts, len);

		//filter_tmsi(data,len);//uncomment to activate
		out_gsmdecode(0, 0, ts, ctx->fn, data, len);

		if (ctx->gsmtap_inst) {
			/* Dieter: set channel type according to configuration */
			struct msgb *msg;
			uint8_t chan_type = GSMTAP_CHANNEL_BCCH;
			uint8_t ss = 0;
			int fn = (ctx->fn - 3); /*  "- 3" for start of frame */

			chan_type = get_chan_type(ts_ctx->type, fn, &ss);

			/* arfcn, ts, chan_type, ss, fn, signal, snr, data, len */
			msg = gsmtap_makemsg(0, ts, chan_type, ss,
					     ctx->fn, 0, 0, data, len);
			if (msg)
				gsmtap_sendmsg(ctx->gsmtap_inst, msg);
		}

#if 0
		if (ctx->fn % 51 != 0) && ( (((ctx->fn % 51 + 5) % 10 == 0) || (((ctx->fn % 51) + 1) % 10 ==0) ) )
			ready = 1;
#endif
		
		return 0;
	}
}


/*
 * Output data so that it can be parsed from gsmdecode.
 */
static void
out_gsmdecode(char type, int arfcn, int ts, int fn, char *data, int len)
{
	char *end = data + len;

	printf("%6d %d:", (fn + 0), ts);

	/* FIXME: speed this up by first printing into an array */
	while (data < end)
		printf(" %02.2x", (unsigned char)*data++);
	printf("\n");
	fflush(stdout);
}

/*
 *Dump all tmsi and imsi with a timestamp.
 */
static void
filter_tmsi(char *data,int len)
{

  uint8_t msg_len = data[0];
  uint8_t direction_and_protocol = data[1];
  uint8_t msg_type = data[2];

    if( direction_and_protocol == 0x06 &&                    //direction from originating site, transaction id==0, Radio Resouce Management protocol
        (msg_type==0x21 || msg_type==0x22 || msg_type==0x24) //types corresponding to paging requests
      ) 
    {
        //write timestamp
        switch(msg_type) {
            case 0x21: //Paging Request Type 1
            {
                uint8_t mobile_identity_type = data[5] & 0x07;// binary 
                unsigned int next_element_index = 0; //position of the next element
                unsigned int found_id_element = 0;// 0 = false 1 = true
                //printf("21");                                
                if(mobile_identity_type == 0x04) //identity type: TMSI (binary 100)
                {
                  next_element_index = 10;
                  found_id_element = 1;//true
		  write_tmsi(data, 6);

		}else 
                if(mobile_identity_type == 0x01) //identity type: IMSI (binary 001)
                {
                  next_element_index = 13;
                  found_id_element = 1;//true
		  write_imsi(data,5);

                }
	      
                if(found_id_element == 1)
                {
                    //check if there is additional id element
                    uint8_t element_id = data[next_element_index];
                    if((next_element_index < (msg_len+1)) && (element_id == 0x17)){
                        //check if there is another element
                        uint8_t element_len = data[next_element_index+1];
                        mobile_identity_type = data[next_element_index+2] & 0x07;

                        if(mobile_identity_type == 0x04) //identity type: TMSI
                        {
			  write_tmsi(data, next_element_index+3);

                        } else 
                        if(mobile_identity_type == 0x01) //identity type: IMSI
                        {
			  write_imsi(data, next_element_index+2);
                        }
                    }
                    
                } 	      


	    }break;

            case 0x22: //Paging Request Type 1
            {

                uint8_t mobile_identity_type = data[14] & 0x07;
		write_tmsi(data, 4);
		write_tmsi(data, 8);
                                                
                if(mobile_identity_type == 0x04) //identity type: TMSI
                {
		  write_tmsi(data,15);
                  
                } else 
                if(mobile_identity_type == 0x01) //identity type: IMSI
                {
                    write_imsi(data,14);  
                }

	      
	    }break;
	    case 0x24: //Paging Request Type 1
            {

		unsigned int TMSI_INDEX[4] ={4,8,12,16};// indexes of the 4 tmsi's 
		int x;
		for(x =0;x < 4;x++)
		{
                    write_tmsi(data,TMSI_INDEX[x]);
 
		}
	      
	    }break;
	}
    }


}

void write_tmsi(char *tmsi, unsigned int tmsi_index){
 
  tmsiFile = fopen("tmsicount.txt", "a+");
  fprintf(tmsiFile,"%02.2x%02.2x%02.2x%02.2x",
	 (unsigned char)tmsi[tmsi_index],
	 (unsigned char)tmsi[tmsi_index+1],
	 (unsigned char)tmsi[tmsi_index+2],
	  (unsigned char)tmsi[tmsi_index+3]);
  
  writetimestamp(tmsiFile,0);


}

void write_imsi(char *imsi, unsigned int imsi_index){
  
  tmsiFile = fopen("tmsicount.txt", "a+");
  writetimestamp(tmsiFile,1);

   fprintf(tmsiFile,"%02.2x%02.2x%02.2x%02.2x%02.2x%02.2x%02.2x%02.2x\n",
		  (unsigned char)imsi[imsi_index],
		  (unsigned char)imsi[imsi_index+1],
		  (unsigned char)imsi[imsi_index+2],
		  (unsigned char)imsi[imsi_index+3],
		  (unsigned char)imsi[imsi_index+4],
		  (unsigned char)imsi[imsi_index+5],
		  (unsigned char)imsi[imsi_index+6],
		  (unsigned char)imsi[imsi_index+7],
		  (unsigned char)imsi[imsi_index+8]);
   fclose(tmsiFile);
}

void writetimestamp(FILE* filename, int page_type)
{

  time (&rawtime);
  timeinfo = localtime (&rawtime);

  switch(page_type)
    {
    case 0://tmsi = 0
    {
        fprintf(filename,"-%02i%02i%02i%02i%02i%02i-0\n",
		   	   1900 + timeinfo->tm_year-2000,
		   	   1+timeinfo->tm_mon,
		   	   timeinfo->tm_mday,
		   	   timeinfo->tm_hour,
		   	   timeinfo->tm_min,
		   	   timeinfo->tm_sec);
	fclose(filename);
    }break;
    case 1:// imsi = 1
    {

      fprintf(filename,"0-%02i%02i%02i%02i%02i%02i-",
		   	   1900 + timeinfo->tm_year-2000,
		   	   1+timeinfo->tm_mon,
		   	   timeinfo->tm_mday,
		   	   timeinfo->tm_hour,
		   	   timeinfo->tm_min,
		   	   timeinfo->tm_sec);
    }break;
    }

}
