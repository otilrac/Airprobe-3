#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
# Copyright 2014 Paul Kinsella <paulkinsella29@yahoo.ie>
# 
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this software; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 


import serial, time
import sys
import binascii
import os
from datetime import datetime
pagecount = 0;
smsSendCount =0

gsm = ("@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
"¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ`¿abcdefghijklmnopqrstuvwxyzäöñüà").decode('utf8')
ext = ("````````````````````^```````````````````{}`````\\````````````[~]`"
"|````````````````````````````````````€``````````````````````````") 

def setSmsSendCount(setcount):
	global smsSendCount
	smsSendCount = setcount

def getSmsSendCount():
	global smsSendCount
	return smsSendCount

def incSmsSendCount():
	global smsSendCount
	smsSendCount += 1
def incTmsiCount():
    global pagecount
    pagecount += 1

def resetTmsiCount():
	global pagecount
	pagecount = 0

###############################################################################
#	SWAPS NUMBER EVERY 2 DIGITS USED FOR PDU
#############################################################################
def swapNumber(number):
	swaparray = []
	returnNumber =""
	first1 = 0
	first2 = 1
	second1 =1
	second2 = 2

	for x in range (0,len(number)/2):
		swaparray.append(number[second1:second2])
		swaparray.append(number[first1:first2])
		first1 +=2
		first2 +=2
		second1 +=2
		second2 +=2

	for num in swaparray:
		returnNumber += num
	#print("DEBUG", returnNumber)
	return returnNumber	
	
###############################################################################
#	ENCODE SMS TEXT TO GSM
#############################################################################
def gsm_encode(plaintext):
      res = ""
	    
      for c in plaintext:
	     idx = gsm.find(c);
	     if idx != -1:
		 res += chr(idx)
		 continue
	     idx = ext.find(c)
	     if idx != -1:
		     res += chr(27) + chr(idx)

      return binascii.b2a_hex(res.encode('utf-8'))
###############################################################################
#	ENCODE SMS TEXT TO GSM 8bit
#############################################################################
def gsm_encode8bit(SMS):
	res = ""
	plaintext = SMS
	for c in plaintext:
		idx = gsm.find(c);
		if idx != -1:
			res += chr(idx)
			continue
		idx = ext.find(c)
		if idx != -1:
			res += chr(27) + chr(idx)
	return binascii.b2a_hex(res.encode('utf-8'))
	    #return res.encode('hex')
########################################################################
#			CREATE PDU STRING
# PDU_STRING = createPduString("12345","this is an sms","04"):
########################################################################

def createPduString(phone_num,sms_text,message_type):
	NUMBER_LEN = len(phone_num)
	NUMBER = phone_num
	SMS_TYPE = message_type

	#If number is odd add an F pdu needs to be even number
	if NUMBER_LEN % 2 != 0:
		NUMBER += "F"
		#print("DEBUG", NUMBER)

	NUMBER = swapNumber(NUMBER)
	NUMBER_LEN_HEX = str(hex(NUMBER_LEN)).lstrip('0x')#GET LEN OF PHONE NUMBER IN HEX

	if NUMBER_LEN <= 15:
		NUMBER_LEN_HEX = "0"+NUMBER_LEN_HEX
	

	smslen = len(sms_text)
	MSG_LEN = str(hex(smslen)).lstrip('0x')#get sms data length in hex
	SMS = sms_text
	NUM = phone_num

	if smslen <= 15:
		decodedstr1 =  gsm_encode(sms_text)
		PDU_STRING = "002100"+NUMBER_LEN_HEX+"91"+NUMBER+"00"+SMS_TYPE+"0"+MSG_LEN +decodedstr1
		#print("In smslen <= 15")#if sms length is less than 15 we need to add a 0 to hex value B becomes 0B

	if smslen > 15:#if sms len more than 15 add no 0.
		decodedstr1 =  gsm_encode(self.editpdu_PDU_SMS.GetValue())
		PDU_STRING = "002100"+NUMBER_LEN_HEX+"91"+NUMBER+"00"+SMS_TYPE+MSG_LEN +decodedstr1

	return PDU_STRING
