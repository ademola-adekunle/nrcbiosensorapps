#! /usr/bin/python3

#Version Control: March 8th, 2020 at 7:30
#VERSION 1 
#NOTE -> THIS PROGRAM USES Python 3.7, 3.8
#Import packages: Serial+serial tools for serial communication, io/os for file manipulation, time/datetime for dates, re(regex) for parsing, and math for calculations
import sys
import glob
import serial
import serial.tools.list_ports
import io
import time
import datetime
import os
import re
import math
import platform

#Matplotlib
import matplotlib
matplotlib.use('QT5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

#Numpy for dataframes and matplotlib dependencies
import numpy as np
from numpy import arange,sin,pi

#Used for excel reading and writing (Version 0.23.3)
import pandas as pd

#Used to find file path
import pathlib
from pathlib import Path

#Used to support threading
import threading
from threading import Thread

#Used for BOD/COD regressions (Version 0.20.2)
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures, FunctionTransformer
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from scipy.integrate import simps #for mathematical calculations
from numpy import trapz #for mathematical calculations

#GUI packages
import PyQt5
from PyQt5 import QtWidgets, QtCore, QtGui, uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

#Global Variables 
ports = serial.tools.list_ports.comports() #List of all connected serial ports
biosensor_ports = []   #List of all biosensor compatible ports
serial_objects = []    #List of all biosensor serial objects
channel_selection = [] #List of all channels
channel_params = []    #List of the biosensor parameters
acquisiton_rate = []   #Time interval between each acquisition
mainTable = []         #Display Table for acquisition data
outputs = []           #Placeholder used to store acquisition data
graphs_limits = []     #Y_limit params for graph
startTime = []         #Start time of program
endTime = []           #End time used for plotting elapsed time
graphspan = []         #Graph span used for plotting purposes (Default: 6hours)
timevec = []           #Used for elapsed time
settingsFlag = []      #Flag used to check if settings need to be saved
endFlag = []           #End thread condition
initial = False        #If no ports found -> Exit program
loaded = False         #While main UI isn't loaded
loaded2 = False
startUp = True        #If this is the initial autoStartRun
dfs_old = []           #Previous dataframe data
dfs = []               #New calibration dataframe data
bod_cod_flag = []      #If BOD/COD mode -> DO THIS flag
start_plotting = []    #Once data_acquisition is done -> start plotting flag
waiting_for_something_to_happen = [] #Filler
threadEnded = []       #Once thread has been ended
bod_fits = []
cod_fits = []

file_locations = [] #File locations list

#All file path globals used
current = pathlib.Path().absolute()
if platform.system() == 'Linux':
    uis = current / 'UI_Forms'
else:
    uis = 'UI_Forms'
defaults = current / 'defaults.txt'

data_dir_channel1 = current / 'Channel1'

data_dir_channel1_TOX = data_dir_channel1 / 'TOX'
channel1_TOX_Logs = data_dir_channel1_TOX / 'Channel1_TOX_Logs.txt'
channel1_TOX_Polarization = data_dir_channel1_TOX / 'Channel1_TOX_PolarizationTest.txt'
data_dir_channel1_TOX_Configurations = data_dir_channel1_TOX / 'Channel1_TOX_Configuration'
channel1_TOX_Configurations = data_dir_channel1_TOX_Configurations / 'Channel1_TOX_Config.txt'

data_dir_channel1_BODCOD = data_dir_channel1 / 'BODCOD'
channel1_BODCOD_Logs = data_dir_channel1_BODCOD / 'Channel1_BODCOD_Logs.txt'
channel1_BODCOD_Polarization = data_dir_channel1_BODCOD / 'Channel1_BODCOD_PolarizationTest.txt'
data_dir_channel1_BODCOD_Configurations = data_dir_channel1_BODCOD / 'Channel1_BODCOD_Configuration'
channel1_BODCOD_Configurations = data_dir_channel1_BODCOD_Configurations / 'Channel1_BODCOD_Config.txt'
BODCalibLocation_channel1 = data_dir_channel1_BODCOD_Configurations /'Calibration_Data.csv'
BODCalibType1 = data_dir_channel1_BODCOD_Configurations /'calib_defaults_channel1.txt'
data_dir_channel2 = current / 'Channel2'

data_dir_channel2_TOX = data_dir_channel2 / 'TOX'
channel2_TOX_Logs = data_dir_channel2_TOX / 'channel2_TOX_Logs.txt'
channel2_TOX_Polarization = data_dir_channel2_TOX / 'Channel2_TOX_PolarizationTest.txt'
data_dir_channel2_TOX_Configurations = data_dir_channel2_TOX / 'channel2_TOX_Configuration'
channel2_TOX_Configurations = data_dir_channel2_TOX_Configurations / 'channel2_TOX_Config.txt'

data_dir_channel2_BODCOD = data_dir_channel2 / 'BODCOD'
channel2_BODCOD_Logs = data_dir_channel2_BODCOD / 'channel2_BODCOD_Logs.txt'
channel2_BODCOD_Polarization = data_dir_channel2_BODCOD / 'Channel2_BODCOD_PolarizationTest.txt'
data_dir_channel2_BODCOD_Configurations = data_dir_channel2_BODCOD / 'channel2_BODCOD_Configuration'
channel2_BODCOD_Configurations = data_dir_channel2_BODCOD_Configurations / 'channel2_BODCOD_Config.txt'
BODCalibLocation_channel2 = data_dir_channel2_BODCOD_Configurations /'Calibration_Data.csv'
BODCalibType2 = data_dir_channel2_BODCOD_Configurations /'calib_defaults_channel2.txt'


file_locations.append(channel1_TOX_Logs)
file_locations.append(channel1_TOX_Configurations)
file_locations.append(channel1_BODCOD_Logs)
file_locations.append(channel1_BODCOD_Configurations)
file_locations.append(channel2_TOX_Logs)
file_locations.append(channel2_TOX_Configurations)
file_locations.append(channel2_BODCOD_Logs)
file_locations.append(channel2_BODCOD_Configurations)

#Define resource path to access external files when using pyinstaller
def resourcepath(relative_path):
    #Get absolute path to resource and then appends correct file prefix
    try:
        #PYinstaller temp folder
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
        
    return os.path.join(base_path, relative_path)

#On disconnect biosensor method
class disconnectBiosensor(QDialog):
    
    def __init__(self, parent =None):
        super().__init__()
        
        #Load UI and locate ui ojects
        uic.loadUi(resourcepath(str(uis) + '/disconnectDialog.ui'),self)
        self.setWindowIcon(QtGui.QIcon(str(uis) + '/NRCLogo.ico'))
        self.setModal(True)
        self.text = self.findChild(QLabel, "userInfo")
        self.exit = self.findChild(QPushButton, "exit")
        
        #IF disconnected -> Linux Text vs Windows Text
        if(platform.system()== 'Linux'):
            self.text.setText("<p>Sudden biosensor connection loss.<br>Please reconnect your biosensor and hit OK.<br><b>Your Raspberry Pi will automatically reboot so save all your<br>work.</b></p>")
        else:
            self.text.setText("<p>Sudden biosensor connection loss.<br>Please reconnect your biosensor and hit OK.<br><b>Your application will automatically exit.</b>")
        
        #If exit button clicked -> Run close Event
        self.exit.clicked.connect(self.close)
        
    #Custom close event -> If Linux -> reboot, else -> Exit Application
    def closeEvent(self,event):
        if(platform.system() == 'Linux'):
                os.system('sudo shutdown -r now')
        else:
            sys.exit()

#Writing params/logs into files
def writeIntoFile(channel, mode, flag , text):
    global file_locations
    
    if channel == 0: #Channel 1
        if mode == 0: #Tox Mode
            if flag == True: #LOG FILE
                if (file_locations[0].is_file()):
                    try:
                        f = open (file_locations[0], "a+") #Append mode
                        f.write(text)
                        f.close()
                    except Exception:
                        print("Error opening log file")
                
            elif flag == False:#SETTINGS FILE
                if (file_locations[1].is_file()):
                    try:
                        f = open (file_locations[1], "a+")
                        f.write(text)
                        f.close()
                    except Exception:
                        print("Error opening parameter file")
                        
        elif mode == 1: #BOD/COD  Mode
            if flag == True:
                if (file_locations[2].is_file()):
                    try:
                        f = open (file_locations[2], "a+")
                        f.write(text)
                        f.close()
                    except Exception:
                        print("Error opening log file")
                
            elif flag == False:
                if (file_locations[3].is_file()):
                    try:
                        f = open (file_locations[3], "a+")
                        f.write(text)
                        f.close()
                    except Exception:
                        print("Error opening parameter file")
                        
    elif channel == 1:
        if mode == 0:
            if flag == True:
                if (file_locations[4].is_file()):
                    try:
                        f = open (file_locations[4], "a+")
                        f.write(text)
                        f.close()
                    except Exception:
                        print("Error opening log file")
                
            elif flag == False:
                if (file_locations[5].is_file()):
                    try:
                        f = open (file_locations[5], "a+")
                        f.write(text)
                        f.close()
                    except Exception:
                        print("Error opening parameter file")
        
        elif mode == 1:
            if flag == True:
                if (file_locations[6].is_file()):
                    try:
                        f = open (file_locations[6], "a+")
                        f.write(text)
                        f.close()
                    except Exception:
                        print("Error opening log file")
                
            elif flag == False:
                if (file_locations[7].is_file()):
                    try:
                        f = open (file_locations[7], "a+")
                        f.write(text)
                        f.close()
                    except Exception:
                        print("Error opening parameter file")
    
           
    
    
def AprilPoly(T): #Function for calculation Y. Program currently uses March-April GPRC polynomial
    return 0.016072*(T**3)-1.29312*(T**2)+36.04835*(T)+143.2215

def read_all(port, params): #Read all serial information as long as there is something in the buffer.
    if (not port.timeout):
        raise TypeError('Port needs to have a timeout set!')

    if (params):
        read_buffer = b'' #Set-up read buffer
        read_buffer += port.read(1)
        while(port.inWaiting() > 0): #If there is info in port -> read
            read_buffer += port.read(port.inWaiting()) #Read what is in port
            time.sleep(1) #If reading params -> wait 1 seconds
            
        return read_buffer
    else:       #If reading acquisition -> read until ending command
        reading = b''
        while True:
            read = port.readline()
            if not (read == b''):
                reading += read
            if (b"Staying Awake" in read): #Ending command
                break
            else:
                time.sleep(0.1)
        return reading
    

def CheckingforPorts(): #Check all ports for biosensor compatible devices and initialize them
    global ports
    global biosensor_ports
    global serial_objects
    
    for p in ports: #Check all ports for biosensor compatible devices
        if '0483:374B' in p.hwid: #Unique ID for biosensors (Add more to list if other IDs are found)
            biosensor_ports.append(p.device)

    for b in biosensor_ports: #Initialze all biosensor ports with the settings below
        ser = serial.Serial(
            port = b,
            baudrate = 921600,
            parity = serial.PARITY_NONE,
            stopbits = serial.STOPBITS_ONE,
            bytesize = serial.EIGHTBITS,
            timeout=1,
            write_timeout=5.0,
            inter_byte_timeout=1.0
        )
        serial_objects.append(ser) #Append to biosensor serial objects list

def writeAllParams(channel): #Writing MCU settings into files, SerialWriting is the command, reading is to remove buffer
    global channel_params
    global serial_objects
    
    time.sleep(0.01)
    serial_objects[channel].reset_output_buffer() 
    value = channel_params[channel][0]
    value = value.strip().encode()
    serial_objects[channel].write(b"SetParam MinV "+ value + b"\r")
    time.sleep(0.01)
    text = serial_objects[channel].readline()
    
    time.sleep(0.01)
    serial_objects[channel].reset_output_buffer()
    value = channel_params[channel][1]
    value = value.strip().encode()
    serial_objects[channel].write(b"SetParam MaxV "+ value + b"\r")
    time.sleep(0.01)
    text = serial_objects[channel].readline()
    
    time.sleep(0.01)
    serial_objects[channel].reset_output_buffer()
    value = channel_params[channel][2]
    value = value.strip().encode()
    serial_objects[channel].write(b"SetParam OCSampleRate "+ value + b"\r")
    time.sleep(0.01)
    text = serial_objects[channel].readline()
    
    time.sleep(0.01)
    serial_objects[channel].reset_output_buffer()
    value = channel_params[channel][3]
    value = value.strip().encode()
    serial_objects[channel].write(b"SetParam CCSampleRate "+ value + b"\r")
    time.sleep(0.01)
    text = serial_objects[channel].readline()
    
    time.sleep(0.01)
    serial_objects[channel].reset_output_buffer()
    value = channel_params[channel][4]
    value = value.strip().encode()
    serial_objects[channel].write(b"SetParam OCMinTimeLimit "+ value + b"\r")
    time.sleep(0.01)
    text = serial_objects[channel].readline()
    
    time.sleep(0.01)
    serial_objects[channel].reset_output_buffer()
    value = channel_params[channel][5]
    value = value.strip().encode()
    serial_objects[channel].write(b"SetParam CCMinTimeLimit "+ value + b"\r")
    time.sleep(0.01)
    text = serial_objects[channel].readline()
    
    time.sleep(0.01)
    serial_objects[channel].reset_output_buffer()
    value = channel_params[channel][6]
    value = value.strip().encode()
    serial_objects[channel].write(b"SetParam OCMaxTimeLimit "+ value + b"\r")
    time.sleep(0.01)
    text = serial_objects[channel].readline()
    
    time.sleep(0.01)
    serial_objects[channel].reset_output_buffer()
    value = channel_params[channel][7]
    value = value.strip().encode()
    serial_objects[channel].write(b"SetParam CCMaxTimeLimit "+ value + b"\r")
    time.sleep(0.01)
    text = serial_objects[channel].readline()
    
    time.sleep(0.01)
    serial_objects[channel].reset_output_buffer()
    value = channel_params[channel][8]
    value = value.strip().encode()
    serial_objects[channel].write(b"SetParam OCFracV "+ value + b"\r")
    time.sleep(0.01)
    text = serial_objects[channel].readline()
    
    time.sleep(0.01)
    serial_objects[channel].reset_output_buffer()
    value = channel_params[channel][9]
    value = value.strip().encode()
    serial_objects[channel].write(b"SetParam CCFracV "+ value + b"\r")
    time.sleep(0.01)
    text = serial_objects[channel].readline()
    
    time.sleep(0.01)
    serial_objects[channel].reset_output_buffer()
    value = channel_params[channel][10]
    value = value.strip().encode()
    serial_objects[channel].write(b"SetParam Alpha "+ value + b"\r")
    time.sleep(0.01)
    text = serial_objects[channel].readline()
    
    time.sleep(0.01)
    serial_objects[channel].reset_output_buffer()
    value = channel_params[channel][11]
    value = value.strip().encode()
    serial_objects[channel].write(b"SetParam Epsilon "+ value + b"\r")
    time.sleep(0.01)
    text = serial_objects[channel].readline()
    
    time.sleep(0.01)
    serial_objects[channel].reset_output_buffer()
    value = channel_params[channel][12]
    value = value.strip().encode()
    serial_objects[channel].write(b"SetParam TimeReference "+ value + b"\r")
    time.sleep(0.01)
    text = serial_objects[channel].readline()
    
    time.sleep(0.01)
    serial_objects[channel].reset_output_buffer()
    value = channel_params[channel][13]
    value = value.strip().encode()
    serial_objects[channel].write(b"SetParam TimeInterval "+ value + b"\r")
    time.sleep(0.01)
    text = serial_objects[channel].readline()
    
    time.sleep(0.01)
    serial_objects[channel].reset_output_buffer()
    value = channel_params[channel][14]
    value = value.strip().encode()
    serial_objects[channel].write(b"SetParam MinTimeInterval "+ value + b"\r")
    time.sleep(0.01)
    text = serial_objects[channel].readline()
    
    time.sleep(0.01)
    serial_objects[channel].reset_output_buffer()
    value = channel_params[channel][15]
    value = value.strip().encode()
    serial_objects[channel].write(b"SetParam EpsilonMaxCount "+ value + b"\r")
    time.sleep(0.01)
    text = serial_objects[channel].readline()
    
    time.sleep(0.01)
    serial_objects[channel].reset_output_buffer()
    serial_objects[channel].write(b"SetDigitalPot " + (channel_params[channel][16]).encode() + b"\r")
    time.sleep(0.05)
    text = serial_objects[channel].readline()
    text = text.decode()
    temp = re.findall(r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", text)
    channel_params[channel][16] = temp[0].strip()
    value = channel_params[channel][16]
    value = value.strip().encode()
    serial_objects[channel].write(b"SetParam RLoad "+ value + b"\r")
    time.sleep(0.01)
    text = serial_objects[channel].readline()

    time.sleep(0.01)
    serial_objects[channel].reset_output_buffer()
    value = channel_params[channel][17]
    value = value.strip().encode()
    serial_objects[channel].write(b"SetParam CalibADCVRef "+ value + b"\r")
    time.sleep(0.01)
    text = serial_objects[channel].readline()

    time.sleep(0.01)
    serial_objects[channel].reset_output_buffer()
    value = channel_params[channel][18]
    value = value.strip().encode()
    serial_objects[channel].write(b"SetParam CalibADCZero "+ value + b"\r")
    time.sleep(0.01)
    text = serial_objects[channel].readline()

    time.sleep(0.01)
    serial_objects[channel].reset_output_buffer()
    value = channel_params[channel][19]
    value = value.strip().encode()
    serial_objects[channel].write(b"SetParam CalibADCMax "+ value + b"\r")
    time.sleep(0.01)
    text = serial_objects[channel].readline()

    time.sleep(0.01)
    serial_objects[channel].reset_output_buffer()
    value = channel_params[channel][20]
    value = value.strip().encode()
    serial_objects[channel].write(b"SetParam DeviceId "+ value + b"\r")
    time.sleep(0.01)
    text = serial_objects[channel].readline()
    
    time.sleep(0.01)
    serial_objects[channel].reset_output_buffer()
    value = channel_params[channel][21]
    value = value.strip().encode()
    serial_objects[channel].write(b"SetParam LoraEnabled "+ value + b"\r")
    time.sleep(0.01)
    text = serial_objects[channel].readline()
    
    time.sleep(0.01)
    serial_objects[channel].reset_output_buffer()
    value = channel_params[channel][22]
    value = value.strip().encode()
    serial_objects[channel].write(b"SetParam DeviceEUI "+ value + b"\r")
    time.sleep(0.01)
    text = serial_objects[channel].readline()
    
    time.sleep(0.01)
    serial_objects[channel].reset_output_buffer()
    value = channel_params[channel][23]
    value = value.strip().encode()
    serial_objects[channel].write(b"SetParam AppEUI "+ value + b"\r")
    time.sleep(0.01)
    text = serial_objects[channel].readline()
    
    time.sleep(0.01)
    serial_objects[channel].reset_output_buffer()
    value = channel_params[channel][24]
    value = value.strip().encode()
    serial_objects[channel].write(b"SetParam AppKey "+ value + b"\r")
    time.sleep(0.01)
    text = serial_objects[channel].readline()
    
class MplCanvas(FigureCanvas): #PYQT5 Compatible Canvas for matplotlib (Used for main graphs)
    
    def __init__(self, parent=None, width = 3.5, height = 2.5, dpi = 100):
        self.fig = Figure (figsize=(width,height),dpi = dpi, tight_layout=True)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas,self).__init__(self.fig)
        
class MplCanvas1(FigureCanvas): #PYQT5 Compatible Canvas for matplotlib (Used for polarization graphs
    
    def __init__(self, parent=None, width = 1.5, height = 2.4, dpi = 100):
        self.fig = Figure (figsize=(width,height),dpi = dpi, tight_layout=True)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas1,self).__init__(self.fig)

class CustomVLine(QFrame):
    def __init__(self):
        super(CustomVLine,self).__init__()
        self.setFrameShape(self.VLine|self.Sunken)
    
class PandasModel(QAbstractTableModel): #Pandas Model for table display
    def __init__(self, data):
        QAbstractTableModel.__init__(self)
        self._data = data

    def rowCount(self, parent=None): #Custom rowcount function
        return self._data.shape[0]

    def columnCount(self, parnet=None): #Custom column count function
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole): #Custom data function
        if index.isValid():
            if role == Qt.DisplayRole:
                return str(self._data.iloc[index.row(), index.column()])
        return None

    def headerData(self, col, orientation, role): #Header Data function
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._data.columns[col]
        return None
    
class Ui(QWidget): #Set up Ui Classes

    def setupUi(self, Main):
        global serial_objects
        global initial
        global loaded
        global loaded2
        
        #Set Window Parameters
        Main.setObjectName("Main")
        Main.setFixedSize(700, 410)
        self.width = 700
        self.height = 410
        self.setFixedSize(self.width, self.height)
        self.setWindowIcon(QtGui.QIcon(str(uis) + '/NRCLogo.ico'))
        
        #Declare Stacked Layout for multiple pages
        self.menu = QStackedLayout()

        self.NavigationDialog = QDialog()
        self.NavigationDialogUi()
        
        self.NavigationDialog.exec()
        
        
        #If there are no serial objects -> Exit, If x was pressed -> Exit
        if (len(serial_objects) == 0):
            sys.exit()
        if (initial == False):
            sys.exit()
        
        #Probe the serial ports to make sure they're ready
        if(platform.system() == 'Linux'):
            os.system('st-info --probe')
            time.sleep(1)
        
        #Initialize MainPage and add to self, hide immediately to let params load
        self.MainWindow = MainPage()
        self.menu.addWidget(self.MainWindow)
        self.MainWindow.hide()
        
        #Create New Dialog and set width/height, title and taskbar icon
        wait = QDialog()
        wait.setWindowTitle("Loading Application")
        width = 600
        height = 150
        wait.setFixedSize(width, height)
        wait.setWindowIcon(QtGui.QIcon(str(uis) + '/NRCLogo.ico'))
        
        #Set DialogText Settings and stlying
        waitText = QLabel(wait)
        waitText.setGeometry(QRect(50, 30, 650, 200))
        waitText.setStyleSheet("font-family: Century Gothic")
        waitText.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
        waitText.setText("Loading... \nPlease wait at most 5 minutes until the operation is over.\nAfter 5 minutes have passed and the program is still loading,\nplease restart your device.")
        
        #Show Text and wait until loaded parameter is true (Aka, main page is done loading)
        wait.show()
        loop = QEventLoop()
        QTimer.singleShot(500, loop.quit) #Pauses UI for half a second and loops
        loop.exec_()

        while loaded == False:
            loop = QEventLoop()
            QTimer.singleShot(500, loop.quit)
            loop.exec_()
            
        wait.close()
        
    def NavigationDialogUi(self):
        global ports
        global biosensor_ports
        global serial_objects
        global channel_selection
        global initial
        global mainTable
        
        #Initialize NavigationDialog Window Parameters
        self.NavigationDialog.setWindowTitle("Channel Selection - Version 1")
        self.width = 700
        self.height = 300
        self.NavigationDialog.setFixedSize(self.width, self.height)
        self.NavigationDialog.setWindowIcon(QtGui.QIcon(str(uis) + '/NRCLogo.ico'))
        
        #Set up Navigation Label
        self.NavigationDialogText = QLabel(self.NavigationDialog)
        self.NavigationDialogText.setGeometry(QRect(30, 30, 650, 200))
        self.NavigationDialogText.setStyleSheet("font-family: Century Gothic")
        self.NavigationDialogText.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
        
        if (len(serial_objects)==0):
            self.NavigationDialogText.setText("No compatible biosensors detected.\nClose the application and please connect your biosensor before trying again!")
             
        else:
            self.NavigationDialogText.setText("Below is a list of all compatible biosensors connected: \nPlease choose if each channel should run in TOX mode or BOD/COD mode.")
            
            channel_selection = [0] * len(serial_objects)   #Selected Choices
            mainTable = [0] * len(serial_objects)  #Initialize tables
            options = ["TOX Mode", "BOD/COD Mode"] #Dropdown choices
            
            #Create combo boxes for each available channel
            for i in range(len(serial_objects)):
               channel_selection[i] = QComboBox()
               channel_selection[i].addItems(options)
            
            #Open Default Behaviour
            try:
                f = open(defaults, "r+")
                selections = f.readlines()
                f.close()
            except Exception:
                print("Error opening default file")
                
            #Create a GridLayout to place channel labels and comboboxes
            layout = QGridLayout()
            layout.setSpacing(0)
            for i in range(len(serial_objects)):
                layout.addWidget(QLabel("Channel " + str(i+1) + ": "),i+1, 0)
                layout.addWidget(channel_selection[i], i+1, 1)
                channel_selection[i].setCurrentIndex(int(selections[i]))
            
            #Add Confirmation Button
            self.confirm = QPushButton("Confirm (Continues in 30 s)",self.NavigationDialog)
            self.confirm.setGeometry(430, 250, 250, 30)
            self.NavigationDialog.setLayout(layout)
            

            #Attach the following functions to the button -> xPressed checks if closed vs confirm and the .close closes the function 
            self.confirm.clicked.connect(lambda: xPressed.checked(channel_selection, selections))
            self.confirm.clicked.connect(self.NavigationDialog.close)
            
            self.time = 30
            self.continueTimer = QTimer()
            self.continueTimer.timeout.connect(self.update_button) #> Sends defaults after 30 seconds
            self.continueTimer.start(1000)
    
    #Counter function to update text and send command
    def update_button(self):
        self.time-=1
        self.confirm.setText("Confirm (Continues in " + str(self.time) + "s)")
        
        if self.time == 0:
            self.continueTimer.stop()
            self.confirm.click()
            
#Change flag variable to confirm close
class xPressed():
    def checked(user_selection, prev_selection):
        global initial
        initial = True
         
        #Based on selections, save default behaviours
        for i in range(len(user_selection)):
            prev_selection[i] = str(user_selection[i].currentIndex()).strip()
            prev_selection[i] += '\n'
        text = ''
        
        for i in range(len(prev_selection)):
            text += prev_selection[i]
            
        try:
            f = open(defaults, "w+")
            f.write(text)
            f.close()
        except Exception:
            print("Error opening default file")
        
class MyDelegate(QItemDelegate): #SPINBOX delegate for polarization values (Min 1, Max 500000ohms)
    def createEditor(self, parent, option, index):
        spin = QSpinBox(parent)
        spin.setMaximum(50000)
        spin.setMinimum(1)
        return spin

class PolarizationTable(QDialog):
    
    def __init__(self, channel, mode, runTime, rows, ssTolerance, ssIterations, alpha):
        super().__init__()
        
        #Associate Arguments with self variables
        self.channel = channel
        self.mode = mode
        self.rows = rows+1
        self.runTime = runTime
        self.ssTolerance = ssTolerance
        self.ssIterations = ssIterations
        self.alpha = alpha
        
        #Load UI and UI objects
        uic.loadUi(resourcepath(str(uis) + '/PolarizationTestTable.ui'),self)
        self.polarizationTable = self.findChild(QTableView, 'polarizationTable')
        self.loadPolarization  = self.findChild(QPushButton, 'loadPolarization')
        self.cancel = self.findChild(QPushButton, 'cancel')
        self.setWindowIcon(QtGui.QIcon(str(uis) + '/NRCLogo.ico'))
        
        #Create new Model, add headers and create rows depending on user selection
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['Resistance in Ohms'])
        for i in range(self.rows):
            self.model.insertRow(i)
            
        #Set table to new model and resize
        self.polarizationTable.setModel(self.model)
        self.polarizationTable.resizeColumnsToContents()
        
        #Set SpinBox format to delegate
        delegate = MyDelegate()
        self.polarizationTable.setItemDelegate(delegate)
        
        #Resize table according to rows
        for rows in range(self.model.rowCount()):
            self.polarizationTable.setRowHeight(rows, int(271/self.model.rowCount()))
        
        #Create filler item for OCV
        item = QStandardItem("OCV")
        item.setFlags(item.flags() ^ Qt.ItemIsEditable)
        self.model.setItem(0,0,item)
        
        #Starting default value in model is 1
        for i in range(1, self.model.rowCount()):
            self.model.setItem(i, 0, QStandardItem("1"))
        
        #Attach methods to button click events -> Cancel = Close, loadPolarization = Checker
        self.cancel.clicked.connect(self.close)
        self.loadPolarization.clicked.connect(self.checker)
    
    #Check model data to make sure there are not duplicate digital pot entries
    def checker(self):
        arr = []
        arr2 = []
        arr3 = []
        
        #Append table to array
        for rows in range(1, self.model.rowCount()):
            arr.append(self.model.item(rows,0).text())
        
        #Create wait dialog and set modal. Also set fixed size and set window icon to the logo
        wait = QDialog()
        wait.setWindowTitle("Adjusting Digital Pot...")
        wait.setModal(True)
        width = 500
        height = 100
        wait.setFixedSize(width, height)
        wait.setWindowIcon(QtGui.QIcon(str(uis) + '/NRCLogo.ico'))
        
        #Create label and add text
        waitText = QLabel(wait)
        waitText.setGeometry(QRect(30, 30, 650, 200))
        waitText.setStyleSheet("font-family: Century Gothic")
        waitText.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
        waitText.setText("Adjusting resistor entries to available digital pot values\nPlease wait until the operation is over.\nIf there are any duplicates, you will have to try again.")
        
        wait.show()
        
        #Pause ui for 0.1 secs to let it load
        loop = QEventLoop()
        QTimer.singleShot(100, loop.quit)
        loop.exec_()
        
        #Adjust user entered Rloads to available digital pot values
        for rows in range(len(arr)): #Loops array based on available values
            
            serial_objects[self.channel].read(2048)
            serial_objects[self.channel].write(b"SetDigitalPot " + (arr[rows]).encode() + b"\r") #Set Digital Pot
            loop = QEventLoop()
            QTimer.singleShot(100, loop.quit) #Pause UI
            loop.exec_()
            text = serial_objects[self.channel].readline() #Read Adjusted Rload
            text = text.decode()
            temp = re.findall(r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", text) #Using regex to isolate for numbers
            arr2.append(int(temp[0].strip())) #Append adjusted value to array
        
        
        arr3 = sorted(arr2, reverse = True) #Sort Array in reversed order

        for rows in range(len(arr3)): #Place sorted array into the table model
            self.model.setItem(rows+1, 0, QStandardItem(str(arr3[rows])))
        
        for rows in range(self.model.rowCount()): #Resize table
            self.polarizationTable.setRowHeight(rows, int(271/self.model.rowCount()))
        
        wait.close() #Closed waiting screen
        
        #If array of adjusted, sorted digital pot values is different from set of values -> Duplicate entries (Try again)
        if (len(arr3) != len(set(arr3))):
            error = QMessageBox.warning(self, 'Duplicate Entries', 'Please enter unique resistor values')
        else: #Otherwise begin polarization
            self.beginPolarization()
        
    #Polarization Initializing function 
    def beginPolarization(self):
        #Set dlg to polarization class with self as an argument
        Polarization_dlg = self.Polarization_Dialog(self)
        
        #Try closing current dlg and exec polarization dialog(Set modality to true)
        try:
            self.close()
            Polarization_dlg.exec_()
        except Exception: #Else open error
            error = QMessageBox.warning(self, 'Error!', 'Polarization Failed to Open')
    
    #Polarization Dialog Subclass (Where you view all the test outputs)
    class Polarization_Dialog(QDialog):
        #Create class signals
        #When signal is emitted (Display Finished Message)
        displayFinishedMessage = pyqtSignal(int,float)
        #When signal is emitted (Update Table)
        updatePolarizationTableSignal = pyqtSignal(int,int,str)
        
        def __init__(self, parent):
            super().__init__(parent)
            
            #Set self variables according to parent variables
            self.parent = parent
            self.channel = self.parent.channel
            self.mode = self.parent.mode
            self.runTime = self.parent.runTime
            self.ssTolerance = self.parent.ssTolerance
            self.ssIterations = self.parent.ssIterations
            self.alpha = self.parent.alpha
            
            #Load UI and UI objects
            uic.loadUi(resourcepath(str(uis) + '/PolarizationDialog.ui'),self)
            self.polarizationGraph = self.findChild(QScrollArea, 'graphingArea')
            self.mfcTable = self.findChild(QTableWidget, 'mfcTable')
            self.statusMsg = self.findChild(QLabel, 'status')
            self.Rint = self.findChild(QLabel, 'estRint')
            self.Rint_forward = self.findChild(QLabel, 'estRint_Forward')
            self.Rint_backward = self.findChild(QLabel, 'estRint_Backward')
            self.cancel = self.findChild(QPushButton, 'cancel')
            self.setWindowIcon(QtGui.QIcon(str(uis) + '/NRCLogo.ico'))
            
            #Initial flags
            self.cancelFlag = False
            self.plot1 = False
            self.plot2 = False
            self.finished = False
            self.endThread = False
            
            #Create disconnect class
            self.disconnect = disconnectBiosensor(self)
            #Create new Model, add headers and create rows depending on user selection
            self.mfcTable.horizontalHeader().setStretchLastSection(True)
            self.mfcTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            
            #Add rows
            for i in range((self.parent.rows - 1) * 2):
                self.mfcTable.insertRow(i)
            #Resize Table
            for i in range(self.mfcTable.rowCount()):
                self.mfcTable.setRowHeight(i, int(281/self.mfcTable.rowCount()))
            #Hide header and resize columns
            self.mfcTable.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
            self.mfcTable.verticalHeader().hide()
            
            #Add OCV row and disable editing
            item = QTableWidgetItem("OCV")
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.mfcTable.setItem(0,0,item)
            
            #Add model items into new table and set them to uneditable
            for i in range(1, int(self.mfcTable.rowCount()/2) +1):
                item = QTableWidgetItem(self.parent.model.item(i,0).text())
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.mfcTable.setItem(i,0, item)
            
            #Add model items in reverse into new table and set them to uneditable
            for i in range(int(self.mfcTable.rowCount()/2)+1, self.mfcTable.rowCount()):
                item = QTableWidgetItem(self.parent.model.item(self.mfcTable.rowCount() - i, 0).text())
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.mfcTable.setItem(i,0, item)
            
            #Add placeholders for MFC voltage values in 2nd columns and set to uneditable
            for i in range(self.mfcTable.rowCount()):
                item = QTableWidgetItem("-")
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.mfcTable.setItem(i,1, item)
            
            #Create new widget and layout
            self.contents = QWidget()
            self.store = QVBoxLayout()
            
            #Initialize graph and graph parameters
            self.graph = MplCanvas1(self, width = 1.5, height = 2.4, dpi =100)
            self.graph.axes.set_title("Polarization Test", fontweight = 'bold')
            self.graph.axes.set_xlabel("Current (mA)", fontweight = 'bold')
            self.graph.axes.set_ylabel('Voltage (mV)', fontweight = 'bold')
            self.x1 = []
            self.x2 = []
            self.y1 = []
            self.y2 = []
            
            #Set minimum size and add graph to widget
            self.graph.setMinimumSize(self.graph.size()) #forces plots to be a uniform size
            self.store.addWidget(self.graph) #Add to scrollable content area
            #Set widget layout to Vertical Box
            self.contents.setLayout(self.store)
            
            #Set graph area size policies
            self.polarizationGraph.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            self.polarizationGraph.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.polarizationGraph.setWidgetResizable(True)
            self.polarizationGraph.setWidget(self.contents)
            
            #Connect signals to slots and buttons to functions
            #When displayFinishedMessage signal is emitted -> Activate createRloadDialog
            self.displayFinishedMessage.connect(self.createRloadDialog)
            #When updatePolarizationTableSignal is emitted -> Activate updatepolarizationTable
            self.updatePolarizationTableSignal.connect(self.updatePolarizationTable)
            #If clicked close window
            self.cancel.clicked.connect(self.close)
            
            #Auto start thread function
            self.runPolarization()
        
        #Update Table slot (according to arguments set current table slot to text)
        @QtCore.pyqtSlot(int,int,str)
        def updatePolarizationTable(self, row, col, text):
            item = QTableWidgetItem(text)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.mfcTable.setItem(row,col, item)
        
        #When signal is emitted, prompt user to choose whether they want to change rload or not
        @QtCore.pyqtSlot(int,float)
        def createRloadDialog(self, channel, Rint):
            #CHANGE RLOAD MESSAGE if user desires
            isFinished = QMessageBox.question(self, 'Change Internal Resitance', 'Would you like to change RLoad to the estimated internal resistance?', QMessageBox.Yes | QMessageBox.No)
            
            #If yes was selected
            if isFinished == QMessageBox.Yes:
                if(Rint <= 0): #If rint <=0 -> auto set to 1
                    Rint = 1
                rload = str(int(Rint)) #Change Rint to a integer and then a string
                time.sleep(0.01)
                serial_objects[channel].reset_output_buffer()
                serial_objects[channel].write(b"SetDigitalPot " + rload.encode() + b"\r") #Set digital pot to rload
                time.sleep(0.05)
                text = serial_objects[channel].readline() #After adjustments -> Find actual value
                text = text.decode()
                temp = re.findall(r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", text)
                channel_params[channel][16] = temp[0].strip() #Set Channel Params to new value
                value = channel_params[channel][16]
                value = value.strip().encode()
                serial_objects[channel].write(b"SetParam RLoad "+ value + b"\r") #Set Rload in the MCU settings to new value
                time.sleep(0.01)
                text = serial_objects[channel].readline()
            else:
                pass #otherwise do nothing

        #Auto run threads (SerialComm and Graphs)  
        def runPolarization(self):
            tPolarizationComms = threading.Thread(target = self.forward_backward, args=(self.channel,self.mode, self.runTime))
            tPolarizationPlots = threading.Thread(target = self.update_plot_polarization)
            tPolarizationComms.daemon = True
            tPolarizationPlots.daemon = True
            tPolarizationComms.start()
            tPolarizationPlots.start()
        
        #Serial Comm threads
        def forward_backward(self, channel, mode, runTime):
            #try:
            self.plot = False #Set plotting to false 
            self.DisconnectLoad(channel) #Disconnect Load 
            self.statusMsg.setText("Estimating OCV steady-state voltage...") #Change status message
            for i in range(60*self.runTime): #According to user input runTime (Wait x minutes for OCV ss voltage)
                time.sleep(1)
                if self.cancelFlag: #If cancelled during this point (break out of loops and end threads)
                    self.endThread = True
                    break
                
            if (self.cancelFlag == False): #Only enter if flag is true
                prev = float(self.GetMfcVoltage(channel)) #Get MFC Voltage
                
                while True:
                    time.sleep(5)
                    curr =(self.alpha * float(self.GetMfcVoltage(channel))) + (1-self.alpha)*(prev)
                    if (self.percentDifference(prev, curr)) <= self.ssTolerance:
                        break
                    if self.cancelFlag: #If cancelled during this point (break out of loops and end threads)
                        self.endThread = True
                        break
                    
                OCV_voltage = curr
                self.updatePolarizationTableSignal.emit(0, 1, str(int(OCV_voltage))) #Emit signal with (row, col, value)
                
            self.ConnectLoad(channel) #ConnectLoad

            if(self.cancelFlag == False): #Only Enter if flag is true
                for i in range(1, int(self.mfcTable.rowCount()/2) +1): #Loop through descending resistor values
                    self.statusMsg.setText("Estimating SS voltage at resistor value: " + str(i)) #Set Message
                    while True:
                        self.SetDigitalPot(self.channel, self.parent.model.item(i,0).text()) #SetDigitalPot to table entry
                        previous = float(self.GetMfcVoltage(channel)) #Find first MFC Voltage
                        mfc_voltage = self.recursiveCheck(previous,  i, 0, channel) #Recursively solve until we get a ss-voltage according to user preferences
                        break #Exit while loop
                    self.updatePolarizationTableSignal.emit(i, 1, str(int(mfc_voltage))) #Emit signal to update table (row position, column, MFC_Voltage)
                    self.tempY = int(mfc_voltage) #Append MFC to y_axis placeholder
                    self.tempX = int(self.parent.model.item(i,0).text()) #Append resistor to x axis placeholder
                    self.plot1 = True #Set plotting to true to begin plotting 
                    time.sleep(5) #Sleep for 5 seconds
                    if self.cancelFlag: #Exit loop if cancel button was pressed
                        self.endThread = True #Set flag to true to end thread
                        break
                
                #After all resistor values have been iterated through (descending) -> Create a linear model and find abs coef for forward test
                if(self.cancelFlag == False):
                    x = np.array(self.sorted_listA).reshape((-1,1))
                    y = np.array(self.y1)
                    model1 = LinearRegression()
                    model1 = model1.fit(x,y)
                    
                    self.Rint_forward.setText(str(abs(round(model1.coef_[0],5))))
            
            #Append last descending test value to list of values for second line graph 
            if(self.cancelFlag == False):
                self.x2.append(self.tempX)
                self.y2.append(self.tempY)
                
            if(self.cancelFlag == False): #Only Enter if flag is true
                for i in range(int(self.mfcTable.rowCount()/2)+1, self.mfcTable.rowCount()): #Loop through descending resistor values
                    self.statusMsg.setText("Estimating SS voltage at resistor value: " + str(i)) #Set Message
                    while True:
                        self.SetDigitalPot(self.channel, self.parent.model.item(self.mfcTable.rowCount() - i,0).text()) #SetDigitalPot to table entry
                        previous = float(self.GetMfcVoltage(channel)) #Find first MFC Voltage
                        mfc_voltage = self.recursiveCheck(previous, i, 0, channel) #Recursively solve until we get a ss-voltage according to user preferences
                        break #Exit loop
                
                    self.updatePolarizationTableSignal.emit(i, 1, str(int(mfc_voltage)))
                    self.tempY = int(mfc_voltage)
                    self.tempX = int(self.parent.model.item(self.mfcTable.rowCount() - i,0).text())
                    self.plot2 = True
                    time.sleep(5)
                    if self.cancelFlag:
                        self.endThread = True
                        break
                
                #After all resistor values have been iterated through (ascending) -> Create a linear model and find abs coef for backwards test
                if(self.cancelFlag == False):
                    x = np.array(self.sorted_listB).reshape((-1,1))
                    y = np.array(self.y2)
                    model2 = LinearRegression()
                    model2 = model2.fit(x,y)
                    
                    self.Rint_backward.setText(str(abs(round(model2.coef_[0],5))))
                    
            if(self.cancelFlag == False):
                #Solve for average slope to use as RLOAD
                r_int = (abs(model1.coef_[0]) + abs(model2.coef_[0]))/2
                
                #Update label to display Rload
                self.Rint.setText(str(round(r_int,5)))
                
                #SAVE FILE
                #Append Text to empty string
                text = ''
                writeTime=str(datetime.datetime.now())[:19]
                text += writeTime
                text += '\nEstimated Rint (Forward Test with descending resistances): ' + str(round(model1.coef_[0],5))
                text += '\nEstimated Rint (Backward Test with ascending resistances): ' + str(round(model2.coef_[0],5))
                text += '\nEstimated Rint: ' + str(round(r_int,5))
                text += '\nNumber of entries: '+ str(self.mfcTable.rowCount()-1)
                
                #Append resistor values with estimated voltage
                for x in range(1, self.mfcTable.rowCount()):
                    text += '\nResistor '+ str(x) + ": " + self.mfcTable.item(x,0).text() + '\t\tEstimated Voltage: ' + self.mfcTable.item(x,1).text()
                
                text += '\n\n'
                
                #Save into appropriate file location depending on user selection in Navigation Dialog
                if channel == 0:
                    if mode == 0:
                        if (channel1_TOX_Polarization.is_file()):
                            try:
                                f = open(channel1_TOX_Polarization, "a+")
                                f.write(text)
                                f.close()
                            except Exception:
                                print("Error opening polarization file")
                    elif mode == 1:
                        try:
                            if (channel1_BODCOD_Polarization.is_file()):
                                f = open(channel1_BODCOD_Polarization, "a+")
                                f.write(text)
                                f.close()
                        except Exception:
                                print("Error opening polarization file")
                            
                elif channel == 1:
                    if mode == 0:
                        try:
                            if (channel2_TOX_Polarization.is_file()):
                                f = open(channel2_TOX_Polarization, "a+")
                                f.write(text)
                                f.close()
                        except Exception:
                            print("Error opening polarization file")
                    elif mode ==1:
                        if (channel2_BODCOD_Polarization.is_file()):
                            try:
                                f = open(channel2_BODCOD_Polarization, "a+")
                                f.write(text)
                                f.close()
                            except Exception:
                                print("Error opening polarization file")
                #Set Status to all done and user can exit           
                self.statusMsg.setText("Est. Rint has been found and file had been saved. You may exit polarization test.")
                
                #Set finished and endthread flags to true 
                self.finished = True
                self.endThread = True
                
                #Emit display final message signal with the arguments below
                self.displayFinishedMessage.emit(channel, r_int)
                    
            #If there was an exception (execute disconnect dialog)   
            #except Exception:
                #self.disconnect.exec_()
        
        #Update plots
        def update_plot_polarization(self):
            
            while True:
                if self.plot1 == True:
                    self.x1.append(self.tempX)
                    self.y1.append(self.tempY)

                    self.sorted_listA = []
                    
                    #Change x-axis to current (I = V/R)
                    for i in range(len(self.x1)):
                        self.sorted_listA.append(float(self.y1[i]/self.x1[i]))
                    
                    #Clear axes and begin plotting
                    self.graph.axes.cla()
                    self.graph.axes.set_title("Polarization Test", fontweight = 'bold')
                    self.graph.axes.set_xlabel("Current (mA)", fontweight = 'bold')
                    self.graph.axes.set_ylabel('Voltage (mV)', fontweight = 'bold')
                    self.graph.axes.plot(self.sorted_listA, self.y1, 'r', label = r"Resistor($\downarrow$)", linestyle ='dashed', marker ="o")
                    self.graph.axes.legend()
                    self.graph.draw_idle()
                    #After plot -> Set plot1 flag to false
                    self.plot1 = False
                    
                elif self.plot2 == True:
                    self.x2.append(self.tempX)
                    self.y2.append(self.tempY)
                    
                    self.sorted_listB = []
                    #Change x-axis to current (I = V/R)
                    for i in range(len(self.x2)):
                        self.sorted_listB.append(float(self.y2[i]/self.x2[i]))
                        
                    #Clear axes and begin plotting
                    self.graph.axes.cla()
                    self.graph.axes.set_title("Polarization Test", fontweight = 'bold')
                    self.graph.axes.set_xlabel("Current(mA)", fontweight = 'bold')
                    self.graph.axes.set_ylabel('Voltage (mV)', fontweight = 'bold')
                    self.graph.axes.plot(self.sorted_listA, self.y1, 'r', label = r"Resistor($\downarrow$)", linestyle ='dashed', marker ="o")
                    self.graph.axes.plot(self.sorted_listB, self.y2, 'b', label = r"Resistor($\uparrow$)", linestyle ='dashed', marker ="v")
                    self.graph.axes.legend()
                    self.graph.draw_idle()
                    #After plot -> Set plot2 flag to false
                    self.plot2 = False
                
                #If cancel is ever triggered -> Break Loop
                if self.cancelFlag:
                    break
                #Sleep for 1 sec
                time.sleep(1)
        
        #Recursively solve for SS voltage
        def recursiveCheck(self, previous,  position, iterations, channel):
            #Wait 5 seconds and try with filtered value
            time.sleep(5)
            current = (self.alpha * float(self.GetMfcVoltage(channel))) + (1-self.alpha)*(previous)
            
            #If iterations == user entered iterations -> Return current MFC voltage value
            if iterations == self.ssIterations:
                return current
            
            #If percent difference is within user selected tolerance (increase consecutive succesful iteration by 1) and repeat
            elif (self.percentDifference(previous, current)) <= self.ssTolerance:
                iterations+=1
                #Try to run it again recursively -> If stack overflow (Return current value) -> Treat current as previous for next iteration
                try:
                    return self.recursiveCheck(current, position, iterations, channel)
                except Exception:
                    return current
            #Otherwise, reset consecutive succesful iteration to 0 and repeat
            else:
                iterations = 0
                #Try to run it again recursively -> If stack overflow (Return current value)
                try:
                    return self.recursiveCheck( current, position, iterations, channel)
                except Exception:
                    return current
        
        #Helper method to calculate if previous vs current MFC voltage percent difference
        def percentDifference(self, previous, current):
            if current == previous:
                return 0
            
            try:
                return(abs(current-previous)/previous)*100
            
            except ZeroDivisionError:
                return float('inf')
        
        #Helper method to calculate MFC voltage
        def GetMfcVoltage(self, channel):
            global serial_objects
            
            serial_objects[channel].read(2048)
            serial_objects[channel].write(b"GetMfcVoltage\r") #Write command to terminal
            time.sleep(0.1)
            serial_objects[channel].read_until(b"MFC voltage=")
            text = serial_objects[channel].read_until(b" ") #Read Value and return value
            text = text.strip().decode()
            #Exponential Filter with alpha here *IMPORTANT
            return text
        
        #Helper method to connect load
        def ConnectLoad(self, channel):
            global serial_objects
            
            serial_objects[channel].read(2048) #Empty input buffer
            serial_objects[channel].write(b"ConnectLoad\r") #Write command to terminal
            time.sleep(0.1)
            text = serial_objects[channel].readline() #Read sucessful command
        
        #Helper method to disconnect load
        def DisconnectLoad(self, channel):
            global serial_objects
            
            serial_objects[channel].read(2048)
            serial_objects[channel].write(b"DisconnectLoad\r") #Write command to terminal
            time.sleep(0.1)
            text = serial_objects[channel].readline() #Read sucessful command
        
        #Helper method to set digital pot
        def SetDigitalPot(self, channel, value):
            global serial_objects
            
            serial_objects[channel].read(2048)
            value = value.encode()
            serial_objects[channel].write(b"SetDigitalPot "+ value + b"\r") #Write command to terminal
            time.sleep(1)
            text = serial_objects[channel].readline() #Read sucessful command

        #Custom close event with different messages according to flags
        def closeEvent(self, event):
            #If not finished -> Cancel test?
            if self.finished == False:
                exiting = QMessageBox.question(self, 'Exit Polarization', 'Are you sure you want to cancel the polarization test?', QMessageBox.Yes | QMessageBox.No)
            #If finished -> Close page?
            elif self.finished == True:
                exiting = QMessageBox.question(self, 'Exit Polarization', 'Are you sure you want to close this page?', QMessageBox.Yes | QMessageBox.No)
            
            #If user selects yes -> Set cancel flag to True
            if exiting == QMessageBox.Yes:
                self.cancelFlag = True
                
                #Create waiting dialog with custom settings
                wait = QDialog()
                wait.setWindowTitle("Stopping Polarization Test")
                wait.setModal(True)
                width = 500
                height = 100
                wait.setFixedSize(width, height)
                wait.setWindowIcon(QtGui.QIcon(str(uis) + '/NRCLogo.ico'))
                
                #Create waiting text
                waitText = QLabel(wait)
                waitText.setGeometry(QRect(50, 30, 650, 200))
                waitText.setStyleSheet("font-family: Century Gothic")
                waitText.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
                waitText.setText("Stopping polarization test for channel " +str(self.channel+1)+ ".\nPlease wait until the operation is over.")
                
                #Show Waiting Test
                wait.show()
                #While thread has not ended -> Pause UI for 1 second
                while self.endThread == False:
                    loop = QEventLoop()
                    QTimer.singleShot(1000, loop.quit)
                    loop.exec_()
                wait.close()
                
                #Once finished accept close event and close current page
                event.accept()
            #Any other form of user selection -> will be ignored
            else:
                if not type(event) == bool:
                    event.ignore()
            
#Main Page Class
class MainPage(QWidget):
    
    def __init__(self, parent=None):
        global serial_objects
        global channel_selection
        global channel
        global channel_params
        global graphs_limits
        global outputs
        global startTime
        global endTime
        global graphspan
        global timevec
        global settingsFlag
        global endFlag
        global dfs_old
        global dfs
        global bod_cod_flag
        global start_plotting
        global waiting_for_something_to_happen
        global threadEnded
        global bod_fits
        global cod_fits
        
        super().__init__(parent)
        
        #Initialize globals according to number of compatible biosensors
        channel = [0] * len(channel_selection)
        startTime = [0] * len(serial_objects)
        endTime = [0] * len(serial_objects)
        graphspan = [6] * len(serial_objects)
        timevec = [0]*len(serial_objects)
        settingsFlag = [False] * len(serial_objects)
        endFlag = [False] * len(serial_objects)
        bod_cod_flag = [False] * len(serial_objects)
        start_plotting = [False] * len(serial_objects)
        waiting_for_something_to_happen = [False] * len(serial_objects)
        dfs_old = [0] * len(serial_objects)
        dfs = [0] * len(serial_objects)
        threadEnded = [False] * len(serial_objects)
        
        #10 possible graphs -> Initialize in 2D array
        for x in range(len(channel_selection)):
            new = []
            for y in range(0,10):
                new.append(0)
            graphs_limits.append(new)
        
        #25 MCU parameters -> initialize in 2D array
        for x in range(len(channel_selection)):
            new = []
            for y in range(0,25):
                new.append(str(0.0))
            channel_params.append(new)
        
        #9 table outputs -> initialize in 2D Array
        for x in range(len(serial_objects)):
            new = []
            for y in range(0,9):
                new.append(None)
            outputs.append(new)
            
        for x in range(len(serial_objects)):
            new = []
            for y in range(0,3):
                new.append(False)
            bod_fits.append(new)
            
        for x in range(len(serial_objects)):
            new = []
            for y in range(0,3):
                new.append(False)
            cod_fits.append(new)
        
        #MAKE SURE CLOSE EVENT IS SET UP HERE
        #Set up window settings
        self.setWindowTitle("Biosensor Data Collection")
        self.width = 700 #900
        self.height = 440 #700
        self.setFixedSize(self.width, self.height)
        self.setWindowIcon(QtGui.QIcon(str(uis) + '/NRCLogo.ico'))
        
        #Declare Layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        tabs = QTabWidget()
        
        #Add tabs according to user selection in the navigation dialog
        #Depending on the selection -> Load a different UI for that purpose
        for x in range(len(channel_selection)):
            y = channel_selection[x].currentIndex()
            channel[x] =  self.Mode(self, x, y)
            if (channel_selection[x].currentText() == "TOX Mode"):
                tabs.addTab(channel[x], ("Channel " + str(x+1) + ": Tox Mode"))
            elif (channel_selection[x].currentText() == "BOD/COD Mode"):
                tabs.addTab(channel[x], ("Channel " + str(x+1) + ": BOD/COD Mode"))
        layout.addWidget(tabs)
        
    #Mode subclass for running TOX or BOD/COD modes
    class Mode(QWidget):
        #Custom class signals 
        #(CHANNEL, ROW, COL, Text)
        updateMainTableSignal = pyqtSignal(int,int,int,str)
        
        #(ROW,Col,Text)
        updateBodCodSignal = pyqtSignal(int,int,str)
        
        #(bool,bool)
        
        updateStatusBarSignal = pyqtSignal(bool,bool)

        
        def __init__(self, parent, channel, mode):
            global mainTable
            global serial_objects
            global graphs_limits
            global endFlag
            global startTime
            global dfs_old
            global dfs
            
            super().__init__(parent)
            self.channel = channel+1
            self.mode = mode
            self.parent = parent
            
            #If TOX -> Load Tox
            if(self.mode == 0):
                uic.loadUi(resourcepath(str(uis) + '/ToxMode.ui'),self)
                
            #If BOD/COD -> Load BOD/COD UI and load calibration sheet
            elif(self.mode == 1):
                if self.channel == 1:
                    dfs[self.channel-1] = dfs_old[self.channel-1] = pd.read_csv(BODCalibLocation_channel1, delimiter = ",")
                    (self.calib_rows, self.calib_columns) = dfs[self.channel-1].shape
                    

                elif self.channel == 2:
                    dfs[self.channel-1] = dfs_old[self.channel-1] = pd.read_csv(BODCalibLocation_channel2, delimiter = ",")
                    (self.calib_rows, self.calib_columns) = dfs[self.channel-1].shape
                    
                uic.loadUi(resourcepath(str(uis) + '/BODCODMode.ui'),self)
                
                #Assign UI objects to self and modify settings
                self.calibrationSettings = self.findChild(QPushButton,'calibSettings')
                self.Bod_Cod_Values = self.findChild(QTableWidget,'BOD_COD_Values')
                self.Bod_Cod_Values.horizontalHeader().setStretchLastSection(True)
                self.Bod_Cod_Values.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                self.Bod_Cod_Values.horizontalHeader().hide()
                for i in range(self.Bod_Cod_Values.rowCount()):
                    self.Bod_Cod_Values.setRowHeight(i, 30)
                self.Bod_Cod_Values.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
                
            #Start BOD/COD regression 
            if (self.mode == 1):
                self.BOD_Regression(self.channel-1)
                self.COD_regression(self.channel-1)
                
            #Program starttime is here and assign UI objects to self and modify settings
            startTime[channel] = time.time()
            self.mainSettings = self.findChild(QPushButton,'settings1')
            mainTable[channel] = self.findChild(QTableWidget,'mainTable')
            self.status = self.findChild(QLabel, 'status1')
            self.status.setText("Acquisition Start")
            self.graphArea = self.findChild(QScrollArea, 'graphingArea')
            self.graphSettings = self.findChild(QPushButton, 'graphSettings')
            self.start_stop = self.findChild(QPushButton, 'start_stop')
            self.polarizationTest = self.findChild(QPushButton, 'polarizationTest')

            
            for i in range(mainTable[channel].rowCount()):
                mainTable[channel].setRowHeight(i, 30)
            
            mainTable[channel].verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
            mainTable[channel].horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            mainTable[channel].horizontalHeader().hide()
            
            #Make button a toggle button and connect to method btnState
            self.start_stop.toggle()
            self.start_stop.clicked.connect(self.btnState)
            
            #Create a scrollable graph area content storage area and intialize empty plots there
            self.contents = QWidget()
            self.store = QVBoxLayout()
            
            self.graph1 = MplCanvas(self,width = 3.5, height = 2.5, dpi =100)
            self.x = [] #Initalize graph variables
            self.y1 = []
            self.y2 = []
            self.graph1.axes.set_title("V$_\mathbf{min}$ and V$_\mathbf{max}$", fontweight = 'bold')
            self.graph1.axes.set_xlabel("Time Elapsed (hours)", fontweight = 'bold')
            self.graph1.axes.set_ylabel('V$_\mathbf{min}$ (mV)', fontweight = 'bold')
            self.axes2 = self.graph1.axes.twinx() #Creates a two axes plot
            self.axes2.set_ylabel('V$_\mathbf{max}$ (mv)', fontweight = 'bold')
            self.graph1.setMinimumSize(self.graph1.size()) #forces plots to be a uniform size
            
            
            self.graph2 = MplCanvas(self,width = 3.5, height = 2.5, dpi =100)
            self.y3 = []  #Initalize graph variables
            self.graph2.axes.set_title("Battery Voltage", fontweight = 'bold')
            self.graph2.axes.set_xlabel("Time Elapsed (hours)", fontweight = 'bold')
            self.graph2.axes.set_ylabel('Voltage (mV)', fontweight = 'bold')
            self.graph2.setMinimumSize(self.graph1.size()) #forces plots to be a uniform size
            
            self.graph3 = MplCanvas(self,width = 3.5, height = 2.5, dpi =100)
            self.y4 = []
            self.graph3.axes.set_title("Temperature over time", fontweight = 'bold')
            self.graph3.axes.set_xlabel("Time Elapsed (hours)", fontweight = 'bold')
            self.graph3.axes.set_ylabel('Temperature (C)', fontweight = 'bold')
            self.graph3.setMinimumSize(self.graph1.size())
            
            self.graph4 = MplCanvas(self,width = 3.5, height = 2.5, dpi =100)
            self.y5 = []
            self.y6 = []
            self.graph4.axes.set_title("R$_\mathbf1$ and R$_\mathbf2$ over time", fontweight = 'bold')
            self.graph4.axes.set_xlabel("Time Elapsed (hours)", fontweight = 'bold')
            self.graph4.axes.set_ylabel('R$_\mathbf1$ (ohms)', fontweight = 'bold')
            self.axes4 = self.graph4.axes.twinx()
            self.axes4.set_ylabel('R$_\mathbf2$ (ohms)', fontweight = 'bold')
            self.graph4.setMinimumSize(self.graph1.size())
            
            self.graph5 = MplCanvas(self,width = 3.5, height = 2.5, dpi =100)
            self.y7 = []
            self.graph5.axes.set_title("Capacitance over time", fontweight = 'bold')
            self.graph5.axes.set_xlabel("Elapsed Time (hours)", fontweight = 'bold')
            self.graph5.axes.set_ylabel('Capacitance (uF)', fontweight = 'bold')
            self.graph5.setMinimumSize(self.graph1.size())
            
            self.store.addWidget(self.graph1) #Add to scrollable content area
            self.store.addWidget(self.graph3) #Add to scrollable content area
            self.store.addWidget(self.graph4) #Add to scrollable content area
            self.store.addWidget(self.graph5) #Add to scrollable content area
            self.store.addWidget(self.graph2) #Add to scrollable content area
            
            if(self.mode == 1): #If BOD/COD mode -> Add the graph below
                self.graph6 = MplCanvas(self,width = 3.5, height = 2.5, dpi =100)
                self.y8 = []
                self.y9 = []
                self.graph6.axes.set_title("BOD and COD over time", fontweight = 'bold')
                self.graph6.axes.set_xlabel("Elapsed Time (hours)", fontweight = 'bold')
                self.graph6.axes.set_ylabel('BOD est.(mg/L)', fontweight = 'bold')
                self.axes6 = self.graph6.axes.twinx()
                self.axes6.set_ylabel('COD est. (mg/L)', fontweight = 'bold')
                self.graph6.setMinimumSize(self.graph1.size())
                self.store.addWidget(self.graph6)
            
            self.contents.setLayout(self.store) #Add the scrollable content area to the layout
            
            #Modify Graph Area settings
            self.graphArea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            self.graphArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.graphArea.setWidgetResizable(True)
            self.graphArea.setWidget(self.contents)
            
            #Add new statusBar
            self.statusBarLayout = self.findChild(QVBoxLayout, "statusBarLayout")
            self.loraBar = QStatusBar()
            self.loraStatusLabel = QLabel("Lora Enabled")
            self.loraStatusLabel.setStyleSheet("border:0 ; color: black; font:italic;")
            self.loraConnectionLabel = QLabel("Connected")
            self.loraConnectionLabel.setStyleSheet("border:0 ; color: black; font:italic;")
            
            self.loraBar.reformat()
            self.loraBar.setStyleSheet('border: 0; background-color: lightgray; font:italic;')
            self.loraBar.setStyleSheet("QStatusBar::item {border: none;}")
            
            self.loraBar.addPermanentWidget(CustomVLine())
            self.loraBar.addPermanentWidget(self.loraStatusLabel)
            self.loraBar.addPermanentWidget(CustomVLine())
            self.loraBar.addPermanentWidget(self.loraConnectionLabel)
            self.loraBar.addPermanentWidget(CustomVLine())
            self.statusBarLayout.addWidget(self.loraBar)
            
            self.disconnect = disconnectBiosensor(self)
            #print(self.disconnect)
            
            #Begin Threading
            self.run(self.channel, self.mode, self.parent)
            
            #IF BOD/MODE assign onCalibOpen method to calibration button
            if self.mode == 1:
                self.calibrationSettings.clicked.connect(lambda: self.onCalibOpen(self.channel-1, self.mode, self.r2_BOD, self.BOD_fit_eqn, self.BOD_fit_type, self.r2_COD, self.COD_fit_eqn, self.COD_fit_type))
            
            #If signals are connected / connect the slots
            self.updateMainTableSignal.connect(self.updateMainTable)
            self.updateBodCodSignal.connect(self.updateBodCod)
            self.updateStatusBarSignal.connect(self.updateStatusBar)

            
            #Assign MCU settings and Graph settings to respective open function
            self.mainSettings.clicked.connect(lambda: self.onBtnOpen(self.channel-1, self.mode))
            self.graphSettings.clicked.connect(lambda: self.onGraphOpen(self.channel -1 , self.mode))
            self.polarizationTest.clicked.connect(lambda: self.onPolarizationOpen(self.channel-1,self.mode))
        
        #Update table according to channel, row and column with corresponding text
        @QtCore.pyqtSlot(int,int,int,str)
        def updateMainTable(self, channel, row, col, text):
            global mainTable
            item = QTableWidgetItem(text)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable) #Keeps item uneditable
            mainTable[channel].setItem(row,col,item) 
        
        #Update table according to row and column with corresponding text
        @QtCore.pyqtSlot(int,int,str)
        def updateBodCod(self, row, col, text):
            item = QTableWidgetItem(text)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable) #Keeps item uneditable
            self.BOD_COD_Values.setItem(row, col, item)
        
        #Update status bar
        @QtCore.pyqtSlot(bool, bool)
        def updateStatusBar(self, loraEnabled, startUpCheck):
            if not loraEnabled:
                self.loraStatusLabel.setStyleSheet("border:0 ; color: red; font:italic;")
                self.loraConnectionLabel.setStyleSheet("border:0 ; color: red; font:italic;")
                self.loraStatusLabel.setText("Lora disabled")
                self.loraConnectionLabel.setText("Not connected")
            else:
                self.loraStatusLabel.setStyleSheet("border:0 ; color: green; font:italic;")
                self.loraStatusLabel.setText("Lora enabled")
                if startUpCheck:
                    self.loraConnectionLabel.setStyleSheet("border:0 ; color: green; font:italic;")
                    self.loraConnectionLabel.setText("Connected")
                else:
                    self.loraConnectionLabel.setStyleSheet("border:0 ; color: red; font:italic;")
                    self.loraConnectionLabel.setText("Not connected")

            
        #BOD Regression Formula
        def BOD_Regression(self, channel):
            global dfs_old
            global dfs
            global bod_fits
            global bod_cod_flag

            
            self.r2_BOD = 0.0
            self.BOD_fit_eqn ='-'
            self.BOD_fit_type = '-'
            
            if (channel == 0):
                dfs[channel] = pd.read_csv(BODCalibLocation_channel1, delimiter = ",")
                (self.calib_rows, self.calib_columns) = dfs[channel].shape
                #Open Default Behaviour
                try:
                    f = open(BODCalibType1, "r+")
                    self.fit_selections = f.readlines()
                    f.close()
                except Exception:
                    print("Error opening default file")
                
            elif (channel == 1):
                dfs[channel] = pd.read_csv(BODCalibLocation_channel2, delimiter = ",")
                (self.calib_rows, self.calib_columns) = dfs[channel].shape
                #Open Default Behaviour
                try:
                    f = open(BODCalibType2, "r+")
                    self.fit_selections = f.readlines()
                    f.close()
                except Exception:
                    print("Error opening default file")
                
            print(dfs)
            for i in range(len(self.fit_selections)):
                self.fit_selections[i] = self.fit_selections[i].strip()            
            
            V_avgs = dfs[channel]['Average_Vmin(mV)'].values
            BOD_input = dfs[channel]['BOD measured(mg/L)'].values
            T_avgs = dfs[channel]['Average_Temperature(C)'].values
            
            Y_avgs = V_avgs/AprilPoly(T_avgs)
            
            #this can be integrated into the pandas
            if np.amin(BOD_input) > 3: #checks if there is a "0 point" in the given data (<3 considered enough a zero; BOD of 2 taken as a "0" for these fits)
                BOD_input = np.append(BOD_input,0.1) #adds a "0" point for BOD; 0.1 because it cannot do log calc with a 0 value
                Y_avgs = np.append(Y_avgs,0) #adds a "0" point for Y_avgs

            try:
                #FIT TO LOG & EXPONENTIAL REGRESSIONS THEN SAVE COEFFICIENTS
                self.bad_calibration = False
                self.BOD_exp_coefs = np.polyfit(Y_avgs,np.log(BOD_input),1,w=np.sqrt(BOD_input))

                #EXTRACT R-squared score
                BOD_r2_exp = r2_score(BOD_input, np.exp(self.BOD_exp_coefs[1])*np.exp(self.BOD_exp_coefs[0]*Y_avgs))
                BOD_r2_exp = round(BOD_r2_exp, 2)

                #turns the BOD_input and Y_avgs array into 2D arrays; required for polynomial regressions
                BOD_input = BOD_input[:, np.newaxis]
                Y_avgs = Y_avgs[:, np.newaxis]

                #HERE for strictly BOD
                for i in range(1,3): #iterates with i = 1,2
                    polyfeats = PolynomialFeatures(degree=i)
                    BOD_modelo = make_pipeline(polyfeats,LinearRegression())
                    BOD_modelo.fit(Y_avgs,BOD_input)
                    BOD_poly_pred = BOD_modelo.predict(Y_avgs)

                    if i == 1:
                        BOD_r2_lin = r2_score(BOD_input,BOD_poly_pred) #r2 score for linear
                        BOD_r2_lin = round(BOD_r2_lin,2)
                        self.BOD_lin_coefs = BOD_modelo.steps[1][1].coef_
                        self.BOD_lin_inter = BOD_modelo.steps[1][1].intercept_

                    if i == 2:
                        BOD_r2_poly2 = r2_score(BOD_input,BOD_poly_pred) #r2 score for 2nd order polynomial
                        BOD_r2_poly2 = round(BOD_r2_poly2, 2)
                        self.BOD_poly2_coefs = BOD_modelo.steps[1][1].coef_
                        self.BOD_poly2_inter = BOD_modelo.steps[1][1].intercept_
                
                if bod_cod_flag[channel]:
                    
                    if bod_fits[channel][0] == False:
                        BOD_r2_exp = 0
                    if bod_fits[channel][1] == False:
                        BOD_r2_lin = 0
                    if bod_fits[channel][2] == False:
                        BOD_r2_poly2 = 0

                if BOD_r2_exp > BOD_r2_lin: #if the r2 of the exp is greater than the linear, the exp is initally taken as the best fit
                    Is_Negative = False
                    for i in [float(j)/100 for j in range(0,100,1)]: #checks if there are any negative values for Y = 0 to 0.99
                        if np.exp(self.BOD_exp_coefs[1])*np.exp(self.BOD_exp_coefs[0]*i) < 0:
                            Is_Negative = True
                            break
                    if Is_Negative == False:
                        self.r2_BOD = BOD_r2_exp
                        self.BOD_fit_eqn = "BOD = exp(%f)*exp(%f*Y)" % (self.BOD_exp_coefs[1],self.BOD_exp_coefs[0])
                        self.BOD_fit_type = 'Exponential'
                        #print (BOD_fit_eqn)
                        #print (Is_Negative)

                if BOD_r2_exp <= BOD_r2_lin: #if this is not the case, then the linear is initially taken as the best fit
                    Is_Negative = False
                    for i in [float(j)/100 for j in range(0,100,1)]: #checks if there are any negative values for Y = 0 to 0.99
                        if self.BOD_lin_inter+self.BOD_lin_coefs[0][1]*i < 0:
                            Is_Negative = True
                            break
                    if Is_Negative == False:
                        self.r2_BOD = BOD_r2_lin
                        self.BOD_fit_eqn = "BOD = %f + %f*Y" % (self.BOD_lin_inter,self.BOD_lin_coefs[0][1])
                        self.BOD_fit_type = 'Linear'


                if BOD_r2_poly2 > max(BOD_r2_lin,BOD_r2_exp): #checks that the r2 of poly4 is greater than all other r2s
                    Is_Negative = False
                    for i in [float(j)/100 for j in range(0,100,1)]: #checks if there are any negative values for Y = 0 to 0.99
                        if self.BOD_poly2_inter+self.BOD_poly2_coefs[0][1]*i+self.BOD_poly2_coefs[0][2]*(i**2) < 0:
                            Is_Negative = True
                            break
                    if Is_Negative == True:
                        self.r2_BOD = BOD_r2_poly2
                        self.BOD_fit_eqn = "BOD = %f + %f*Y + %f*Y^2" % (self.BOD_poly2_inter,self.BOD_poly2_coefs[0][1],self.BOD_poly2_coefs[0][2])
                        self.BOD_fit_type = 'Polynomial'
                        #print (r2_BOD)
                
                if bod_cod_flag[channel] == False:
                    
                    if self.fit_selections[0] == "Exponential":
                        self.r2_BOD = BOD_r2_exp
                        self.BOD_fit_eqn = "BOD = exp(%f)*exp(%f*Y)" % (self.BOD_exp_coefs[1],self.BOD_exp_coefs[0])
                        self.BOD_fit_type = 'Exponential'
                        
                    elif self.fit_selections[0] == "Linear":
                        self.r2_BOD = BOD_r2_lin
                        self.BOD_fit_eqn = "BOD = %f + %f*Y" % (self.BOD_lin_inter,self.BOD_lin_coefs[0][1])
                        self.BOD_fit_type = 'Linear'
                        
                    elif self.fit_selections[0] == "Polynomial":
                        self.r2_BOD = BOD_r2_poly2
                        self.BOD_fit_eqn = "BOD = %f + %f*Y + %f*Y^2" % (self.BOD_poly2_inter,self.BOD_poly2_coefs[0][1],self.BOD_poly2_coefs[0][2])
                        self.BOD_fit_type = 'Polynomial'

            except Exception:
                #print "BAD Calibration Data, Revert to OLD Data"
                
                self.bad_calibration = True
                dfs[channel] = dfs_old[channel]
                print (dfs[channel])
                if (channel == 0):
                    dfs[channel].to_csv(BODCalibLocation_channel1, index = False, header = True)
                    
                elif (channel == 1):
                    dfs[channel].to_csv(BODCalibLocation_channel2, index = False, header = True)
                bod_cod_flag[channel] == False
                self.BOD_Regression(channel)
                
        def COD_regression(self, channel):
            global dfs_old
            global dfs
            global cod_fits

            self.r2_COD = 0.0
            self.COD_fit_eqn ='-'
            self.COD_fit_type = '-'

            #EXTRACT VALUES FROM CALIBRATION TABLE
            V_avgs = dfs[channel]['Average_Vmin(mV)'].values
            COD_input = dfs[channel]['COD measured(mg/L)'].values
            T_avgs = dfs[channel]['Average_Temperature(C)'].values


            #CALCULATE Ys
            Y_avgs = V_avgs/AprilPoly(T_avgs)

            #this can be integrated into the pandas
            if np.amin(COD_input) > 3: #checks if there is a "0 point" in the given data (<3 considered enough a zero; COD of 2 taken as a "0" for these fits)
                COD_input = np.append(COD_input,0.1) #adds a "0" point for COD; 0.1 because it cannot do log calc with a 0 value
                Y_avgs = np.append(Y_avgs,0) #adds a "0" point for Y_avgs

            try:
                #FIT TO LOG & EXPONENTIAL REGRESSIONS THEN SAVE COEFFICIENTS
                self.bad_calibration = False
                self.COD_exp_coefs = np.polyfit(Y_avgs,np.log(COD_input),1,w=np.sqrt(COD_input))

                #EXTRACT R-squared score
                COD_r2_exp = r2_score(COD_input, np.exp(self.COD_exp_coefs[1])*np.exp(self.COD_exp_coefs[0]*Y_avgs))
                COD_r2_exp = round(COD_r2_exp, 2)

                #turns the COD_input and Y_avgs array into 2D arrays; required for polynomial regressions
                COD_input = COD_input[:, np.newaxis]
                Y_avgs = Y_avgs[:, np.newaxis]

                #HERE for strictly COD
                for i in range(1,3): #iterates with i = 1,2
                    polyfeats = PolynomialFeatures(degree=i)
                    COD_modelo = make_pipeline(polyfeats,LinearRegression())
                    COD_modelo.fit(Y_avgs,COD_input)
                    COD_poly_pred = COD_modelo.predict(Y_avgs)

                    if i == 1:
                        COD_r2_lin = r2_score(COD_input,COD_poly_pred) #r2 score for linear
                        COD_r2_lin = round(COD_r2_lin,2)
                        self.COD_lin_coefs = COD_modelo.steps[1][1].coef_
                        self.COD_lin_inter = COD_modelo.steps[1][1].intercept_

                    if i == 2:
                        COD_r2_poly2 = r2_score(COD_input,COD_poly_pred) #r2 score for 2nd order polynomial
                        COD_r2_poly2 = round(COD_r2_poly2, 2)
                        self.COD_poly2_coefs = COD_modelo.steps[1][1].coef_
                        self.COD_poly2_inter = COD_modelo.steps[1][1].intercept_

                if bod_cod_flag[channel]:
                    
                    if cod_fits[channel][0] == False:
                        COD_r2_exp = 0
                    if cod_fits[channel][1] == False:
                        COD_r2_lin = 0
                    if cod_fits[channel][2] == False:
                        COD_r2_poly2 = 0
                
                if COD_r2_exp > COD_r2_lin: #if the r2 of the exp is greater than the linear, the exp is initally taken as the best fit
                    Is_Negative = False
                    for i in [float(j)/100 for j in range(0,100,1)]: #checks if there are any negative values for Y = 0 to 0.99
                        if np.exp(self.COD_exp_coefs[1])*np.exp(self.COD_exp_coefs[0]*i) < 0:
                            Is_Negative = True
                            break
                    if Is_Negative == False:
                        self.r2_COD = COD_r2_exp
                        self.COD_fit_eqn = "COD = exp(%f)*exp(%f*Y)" % (self.COD_exp_coefs[1],self.COD_exp_coefs[0])
                        self.COD_fit_type = 'Exponential'
                        #print (COD_fit_eqn)
                        #print (Is_Negative)

                if COD_r2_exp <= COD_r2_lin: #if this is not the case, then the linear is initially taken as the best fit
                    Is_Negative = False
                    for i in [float(j)/100 for j in range(0,100,1)]: #checks if there are any negative values for Y = 0 to 0.99
                        if self.COD_lin_inter+self.COD_lin_coefs[0][1]*i < 0:
                            Is_Negative = True
                            break
                    if Is_Negative == False:
                        self.r2_COD = COD_r2_lin
                        self.COD_fit_eqn = "COD = %f + %f*Y" % (self.COD_lin_inter,self.COD_lin_coefs[0][1])
                        self.COD_fit_type = 'Linear'


                if COD_r2_poly2 > max(COD_r2_lin,COD_r2_exp): #checks that the r2 of poly4 is greater than all other r2s
                    Is_Negative = False
                    for i in [float(j)/100 for j in range(0,100,1)]: #checks if there are any negative values for Y = 0 to 0.99
                        if self.COD_poly2_inter+self.COD_poly2_coefs[0][1]*i+self.COD_poly2_coefs[0][2]*(i**2) < 0:
                            Is_Negative = True
                            break
                    if Is_Negative == True:
                        self.r2_COD = COD_r2_poly2
                        self.COD_fit_eqn = "COD = %f + %f*Y + %f*Y^2" % (self.COD_poly2_inter,self.COD_poly2_coefs[0][1],self.COD_poly2_coefs[0][2])
                        self.COD_fit_type = 'Polynomial'
                        #print (r2_COD)

                if bod_cod_flag[channel] == False:
                    if self.fit_selections[1] == "Exponential":
                        self.r2_COD = COD_r2_exp
                        self.COD_fit_eqn = "COD = exp(%f)*exp(%f*Y)" % (self.COD_exp_coefs[1],self.COD_exp_coefs[0])
                        self.COD_fit_type = 'Exponential'
                        
                    elif self.fit_selections[1] == "Linear":
                        self.r2_COD = COD_r2_lin
                        self.COD_fit_eqn = "COD = %f + %f*Y" % (self.COD_lin_inter,self.COD_lin_coefs[0][1])
                        self.COD_fit_type = 'Linear'
                        
                    elif self.fit_selections[1] == "Polynomial":
                        self.r2_COD = COD_r2_poly2
                        self.COD_fit_eqn = "COD = %f + %f*Y + %f*Y^2" % (self.COD_poly2_inter,self.COD_poly2_coefs[0][1],self.COD_poly2_coefs[0][2])
                        self.COD_fit_type = 'Polynomial'
                
                if bod_cod_flag[channel] == True:
                    datastruct = ''
                    datastruct += self.BOD_fit_type.strip()
                    datastruct += '\n'
                    datastruct += self.COD_fit_type.strip()
                    if (channel == 0):
                        try:
                            f = open(BODCalibType1, "w+")
                            f.write(datastruct)
                            f.close()
                        except Exception:
                            print("Error opening default file")
                        
                    if (channel == 1):
                        try:
                            f = open(BODCalibType2, "w+")
                            f.write(datastruct)
                            f.close()
                        except Exception:
                            print("Error opening default file")
                            
            except Exception:
                #print "BAD Calibration Data, Revert to OLD Data"
                self.bad_calibration = True
                dfs[channel] = dfs_old[channel]
                print (dfs[channel])
                if (channel == 0):
                    dfs[channel].to_csv(BODCalibLocation_channel1, index = False, header = True)
                    
                elif (channel == 1):
                    dfs[channel].to_csv(BODCalibLocation_channel1, index = False, header = True)
                bod_cod_flag[channel] == False
                self.COD_regression(channel)
                    
        #Main Threading function -> Depending on the channel -> Start thread 1+2 or thread 3+4 (Pass channel, mode parameters for globals)            
        def run(self, channel, mode, parent):
            if channel == 1:
                
                t1 = threading.Thread(target= self.mainThread, args=(channel-1,mode, parent))
                t2 = threading.Thread(target= self.update_plot, args=(channel-1,mode,))
                t1.daemon = True
                t2.daemon = True
                t1.start()
                t2.start()
        
            if channel == 2:
                t3 = threading.Thread(target= self.mainThread, args=(channel-1,mode, parent))
                t4 = threading.Thread(target= self.update_plot, args=(channel-1,mode,))
                t3.daemon = True
                t4.daemon = True
                t3.start()
                t4.start()
  
        #main_thread
        def mainThread(self,channel,mode,parent):
            global endFlag
            global channel_params
            global serial_objects
            global mainTable
            global outputs
            global settingsFlag
            global bod_cod_flag
            global start_plotting
            global threadEnded
            global waiting_for_something_to_happen
            global loaded
            global loaded2
            global loraStartUpCheck
            global startUp
            
            loraStartUpCheck = [False] * len(serial_objects)
            
            while True:
                if startUp == True:
                    try:
                        #Checker reading -> Until I receive serial information in port -> Send Command, wait and read
                        threadEnded[channel] = False
                        serial_objects[channel].read(2048)
                        while(serial_objects[channel].read(1) == b''):
                            serial_objects[channel].write(b'GetAllParams\r')
                            #print('waiting for first read')
                            time.sleep(1)
                        #Flush the input buffer
                        text = read_all(serial_objects[channel], True)
                        #print(text)
                        time.sleep(0.1)
                        #Load Biosensor Params and separates into list 
                        serial_objects[channel].write(b"GetAllParams\r")
                        time.sleep(0.1)
                        text = read_all(serial_objects[channel], True).split(b"\r")
                        #print(text)
                        #Set MCU parameters to readings
                        for i in range(22):
                            x = text[i].decode()
                            temp = re.findall(r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", x)
                            channel_params[channel][i] = temp[0].strip()
                        for i in range(22,25):
                            x = text[i].decode()
                            channel_arr = x.split(":")
                            channel_params[channel][i] = channel_arr[2].strip()
                            
                        
                        #Set digital pot according to MCU parameter
                        while True:
                            serial_objects[channel].write(b"SetDigitalPot " + (channel_params[channel][16]).encode() + b"\r")
                            time.sleep(0.05)
                            text = serial_objects[channel].readline()
                            text = text.decode().replace('\x00','')
                            temp = re.findall(r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", text)
                            if not (temp[0] == None):
                                channel_params[channel][16] = temp[0].strip()
                                value = channel_params[channel][16]
                                value = value.strip().encode()
                                serial_objects[channel].write(b"SetParam RLoad "+ value + b"\r")
                                time.sleep(0.01)
                                text = serial_objects[channel].readline()
                                break
                            else:
                                time.sleep(0.1)
                                
                        #IF PARAMs == 1 for lora -> wait 1 minute to let load
                        if channel_params[channel][21].strip() == "1":
                            startcheck = time.time()
                            tempArr = []
                            serial_objects[channel].write(b'Reset\r')
                            time.sleep(0.1)
                            while True:
                                text = serial_objects[channel].readline().decode().replace('\x00','')
                                #print(text)
                                tempArr.append(text)
                                if 'Send ? command' in text:
                                    break
                                endcheck = time.time()
                                if endcheck - startcheck >= 300:
                                    if(platform.system() == 'Linux'):
                                        os.system('sudo shutdown -r now')
                                    else:
                                        sys.exit()
                                loop = QEventLoop()
                                QTimer.singleShot(1000, loop.quit)
                                loop.exec_()
                                
                            loraFailFlag = False
                            for x in tempArr:
                                if 'ERROR: Join attempts failed, reset to attempt again' in x:
                                    loraFailFlag = True
                            print(tempArr) 
                            if loraFailFlag:
                                loraStartUpCheck[channel] = False
                            else:
                                loraStartUpCheck[channel] = True
                            self.updateStatusBarSignal.emit(True,loraStartUpCheck[channel])
                        else:
                            loraStartUpCheck[channel] = False
                            self.updateStatusBarSignal.emit(False,loraStartUpCheck[channel])
                        #print('exit')
                        
                        
                        if (self.parent.isVisible() == False) and loaded2 == False and len(serial_objects) == 2:
                            loaded2 = True
                            while loaded == False:
                                loop = QEventLoop()
                                QTimer.singleShot(500, loop.quit)
                                loop.exec_()
                        
                        #If parent is hidden -> Show and set global loaded variable to true
                        if (self.parent.isVisible() == False):
                            self.parent.show()
                            loaded = True
                        
                        #IF LORa FAILEd or sucess show a dialog
                        #Set-up datastruct and parameters to be written into file 
                        writeTime=str(datetime.datetime.now())[:19] #get date and time program starts
                        parameterLog = ''
                        parameterLog += writeTime
                        parameterLog += ' '
                        for i in range(25):
                            parameterLog += channel_params[channel][i]
                            parameterLog += '\t\t'
                        parameterLog+='\n'
                        
                        text = ''
                        text += parameterLog
                        #Write into file (with the appropriate channel, mode, log vs parameter, and text being written)
                        writeIntoFile(channel, mode, False, text)
                        startUp = False
                        threadEnded[channel] = True
                    except Exception:
                        self.disconnect.exec_()
                        
                #Main Loop Area
                
                if settingsFlag[channel] == True:
                    threadEnded[channel] = False
                    self.status.setText("Saving settings...")
                    self.mainSettings.setEnabled(False)
                    try:
                        writeAllParams(channel)
                    except Exception:
                        self.disconnect.exec_()
                    time.sleep(0.5)
                    self.mainSettings.setEnabled(True)
                    self.status.setText("Settings saved")
                    settingsFlag[channel] = False
                    threadEnded[channel] = True
                    
                if (bod_cod_flag[channel] == True):
                    threadEnded[channel] = False
                    self.BOD_Regression(channel)
                    self.COD_regression(channel)
                    bod_cod_flag[channel] = False
                    threadEnded[channel] = True
                    
                if (settingsFlag[channel] == False) and (endFlag[channel] == False):
                    self.serial_comm(channel, mode, parent)
                    
                    self.start_stop.setEnabled(True)
                       
        #Serial Communication Thread
        def serial_comm(self, channel, mode, parent):
            global endFlag
            global channel_params
            global serial_objects
            global mainTable
            global outputs
            global settingsFlag
            global bod_cod_flag
            global start_plotting
            global threadEnded
            global waiting_for_something_to_happen
            global loaded
            
            try:
            
                #Thread Loop -> Loops all serial communication and exits thread only when endFlag is triggered.
                threadEnded[channel] = False
                
                #Initialize empty str variables
                acquisitionLog = '\n'
                text = ''

                #Set time interval between acquisition cycles and disable start/stop thread (button)
                interval = int(channel_params[channel][13])
                self.start_stop.setEnabled(False)
                
                    
                #Find data acquisition start time    
                programstart = datetime.datetime.now()
                outputs[channel][0] = str(programstart)[:19]
                
                #Read Rload and save as a table output
                serial_objects[channel].read(2048)
                serial_objects[channel].write(b"GetParam RLoad\r")
                time.sleep(0.05)
                text = read_all(serial_objects[channel], True).decode()
                temp = re.findall(r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", text)
                outputs[channel][8] = temp[0].strip()
                time.sleep(0.01)

                flag = True
                #Flag acts as a checker for Start Acquisition -> If not all outputs are filled appropriately (Try start acquisition again)
                while(flag):
                    flag = False
                    serial_objects[channel].read(2048)
                    time.sleep(0.1)
                    #print("Attempting Start Acquisition")
                    serial_objects[channel].write(b"StartAcquisition\r")
                    time.sleep(0.5)
                    self.status.setText("Acquiring acquisition data...")
                    
                    #While nothing is read -> Wait and try again
                    while(serial_objects[channel].read(1) == b''):
                        time.sleep(1)
                        
                    #Read all and split based on carriage return. 
                    temp = read_all(serial_objects[channel], False).split(b"\r")
                    #print(temp)
                    empty = read_all(serial_objects[channel], True)
                    #Parse through list and find outputs
                    for x in temp:
                        x = x.decode() #Decode bytes to string
                        if ("Temperature" in x) and ("Celsius" in x):
                            text = re.findall(r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", x) #Regex Code to find the number in the string
                            outputs[channel][4] = text[0].strip() #Set text to outputs after removing whitespace

                            
                        elif ("Battery Voltage" in x) and ('mV' in x):
                            text = re.findall(r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", x)
                            if not text == None:
                                try:
                                    num = float(text[0].strip())
                                    if num <= 0:
                                        outputs[channel][1] = 0
                                    else:
                                        outputs[channel][1] = num
                                except Exception:
                                    outputs[channel][1] = 0
                            else:
                                outputs[channel][1] = 0
                                    
                        elif ("SS Vcc" in x) and ("mV" in x):
                            text = re.findall(r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", x)
                            if not text == None:
                                try:
                                    num = float(text[0].strip())
                                    if num <= 0:
                                        outputs[channel][2] = 0
                                    else:
                                        outputs[channel][2] = num
                                except Exception:
                                    outputs[channel][2] = 0
                            else:
                                outputs[channel][2] = 0
                        
                        elif ("SS Voc" in x) and ("mV" in x):
                            text = re.findall(r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", x)
                            if not text == None:
                                try:
                                    num = float(text[0].strip())
                                    if num <= 0:
                                        outputs[channel][3] = 0
                                    else:
                                        outputs[channel][3] = num
                                except Exception:
                                    outputs[channel][3] = 0
                            else:
                                outputs[channel][3] = 0
                        
                        elif ("Rr" in x) and ('ohms' in x):
                            text = re.findall(r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", x)
                            if not text == None:
                                try:
                                    num = float(text[0].strip())
                                    if num <= 0:
                                        outputs[channel][5] = 0
                                    else:
                                        outputs[channel][5] = num
                                except Exception:
                                    outputs[channel][5] = 0
                            else:
                                outputs[channel][5] = 0
                            
                        elif ("Ra" in x) and ('ohms' in x):
                            text = re.findall(r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", x)
                            if not text == None:
                                try:
                                    num = float(text[0].strip())
                                    if num <= 0:
                                        outputs[channel][6] = 0
                                    else:
                                        outputs[channel][6] = num
                                except Exception:
                                    outputs[channel][6] = 0
                            else:
                                outputs[channel][6] = 0
                        
                        elif ("Ca" in x) and ("uF" in x):
                            text = re.findall(r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", x)
                            if not text == None:
                                try:
                                    num = float(text[0].strip())
                                    if num <= 0:
                                        outputs[channel][7] = 0
                                    else:
                                        outputs[channel][7] = num
                                except Exception:
                                    outputs[channel][7] = 0
                            else:
                                outputs[channel][7] = 0
                            
                    #IF all outputs have been appropriately set -> Continue        
                    for i in range(0 , 8):
                        #print(outputs[channel][i])
                        if outputs[channel][i] == None:
                            flag = True
                    time.sleep(1)
                #Begin interval timer for next acquisition cycle
                start = time.perf_counter()
                
                #Add output values to table
                for i in range(8):
                    #Emit signal to update table with the proper arguments
                    #Channel, row, column, text
                    self.updateMainTableSignal.emit(channel, i, 0, str(outputs[channel][i+1]))
                
                for i in range(9):
                    acquisitionLog += str(outputs[channel][i])
                    acquisitionLog += '\t\t'
                
                #If bod/cod run this
                if (mode ==1):
                    
                    #If calibration was changed ->Run regressions
                    if (bod_cod_flag[channel] == True):
                        self.BOD_Regression(channel)
                        self.COD_regression(channel)
                        bod_cod_flag[channel] = False
                        
                                        
                    Y_calculated = float(outputs[channel][1])/AprilPoly(float(outputs[channel][4]))

                    #Estimate BOD
                    if self.BOD_fit_type == 'Linear':
                        self.bodV = self.BOD_lin_inter[0] + (self.BOD_lin_coefs[0][0]*Y_calculated)
                        self.bodV = round(self.bodV, 2)
                        

                    if self.BOD_fit_type == 'Exponential':
                        self.bodV = math.exp(self.BOD_exp_coefs[1]) * math.exp(self.BOD_exp_coefs[0]*Y_calculated)
                        self.bodV = round(self.bodV, 2)

                    if self.BOD_fit_type == 'Polynomial':
                        self.bodV = self.BOD_poly2_inter[0] + (self.BOD_poly2_coefs[0][1] *Y_calculated)  + (self.BOD_poly2_coefs[0][2] * (Y_calculated * Y_calculated))  
                        self.bodV = round(self.bodV, 2)

                    #Estimate COD
                    if self.COD_fit_type == 'Linear':
                        self.codV = float(self.COD_lin_inter[0]) + float(self.COD_lin_coefs[0][0]*Y_calculated)
                        self.codV = round(self.codV, 2)

                    if self.COD_fit_type == 'Exponential':
                        self.codV = math.exp(self.COD_exp_coefs[1]) * math.exp(self.COD_exp_coefs[0]*Y_calculated)
                        self.codV = round(self.codV, 2)

                    if self.COD_fit_type == 'Polynomial':
                        self.codV = self.COD_poly2_inter[0] + (self.COD_poly2_coefs[0][1] *Y_calculated)  + (self.COD_poly2_coefs[0][2] * (Y_calculated * Y_calculated))
                        self.codV = round(self.codV, 2)
                    
                    #UpdateBODCOD Table according to estimated BODV and CODV
                    self.updateBodCodSignal.emit(0, 0, str(self.bodV))
                    self.updateBodCodSignal.emit(0, 1, str(self.codV))
                    
                    #Set up file structure for additional information
                    acquisitionLog += str(self.bodV)
                    acquisitionLog += '\t\t'
                    acquisitionLog += str(self.codV)
                    acquisitionLog += '\t\t'
                    acquisitionLog += str(self.r2_BOD)
                    acquisitionLog += '\t\t'
                    acquisitionLog += str(self.BOD_fit_eqn)
                    acquisitionLog += '\t'
                    acquisitionLog += str(self.BOD_fit_type)
                    acquisitionLog += '\t'
                    acquisitionLog += str(self.r2_COD)
                    acquisitionLog += '\t\t'
                    acquisitionLog += str(self.COD_fit_eqn)
                    acquisitionLog += '\t'
                    acquisitionLog += str(self.COD_fit_type)
                    acquisitionLog += '\t'
                
                #Once all information has been acquired -> Set plotting flag to true and begin plotting current info
                start_plotting[channel] = True
                
                #Writing into file
                text = ''
                text += acquisitionLog
                writeIntoFile(channel, mode, True, text)
                
                #End time for above operations
                end = time.perf_counter()
                
                #If time spent on operations less than time interval
                if(end - start <= interval):
                    #Enable start/stop
                    self.start_stop.setEnabled(True)
                    
                    #Set-up waiting value depending on time interval and time taken
                    wait = end -start
                    wait = interval - wait
                    
                    #During wait sequence -> If calibration was changed -> Regress
                    #During wait sequence -> If settings was saved -> Save settings
                    #During wait sequence -> If endFlag was triggered -> Exit 
                    for i in range(int(wait), 0, -1):
                        self.status.setText("Next acquisition in: " + str(i) + " s")
                        if (bod_cod_flag[channel] == True):
                            self.BOD_Regression(channel)
                            self.COD_regression(channel)
                            bod_cod_flag[channel] = False
                            
                        if settingsFlag[channel] == True:
                            self.status.setText("Saving settings...")
                            self.mainSettings.setEnabled(False)
                            settingsSaveTimerStart = time.perf_counter()
                            writeAllParams(channel)
                            settingsFlag[channel] = False
                            self.mainSettings.setEnabled(True)
                            settingsSaveTimerEnd = time.perf_counter()
                            settingsWait = settingsSaveTimerEnd - settingsSaveTimerStart
                            wait = int(channel_params[channel][13])
                            i = i - settingsWait
                            if(i<0):
                                break
                        #Modify button styling if acquisition is stopped
                        if(endFlag[channel] == True):
                            self.status.setText("Acquisition stopped")
                            threadEnded[channel] = True
                            #self.start_stop.toggle()
                            self.start_stop.setStyleSheet("background-color : green")
                            self.start_stop.setText("Start")
                            break
                        
                        #Read a byte to check if disconnected
                        serial_objects[channel].read(1)
                        
                        time.sleep(0.7)
                        
                if(endFlag[channel]):
                    self.status.setText("Acquisition stopped")
                    threadEnded[channel] = True
                    self.start_stop.setStyleSheet("background-color : green")
                    self.start_stop.setText("Start")
                    
            #If disconnect ->Execute disconnected Dialog
            except Exception:
                self.disconnect.exec_()      
                  
        #Updating Plot Method            
        def update_plot(self, channel, mode):
            global endFlag
            global startTime
            global endTime
            global graphspan
            global graphs_limits
            global timevec
            global start_plotting
            global waiting_for_something_to_happen
            timewait = 0
            
            #Looping function for thread
            while True:
                #While start_plotting flag == False -> Wait (If endFlag is triggered break loop and exit)
                while (start_plotting[channel] == False):
                    time.sleep(1)
                
                #Once start_plotting == True ->Set up time intervals for elapsed time and next cycle timings
                interval = int(channel_params[channel][13])
                start_plotting[channel] = False  
                start = time.perf_counter()
                endTime[channel] = time.time() #End time 
                t_elapsed = endTime[channel] - startTime[channel] #Time elapsed
                tchart = round(((t_elapsed)/3600),3) #Set-up tchart timing for elapsed time
                
                #Check is finding the total graph span of the graph between the end point and the first point
                timevec_checker = self.x
                timevec_checker = timevec_checker+[tchart]
                check=timevec_checker[-1]-timevec_checker[0]
                
                #As long as the check span is less than graphspan -> Add to list of data points
                if check <=graphspan[channel]:
                    self.x.append(tchart)
                    self.y1.append(float(outputs[channel][2]))
                    self.y2.append(float(outputs[channel][3]))
                    self.y3.append(float(outputs[channel][1]))
                    self.y4.append(float(outputs[channel][4]))
                    self.y5.append(float(outputs[channel][5]))
                    self.y6.append(float(outputs[channel][6]))
                    self.y7.append(float(outputs[channel][7]))
                    if (mode == 1):
                        self.y8.append(float(self.bodV))
                        self.y9.append(float(self.codV))
                        
                #Otherwise, clear as many points as needed          
                else:
                    difference = check - graphspan[channel]
                    int_hours = interval/3600
                    shift = int(difference/int_hours) 

                    self.x = self.x[shift:]
                    self.x.append(tchart)
                    self.y1 = self.y1[shift:]
                    self.y1.append(float(outputs[channel][2]))
                    self.y2 = self.y2[shift:]
                    self.y2.append(float(outputs[channel][3]))
                    self.y3 = self.y3[shift:]
                    self.y3.append(float(outputs[channel][1]))
                    self.y4 = self.y4[shift:]
                    self.y4.append(float(outputs[channel][4]))
                    self.y5 = self.y5[shift:]
                    self.y5.append(float(outputs[channel][5]))
                    self.y6 = self.y6[shift:]
                    self.y6.append(float(outputs[channel][6]))
                    self.y7 = self.y7[shift:]
                    self.y7.append(float(outputs[channel][7]))
                    if (mode == 1):
                        self.y8 = self.y8[shift:]
                        self.y8.append(float(self.bodV))
                        self.y9 = self.y9[shift:]
                        self.y9.append(float(self.codV))
            
                
                self.graph1.axes.cla()
                self.axes2.cla()
                self.graph1.axes.set_title(r"V$_\mathbf{min}$ and V$_\mathbf{max}$", fontweight = 'bold')
                self.graph1.axes.set_xlabel("Elapsed Time (hours)", fontweight = 'bold')
                self.graph1.axes.set_ylabel(r'V$_\mathbf{min}$ (mV)', color = 'tab:red', fontweight = 'bold')
                if not(graphs_limits[channel][0] == 0):
                    self.graph1.axes.set_ylim(0, int(graphs_limits[channel][0]))
                self.graph1.axes.plot(self.x, self.y1, 'r', label = "$V_{min}", linestyle ='dashed', marker ="o")
                self.graph1.axes.tick_params(axis='y', labelcolor='tab:red')
                self.axes2.set_ylabel(r'V$_\mathbf{max}$ (mv)', color = 'tab:blue', fontweight = 'bold')
                if not(graphs_limits[channel][1] == 0):
                    self.axes2.set_ylim(0, int(graphs_limits[channel][1]))
                self.axes2.plot(self.x,self.y2,'b', linestyle ='dashed', marker = "v")
                self.axes2.tick_params(axis='y', labelcolor = 'tab:blue')
                plt.setp(self.graph1.axes.get_xticklabels(), rotation = 30, horizontalalignment = 'right')
                self.graph1.draw_idle()
        
                self.graph2.axes.cla()
                self.graph2.axes.set_title("Battery Voltage", fontweight = 'bold')
                self.graph2.axes.set_xlabel("Elapsed Time (hours)", fontweight = 'bold')
                self.graph2.axes.set_ylabel('Voltage (mV)',color = 'tab:olive', fontweight = 'bold')
                if not(graphs_limits[channel][2] == 0):
                    self.graph2.axes.set_ylim(0, int(graphs_limits[channel][2]))
                self.graph2.axes.plot(self.x, self.y3, 'y', label = "Battery Voltage", linestyle ='dashed', marker ="o")
                plt.setp(self.graph2.axes.get_xticklabels(), rotation = 30, horizontalalignment = 'right')
                self.graph2.axes.legend()
                self.graph2.draw_idle()
                
                self.graph3.axes.cla()
                self.graph3.axes.set_title("Temperature",fontweight = 'bold')
                self.graph3.axes.set_xlabel("Elapsed Time (hours)", fontweight = 'bold')
                self.graph3.axes.set_ylabel('Temperature (C)', color = 'tab:green', fontweight = 'bold')
                if not(graphs_limits[channel][3] == 0):
                    self.graph3.axes.set_ylim(0, int(graphs_limits[channel][3]))
                self.graph3.axes.plot(self.x, self.y4, 'g', label = "Temp", linestyle ='dashed', marker ="o")
                plt.setp(self.graph3.axes.get_xticklabels(), rotation = 30, horizontalalignment = 'right')
                self.graph3.axes.legend()
                self.graph3.draw_idle()
                
                self.graph4.axes.cla()
                self.axes4.cla()
                self.graph4.axes.set_title("R$_\mathbf{1}$ and R$_\mathbf{2}$", fontweight = 'bold')
                self.graph4.axes.set_xlabel("Elapsed Time (hours)", fontweight = 'bold')
                self.graph4.axes.set_ylabel('R$_\mathbf{1}$ (ohms)', color = 'tab:red', fontweight = 'bold')
                if not(graphs_limits[channel][4] == 0):
                    self.graph4.axes.set_ylim(0, int(graphs_limits[channel][4]))
                self.graph4.axes.plot(self.x, self.y5, 'r', label = "R1", linestyle ='dashed', marker ="o")
                self.graph4.axes.tick_params(axis='y', labelcolor='tab:red')
                self.axes4.set_ylabel('R$_{2}$ (ohms)', color = 'tab:blue' , fontweight = 'bold')
                if not(graphs_limits[channel][5] == 0):
                    self.axes4.set_ylim(0, int(graphs_limits[channel][5]))
                self.axes4.plot(self.x,self.y6,'b', linestyle ='dashed', marker ="v")
                self.axes4.tick_params(axis='y', labelcolor = 'tab:blue')
                plt.setp(self.graph4.axes.get_xticklabels(), rotation = 30, horizontalalignment = 'right')
                self.graph4.draw_idle()
                
                self.graph5.axes.cla()
                self.graph5.axes.set_title("Capacitance", fontweight = 'bold')
                self.graph5.axes.set_xlabel("Elapsed Time (hours)", fontweight = 'bold')
                self.graph5.axes.set_ylabel('Capacitance (uF)', color = 'tab:purple', fontweight = 'bold')
                if not(graphs_limits[channel][6] == 0):
                    self.graph5.axes.set_ylim(0, int(graphs_limits[channel][6]))
                self.graph5.axes.plot(self.x, self.y7, 'm', label = "Capacitance", linestyle ='dashed', marker ="o")
                plt.setp(self.graph5.axes.get_xticklabels(), rotation = 30, horizontalalignment = 'right')
                self.graph5.axes.legend()
                self.graph5.draw_idle()
                
                if (mode == 1):
                    self.graph6.axes.cla()
                    self.axes6.cla()
                    self.graph6.axes.set_title("BOD and COD", fontweight = 'bold')
                    self.graph6.axes.set_xlabel("Elapsed Time (hours)", fontweight = 'bold')
                    self.graph6.axes.set_ylabel('BOD est.(mg/L)', color = 'tab:red', fontweight = 'bold')
                    if not(graphs_limits[channel][7] == 0):
                        self.graph6.axes.set_ylim(0, int(graphs_limits[channel][7]))
                    self.graph6.axes.plot(self.x, self.y8, 'r', label = "BOD", linestyle ='dashed', marker ="o")
                    self.graph6.axes.tick_params(axis='y', labelcolor='tab:red')
                    self.axes6.set_ylabel('COD est.(mg/L)', color = 'tab:blue',fontweight = 'bold')
                    if not(graphs_limits[channel][8] == 0):
                        self.axes6.set_ylim(0, int(graphs_limits[channel][8]))
                    self.axes6.plot(self.x,self.y9,'b', linestyle ='dashed', marker ="v")
                    self.axes6.tick_params(axis='y', labelcolor = 'tab:blue')
                    plt.setp(self.graph6.axes.get_xticklabels(), rotation = 30, horizontalalignment = 'right')
                    self.graph6.draw_idle()
        
        def clearGraph(self):
            #Used to zero the graph for elapsed time
            startTime[self.channel-1] = time.time()
            #Empty out the graphing variables and clear settings
            self.x = []
            self.y1 = []
            self.y2 = []
            self.y3 = []
            self.y4 = []
            self.y5 = []
            self.y6 = []
            self.y7 = []
            self.graph1.axes.clear()
            self.axes2.clear()
            self.graph1.axes.set_title(r"V$_\mathbf{min}$ and V$_\mathbf{max}$", fontweight = 'bold')
            self.graph1.axes.set_xlabel("Elapsed Time (hours)", fontweight = 'bold')
            self.graph1.axes.set_ylabel(r'V$_\mathbf{min}$ (mV)', color = 'tab:red', fontweight = 'bold')
            self.axes2.set_ylabel(r'V$_\mathbf{max}$ (mv)', color = 'tab:blue', fontweight = 'bold')
            self.graph1.draw()
            self.graph2.axes.clear()
            self.graph2.axes.set_title("Battery Voltage",fontweight = 'bold')
            self.graph2.axes.set_xlabel("Elapsed Time (hours)", fontweight = 'bold')
            self.graph2.axes.set_ylabel('Voltage (mV)',color = 'tab:olive', fontweight = 'bold')
            self.graph2.draw()
            self.graph3.axes.clear()
            self.graph3.axes.set_title("Temperature",fontweight = 'bold')
            self.graph3.axes.set_xlabel("Elapsed Time (hours)", fontweight = 'bold')
            self.graph3.axes.set_ylabel('Temperature (C)', color = 'tab:green', fontweight = 'bold')
            self.graph3.draw()
            self.graph4.axes.clear()
            self.axes4.clear()
            self.graph4.axes.set_title("R$_\mathbf{1}$ and R$_\mathbf{2}$",fontweight = 'bold')
            self.graph4.axes.set_xlabel("Elapsed Time (hours)", fontweight = 'bold')
            self.graph4.axes.set_ylabel('R$_\mathbf{1}$ (ohms)', color = 'tab:red', fontweight = 'bold')
            self.axes4.set_ylabel('R$_{2}$ (ohms)', color = 'tab:blue' , fontweight = 'bold')
            self.graph4.draw()
            self.graph5.axes.clear()
            self.graph5.axes.set_title("Capacitance",fontweight = 'bold')
            self.graph5.axes.set_xlabel("Elapsed Time (hours)", fontweight = 'bold')
            self.graph5.axes.set_ylabel('Capacitance (uF)', color = 'tab:purple', fontweight = 'bold')
            self.graph5.draw()
            #IF BOD/COD Mode -> Do the same thing
            if(self.mode == 1):
                self.y8 = []
                self.y9 =[]
                self.graph6.axes.clear()
                self.axes6.clear()
                self.graph6.axes.set_title("BOD and COD",fontweight = 'bold')
                self.graph6.axes.set_xlabel("Elapsed Time (hours)", fontweight = 'bold')
                self.graph6.axes.set_ylabel('BOD est.(mg/L)', color = 'tab:red', fontweight = 'bold')
                self.axes6.set_ylabel('COD est.(mg/L)', color = 'tab:blue',fontweight = 'bold')
                self.graph6.draw()
                
        #FUNCTION FOR START/STOP BUTTON
        def btnState(self):
            global endFlag
            
            #IF pressed -> Set end flag to false and start running
            if self.start_stop.isChecked():
                self.start_stop.setEnabled(False)
                self.clearGraph()
                endFlag[self.channel-1] = False
                #print('Pressed')
                #Change Button styling and disable it
                self.start_stop.setStyleSheet("background-color : red")
                self.start_stop.setText("Stop")
                self.status.setText("Acquisition start")
                self.start_stop.setEnabled(False)
                time.sleep(1.5)
                 
                #self.start_stop.setEnabled(True)
                
            #If unpressed -> Change button styling and set end flag to true    
            else:
                #print ("Released")
                self.start_stop.setEnabled(False)
                self.start_stop.setStyleSheet("background-color : green")
                self.start_stop.setText("Start")
                endFlag[self.channel-1] = True
                self.start_stop.setEnabled(False)
                time.sleep(1.5)
                self.start_stop.setEnabled(True)
    
        def onPolarizationOpen(self, x, y):
            global endFlag
            global threadEnded
            
            #If current channel thread has ended -> Display different Messages
            if (threadEnded[x] == False):
                check_dlg = QMessageBox.question(self, "Polarization Test", "Polarization test will stop current operation.\nAre you sure you want to continue?", QMessageBox.Yes | QMessageBox.No)
            elif(threadEnded[x] == True):
                check_dlg = QMessageBox.question(self, "Polarization Test", "Polarization test will take some time.\nAre you sure you want to continue?", QMessageBox.Yes | QMessageBox.No)

            #If yes was selected
            if (check_dlg) == QMessageBox.Yes:
                #Hide Parent #
                self.parent.hide()
                #If button is toggled -> set stopthread to true
                if self.start_stop.isChecked():
                    endFlag[x] = True
                    
                    #Create Waiting Dialog
                    wait = QDialog()
                    wait.setWindowTitle("Closing Channel " + str(x+1))
                    width = 500
                    height = 100
                    wait.setFixedSize(width, height)
                    wait.setWindowIcon(QtGui.QIcon(str(uis) + '/NRCLogo.ico'))
                    
                    #Set waiting Text
                    waitText = QLabel(wait)
                    waitText.setGeometry(QRect(50, 30, 650, 200))
                    waitText.setStyleSheet("font-family: Century Gothic")
                    waitText.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
                    waitText.setText("Stopping data acquisition for channel " +str(x+1)+ ".\nPlease wait until the operation is over.")
                    
                    #Show Waiting Dialog
                    wait.show()
                    #Loop UI until thread has ended (Pause UI for one second and then checks)
                    while threadEnded[x] == False:
                        loop = QEventLoop()
                        QTimer.singleShot(1000, loop.quit)
                        loop.exec_()
                    #Close waiting dialog
                    wait.close()
                
                #Initialize new form with (channel, mode) as arguments
                polarization_Form = PolarizationForm(x,y)
                #Execute form -> (AKA Will not pause everything on this thread until polarization_Form is closed)
                polarization_Form.exec_()
                #Then show parent
                self.parent.show()
            #Otherwise pass
            else:
                pass
                
        
        #On graph settings button open -> Load graph settings dialog and execute. If exception -> Create warning
        def onGraphOpen(self, x, y):
            Graph_dlg = GraphSettingsDialog(self,x,y)
        
            try:
                Graph_dlg.exec_()
            except Exception:
                error = QMessageBox.warning(self, 'Error!', 'Graph Settings Failed to Open')
        
        #On MCU settings button open -> Load basic settings dialog and execute. If exception -> Create warning 
        def onBtnOpen(self, x ,y):
            Main_dlg = BasicSettingsDialog(self,x,y)
            
            try:
                Main_dlg.exec_()
            except Exception:
                error = QMessageBox.warning(self, 'Error!', 'Settings Failed to Open')
        
        #On Calibration Open -> Load Calibration settings dialog and execute. If exception -> Create warning
        def onCalibOpen(self, x ,y, a, b, c, d, e, f):
            Calib_dlg = BODCODWindow(self, x, y, a, b, c, d, e, f)
            
            try:
                Calib_dlg.exec_()
            except Exception:
                error = QMessageBox.warning(self, 'Error!', 'Settings Failed to Open')
        
    #Closing Event
    def closeEvent(self, event):
        global serial_objects
        global threadEnded
        
        #Create QMessageBox Question
        exiting = QMessageBox.question(self, 'Exit Program', 'Are you sure you want to exit the program?', QMessageBox.Yes | QMessageBox.No)
        
        #If yes was selected
        if exiting == QMessageBox.Yes:
            
            #Create Waiting Dialog
            wait = QDialog()
            wait.setWindowTitle("Closing Application...")#
            width = 500
            height = 100
            wait.setFixedSize(width, height)
            wait.setWindowIcon(QtGui.QIcon(str(uis) + '/NRCLogo.ico'))
            
            #Set Wait text
            waitText = QLabel(wait)
            waitText.setGeometry(QRect(50, 30, 650, 200))
            waitText.setStyleSheet("font: Century Gothic")
            waitText.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
            waitText.setText("Please wait as your application automatically exits")
            
            #Show wait dialog
            wait.show()
            
            #Set all endFlags to true -> ie: stop thread flag
            for i in range(len(serial_objects)):
                endFlag[i] = True
            
            #Loop while threads haven't ended
            flag = True
            while flag == True:
                flag = False
                for i in range(len(serial_objects)):
                    if(threadEnded[i] == False):
                        flag = True
                #Pause UI for 1 second
                loop = QEventLoop()
                QTimer.singleShot(1000, loop.quit)
                loop.exec_()
            #Once all threads have ended -> Close oneself
            event.accept()
        #Any other input is ignored.
        else:
            if not type(event) == bool:
                event.ignore()

#Polarization Form Class
class PolarizationForm(QDialog):
    
    def __init__(self, channel, mode):
        global channel_params
        
        super().__init__(parent = None)
        #Load channel and mode to self
        self.channel = channel
        self.mode = mode
        
        #Load UI and UI objects
        uic.loadUi(resourcepath(str(uis) +'/polarizationForm.ui'),self)
        self.setWindowTitle("New Polarization Test for Channel " + str(self.channel+1))
        self.ocvRunTime = self.findChild(QSpinBox, 'ocvRunTime')
        self.resistorValues = self.findChild(QSpinBox, 'rows')
        self.ssTolerance = self.findChild(QSpinBox, 'ssTolerance')
        self.ssIterations = self.findChild(QSpinBox, 'ssIterations')
        self.alpha = self.findChild(QDoubleSpinBox, 'filterCoef')
        self.cancel = self.findChild(QPushButton, 'cancel')
        self.save = self.findChild(QPushButton, 'saveForm')
        
        #Set alpha to MCU parameters
        self.alpha.setValue(float(channel_params[channel][10]))
        
        #link buttons with methods
        self.cancel.clicked.connect(self.close)
        self.save.clicked.connect(self.savingForm)
        
    def savingForm(self):
        #Close form
        self.close()
        
        #Execute new polarization Table with the arguments( channel, mode, OCVRunTime, # of resistor values, SS tolerance, Iterations for SS, Alpha)
        polarization = PolarizationTable(self.channel, self.mode, self.ocvRunTime.value(), self.resistorValues.value(), self.ssTolerance.value(), self.ssIterations.value(), self.alpha.value())
        polarization.exec_()
        
        
#BODCOD Window for calibration display
class BODCODWindow(QDialog):
    
    def __init__(self, parent, channel, mode, r2_BOD, BOD_fit_eqn, BOD_fit_type, r2_COD, COD_fit_eqn, COD_fit_type):
        global dfs
        
        #Load UI
        super().__init__(parent)
        uic.loadUi(resourcepath(str(uis) +'/bodwindow.ui'),self)
        
        #Load objects to self objevts
        self.calibration = self.findChild(QTableView,'calibrationSettingsTable')
        self.regression = self.findChild(QTableWidget, 'regressionInfo')
        self.cancel = self.findChild(QPushButton, 'cancel')
        self.newCalib = self.findChild(QPushButton, 'newCalib')
        self.lastModified = self.findChild(QLabel, 'lastModified')
        
        if (channel == 0):
            info = BODCalibLocation_channel1.stat()
        elif (channel == 1):
            info = BODCalibLocation_channel2.stat()
        
        self.lastModified.setText("Last Modified: " + (self.convert_date(info.st_mtime)))
        #Create a new qt5 compatible model 
        model = PandasModel(dfs[channel])
        
        #Set model to qtableview and resize
        self.calibration.setModel(model)
        self.calibration.resizeColumnsToContents()
        
        #Populate table model and set up items
        for rows in range(model.rowCount()):
            self.calibration.setRowHeight(rows, int(251/model.rowCount()))
        
        #Add BOD/COD fits to table
        item = QTableWidgetItem(BOD_fit_eqn)
        item.setFlags(item.flags() ^ Qt.ItemIsEditable)
        self.regression.setItem(0, 0, item)
        
        item = QTableWidgetItem(str(r2_BOD))
        item.setFlags(item.flags() ^ Qt.ItemIsEditable)
        self.regression.setItem(0, 1, item)
        
        item = QTableWidgetItem(BOD_fit_type)
        item.setFlags(item.flags() ^ Qt.ItemIsEditable)
        self.regression.setItem(0, 2, item)
        
        item = QTableWidgetItem(COD_fit_eqn)
        item.setFlags(item.flags() ^ Qt.ItemIsEditable)
        self.regression.setItem(0, 3, item)
        
        item = QTableWidgetItem(str(r2_COD))
        item.setFlags(item.flags() ^ Qt.ItemIsEditable)
        self.regression.setItem(0, 4, item)
        
        item = QTableWidgetItem(COD_fit_type)
        item.setFlags(item.flags() ^ Qt.ItemIsEditable)
        self.regression.setItem(0, 5, item)
        
        #Set settings to table
        self.regression.horizontalHeader().setStretchLastSection(True)
        self.regression.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.regression.horizontalHeader().hide()
        
        #Attach the functions below to the buttons
        self.cancel.clicked.connect(self.close)
        self.newCalib.clicked.connect(lambda: self.showDialog(parent, channel))
    
    
    #Convert timestamp to date
    def convert_date(self, timestamp):
        d = datetime.datetime.fromtimestamp(timestamp)
        formated_date = d.strftime('%d %b %Y - %H:%M:%S' )
        return formated_date
    
    #Create a dialog that asks user how many rows they want for new calib table
    def showDialog(self,parent, channel):
        global dfs
        
        (calib_rows, calib_columns) = dfs[channel].shape
        
        calib_rows_new, ok = QInputDialog.getInt(self, 'New Calibration', 'Enter number of data points', int(calib_rows))
        
        if ok:
            try:
                if int(calib_rows_new)<4:
                    calib_rows_new = 4
                else:
                    calib_rows_new = int(calib_rows_new)
            except TypeError:
                calib_rows = calib_rows
                
            newCalib_dlg = newCalibTable(self, channel, calib_rows_new)
            self.close()
            try:
                newCalib_dlg.exec_()
            except Exception:
                error = QMessageBox.warning(self, 'Error!', 'Calibration Table Failed to Open')
                
        else:
            self.close()

#Create new Table according to above settings
class newCalibTable(QDialog):
    
    def __init__(self, parent, channel, calib_rows):
        global dfs
        global dfs_old
        global bod_cod_flag
        
        super().__init__()
        self.calib_columns = calib_columns = 5
        self.calib_rows = calib_rows
        self.channel = channel
        
        #Load UI and attach UI objects to self
        uic.loadUi(resourcepath(str(uis) +'/bodwindowTemp.ui'),self)
        self.newcalibration = self.findChild(QTableView,'newcalibrationSettings')
        self.bod_exponential = self.findChild(QCheckBox, 'bod_exponential')
        self.bod_linear = self.findChild(QCheckBox, 'bod_linear')
        self.bod_bod_polynomial = self.findChild(QCheckBox, 'bod_polynomial')
        self.cod_exponential = self.findChild(QCheckBox, 'cod_exponential')
        self.cod_linear = self.findChild(QCheckBox, 'cod_linear')
        self.cod_cod_polynomial = self.findChild(QCheckBox, 'cod_polynomial')

        
        self.save = self.findChild(QPushButton, 'save')
        self.cancel = self.findChild(QPushButton, 'cancel')
        

        #Create new Model, add headers and create rows depending on user selection
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['Average_Vmin(mV)', 'Average_Temperature(C)', 'BOD measured(mg/L)', 'COD measured(mg/L)'])
        for i in range(calib_rows):
            self.model.insertRow(i)
            
        #Set table to new model and resize
        self.newcalibration.setModel(self.model)
        self.newcalibration.resizeColumnsToContents()
        
        #Autopopulate with with a value of 2
        for i in range(calib_rows):
            for j in range(calib_columns-1):
                self.model.setItem(i,j, QStandardItem("2"))
        for rows in range(self.model.rowCount()):
            self.newcalibration.setRowHeight(rows, int(251/self.model.rowCount()))
        
        #Attach cancel with the close function and attach save with createDF function
        self.cancel.clicked.connect(self.close)
        self.save.clicked.connect(self.checkState)
        #self.save.clicked.connect(lambda: self.createDF(channel, calib_rows, calib_columns))
    
    def checkState(self):
        global bod_fits
        global cod_fits
        if (self.bod_exponential.isChecked() or self.bod_linear.isChecked() or self.bod_polynomial.isChecked()) and (self.cod_exponential.isChecked() or self.cod_linear.isChecked() or self.cod_polynomial.isChecked()):
            
            if self.bod_exponential.isChecked():
                bod_fits[self.channel][0] = True
            else:
                bod_fits[self.channel][0] = False
                
            if self.bod_linear.isChecked():
                bod_fits[self.channel][1] = True
            else:
                bod_fits[self.channel][1] = False
                
            if self.bod_polynomial.isChecked():
                bod_fits[self.channel][2] = True
            else:
                bod_fits[self.channel][2] = False
                
            if self.cod_exponential.isChecked():
                cod_fits[self.channel][0] = True
            else:
                cod_fits[self.channel][0] = False

            if self.cod_linear.isChecked():
                cod_fits[self.channel][1] = True
            else:
                cod_fits[self.channel][1] = False
                
            if self.cod_polynomial.isChecked():
                cod_fits[self.channel][2] = True
            else:
                cod_fits[self.channel][2] = False

            self.createDF(self.channel, self.calib_rows, self.calib_columns)
        
        else:
            error_Message = QMessageBox.warning(self, 'Error!', 'Make sure to select at least one fit type option for BOD and COD respectively.')

    
    #Creates a new dataFrame 
    def createDF(self,channel, calib_rows, calib_columns):
        global dfs
        global dfs_old

        #Initialize dataframe with columns
        dfs[channel] = pd.DataFrame(
            columns = ['S/N', 'Average_Vmin(mV)', 'Average_Temperature(C)', 'BOD measured(mg/L)', 'COD measured(mg/L)'],
            index = range(calib_rows)
            )
       
        #Append the dataframe with the table values
        for i in range(self.model.rowCount()):
            dfs[channel].iloc[i,0] = i+1
        
        for j in range(0, calib_columns-1):
            for i in range(0, self.model.rowCount()):
                if(float(self.model.item(i,j).text())) == 0 and not(j == 1): #If value = 0 and cols not equal to temp -> Autoadjust value to 0.1
                    dfs[channel].iloc[i, j+1] = 0.1
                else:   
                    dfs[channel].iloc[i,j+1] = float(self.model.item(i,j).text())
        
        #Set columns types
        dfs[channel]['S/N'] = dfs[channel]['S/N'].astype(int)
        dfs[channel]['Average_Vmin(mV)'] = dfs[channel]['Average_Vmin(mV)'].astype(float)
        dfs[channel]['Average_Temperature(C)'] = dfs[channel]['Average_Temperature(C)'].astype(float)
        dfs[channel]['BOD measured(mg/L)'] = dfs[channel]['BOD measured(mg/L)'].astype(float)
        dfs[channel]['COD measured(mg/L)'] = dfs[channel]['COD measured(mg/L)'].astype(float)
        
        #Save new dataframe as excel file in appropriate location
        if channel == 0:
            dfs[channel].to_csv(BODCalibLocation_channel1, index = False, header = True)
            dfs[channel] = pd.read_csv(BODCalibLocation_channel1)
        
        elif channel ==1:
            dfs[channel].to_csv(BODCalibLocation_channel2, index = False, header = True)
            dfs[channel] = pd.read_csv(BODCalibLocation_channel2)
        
        (calib_rows, calib_columns) = dfs[channel].shape
        
        #New Table created flag  set to true
        bod_cod_flag[channel] = True
        #Auto close after all operations
        self.close()
        
#Basic settings dialog
class BasicSettingsDialog(QDialog):
    
    def __init__(self, parent, channel, mode):
        global channel_params
        global serial_objects
        self.params = [0]*25

        
        super().__init__(parent)
        uic.loadUi(resourcepath(str(uis) +'/basicsettings.ui'),self) #Load UI
        self.mode = mode
        self.channel = channel
        self.parent = parent
        
        #Load UI objects to self
        self.saveSettingsBasic = self.findChild(QPushButton,'saveSettingsBasic')
        self.cancelBasic = self.findChild(QPushButton,'cancelBasic')
        self.advancedSettings = self.findChild(QPushButton,'advancedSettings')
        
        self.params[0] = self.findChild(QDoubleSpinBox,'minV')
        self.params[13] = self.findChild(QSpinBox,'timeInt')
        self.params[16] = self.findChild(QSpinBox,'rload')
        self.params[20] = self.findChild(QSpinBox,'deviceID')
        
        #Set text according to MCU settings
        self.params[0].setValue(float(channel_params[self.channel][0]))
        self.params[13].setValue(int(channel_params[self.channel][13]))
        self.params[16].setValue(int(channel_params[self.channel][16]))
        self.params[20].setValue(int(channel_params[self.channel][20]))
        
        #If time interval changes -> Check if acquisition rate is greater than 30secs
        self.params[13].valueChanged.connect(self.check_state)
        self.params[13].valueChanged.emit(self.timeInt.value())
        
        #Connect buttons with class methods   
        self.saveSettingsBasic.clicked.connect(lambda: self.save(self.channel, self.mode))
        self.cancelBasic.clicked.connect(self.close)
        self.advancedSettings.clicked.connect(self.openAdvancedSettingsDialog)
    
    #On Advanced Settings Open -> Load advanced settings dialog and execute. If exception -> Create warning
    def openAdvancedSettingsDialog(self, event):
        advanced = QMessageBox.question(self, 'Open Advanced Settings?', 'Are you sure you want to edit advanced settings?', QMessageBox.Yes | QMessageBox.No)
            
        if advanced == QMessageBox.Yes:
            if not type(event) == bool:
                event.accept()
            else:
                Adv_dlg = MainSettingsDialog(self.parent, self.channel,self.mode)
    
                try:
                    self.close()
                    Adv_dlg.exec_()
                except Exception:
                    error = QMessageBox.warning(self, 'Error!', 'Settings Failed to Open')
        else:
            if not type(event) == bool:
                event.ignore()
                
    #Check state, if interval last than 30secs, prevent saving    
    def check_state(self):
        try:
            if (self.timeInt.value()) < 30:
                error = QMessageBox.warning(self, 'Warning', 'Time interval cannot be less than 30 seconds!')
                self.saveSettingsBasic.setEnabled(False)
            else:
                self.saveSettingsBasic.setEnabled(True)
        except Exception:
            pass
    
    #Save into channel parameters and respective channel according to text
    def save(self, y, x):
        global channel_params
        global settingsFlag
        
        channel_params[y][0] = str(self.params[0].value())
        channel_params[y][13] = str(self.params[13].value())
        channel_params[y][16] = str(self.params[16].value())
        channel_params[y][20] = str(self.params[20].value())
        
        #Settings flag sets to true
        settingsFlag[y] = True
        
        #Set-up dataStructure
        writeTime=str(datetime.datetime.now())[:19] #get date and time program starts

        parameterLog = ''
        parameterLog += writeTime
        parameterLog += ' '
        for i in range(25):
            parameterLog += channel_params[y][i]
            parameterLog += '\t\t'
        parameterLog+='\n'
        
        #Write into file
        text = ''
        text += parameterLog
        writeIntoFile(y, x, False, text)
                        
        time.sleep(0.1)
        #Autoclose open finishing
        self.close()
        
class MainSettingsDialog(QDialog):
    
    def __init__(self, parent, mode, channel):
        global channel_params
        global serial_objects
        
        super().__init__(parent)
        uic.loadUi(resourcepath(str(uis) +'/settings1.ui'),self) #Load UI
        self.mode = mode
        self.channel = channel-1
        self.params = [0]*25
        self.parent = parent
        
        #Load UI objects into self -> Set validators
        self.params[0] = self.findChild(QDoubleSpinBox,'minV')
        self.params[1] = self.findChild(QDoubleSpinBox,'maxV')
        self.params[2] = self.findChild(QSpinBox,'ocSample')
        self.params[3] = self.findChild(QSpinBox,'ccSample')
        self.params[4] = self.findChild(QSpinBox,'ocMin')
        self.params[5] = self.findChild(QSpinBox,'ccMin')
        self.params[6] = self.findChild(QSpinBox,'ocMax')
        self.params[7] = self.findChild(QSpinBox,'ccMax')
        self.params[8] = self.findChild(QDoubleSpinBox,'ocFrac')
        self.params[9] = self.findChild(QDoubleSpinBox,'ccFrac')
        self.params[10] = self.findChild(QDoubleSpinBox,'alpha')
        self.params[11] = self.findChild(QDoubleSpinBox,'epsilon')
        self.params[12] = self.findChild(QSpinBox,'timeRef')
        self.params[13] = self.findChild(QSpinBox,'timeInt')
        self.params[14] = self.findChild(QSpinBox,'minTimeInt')
        self.params[15] = self.findChild(QSpinBox,'epsilonMaxCount')
        self.params[16] = self.findChild(QSpinBox,'rload')
        self.params[17] = self.findChild(QDoubleSpinBox,'calibRef')
        self.params[18] = self.findChild(QDoubleSpinBox,'calibZero')
        self.params[19] = self.findChild(QDoubleSpinBox,'calibMax')
        self.params[20] = self.findChild(QSpinBox,'deviceID')
        self.params[21] = self.findChild(QSpinBox,'loraEnabled')
        self.params[22] = self.findChild(QLineEdit,'devEUI')        
        self.params[23] = self.findChild(QLineEdit,'appEUI')        
        self.params[24] = self.findChild(QLineEdit,'appKey')        

        #Attach function to timeInterval 
        self.params[13].valueChanged.connect(self.check_state)
        self.params[13].valueChanged.emit(self.timeInt.value())
        
        #Load UI objects into self 
        self.saveSettings = self.findChild(QPushButton,'saveSettings')
        self.cancel = self.findChild(QPushButton,'cancel')
        
        #Populate table according to MCU settings
        for i in range(22):
            if (i == 0) or (i == 1) or (i == 8) or (i == 9) or (i == 10) or (i == 11) or (i == 17) or (i == 18) or (i == 19):
                self.params[i].setValue(float(channel_params[self.channel][i]))
            else:
                self.params[i].setValue(int(channel_params[self.channel][i]))
                
        for i in range(22, 25):
            self.params[i].setText(str(channel_params[self.channel][i]))
        
        self.loraCheck = self.params[21].value()
        #print(self.loraCheck)

        #Attach class methods to buttons
        self.saveSettings.clicked.connect(lambda: self.save(self.channel, self.mode))
        self.cancel.clicked.connect(self.close)

    #Check state, if interval last than 30secs, prevent saving
    
    def check_state(self):
        try:
            if (self.timeInt.value()) < 30:
                error = QMessageBox.warning(self, 'Warning', 'Time interval cannot be less than 30 seconds!')
                self.saveSettings.setEnabled(False)
            else:
                self.saveSettings.setEnabled(True)
        except Exception:
            pass
    
    #Save into channel parameters and respective channel
    def save(self, y, x):
        global channel_params
        global settingsFlag
        global loraStartUpCheck
        
        last_check = QMessageBox.question(self, 'Save', 'Are you sure you want to save settings?', QMessageBox.Yes | QMessageBox.No)
        
        if last_check == QMessageBox.Yes:
            #Set Channel parameters to user entries
            for i in range(22):
                channel_params[y][i] = str(self.params[i].value())
                
            for i in range(22, 25):
                channel_params[y][i] = (self.params[i].text())

            
            #Set save settings Flag to True
            settingsFlag[y] = True
            
            #Set up datastructure for file writing
            writeTime=str(datetime.datetime.now())[:19] #get date and time program starts
            
            parameterLog = ''
            parameterLog += writeTime
            parameterLog += ' '
            for i in range(22):
                parameterLog += self.params[i].text()
                parameterLog += '\t\t'
            parameterLog+='\n'
            
            #Write into file
            text = ''
            text += parameterLog
            writeIntoFile(y, x, False, text)
                            
            time.sleep(0.1)
            
            if self.loraCheck == 0 and self.params[21].value() == 1:
                warning = QMessageBox.warning(self, 'LORA Enabled', 'LORA has been enabled.\nPlease restart your device/biosensor to enable LORA connection.')
                self.parent.updateStatusBarSignal.emit(True, loraStartUpCheck[y])
            elif self.loraCheck == 1 and self.params[21].value() == 0:
                loraStartUpCheck[y] = False
                self.parent.updateStatusBarSignal.emit(False, loraStartUpCheck[y])

                
            #Autoclose
            self.close()
        else:
            self.close()

#GraphSettingsDialog Class
class GraphSettingsDialog(QDialog):
    
    def __init__(self, parent, channel, mode):
        super().__init__(parent)
        
        self.mode = mode
        self.channel = channel
        
        #Load a different UI depening on set mode
        if (self.mode == 0):
            uic.loadUi(resourcepath(str(uis) +'/graphSettingsTox.ui'),self)
            self.limits = [0] * 8
        
        elif (self.mode == 1):
            uic.loadUi(resourcepath(str(uis) +'/graphSettingsBodCod.ui'), self)
            self.limits = [0] * 10
            
            #Assign UI objects to self
            self.limits[8] = self.findChild(QLineEdit,'y_limit8')
            self.limits[8].setValidator(QIntValidator())
            self.limits[9] = self.findChild(QLineEdit,'y_limit9')
            self.limits[9].setValidator(QIntValidator())
            
            self.limits[8].setText(str(graphs_limits[self.channel][7]))
            self.limits[9].setText(str(graphs_limits[self.channel][8]))
        
        #Assign UI objects to self
        self.saveGraphSetting = self.findChild(QPushButton,'saveGraphSetting')
        self.exitGraphSetting = self.findChild(QPushButton,'exitGraphSetting')
        
        self.limits[0] = self.findChild(QLineEdit,'graphSpanInput')
        self.limits[0].setValidator(QDoubleValidator())
        self.limits[1] = self.findChild(QLineEdit,'y_limit1')
        self.limits[1].setValidator(QIntValidator())
        self.limits[2] = self.findChild(QLineEdit,'y_limit2')
        self.limits[2].setValidator(QIntValidator())
        self.limits[3] = self.findChild(QLineEdit,'y_limit3')
        self.limits[3].setValidator(QIntValidator())
        self.limits[4] = self.findChild(QLineEdit,'y_limit4')
        self.limits[4].setValidator(QIntValidator())
        self.limits[5] = self.findChild(QLineEdit,'y_limit5')
        self.limits[5].setValidator(QIntValidator())
        self.limits[6] = self.findChild(QLineEdit,'y_limit6')
        self.limits[6].setValidator(QIntValidator())
        self.limits[7] = self.findChild(QLineEdit,'y_limit7')
        self.limits[7].setValidator(QIntValidator())
        
        self.limits[0].setText(str(graphspan[self.channel]))
        
        #Set limits to user entries
        for i in range(1,8):
            self.limits[i].setText(str(graphs_limits[self.channel][i-1]))
            
        #Attach class methods to buttons
        self.exitGraphSetting.clicked.connect(self.close)
        self.saveGraphSetting.clicked.connect(lambda: self.saveGraphSettings(self.channel, self.mode))
    
    #Save graph settings
    def saveGraphSettings(self,y ,x):
        global graphs_limits
        global graphspan
        
        #WHEN limits = 0 -> Engage Default Behaviour -> Autofit Graphs.
                
        graphspan[y] = float(self.limits[0].text())
        for i in range(1, 8):
            graphs_limits[y][i-1] = int(self.limits[i].text())
        
        if (x == 1):
            graphs_limits[y][7] = int(self.limits[8].text())
            graphs_limits[y][8] = int(self.limits[9].text())
        
        self.close()
        
#Main class 
class Main(QMainWindow, Ui):
    
    def __init__(self):
        global ports
        global biosensor_ports
        global serial_objects
        global channel_selection
        global programstart
        global file_locations
        
        #Checkforbiosensorports
        CheckingforPorts()
        
        super().__init__()
        
        #If file directories aren't found -> Create them
        if not(data_dir_channel1.exists()):
            os.mkdir(data_dir_channel1)
    
        if not(data_dir_channel1_TOX.exists()):
            os.mkdir(data_dir_channel1_TOX)
            
        if not(data_dir_channel1_TOX_Configurations.exists()):
            os.mkdir(data_dir_channel1_TOX_Configurations)
            
        if not(data_dir_channel1_BODCOD.exists()):
            os.mkdir(data_dir_channel1_BODCOD)
            
        if not(data_dir_channel1_BODCOD_Configurations.exists()):
            os.mkdir(data_dir_channel1_BODCOD_Configurations)
            
        if not(data_dir_channel2.exists()):
            os.mkdir(data_dir_channel2)
        
        if not(data_dir_channel2_TOX.exists()):
            os.mkdir(data_dir_channel2_TOX)
            
        if not(data_dir_channel2_TOX_Configurations.exists()):
            os.mkdir(data_dir_channel2_TOX_Configurations)
            
        if not(data_dir_channel2_BODCOD.exists()):
            os.mkdir(data_dir_channel2_BODCOD)
            
        if not(data_dir_channel2_BODCOD_Configurations.exists()):
            os.mkdir(data_dir_channel2_BODCOD_Configurations)
        
        #If files not found -> Create them
        for i in range(len(file_locations)):
            headers = ''
            if not((file_locations[i]).is_file()):
                if (i == 0) or (i == 4):
                    headers = ('Date\t' +'\t\tBattery Voltage ' + '\tMinV\t ' + '\tMaxV\t ' + 'Temperature ' + '\t\tR1\t\t ' +  'R2\t\t' +
                                'Capacitance' + '\t\tRLoad'
                            )
                
                
                if (i == 1) or (i == 5) or  (i == 3) or (i ==7):  
                    headers  = ('Date\t\t' +' Min V ' + '\t\tMax V ' + '\tOC Sample Time ' + '\tCC Sample Time ' + '\tOC Min Time Limit ' +  ' CC Min Time Limit ' +
                                '\tOC Sample Time Max' + '\tCC Sample Time Max' + '\tOC FracV' + '\tCC FracV' +
                                '\tAlpha '+ '\tEpisilon ' + '\tTime Reference ' + '\tTime Interval ' + ' Min Time Interval' + ' Epsilon Max Count ' + '\tRLoad' +
                                ' CalibADCV Reference ' + ' CalibADC Zero ' + ' CalibADC Max ' + ' Device ID' + ' Acquisition Rate\n'
                                )
                
                if (i == 2) or (i == 6):
                    headers = ('Date\t' +'\t\tBattery Voltage ' + '\tMinV\t ' + '\tMaxV\t ' + 'Temperature ' + '\t\tR1\t\t ' +  'R2\t\t' +
                                'Capacitance' + '\t\tRLoad'
                            )
                    headers += '\t\tBODV'
                    headers += '\t\t\tCODV'
                    headers += '\t\tBOD r2'
                    headers += '\t\tBOD fit eqn'
                    headers += '\t\t\t\tBOD fit type'
                    headers += '\t\tCOD r2'
                    headers += '\t\t\t\t\tCOD fit eqn'
                    headers += '\t\t\tCOD fit type'
                    
                headers+='\n'
                try:
                    f = open (file_locations[i], "w+") #Creating file headers
                    f.write(headers)
                    f.close()
                except Exception:
                    print("Error opening log file")
        
        temp = ''
        temp += '0' + '\n'
        temp += '0' + '\n'
        
        if not (defaults.is_file()):
            try:
                f = open(defaults, "w+")
                f.write(temp)
                f.close()
            except Exception:
                print("Error opening default file")
    
        if not (channel1_TOX_Polarization.is_file()):
            try:
                f = open(channel1_TOX_Polarization, "w+")
                f.close()
            except Exception:
                print("Error opening polarization file")
                
        if not (channel1_BODCOD_Polarization.is_file()):
            try:
                f = open(channel1_BODCOD_Polarization, "w+")
                f.close()
            except Exception:
                print("Error opening polarization file")
            
        if not (channel2_TOX_Polarization.is_file()):
            try:
                f = open(channel2_TOX_Polarization, "w+")
                f.close()
            except Exception:
                print("Error opening polarization file")
                
        if not (channel2_BODCOD_Polarization.is_file()):
            try:
                f = open(channel2_BODCOD_Polarization, "w+")
                f.close()
            except Exception:
                print("Error opening polarization file")
        
        #If csv file not found -> Create them according to 2020 April-May Calibration 
        SN = [1,2,3,4,5,6]
        Average_Vmin = [413.8,478.8,317.2,470.6,497.7,60.13]
        Average_Temperature = [5.3,7.8,9.6,24.1,27.3,35.6]
        BOD_measured = [64.9,57.3,8.3,16,19,2]
        COD_measured = [169, 187, 52, 80, 80, 2]
        
        if not (BODCalibLocation_channel1.is_file()):
            datastruct = ('S/N' +',Average_Vmin(mV)' + ',Average_Temperature(C)' + ',BOD measured(mg/L)' +',COD measured(mg/L)')
            
            for i in range(len(SN)):
                datastruct += '\n'
                datastruct += str(SN[i])
                datastruct += ',' + str(Average_Vmin[i])
                datastruct += ',' + str(Average_Temperature[i])
                datastruct += ',' + str(BOD_measured[i])
                datastruct += ',' + str(COD_measured[i])
                
            try:
                f = open(BODCalibLocation_channel1, "w+")
                f.write(datastruct)
                f.close()
            except Exception:
                print("Error opening calibration file")
                
        if not (BODCalibType1.is_file()):
            datastruct = 'Exponential\nExponential'
            
            try:
                f = open (BODCalibType1, 'w+')
                f.write(datastruct)
                f.close()
            except Exception:
                print("Error opening calibration file")
            
        if not (BODCalibLocation_channel2.is_file()):
            datastruct = ('S/N' +',Average_Vmin(mV)' + ',Average_Temperature(C)' + ',BOD measured(mg/L)' +',COD measured(mg/L)')
            
            for i in range(len(SN)):
                datastruct += '\n'
                datastruct += str(SN[i])
                datastruct += ',' + str(Average_Vmin[i])
                datastruct += ',' + str(Average_Temperature[i])
                datastruct += ',' + str(BOD_measured[i])
                datastruct += ',' + str(COD_measured[i])
                
            try:
                f = open(BODCalibLocation_channel2, "w+")
                f.write(datastruct)
                f.close()
            except Exception:
                print("Error opening calibration file")
        
        if not (BODCalibType2.is_file()):
            datastruct = 'Exponential\nExponential'
            
            try:
                f = open (BODCalibType2, 'w+')
                f.write(datastruct)
                f.close()
            except Exception:
                print("Error opening calibration file")
                
        self.setupUi(self)    

if __name__ == "__main__":
    app = QApplication(sys.argv)
    if not (platform.system()== 'Linux'):
        app.setStyleSheet("QLabel{font-size: 10pt;}")
    app.setStyle("Fusion")
    M = Main()
    sys.exit(app.exec())
