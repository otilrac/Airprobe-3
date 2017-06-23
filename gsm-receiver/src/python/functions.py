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
import serial, time
import glob
from datetime import datetime
###################################
#	Serial setup
###################################
ser = serial.Serial()
ser.port = "/dev/ttyUSB0" #default so not null
ser.baudrate = 9600
ser.bytesize = serial.EIGHTBITS #number of bits per bytes
ser.parity = serial.PARITY_NONE #set parity check: no parity
ser.stopbits = serial.STOPBITS_ONE #number of stop bits
ser.timeout = 0             #non-block read
ser.xonxoff = False     #disable software flow control
ser.rtscts = False     #disable hardware (RTS/CTS) flow control
ser.dsrdtr = False       #disable hardware (DSR/DTR) flow control

AT_COMMANDS = ["AT+CIMI",
"AT+CSIM=14,\"A0A40000027F20\"",
"AT+CSIM=42,\"A088000010FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF\"",
"AT+CSIM=14,\"A0A40000026F20\"",
"AT+CSIM=10,\"A0B0000009\"",
"AT+CSIM=14,\"A0A40000026F7E\"","AT+CSIM=10,\"A0B000000B\""]
ARR_SIZE =  len(AT_COMMANDS)

pagecount = 0;
smsSendCount =0;


gsm = ("@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
"¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ`¿abcdefghijklmnopqrstuvwxyzäöñüà").decode('utf8')
ext = ("````````````````````^```````````````````{}`````\\````````````[~]`"
"|````````````````````````````````````€``````````````````````````")
#################################
#return serial ports list
#################################
def getOpenSerialPorts():
    	if sys.platform.startswith ('linux'):
    		temp_list = glob.glob ('/dev/tty[A-Za-z]*')
    		result = []
    		for a_port in temp_list:
        		try:
        		    s = serial.Serial(a_port)
        		    s.close()
        		    result.append(a_port)
        		except serial.SerialException:
        		    pass
    	return result


########################################################################
# RETURNS 2 ARRAYS 1ST = TMSI NAME 2ND = TMSI PING COUNT BOTH INDEXS
# ARE THE SAME sTmsiArray[1]=aabbccdd iTmsiCount[1]=5
#sTmsiArray, iTmsiCount = getTmsiCount()
#THIS WILL RETURN ALL TMSI'S AND THERE COUNT USEFUL TO SEE HIGHEST COUNT
######################################################################## 
def getTmsiCount():
	tmsiarray = []
	tmsiarraycount =[]
	file = open("tmsicount.txt")
	for line in file:
		if line[0:2] != "0-":
			CURRENT_TMSI = line[:8]
			line = line.rstrip('\n').rstrip('\r')
			i = -1
			try:
				while 1:
					i = tmsiarray.index(CURRENT_TMSI,i+1)
					# print "match at", i,tmsiarray[i]
					if i > -1:
						tmsiarraycount[i] += 1
						break
		     	except ValueError:
				tmsiarray.append(CURRENT_TMSI)
				tmsiarraycount.append(1)

	file.close()
	return tmsiarray,tmsiarraycount
###############################################################################
#	SWAPS NUMBER EVERY 2 DIGITS USED FOR PDU
#############################################################################
def swapNumber2(number):
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

##################################################################
#	GET CURRENT TIMESTAMP
#################################################################
def getCurrentTimeStamp():
	string_timestamp = str(datetime.now()).replace("-","").replace(":","").replace(" ","")[2:14]
	int_timpstamp = int(string_timestamp)
	return int_timpstamp
##################################################################
#	DUMP TIMESTAMP FOR MANUAL MODE
#################################################################
def dumpTimeStampManMode():
	string_timestamp = str(datetime.now()).replace("-","").replace(":","").replace(" ","")[2:14]
	int_timpstamp = int(string_timestamp)
	timestampFile = open("manual_timestamps.txt", "a+")
	timestampFile.write(str(int_timpstamp)+"\n")
	timestampFile.close()
##################################################################
#	GET TIMESTAMPS FROM DELIVERY REPORTS
#	GETS FROM MODEM
#################################################################
def getDeliveryTimeStamps(serial_port):
	print("Getting Delivery Reports")

	if ser.isOpen() == False:
		print("Port Closed Now Openning")
		ser.port = serial_port
	    	ser.open()
	
	time.sleep(0.5)
	ser.write("AT+CMGL=4"+"\x0D")
	time.sleep(0.9)
	bytesToRead = ser.inWaiting()
        time.sleep(0.5)
	delreports = ser.read(bytesToRead)
        time.sleep(0.5)
	
	delreports = delreports.split('\n')
	timestamps = []
	tcount = 0
	for x in range (0,len(delreports)):
		if len(delreports[x]) > 20:
			#print(delreports[x])
			timestamps.append(delreports[x][36:-3]) 
			tcount += 1
	output = []
	for x in range (0,len(timestamps)):
		#output.append(swapNumber(timestamps[x][:12]+timestamps[x][14:-2]))
		output.append(int(swapNumber2(timestamps[x][:12])))
		output.append(int(swapNumber2(timestamps[x][14:-2])))

	ser.close()
	return output


########################################################################
#	GET BACK AN AT COMMAND
########################################################################
def getAtReply(serial_port,at_command):
	ser.port = serial_port
        if ser.isOpen() == False:
            ser.open()
	time.sleep(0.3)
        ress =""
	if ser.isOpen():
            ser.flushInput() #flush input buffer, discarding all its contents
            ser.flushOutput()#flush output buffer, aborting current output 
	    sercmd = at_command
            ser.write(sercmd+"\x0D")
            time.sleep(0.2)
            bytesToRead = ser.inWaiting()
            ress = ser.read(bytesToRead)
            ser.close()
	return ress
########################################################################
#	KEY IMSI TMSI GOT HERE
########################################################################
def GetKeyTmsiImsi(serial_port):
	ser.port = serial_port
	ser.open()
	if ser.isOpen():
            	#print("Ruuing on port:"+ser.port)
		ser.flushInput() #flush input buffer, discarding all its contents
		ser.flushOutput()#flush output buffer, aborting current out
		ser.write(AT_COMMANDS[0]+"\x0D")
		time.sleep(0.3)
		ress = ser.read(300)
		ress = ress.strip(' \t \r \n \r\n').replace("OK",'').replace('\r','').replace('\n','')
		IMSI = ress

		ser.write(AT_COMMANDS[1]+"\x0D")
		time.sleep(0.3)
		ress = ser.read(300)


		ser.write(AT_COMMANDS[2]+"\x0D")
		time.sleep(0.3)
		ress = ser.read(300)

		ser.write(AT_COMMANDS[3]+"\x0D")
		time.sleep(0.3)
		ress = ser.read(300)

		ser.write(AT_COMMANDS[4]+"\x0D")
		time.sleep(0.5)
		ress = ser.read(300)
		ress = ress.strip(' \t \r \n \r\n').replace("OK",'')
		datalen = len(ress)
		FULLKEY = ress

		ser.write(AT_COMMANDS[5]+"\x0D")
		time.sleep(0.3)
		ress = ser.read(300)


		ser.write(AT_COMMANDS[6]+"\x0D")
		time.sleep(0.3)
		ress = ser.read(300)
		ress = ress.strip(' \t \r \n \r\n').replace("OK",'')
		datalen = len(ress)
		FULLTMSI = ress
		ress = ress[32:datalen -23]
		TMSI = ress
		#dump data to log file
	        file = open("tmsi_kc_log.txt","a")
	        file.write("********************\nFULLTMSI ("+FULLTMSI.strip(' \t \r \n \r\n')+")\nTMSI("+FULLTMSI[len(FULLTMSI)-31:-23]+")\nFULLKEY "+FULLKEY.strip(' \t \r \n \r\n')	+"\nKEY("+FULLKEY[len(FULLKEY)-27:-11]+")\nTIMESTAMP "+str(datetime.now())+"\n")
	        file.close()
	        ser.close()
		return FULLTMSI[len(FULLTMSI)-31:-23]+":"+FULLKEY[len(FULLKEY)-27:-11]+":"+IMSI
        else:
	    return "ERROR"	
            ser.close()
