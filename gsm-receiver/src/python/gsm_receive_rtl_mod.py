#!/usr/bin/env python


# Copyright 2012 Dimitri Stolnikov <horiz0n@gmx.net>
# Copyright 2012 Steve Markgraf <steve@steve-m.de>

# Adjust the center frequency (-f) and gain (-g) according to your needs.
# Use left click in Wideband Spectrum window to roughly select a GSM carrier.
# In Wideband Spectrum you can also tune by 1/4 of the bandwidth by clicking on
# the rightmost/leftmost spectrum side.
# Use left click in Channel Spectrum windows to fine tune the carrier by
# clicking on the left or right side of the spectrum.

#Edited version of gsm_reveive_rtl.py
# 2015 Paul Kinsella <kali_gsm_rtl_sdr@gmail.com>

#updates to the standard airprobe gsm_receiver_rtl file
#Change timeslot on the fly,set ppm, finetune freq
#Send silent/flash/normal sms in PDU mode with usb dongle or compatible phone
#filter out a paged tmsi to link to phone number by sending silent sms.
#filter out tmsi's that are spamming on the OB channel for better accuracy linker tmsi to number
#get imsi/tmsi/key from compatible usb modem/phone.
#




from gnuradio import gr, gru, eng_notation, blks2, optfir
from gnuradio.eng_option import eng_option
from gnuradio.wxgui import fftsink2
from gnuradio.wxgui import forms
from grc_gnuradio import wxgui as grc_wxgui

import serial,time,thread,threading
import sys,wx,math,os
from functions import *
from sms_functions import *
from datetime import datetime

from optparse import OptionParser
import osmosdr


FLASH1 = "10"#4 bit encoding
FLASH2 = "14"#8 bit encoding
FLASH3 = "18"#16 bit encoding
SILENT = "C0"
NORMAL = "04"

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
SERIAL_PORT_IDLE = True
at_cmds_array = []

for extdir in ['../../debug/src/lib','../../debug/src/lib/.libs','../lib','../lib/.libs']:
    if extdir not in sys.path:
        sys.path.append(extdir)
import gsm


class tune_corrector(gr.feval_dd):
    def __init__(self, top_block):
        gr.feval_dd.__init__(self)
        self.top_block = top_block

    def eval(self, freq_offset):
        self.top_block.offset = self.top_block.offset + int(freq_offset)
        self.top_block.tuner.set_center_freq(self.top_block.offset)
        return freq_offset

class synchronizer(gr.feval_dd):
    def __init__(self, top_block):
        gr.feval_dd.__init__(self)
        self.top_block = top_block

    def eval(self, timing_offset):
        return timing_offset
###############################
#
#############################
def setPortInUse(setstate):
	global SERIAL_PORT_IDLE
        SERIAL_PORT_IDLE = setstate# False = port is not Idle

def getPortStatus():
	global SERIAL_PORT_IDLE
	return SERIAL_PORT_IDLE


# applies frequency translation, resampling and demodulation

class top_block(grc_wxgui.top_block_gui):

  def __init__(self):
    grc_wxgui.top_block_gui.__init__(self, title="GSM RECEIVER (RTL TOOL KIT MOD)")

    def testmove(test):
        #incgain()
        pass


    #SHOW HOW MANY UNIQUE TMSI'S ARE ON CELL
    def maxUsersTread(void):
	try:
		thread.start_new_thread(maxUsers,(void,),)	
		
	except:
		self.editdebug.AppendText("Unable to send command try again")


    def maxUsers(void):
	tmsiname,tmsicount = getTmsiCount()
	self.debugtext1.SetLabel("Tmsi's:"+str(len(tmsiname)))



	
   #start the function on a thread so not to stop main app
    def filtertimsiTread(void):
	try:
		self.editdebugtmsi.SetValue("")
		thread.start_new_thread(filterTmsiAllCount,(int(self.edit_tmsi_range1.GetValue()),int(self.edit_tmsi_range2.GetValue())),)	
		
	except:
		self.editdebug.AppendText("Unable to send command try again")


    def filterTmsiAllCount(low_range,high_range):
	tmsiname,tmsicount = getTmsiCount()
	x = 0
	alldata = ""
	for tmsi in tmsiname:
		if tmsicount[x] >= low_range and tmsicount[x] <= high_range:
			alldata += tmsiname[x]+":"+str(tmsicount[x])+'\n'
			#self.editdebugtmsi.AppendText(tmsiname[x]+":"+str(tmsicount[x])+'\n')
		x += 1
	
	self.editdebugtmsi.AppendText(alldata)


    ############################################################################
    #	THIS CODE FILTERS OUT TMSI FROM SIM TIMESTAMPS RANGE WITH BUTTON PRESS
    #			USB MODEM MODE
    ############################################################################
    def filterTmsiTimestampMode(event):
	    #ser.close()
	    #ser.port = self.editcomport.GetValue()
	    #ser.open()
	    timer_delay_sms.Stop()
            time.sleep(0.2)
	    times = []
	    selected_port = self.combo_serial_ports.GetValue()
	    times = getDeliveryTimeStamps(selected_port)#input serial port address
		#print("Response "+ress)
	    for xx in range (0,len(times)):
		#output = times[x][:12]+times[x][14:-2]
               	self.editdebug.AppendText(str(times[xx])+'\n')

 
	    tmsiarray = []#HOLDS SINGLE TMSI
            timestamp = []
	    tmsiarraycount =[]#HOLDS HOW MANY TIMES THE TMSI GOT PAGED
            CURRENT_TIMESTAMP = ""
            CURRENT_TMSI = ""

	    low_range = int(self.edit_tmsi_range1.GetValue())
	    high_range = int(self.edit_tmsi_range2.GetValue())
	    self.editdebugtmsi.SetValue("")
	    startindex = 0
	    endindex = 1
	    file = open("tmsicount.txt")
	    file.close()
	    loopcount = len(times)/2# EACH DELIVERY REPORT HAS 2 TIMESTAMPS SO IF 2 DEL REPORTS / 2 THAT LEAVES 4 TIMESTAMPS.
	    print("ARRAY LEN IS: "+str(loopcount))
	    #LOOP THRU ALL THE TIMESTAMPS 
            for x in range(0,loopcount):
			print("IN OPEN FILE LOOP "+str(x)+"\n")
			print(str(startindex)+":"+str(endindex)+"\n")
	    		file = open("tmsicount.txt")

	    		for line in file:
		    		line = line.rstrip('\n').rstrip('\r')
		    		#self.editdebugtmsi.AppendText(line[:8]+"@"+line[9:])
                        	if line[0:2] != "0-":
                            		CURRENT_TMSI = line[:8]
                            		CURRENT_TIMESTAMP = int(line[9:21])
                        		#self.editdebugtmsi.AppendText(str(CURRENT_TIMESTAMP))
                        		passint = 0;
                    			#print(str(startindex)+"\n"+str(endindex))
                    			# times[0] holds first timestamp and times[1] holds second timestamp    {endindex}
                            		if CURRENT_TIMESTAMP >= times[endindex]-3 and CURRENT_TIMESTAMP <= times[endindex]:
                            		#print("IN TIMESTAMP")
                                		if len(line) >= 8:
                                    			i = -1
                                    			try:
                                        			while 1:
                                            				i = tmsiarray.index(CURRENT_TMSI,i+1)#if tmsi in array increment its hit count
                                                			#print "match at", i,tmsiarray[i]
                                                			if i > -1:
                                            					tmsiarraycount[i] += 1
                                                                               	break
                                       			except ValueError:
                                       				tmsiarray.append(CURRENT_TMSI)# if its not in the array add it
                                       				#timestamp[i] = CURRENT_TIMESTAMP
                                       				tmsiarraycount.append(1)
                                            	#self.editdebugtmsi.AppendText(line+'\n')
                                                
                        	else:
                            	     #self.editdebug.AppendText(line+'\n')#<---- imsi are printed here
				     pass


	    		file.close()
			endindex+=2
			startindex += 2
#range loop ends here

	   #for debug output
	    #for tmsi in tmsiarray:
		   # print(tmsi)
	    
	    #prints the tmsi paged count from tmsiarraycount
	    x = 0
	    for tmsi in tmsiarray:
		    if tmsiarraycount[x] >= low_range and tmsiarraycount[x] <= high_range:
			    #print(tmsiarray[x]+":"+str(tmsiarraycount[x]))
			    self.editdebugtmsi.AppendText(tmsiarray[x]+":"+str(tmsiarraycount[x])+'\n')
		    x += 1



    ############################################################################
    #	MANUAL MODE TMSI FILTER
    #	PHONE MODE = MANUAL TIMESTAMPS
    ############################################################################
    
    def filterTmsiTimestampManMode(void):
	    START_TIME_OFFSET = 3
	    END_TIME_OFFSET = START_TIME_OFFSET + 3
	    SENT_TIMESTAMPS=[]
	    tmsiarray = []#HOLDS SINGLE TMSI
            timestamp = []
	    tmsiarraycount =[]#HOLDS HOW MANY TIMES THE TMSI WAS GOT
            CURRENT_TIMESTAMP = ""
            CURRENT_TMSI = ""
	    #self.delivery_report_wait_timer.Stop()
	    file = open("manual_timestamps.txt")

	    for line in file:
			line = line.rstrip('\n').rstrip('\r')
			SENT_TIMESTAMPS.append(int(line))

	    file.close()


	    low_range = int(self.edit_tmsi_range1.GetValue())
	    high_range = int(self.edit_tmsi_range2.GetValue())
	    self.editdebugtmsi.SetValue("")
	    startindex = 0
	    endindex = 1
	    loopcount = len(SENT_TIMESTAMPS)
	    print("ARRAY LEN MANUAL =: "+str(loopcount))
	    #LOOP THRU ALL THE TIMESTAMPS 
            for x in range(0,loopcount):
			print("IN OPEN FILE LOOP "+str(x)+"\n")

	    		file = open("tmsicount.txt")
			print("SENT >"+str(SENT_TIMESTAMPS[x]+int(self.edit_offset_range1.GetValue()))+" < "+str(SENT_TIMESTAMPS[x]+int(self.edit_offset_range2.GetValue())))

	    		for line in file:
		    		line = line.rstrip('\n').rstrip('\r')
		    		#self.editdebugtmsi.AppendText(line[:8]+"@"+line[9:])
                        	if line[0:2] != "0-":
					#
                            		CURRENT_TMSI = line[:8]
                            		CURRENT_TIMESTAMP = int(line[9:21])
		    			#self.editdebugtmsi.AppendText(str(CURRENT_TIMESTAMP))
		    			passint = 0;
					#print(str(startindex)+"\n"+str(endindex))
					# times[0] holds first timestamp and times[1] holds second timestamp
		    			if CURRENT_TIMESTAMP >= SENT_TIMESTAMPS[x]+int(self.edit_offset_range1.GetValue()) and CURRENT_TIMESTAMP <= SENT_TIMESTAMPS[x]+int(self.edit_offset_range2.GetValue()):
						#print("SENT "+SENT_TIMESTAMPS[x]+START_TIME_OFFSET)
                                		if len(line) >= 8:
                                    			i = -1
                                    			try:
                                        			while 1:
                                            				i = tmsiarray.index(CURRENT_TMSI,i+1)
                                                			#print "match at", i,tmsiarray[i]
                                                			if i > -1:
                                            					tmsiarraycount[i] += 1
                                                                               	break
                                       			except ValueError:
                                       				tmsiarray.append(CURRENT_TMSI)
                                       				#timestamp[i] = CURRENT_TIMESTAMP
                                       				tmsiarraycount.append(1)
                                            			#self.editdebugtmsi.AppendText(line+'\n')
                                                
                        	else:
                            	     self.editdebug.AppendText(line+'\n')

	    		file.close()
#range loop ends here

	   #for debug output
	    #for tmsi in tmsiarray:
		   # print(tmsi)
	    
	    #prints the tmsi paged count from tmsiarraycount
	    x = 0
	    for tmsi in tmsiarray:
		    if tmsiarraycount[x] >= low_range and tmsiarraycount[x] <= high_range:
			    #print(tmsiarray[x]+":"+str(tmsiarraycount[x]))
			    self.editdebugtmsi.AppendText(tmsiarray[x]+":"+str(tmsiarraycount[x])+'\n')
		    x += 1



    def OnStartSingleSmsTimer(void):
        print("Clicked")
        btnLabel = self.btnsmssend.GetLabel()
        if btnLabel == "Send":
            timer_single_sms.Start(1000*int(self.edit_sms_delay.GetValue()))
            print("Timer Started")
            self.btnsmssend.SetLabel("Stop")
        else:
            print "timer stopped!"
            timer_single_sms.Stop()
            self.btnsmssend.SetLabel("Send")


    def OnButtonMaxTimer(void):
        print("Clicked")
        btnLabel = self.btngetalltimsi.GetLabel()
        if btnLabel == "O":
            timer_max_users.Start(6000)
            #print("Monitor Timer Started")
            self.btngetalltimsi.SetLabel("X")
        else:
            #print "timer stopped!"
            timer_max_users.Stop()
            self.btngetalltimsi.SetLabel("O")

    def OnButtonMonTimer(void):
        print("Clicked")
        btnLabel = self.btntmsiscan.GetLabel()
        if btnLabel == "scan":
            timer_monitor_tmsi.Start(6000)
            #print("Monitor Timer Started")
            self.btntmsiscan.SetLabel("stop")
        else:
            #print "timer stopped!"
            timer_monitor_tmsi.Stop()
            self.btntmsiscan.SetLabel("scan")

    ###############################################
    #ALL SMS SENT AND CREATED HERE
    ###########################################    
    def timerSingleSendPDU(void):
        print("in timer")
        
	if getSmsSendCount() <= int(self.edit_sms_count.GetValue()):
		ser.port = self.combo_serial_ports.GetValue()
		smstype = self.combo_sms_types.GetValue()
		if smstype == "SILENT":
			SMS_TYPE = SILENT
		if smstype == "NORMAL":
			SMS_TYPE = NORMAL
		if smstype == "FLASH":
			SMS_TYPE = FLASH2
		
		#SMS_TYPE = FLASH2#NORMAL_TEXT
                ser.open()
		if ser.isOpen():
			incSmsSendCount()
			ser.flushInput() #flush input buffer, discarding all its contents
        		ser.flushOutput()#flush output buffer, aborting current output
			ser.write("AT+CMGS=17"+"\x0D")
                        PDU_STRING = createPduString(self.edit_sms_num.GetValue(),self.edit_sms_msg.GetValue(),SMS_TYPE)
			time.sleep(0.9)
			ser.write(PDU_STRING+"\x1A")
			time.sleep(0.9)
			ress = ser.read(500)
                        ser.close()
                        print("Sent")
			#self.lb_smsendcount_text.SetLabel("Sent:"+str(getSmsSendCount()))
			if "OK" or ">" in ress:
				self.editdebug.AppendText("Message Sent:\n"+str(getCurrentTimeStamp())+":\n"+self.edit_sms_msg.GetValue()+"\n")
				dumpTimeStampManMode()#optional
				ser.close()
			else:
				self.editdebug.AppendText("Response: "+ress)
				ser.close()
	#checking that the sms count is == to whatever the user set in the box
	if getSmsSendCount() == int(self.edit_sms_count.GetValue()):
		#print(str(getSmsSendCount))
		setSmsSendCount(0)
                timer_single_sms.Stop()
		self.btnsmssend.SetLabel("Send")
		#longer delay here will have more time from the sms to arrive to the receiver
		print("Stopping Single sms timer......")
		timer_delay_sms.Start(1000*int(self.edit_sms_rep_delay.GetValue()))
            	#print("Timer Started")
		#filterTmsiAllCount()

    
    ###########################################
    #put at commands in combobox
    #########################################
    file = open("at_cmds.txt")
    temparray =[]
    for line in file:
	line = line.rstrip('\n').rstrip('\r')
	temparray = line.split('#')
	at_cmds_array.append(temparray[0])
	#at_cmds_array_info.append(temparray[1])
    file.close()

    def update_gui_editdebug(data):
        self.editdebug.AppendText(data+'\n')
        setPortInUse(True)
        self.btnserialsend.Enable()
        self.btnserialsend2.Enable()

    #start the function on a thread so no to stop main app
    def SendCommandAtComboTread(void):
        self.btnserialsend2.Disable()
        if getPortStatus()== True:
            try:
               thread.start_new_thread(SendCommandAtCombo,(self.combo_serial_ports.GetValue(),self.combo_serial_cmds.GetValue()),)
               
            except:
               self.editdebug.AppendText("Unable to send command try again")
        else:
             self.editdebug.AppendText("Previous At command is progress")

    def SendCommandAtCombo(serial_port,cmd):
        setPortInUse(False)
        self.at_reply = getAtReply(serial_port,cmd)
        update_gui_editdebug(self.at_reply)
                  
            

    def SendCmdAtTread(void):
        self.btnserialsend.Disable()
        if getPortStatus()== True:
            try:
               thread.start_new_thread(SendCmdAt,(self.combo_serial_ports.GetValue(),self.edit_serial_atcmd.GetValue()),)
               
            except:
               self.editdebug.AppendText("Unable to send command try again")
        else:
             self.editdebug.AppendText("Previous At command is progress")


    def SendCmdAt(serial_port,cmd):
        setPortInUse(False)
        self.at_reply = getAtReply(serial_port,cmd)
        update_gui_editdebug(self.at_reply)  
     
    ################################
    # freq button funcs
    #############################
    def incgain(void):
        self.rfgain += 0.2
        #self._rfgain_slider.set_value(self.rfgain)
        self._rfgain_text_box.set_value(self.rfgain)
        self.src.set_gain(0 if self.iagc == 1 else self.rfgain, 0)

    def decgain(void):
        self.rfgain -= 0.2
        #self._rfgain_slider.set_value(self.rfgain)
        self._rfgain_text_box.set_value(self.rfgain)
        self.src.set_gain(0 if self.iagc == 1 else self.rfgain, 0)


    def incfreq(freq):
        self.ifreq += 0.1e6
        self._ifreq_text_box.set_value(self.ifreq)
        self.src.set_center_freq(self.ifreq)

    def decfreq(freq):
        self.ifreq -= 0.1e6
        self._ifreq_text_box.set_value(self.ifreq)
        self.src.set_center_freq(self.ifreq)

    def incfreqfine(freq):
        self.ifreq += 0.01e6
        self._ifreq_text_box.set_value(self.ifreq)
        self.src.set_center_freq(self.ifreq)

    def decfreqfine(freq):
        self.ifreq -= 0.01e6
        self._ifreq_text_box.set_value(self.ifreq)
        self.src.set_center_freq(self.ifreq)

    def setppm(ppm):
        self.ppm = ppm
        self.src.set_freq_corr(self.ppm)
        self.ppmtextbox.set_value(float(self.ppm))
        #print("ppm="+str(self.src.get_freq_corr()))

    def setincppm(ppm):
        self.ppm += 0.1
        self.src.set_freq_corr(self.ppm)
        self.ppmtextbox.set_value(float(self.ppm))
        #print("ppm="+str(self.src.get_freq_corr()))

    def setdecppm(ppm):
        self.ppm -= 0.1
        self.src.set_freq_corr(float(self.ppm))
        self.ppmtextbox.set_value(float(self.ppm))
        #print("ppm="+str(self.src.get_freq_corr()))

    def set_samp_rate(rate):
        self.samprate = int(rate)
        self.src.set_sample_rate(self.samprate)
        print(self.src.get_sample_rate())

    def set_iagc(iagc):
        self.iagc = iagc
        self._agc_check_box.set_value(self.iagc)
        self.src.set_gain_mode(self.iagc, 0)
        self.src.set_gain(0 if self.iagc == 1 else self.rfgain, 0)


    
    def set_rfgain(rfgain):
        self.rfgain = rfgain
        #self._rfgain_slider.set_value(self.rfgain)
        self._rfgain_text_box.set_value(self.rfgain)
        self.src.set_gain(0 if self.iagc == 1 else self.rfgain, 0)




    def getimsi_callback(void):
        thread.start_new_thread(getimsi,(self.combo_serial_ports.GetValue(),))
        self.btnimsigetinfo.Disable()

    def getimsi(serialport):
        #serialport = self.cb_reload_ports.get_value()
        self.data = GetKeyTmsiImsi(serialport)
        #self.text_imsi.set_value(self.data[len(self.data)-15:])
        self.edit_imsi.SetValue("***FILTERED***")
        self.edit_tmsi.SetValue(self.data[:8])
        self.edit_key.SetValue(self.data[9:25])
        self.btnimsigetinfo.Enable()

    def gettmsicount(serialport):
        tmsiarray,tmsicount = getTmsiCount()
        x = 0
        for tmsi in tmsiarray:
            self.editdebugtmsi.AppendText(tmsi+":"+str(tmsicount[x])+"\n")
            x += 1

    def send_at_cmd(data):
        
   	ser.open()
	if ser.isOpen():
         	ser.flushInput()
        	ser.flushOutput()
	        sercmd = data
                time.sleep(0.9)
		ser.write(sercmd+"\x0D")
		time.sleep(0.9)
		bytesToRead = ser.inWaiting()
		ress = ser.read(bytesToRead)
                print(ress)
	ser.close()
    def resetapp(void):
        tb.stop()
        tb.wait()
        self.disconnect(self.src, self.tuner, self.interpolator,self.receiver, self.converter, self.output)
        sample_rate = self.src.get_sample_rate()
        sys.stderr.write("sample rate: %d\n" % (sample_rate))

        gsm_symb_rate = 1625000.0 / 6.0
        sps = sample_rate / gsm_symb_rate / 4
        out_sample_rate = gsm_symb_rate * 4

        self.offset = 0

        taps = gr.firdes.low_pass(1.0, sample_rate, 145e3, 10e3, gr.firdes.WIN_HANN)
        self.tuner = gr.freq_xlating_fir_filter_ccf(1, taps, self.offset, sample_rate)

        self.interpolator = gr.fractional_interpolator_cc(0, sps)
        #channel type
        options.configuration = self.channel_combo_box.get_value()
        #use key or not
        options.key = "0000000000000000"#use this as default        
        if self.cb_imsi.GetValue() == True:
            options.key = str(self.edit_key.GetValue())

       
        self.receiver = gsm.receiver_cf(
        self.tune_corrector_callback, self.synchronizer_callback, 4,
        options.key.replace(' ', '').lower(),
        options.configuration.upper())

        self.output = gr.file_sink(gr.sizeof_float, options.output_file)
    #self.interpolator, self.receiver,
        self.connect(self.src, self.tuner, self.interpolator,self.receiver, self.converter, self.output)
        #ending
        time.sleep(0.5)

        tb.Run(True)
        

    ###### functins end #############
    gsm_scan_range = ['GSM900', 'GSM850', 'GSM-R', 'EGSM', 'DCS','PCS']
    combo_channels = ['0B','0C','1S', '2S', '3S', '4S','5S','6S','7S']
    sms_types = ['SILENT','FLASH','NORMAL']


    #serial
    self.portslist = "no ports"
    
    tested_ports = getOpenSerialPorts()
    if len(tested_ports) >= 1 :
        self.portslist = tested_ports[0]
    else:
        tested_ports.append("no ports")


    #clears delivery reports and deletes tmsi file for fresh attack
    def clearData(void):
	ser.port = self.combo_serial_ports.GetValue()
   	ser.open()
	if ser.isOpen():
		ser.write("AT+CMGD=1,4"+"\x0D")
		time.sleep(0.3)
		ress = ser.read(300)
		
		try:
			os.remove("tmsicount.txt")
			self.editdebug.AppendText("Tmsi file deleted\n")
		except OSError, e:
			self.editdebug.AppendText("Error: %s - %s.\n" % (e.filename,e.strerror))

		try:
			os.remove("manual_timestamps.txt")
			self.editdebug.AppendText("manual timestamps file deleted\n")
		except OSError, e:
			self.editdebug.AppendText("Error: %s - %s.\n" % (e.filename,e.strerror))


		if "OK" or ">" in ress:
			self.editdebug.AppendText("Delivery reports cleaned\n")
			ser.close()
		else:
			self.editdebug.AppendText("ERROR "+ress)
	ser.close()

    #######################SERIAL CONTROLS##########################################
    serialPanel = wx.Panel(self.GetWin(), -1,size=(100,100),style=wx.SUNKEN_BORDER)
    serialPanel.SetBackgroundColour(wx.GREEN)
    #mainPanel.SetBackgroundColour(wx.BLACK)
    self.serialtext1 = wx.StaticText(serialPanel, label="Serial:",pos=(1,5),size=(-1,20))
    self.btnserialreload = wx.Button(serialPanel, label="Reload", pos=(45,2),size=(55,20))
    self.combo_serial_ports = wx.ComboBox(serialPanel,size=(115,20), pos=(100,2), choices=tested_ports, style=wx.CB_READONLY)
    self.combo_serial_ports.SetSelection(0)

    self.serialtext2 = wx.StaticText(serialPanel, label="AT Cmd:",pos=(220,5),size=(-1,20))
    self.edit_serial_atcmd = wx.TextCtrl(serialPanel,value="AT",size=(90,20),pos=(280,2))
    self.btnserialsend = wx.Button(serialPanel, label="Send", pos=(375,2),size=(55,25))
    self.btnserialsend.Bind(wx.EVT_BUTTON,SendCmdAtTread)

    self.serialtext3 = wx.StaticText(serialPanel, label="Misc Cmds:",pos=(430,5),size=(-1,20))
    self.combo_serial_cmds = wx.ComboBox(serialPanel,size=(145,20), pos=(500,2), choices=at_cmds_array, style=wx.CB_READONLY)
    self.combo_serial_cmds.SetSelection(0)
    self.btnserialsend2 = wx.Button(serialPanel, label="Send", pos=(650,2),size=(45,25))
    self.btnserialsend2.Bind(wx.EVT_BUTTON,SendCommandAtComboTread)

    self.btnreset = wx.Button(serialPanel, label="Reset", pos=(775,2),size=(50,25))
    self.btnreset.Bind(wx.EVT_BUTTON,resetapp)


    ###########################################
    #Timers
    #########################################

    TIMER_SEND_SMS_ID = 100  # sent sms timer
    TIMER_DELAY_ID = 101  # delay to check for tmsi timer
    TIMER_MONITOR_ID = 102  # check tmsis every 2 seconds
    TIMER_MAX_USERS_ID = 103  # check tmsis every 2 seconds

    timer_single_sms = wx.Timer(serialPanel, TIMER_SEND_SMS_ID)
    timer_delay_sms = wx.Timer(serialPanel, TIMER_DELAY_ID)
    timer_monitor_tmsi = wx.Timer(serialPanel, TIMER_MONITOR_ID)
    timer_max_users = wx.Timer(serialPanel, TIMER_MAX_USERS_ID)

    wx.EVT_TIMER(serialPanel, TIMER_SEND_SMS_ID, timerSingleSendPDU) 
    wx.EVT_TIMER(serialPanel, TIMER_DELAY_ID, filterTmsiTimestampMode)#filterTmsiAllCount)
    wx.EVT_TIMER(serialPanel, TIMER_MONITOR_ID, filtertimsiTread)
    wx.EVT_TIMER(serialPanel, TIMER_MAX_USERS_ID, maxUsersTread) 

    #######################SMS CONTROLS##########################################
    smsPanel = wx.Panel(self.GetWin(), -1,size=(100,100),style=wx.SUNKEN_BORDER)
   
    self.combo_sms_types = wx.ComboBox(smsPanel,size=(90,20), pos=(2,5), choices=sms_types, style=wx.CB_READONLY)
    self.combo_sms_types.SetSelection(0)
    self.smstext1 = wx.StaticText(smsPanel, label="Number:",pos=(100,5),size=(-1,20))
    self.edit_sms_num = wx.TextCtrl(smsPanel,value="123456789012",size=(110,20),pos=(165,5))

    self.smstext2 = wx.StaticText(smsPanel, label="Msg:",pos=(280,5),size=(-1,20))
    self.edit_sms_msg = wx.TextCtrl(smsPanel,value="Hello",size=(90,20),pos=(310,5))

    self.smstext3 = wx.StaticText(smsPanel, label="Sms Count:",pos=(405,5),size=(-1,20))
    self.edit_sms_count = wx.TextCtrl(smsPanel,value="2",size=(25,20),pos=(480,5))

    self.smstext4 = wx.StaticText(smsPanel, label="Sms Delay:",pos=(508,5),size=(-1,20))
    self.edit_sms_delay = wx.TextCtrl(smsPanel,value="15",size=(25,20),pos=(580,5))

    self.smstext5 = wx.StaticText(smsPanel, label="Reports Delay:",pos=(610,5),size=(-1,20))
    self.edit_sms_rep_delay = wx.TextCtrl(smsPanel,value="15",size=(25,20),pos=(705,5))
    self.btnsmssend = wx.Button(smsPanel, label="Send", pos=(735,5),size=(45,25))
    self.btnsmssend.Bind(wx.EVT_BUTTON,OnStartSingleSmsTimer)

    
    ######################IMSI TMSI CONTROLS############################################
    imsiPanel = wx.Panel(self.GetWin(), -1,size=(100,100),style=wx.SUNKEN_BORDER)
    imsiPanel.SetBackgroundColour(wx.GREEN)
    self.imsitext1 = wx.StaticText(imsiPanel, label="IMSI:",pos=(2,5),size=(-1,20))
    self.edit_imsi = wx.TextCtrl(imsiPanel,value="000000000000000",size=(135,20),pos=(40,5))

    self.imsitext2 = wx.StaticText(imsiPanel, label="TMSI:",pos=(175,5),size=(-1,20))
    self.edit_tmsi = wx.TextCtrl(imsiPanel,value="00000000",size=(90,20),pos=(210,5))

    self.imsitext3 = wx.StaticText(imsiPanel, label="KEY:",pos=(305,5),size=(-1,20))
    self.edit_key = wx.TextCtrl(imsiPanel,value="0000000000000000",size=(140,20),pos=(330,5))
    self.cb_imsi = wx.CheckBox(imsiPanel,-1,'< use key', pos=(480,5))
    self.cb_imsi.SetValue(False)

    self.btnimsigetinfo = wx.Button(imsiPanel, label="<Get", pos=(570,5),size=(45,25))
    self.btnimsigetinfo.Bind(wx.EVT_BUTTON,getimsi_callback)    
    #####################TMSI CONTROLS#####################################
    tmsiPanel = wx.Panel(self.GetWin(), -1,size=(100,100),style=wx.SUNKEN_BORDER)
    self.tmsitext1 = wx.StaticText(tmsiPanel, label="Tmsi Range:",pos=(2,5),size=(-1,20))
    self.edit_tmsi_range1 = wx.TextCtrl(tmsiPanel,value="3",size=(25,20),pos=(80,5))
    self.tmsitext2 = wx.StaticText(tmsiPanel, label=">==<",pos=(110,5),size=(-1,20))
    self.edit_tmsi_range2 = wx.TextCtrl(tmsiPanel,value="7",size=(25,20),pos=(155,5))

    self.tmsitext3 = wx.StaticText(tmsiPanel, label="Offsets:",pos=(180,5),size=(-1,20))
    self.edit_offset_range1 = wx.TextCtrl(tmsiPanel,value="3",size=(25,20),pos=(230,5))
    self.tmsitext4 = wx.StaticText(tmsiPanel, label=">==<",pos=(260,5),size=(-1,20))
    self.edit_offset_range2 = wx.TextCtrl(tmsiPanel,value="7",size=(25,20),pos=(305,5))

    self.btntmsiauto = wx.Button(tmsiPanel, label="Reports", pos=(335,5),size=(60,25))
    self.btntmsimanual = wx.Button(tmsiPanel, label="Manual", pos=(395,5),size=(60,25))
    #self.btntmsimanual.Bind(wx.EVT_BUTTON,gettmsicount)
    self.btntmsimanual.Bind(wx.EVT_BUTTON,filterTmsiTimestampManMode)
    self.btntmsiclean = wx.Button(tmsiPanel, label="Clean", pos=(455,5),size=(60,25))
    self.btntmsiclean.Bind(wx.EVT_BUTTON,clearData)
    #######################DEBUG TEXTBOXS###########################################
    debugPanel = wx.Panel(self.GetWin(), -1,size=(100,100),style=wx.SUNKEN_BORDER)
    self.debugtext1 = wx.StaticText(debugPanel, label="Tmsi's:",pos=(26,1),size=(-1,20))
    self.btngetalltimsi = wx.Button(debugPanel, label="O", pos=(1,2),size=(25,25))
    self.btngetalltimsi.Bind(wx.EVT_BUTTON,OnButtonMaxTimer)#filtertimsiTread(void) filterTmsiAllCount

    self.editdebugtmsi = wx.TextCtrl(debugPanel, size=(120,85),value="",pos=(1,30), style=wx.TE_MULTILINE)

    self.editdebug = wx.TextCtrl(debugPanel, size=(250,85),value="",pos=(135,30), style=wx.TE_MULTILINE)
    self.debugtext2 = wx.StaticText(debugPanel, label="Debug Info:",pos=(135,2),size=(-1,20))
    self.btndebugclear = wx.Button(debugPanel, label="Clear", pos=(210,2),size=(55,25))

    self.tmsitext5 = wx.StaticText(debugPanel, label="SpamTmsi's:",pos=(385,2),size=(-1,20))
    self.btntmsiscan = wx.Button(debugPanel, label="scan", pos=(385,20),size=(45,25))
    self.btntmsiscan.Bind(wx.EVT_BUTTON,OnButtonMonTimer)

    self.btntmsiadd = wx.Button(debugPanel, label="add", pos=(430,20),size=(35,25))


    self.edit_spam_tmsi = wx.TextCtrl(debugPanel,value="FFFFFFF1",size=(100,20),pos=(385,45))
    self.combo_spam_tmsi = wx.ComboBox(debugPanel,size=(100,20), pos=(385,65), choices=sms_types, style=wx.CB_READONLY)
    self.btntmsiclearspam = wx.Button(debugPanel, label="Clear", pos=(385,90),size=(80,25))

    options = get_options()

    self.tune_corrector_callback = tune_corrector(self)
    self.synchronizer_callback = synchronizer(self)
    self.converter = gr.vector_to_stream(gr.sizeof_float, 142)

    self.atcmd = "AT" 
    self.imsi = "000000000000000"
    self.tmsi = "00000000"
    self.key = "0000000000000000"
    self.nokey = "0000000000000000"


    
    self.samprate = int(options.sample_rate)
    self.ifreq = options.frequency
    self.rfgain = options.gain
    self.ppm = 0.0
    self.src = osmosdr.source_c(options.args)
    self.src.set_center_freq(self.ifreq)
    self.src.set_sample_rate(int(options.sample_rate))
    self.chan = options.configuration.upper()

    if self.rfgain is None:
        self.src.set_gain_mode(1)
        self.iagc = 1
        self.rfgain = 0
    else:
        self.iagc = 0
        self.src.set_gain_mode(0)
        self.src.set_gain(self.rfgain)

       

    # may differ from the requested rate
    sample_rate = self.src.get_sample_rate()
    sys.stderr.write("sample rate: %d\n" % (sample_rate))

    gsm_symb_rate = 1625000.0 / 6.0
    sps = sample_rate / gsm_symb_rate / 4
    out_sample_rate = gsm_symb_rate * 4

    self.offset = 0

    taps = gr.firdes.low_pass(1.0, sample_rate, 145e3, 10e3, gr.firdes.WIN_HANN)
    self.tuner = gr.freq_xlating_fir_filter_ccf(1, taps, self.offset, sample_rate)

    self.interpolator = gr.fractional_interpolator_cc(0, sps)
    #options.configuration = "2S"
    self.receiver = gsm.receiver_cf(
         self.tune_corrector_callback, self.synchronizer_callback, 4,
         options.key.replace(' ', '').lower(),
         options.configuration.upper())

    self.output = gr.file_sink(gr.sizeof_float, options.output_file)

    self.connect(self.src, self.tuner, self.interpolator,self.receiver, self.converter, self.output)

    def set_ifreq(ifreq):
        self.ifreq = ifreq
        self._ifreq_text_box.set_value(self.ifreq)
        self.src.set_center_freq(self.ifreq)


    def fftsink2_callback(x, y):
        if abs(x / (sample_rate / 2)) > 0.9:
            set_ifreq(self.ifreq + x / 2)
        else:
            sys.stderr.write("coarse tuned to: %d Hz\n" % x)
            self.offset = -x
            self.tuner.set_center_freq(self.offset)
    #fft sizes 256 512 1024 2048
    self.scope = fftsink2.fft_sink_c(self.GetWin(),
        title="Wideband Spectrum",
        fft_size=256,
        sample_rate=sample_rate,
        ref_scale=2.0,
        ref_level=0,
        y_divs=10,
        fft_rate=10,
        average=False,
        avg_alpha=0.3)

    self.Add(self.scope.win)




    ###################################
    #  freq text and buttons
    ##################################
    freq_sizer = wx.BoxSizer(wx.HORIZONTAL)
    self.ppmtextbox = forms.text_box(
        sizer=freq_sizer,
        width=40,
        parent=self.GetWin(),
        value=self.ppm,
        callback=setppm,
        label="ppm",
        proportion=0,
        converter=forms.float_converter()
    )
   # self.Add(self.ppmtextbox)

    self.btnincppm = forms.single_button(
            sizer=freq_sizer,
            width=25,
            parent=self.GetWin(),
            label='+',
            proportion=0,
            callback=setincppm,)
    #self.Add(self.btnincppm)
    
    self.btndecppm = forms.single_button(
            sizer=freq_sizer,
            width=25,
            parent=self.GetWin(),
            label='-',
            callback=setdecppm,)
    
    self._ifreq_text_box = forms.text_box(
        sizer=freq_sizer,
        parent=self.GetWin(),
        value=self.ifreq,
        callback=set_ifreq,
        label="Freq",
        proportion=0,
        converter=forms.float_converter(),
    )
    self.btnincfreq = forms.single_button(
            sizer=freq_sizer,
            width=25,
            parent=self.GetWin(),
            label='+',
            callback=incfreq,)

    self.btndecfreq = forms.single_button(
            sizer=freq_sizer,
            width=25,
            parent=self.GetWin(),
            label='-',
            callback=decfreq,)
    self.finelabel = forms.static_text(
        sizer=freq_sizer,
        parent=self.GetWin(),
        value="",
        label="Fine Tune",
    )

    self.btnincfreqfine = forms.single_button(
            sizer=freq_sizer,
            width=25,
            parent=self.GetWin(),
            label='+',
            callback=incfreqfine,)

    self.btndecfreqfine = forms.single_button(
            sizer=freq_sizer,
            width=25,
            parent=self.GetWin(),
            label='-',
            callback=decfreqfine,)

    self.channel_combo_box = forms.drop_down(
        sizer=freq_sizer,
        parent=self.GetWin(),
        width=55,
        value='0B',
        choices=combo_channels,
        label="Channel",
        
    )

    self.samplerate_text_box = forms.text_box(
        sizer=freq_sizer,
        width=40,
        parent=self.GetWin(),
        value=self.samprate,
        callback=set_samp_rate,
        label="Samp",
        proportion=0,
        converter=forms.float_converter(),
    )

    self._rfgain_text_box = forms.text_box(
        parent=self.GetWin(),
        width=25,
        sizer=freq_sizer,
        value=self.rfgain,
        callback=set_rfgain,
        label="Gain",
        converter=forms.float_converter(),
        proportion=0,
    )
    self._agc_check_box = forms.check_box(
        sizer=freq_sizer,
        parent=self.GetWin(),
        value=self.iagc,
        callback=set_iagc,
        label="[Auto] ",
        true=1,
        false=0,
    )    
    self.btnincgain = forms.single_button(
            sizer=freq_sizer,
            width=25,
            parent=self.GetWin(),
            label='+',
            callback=incgain,)

    self.btndecgain = forms.single_button(
            sizer=freq_sizer,
            width=25,
            parent=self.GetWin(),
            label='-',
            callback=decgain,)

    self.Add(freq_sizer)
    self.Add(serialPanel)
    self.Add(smsPanel)
    self.Add(imsiPanel)
    self.Add(tmsiPanel)
    self.Add(debugPanel)
    


    self.scope.set_callback(fftsink2_callback)

    self.connect(self.src, self.scope)





def get_options():
    parser = OptionParser(option_class=eng_option)
    parser.add_option("-a", "--args", type="string", default="",help="gr-osmosdr device arguments")
    parser.add_option("-s", "--sample-rate", type="eng_float", default=1400000, help="set receiver sample rate (default 1800000)")
    parser.add_option("-f", "--frequency", type="eng_float", default=927.5e6, help="set receiver center frequency")
    parser.add_option("-g", "--gain", type="eng_float", default=None, help="set receiver gain")
    parser.add_option("-p", "--ppm", type="eng_float",default=0,help="set receiver ppm")

    # demodulator related settings AD 6A 3E C2 B4 42 E4 00
    parser.add_option("-o", "--output-file", type="string", default="cfile2.out", help="specify the output file")
    parser.add_option("-v", "--verbose", action="store_true", default=False, help="dump demodulation data")
    parser.add_option("-k", "--key", type="string", default="00 00 00 00 00 00 00 00", help="KC session key")
    parser.add_option("-c", "--configuration", type="string", default="0B", help="Decoder configuration")
    (options, args) = parser.parse_args()
    if len(args) != 0:
        parser.print_help()
        raise SystemExit, 1

    return (options)

if __name__ == '__main__':
        tb = top_block()
        tb.Run(True)
        tb.start()
        #tb.wait()
        #tb.Run(True)
