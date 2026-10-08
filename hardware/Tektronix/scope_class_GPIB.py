import socket
import numpy as np
from struct import unpack
import pyqtgraph as pg
import time
import os.path
import csv
import visa

class Socket_Instrument(object):
    ''' socket replacement for visa.instrument class'''
    is_connected = False
    def __init__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
       # self.s.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,1250)
        #self.s.connect((IPaddress, PortNumber))

    def write(self, cmd):
        self.s.send(cmd.encode('UTF-8') + '\n'.encode('UTF-8',"backslashreplace"))
        

    def ask(self, cmd, buffer = 1250, timeout = 5):
        # It is necessary to encode the string as bytes in python 3
        # Send and recieve the commands as bytes and convert to string when returning
        self.s.send(cmd.encode('UTF-8') + '\n'.encode('UTF-8',"backslashreplace"))
        response = ''.encode('UTF-8',"backslashreplace")
        while True:
            char = "".encode('UTF-8',"backslashreplace")
            try:
                char = self.s.recv(1)
            except:
                time.sleep(0.00001)
                if response.decode('UTF-8',"backslashreplace").rstrip() != "":
                    break
            if char:
                response += char
        return response.decode('UTF-8',"backslashreplace").rstrip()


    def read(self):
        response = ''.encode('UTF-8',"backslashreplace")
        while True:
            char = "".encode('UTF-8',"backslashreplace")
            try:
                char = self.s.recv(1)
            except:
                time.sleep(0.001)
                if response.decode('UTF-8',"backslashreplace").rstrip() != "":
                    break
            if char:
                response += char
        return response.decode('UTF-8',"backslashreplace").rstrip()
        
    def readBinary(self):
        response = ''.encode('UTF-8',"backslashreplace")
        while True:
            char = "".encode('UTF-8',"backslashreplace")
            try:
                char = self.s.recv(1)
            except:
                time.sleep(0.001)
                if response.decode('UTF-8',"backslashreplace").rstrip() != "":
                    break
            if char:
                response += char
        return response
        
    def getName(self):
            return self.ask('*IDN?')

    
    def connect(self,IPaddress, PortNumber = 4000):
        self.s.connect((IPaddress, PortNumber))
        self.s.setblocking(False)
        self.is_connected = True
        
    def close(self):
        self.s.close()

class Dpo7000:
    """ The class for the Tektronix DPO7254 oscilloscope
    This class is responsible for any functionality not specific to a
    particular channel, e.g. horizontal scale adjustment.
    """
 
    x_incr = False
    x_num = False
    numAvg = 0
    sample_rate = 0
    selectedChannel = 1
    debug = False
    available_tdivs = [1000,
                       500,
                       200,
                       100,
                       50,
                       20,
                       10,
                       5,
                       2,
                       1,
                       0.5,
                       0.2,
                       0.1,
                       0.05,
                       0.02,
                       0.01,
                       0.005,
                       0.002,
                       0.001,
                       0.0005,
                       0.0002,
                       0.0001,
                       0.00005,
                       0.00002,
                       0.00001,
                       0.000005,
                       0.000002,
                       0.000001,
                       0.0000005,
                       0.0000002,
                       0.0000001,
                       0.00000005,
                       0.00000002,
                       0.00000001,
                       0.000000005,
                       0.0000000025,                       
                       0.000000001,
                       0.0000000005,
                       0.00000000025,
                       0.0000000002,
                       0.000000000125,
                       0.0000000001,
                       0.0000000000625,
                       0.00000000005,
                       0.000000000025]
 
    def __init__(self, debug=False,):
        self.instAddress = 'GPIB0::1::INSTR'
        #self.name = self.getName             
        self.debug = debug
        #if self.name == False:
         #   print("Uh Oh! The machine on " + IPaddress + " isn't responding")
            #sys.exit()
        #else:
         #   print("Connected to: " + self.name.rstrip('\n'))
         
    def connect(self,instAddress):
        rm = visa.ResourceManager()
        self.inst = rm.open_resource(instAddress)
        
    def read(self):
        return self.inst.read()
        
    def readBinary(self):
        return self.inst.read_raw()
        
    def write(self,cmd):
        return self.inst.write(cmd)
    
    def ask(self,cmd):
        return self.inst.ask(cmd)

    def query_binary_values(self,cmd):
        self.inst.query_binary_values(cmd, datatype='f', is_big_endian=True)
    def getName(self):
        return self.inst.getName()
        
    def close(self):
        self.inst.close()
        
    def issueCommand(self, command,feedback, wait=True):
        self.inst.write(command)
        if wait == True:
            self.checkComplete()
        
    def checkComplete(self):
        tmp = self.inst.write("*OPC?")
        #print(tmp)
        while tmp != '1':
            tmp = self.inst.read()
        
    def set_tScale(self, s):
        self.issueCommand("HORIZONTAL:MODE:SCALE " + str(s),
                          "Setting timebase to " + str(s) + " s/div")
                          
    def get_tScale(self):
        return self.ask("HORIZONTAL:MODE:SCALE?")
                          
    def set_averaging(self, averages):
        """ Sets or disables averaging (applies to all channels).
        Valid number of averages are either 4,16,64 or 128.
        A value of 0 or False disables averaging
        """
 
        if averages > 0:
            if self.debug == True:
                print("Setting averaging to " + str(averages) + " samples")
            self.write("ACQuire:MODe AVERage")
            self.write("ACQuire:NUMAVg " + str(averages))
            self.numAvg = averages
        elif averages == 0 or averages == False:
            if self.debug == True:
                print("Disabling averaging")
            self.write("ACQuire:MODe SAMPLE")
            self.write("ACQuire:NUMAVg " + str(0))
            self.numAvg = 0
        else:
            print("Not a valid number of averages")
            sys.exit()
            
    def get_averaging(self):
        return self.ask("ACQuire:MODe?")
            
    def acquisition(self, enable):
        """ Sets acquisition parameter.
        Toggling this controls whether the scope acquires a waveform
 
        Arguments:
        enable [bool] Toggles waveform acquisition
        """
        if enable:
            self.write("ACQuire:STATE ON")
        else:
            self.write("ACQuire:STATE OFF")
            
    def get_numAcquisitions(self):
        """ Indicates the number of acquisitions that have taken place since
        starting oscilloscope acquisition. The maximum number of acquisitions
        that can be counted is 231-1. This value is reset to zero when you
        change most Acquisition, Horizontal, Vertical, or Trigger arguments
        that affect the waveform
        """
        num = self.ask("ACQuire:NUMACq?")
        while num == False:
            num = self.read()
        return int(num)
        
    def getAcqLength(self):
        tmp = self.ask('HORizontal:ACQLENGTH?')
        return tmp
    
    def waitForAcquisitions(self, num=False):
        """ Waits in a loop until the scope has captured the required number of
        acquisitions
        """
        until = 0
        if num == False and self.numAvg == False:
            print("Waiting for a single acquisition to finish")
            until = 1
        elif num != False:
            until = num
            print("Waiting until " + str(until) + " acquisitions have been made")
        else:
            until = self.numAvg
            print("Waiting until " + str(until) + " acquisitions have been made")
        last = 0
        done = self.get_numAcquisitions()
        while done < until:
            if done != last:
                print("Waiting for " + str(until - done) + " acquisitions")
                last = done
            done = self.get_numAcquisitions()
            time.sleep(0.01)
            
        
        
class channel(Dpo7000):
    """ Channel class that implements the functionality related to one of
    the oscilloscope's physical channels.
    """
    channel = False  # Channel num
    y_offset = False
    y_mult = False
    y_zero = False
    curve_raw = False
 
    available_vdivs = [10.0,
                       9.0,
                       8.0,
                       7.0,
                       6.0,
                       5.0,
                       4.0,
                       3.0,
                       2.0,
                       1.0,
                       0.9,
                       0.8,
                       0.7,
                       0.6,
                       0.5,
                       0.4,
                       0.3,
                       0.2,
                       0.1,                       
                       0.09,
                       0.08,
                       0.07,
                       0.06,
                       0.05,
                       0.04,
                       0.03,
                       0.02,
                       0.01,                      
                       0.009,
                       0.008,
                       0.007,
                       0.006,
                       0.005,
                       0.004,
                       0.003,
                       0.002,
                       0.001] 
                       
    def __init__(self, inst, channel):
        self.inst = inst
        self.channel = channel   
    
    def updateConnection(self,inst):
        self.inst = inst
        
    def setVScale(self,s):
        self.issueCommand('CH' + str(self.channel) + ':SCAle ' + str(s),"Setting voltage scale to " + str(s) + " V/div")
    
    def getVScale(self):
        tmp = self.ask("CH" + str(self.channel) + ":SCAle?")
        return float(tmp)
    
    #Switch on or off this channel
    def selectChannel(self, on=True):
        if on ==True:
            self.issueCommand('SELECT:CH'+str(self.channel)+' ON','')
        else:
            self.issueCommand('SELECT:CH'+str(self.channel)+' OFF','')
        
        
    def set_waveformParams(self,
                           encoding='ASCII',
                           start=0,
                           stop=5000,
                           width=1):
        """ Sets waveform parameters for the waveform specified by the channel
        parameter.
 
        Arguments:
           channel [int - 1-4] - specifies which channel to configure
           encoding (optional: 'ASCII') [str - {'ASCII' , 'Binary'}] - how the
           waveform is to be transferred (ascii is easiest but slowest)
           start (optional: 0) [int - 0-2499] - data point to begin transfer from
           stop (optional: 2500) [int - 1-2500] - data point to stop transferring at
           width (optional: 2) [int] - how many bytes per data point to transfer.
        """
        self.issueCommand("DATA:SOUrce CH" + str(self.channel),
                          "Setting data source to channel " + str(self.channel),
                          False)
        if encoding == 'ASCII':
            self.issueCommand("DATA:ENCdg ASCIi",
                              "Setting data encoding to ASCII", False)
            self.encoding = 'ASCII'
        else:
            self.issueCommand("DATA:ENCdg RPBinary",
                              "Setting data encoding to RPBinary", False)
            self.encoding = 'RPBinary'
        self.issueCommand("DATA:STARt " + str(start),
                          "Setting start data point to " + str(start), False)
        self.issueCommand("DATA:STOP " + str(stop),
                          "Setting stop data point to " + str(stop), False)
        self.issueCommand("DATA:WIDTH " + str(width),
                          "Setting of bytes to transfer per waveform point to " + str(width),
                          False)
    # Acquires a single acquisition - Equivalent to pressing 'single on the scope'
    def acquireSingle(self, pause = 0.05):
        # Set the acquisition mode to sequence - This stops after the required number of waveforms are aquired
        self.write("ACQ:STOPA SEQ")
        time.sleep(0.05)
        # Start acquisition
        self.write("ACQ:STATE ON")
        # Wait for acquisition to finish
        while '1' in self.ask("ACQ:STATE?"):
            time.sleep(pause)
            
    # Switches off fast frame acquisition and sets the horizontal mode to auto
    def undoFastFrameSetUp(self):
        # Put the horizontal mode back to auto
        self.write('HORizontal:MODE AUTO')
        # Switch off fast frame acq
        self.write('HORizontal:FASTframe:STATE OFF')
        # %first point recorded for a single frame
        self.write('HORizontal:FASTframe:MULtipleframes:FRAMESTart:CH'+ str(self.channel) + ' 1')
        # First recorded point in a frame
        self.write('DATa:FRAMESTARt 1')
        # Last recorded point in a frame
        self.write('DATa:FRAMESTOP '+str(1))
        
    def fastFrameSetup(self, datStart, datStop, nFrames):
        # Set parameters for waveform transfer
        self.set_waveformParams(encoding = 'RPBINARY', start = datStart, stop = datStop)
        #Make sure channel is on
        self.acquisition(False)
        self.write('HORizontal:MODE MANual')
        # Turn on fast frame acq
        self.write('HORizontal:FASTframe:STATE ON')
        # Set no of frames
        self.write('HORizontal:FASTframe:COUNt '+str(nFrames))
        # %first point recorded for a single frame
        self.write('HORizontal:FASTframe:MULtipleframes:FRAMESTart:CH'+ str(self.channel) + ' 1')
        # First recorded point in a frame
        self.write('DATa:FRAMESTARt 1')
        # Last recorded point in a frame
        self.write('DATa:FRAMESTOP '+str(nFrames))
        
    def getFastFrame(self, datStart, datStop, nFrames):
        # Acquire single acquisition
        self.acquireSingle(pause = 0.0001)
        # Get the waveform 
        dat = self.get_waveform(encoding = 'RPBINARY')
        print(len(dat[1]))
        # split the data up into frames 
        dat_y = []
        print(datStop)
        print(datStart)
        #for k in range(nFrames):
        #    dat_y.append(list(dat[1][k*int(datStop):k*int(datStop)+int(datStop)]))
        # Return frames in the format [[x],[[y frame1],[y frame2],[y frame3],...]]
        return [dat[0],dat[1]]
            
    # Function which records a fast frame sequence acquisition and sends it from the scope to the computer
    # datStart and datStop are the start and stop values of each frame 
    # nFrames is the number of frames to be acquired 
    def acquireFastFrame(self, datStart, datStop, nFrames):
        # Set parameters for waveform transfer
        self.set_waveformParams(encoding = 'RPBINARY', start = datStart, stop = datStop)
        #Make sure channel is on
        self.acquisition(False)
        self.write('HORizontal:MODE MANual')
        # Turn on fast frame acq
        self.write('HORizontal:FASTframe:STATE ON')
        # Set no of frames
        self.write('HORizontal:FASTframe:COUNt '+str(nFrames))
        # %first point recorded for a single frame
        self.write('HORizontal:FASTframe:MULtipleframes:FRAMESTart:CH'+ str(self.channel) + ' 1')
        # First recorded point in a frame
        self.write('DATa:FRAMESTARt 1')
        # Last recorded point in a frame
        self.write('DATa:FRAMESTOP '+str(nFrames))
        # Acquire single acquisition
        self.acquireSingle(pause = 0.0001)
        # Get the waveform 
        dat = self.get_waveform(encoding = 'RPBINARY')
        # split the data up into frames 
        dat_y = []
        print(datStop)
        print(datStart)
        for k in range(nFrames):
            dat_y.append(list(dat[1][k*int(datStop):k*int(datStop)+int(datStop)]))
        # Return frames in the format [[x],[[y frame1],[y frame2],[y frame3],...]]
        return [dat[0],dat]
        
    
    def get_waveform(self, debug=False, wait=True,encoding = 'ASCII'):
            """ Downloads this channels waveform data.
            This function will not make any adjustments to the V/div settings.
            If the parameter 'wait' is set to false, the most recent waveform will be
            captured. Otherwise the scope will wait for the next data acquisition
            to complete before downloading waveform data.
            """
            
            # At the moment only ascii encoding is working
            if wait:
                self.waitForAcquisitions()
                print('waiting')
            #print(self.channel)
            self.issueCommand("DATA:SOUrce CH" + str(self.channel),
                            "Setting data source to channel " + str(self.channel), wait = False)
            if debug:
                print("Requesting waveform setup information")

            y_offset = False
            y_mult = False
            x_incr = False
            y_zero = False
            x_num = False
            
            # Get the vertical scale factor 
            y_mult = float(self.ask('WFMOutpre:YMULT?'))
            #print(y_mult)
            #get the zero voltage position
            y_zero = float(self.ask('WFMOUTPRE:YZERO?'))
            #print(y_zero)
            # Get the y offset4
            y_offset = float(self.ask('WFMOUTPRE:YOFF?'))
            #print(y_offset)
            x_incr = float(self.ask('WFMOUTPRE:XINCR?'))
            #print(x_incr)
            # Number of points in the waveform 
            n_Pts = int(self.ask('WFMOutpre:NR_Pt?'))
           # print(n_Pts)
            # Number of frames to be transmitted
            n_Fr = int(self.ask('WFMOutpre:NR_FR?'))
            #print(n_Fr)
            # If the scope did not return a y zero value, set it to zero
            if y_zero == False:
                y_zero = 0
            
            # Ask the scope for the waveform
            print('curve')
            self.write('HEADER OFF')
            self.write('CURVE?')
            time.sleep(0.01)
                
            print('read')
            if encoding == 'ASCII':
                tmp = self.read()
                if tmp == False:
                    tmp = self.read()
                out = tmp.split(',')
                data = [float(i) for i in out]
                data_y = [(i - y_offset) * y_mult  + y_zero for i in data]
            else: 
                tmp = self.inst.readBinary()
                if tmp == False:
                    tmp = self.inst.readBinary()
                #Unpack the waveform
                #print(tmp)
                headerlen = len(tmp) - n_Pts*n_Fr -1
                #headerlen = 2 + int(tmp[1])
                header = tmp[:headerlen]
                data = tmp[headerlen:-1]
                data = np.array(unpack('%sB' % len(data),data))
                data_y = (data + y_offset) * y_mult + y_zero
            
            print('map')
            #data_y = (data - y_offset) * y_mult  + y_zero
            #data_y = list(map(lambda x: ((int(x) - y_offset) * y_mult) + y_zero, data))
            #data_x = list(map(lambda x: x * x_incr , range(len(data_y))))
            data_x = list(map(lambda x: x * x_incr , range(n_Pts)))
            return [data_x, data_y]         
            
    # Function which creates a folder at folderpath if one doesn't already exist
    def saveWaveformSetup(self, foldername, debug = False):
        # make a folder called foldername on c drive
        self.write('FILESystem:CWD "C:\scans"')
        self.write('FILESystem:MKDir' + '"' +  str(foldername) + '"')
        # Set the save format for the scope to CSV
        #self.write('SAVE:WAVEFORM:FILEFORMAT SPREADSHEETCsv')
            
    # def saveWaveform(self, foldername, filename)
    #     scope.write("SAVE:WAVEFORM ALL, \"E:/Saves/All_%s\"" %loop)
        
    # This function saves the data output from get_waveform as a csv file in the 
    # format x[i], y[i][k] etc
    # Arguments overloaded so that you can either enter the full filepath or a 
    # folder path + a filename.
    def saveToCsv(self,data,filePath = None,folderPath = None, fileName = None ):
        # Folder path and file name entered.
        if filePath == None and folderPath != None and fileName != None:
            # Create the full filepath
            file = os.path.abspath(os.path.join(folderPath, fileName + '.csv'))
        # full file path entered
        elif filePath != None and folderPath == None and fileName == None:
            file = os.path.abspath(filePath)
        else: print('Error - either enter a full filepath or a folder path + file name')
        # Open the csv file to be written
        with open(file,"w+") as csvfile:
            #Start csvwriter
            writer = csv.writer(csvfile, delimiter = ',')
            # loop over the data 
            for i in range(len(data[0])):
                row = []
                row.append(data[0][i])
                # This if statement checks whether the data corresponds to a single
                # acquisition or a sequence.
                if isinstance(data[1][0],list)==True:
                    for k in range(len(data[1])):
                        row.append(data[1][k][i])
                else: row.append(data[1][i])
                writer.writerow(row)
      
    # saves data as .npy binary file 
    # The data format is the same as saveToCsv
    def saveToNpy(self,data,filePath = None,folderPath = None, fileName = None ):
        # Folder path and file name entered.
        if filePath == None and folderPath != None and fileName != None:
            # Create the full filepath
            file = os.path.abspath(os.path.join(folderPath, fileName))
        # full file path entered
        elif filePath != None and folderPath == None and fileName == None:
            file = os.path.abspath(filePath)
        else: print('Error - either enter a full filepath or a folder path + file name')
        # Save the data array
        print('save')
        print(len(data[0]))
        print(len(data[1]))
        np.save(file,data)
        print('save complete')
        
