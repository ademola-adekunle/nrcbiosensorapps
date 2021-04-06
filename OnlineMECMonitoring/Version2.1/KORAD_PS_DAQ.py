##time.sleep## For first run on this machine, please follow Steps 1 to 3. Preferably run Python IDLE 3.7.x
# Step 1: Make sure pyserial module is installed.
# Step 2: Open and run KoradCli.py
# Step 3: Open and run Koradserial.py

## Other details.
# Port open, close and flush are carried out by the wrapper module.
# Computer is automatically locked during remote control. No need to send command to lock.
# Port is released after a timeout of no command from the shell or once the program reaches EOL.
# Tested for one power supply as of March 17, 2021.

#IMPORTANT FOR I2C DEVICES -> DEVICE ADDRESS -> USE CONFIG PROGRAM IF NECESSARY
#TEMP_1 (Interior Temperature) : Address == 101
#TEMP_2 (Exterior Temperature) : Address == 102
#pH_1 : Address == 99


import sys, glob, serial, os
import serial.tools.list_ports

import PyQt5
from PyQt5 import QtWidgets, QtCore, QtGui, uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

import time, datetime
from koradserial import KoradSerial
from configparser import ConfigParser

import io
import re
import sys
import fcntl
import time
import copy
import string
from AtlasI2C import (
	 AtlasI2C
)

import matplotlib
matplotlib.use('QT5Agg',warn=False,force = True)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

#Used to find file path
import pathlib
from pathlib import Path

#Used to support threading
import threading
from threading import Thread

global dLogInterval, dAqInterval, dAqON, runPS, fileName, koradports, ports, polling, device_list, serialportsChanged

current = pathlib.Path().absolute()

#print(current)
#------------------------------------------------------------------------------#
# FUNCTIONS
#------------------------------------------------------------------------------#
def print_devices(device_list, device):
    for i in device_list:
        if(i == device):
            print(i)
            print(("--> " + i.get_device_info()).replace('\x00',''))
        else:
            print((" - " + i.get_device_info()).replace('\x00',''))
            
def get_devices():
    device = AtlasI2C()
    device_address_list = device.list_i2c_devices()
    device_list = []

    for i in device_address_list:
        device.set_i2c_address(i)
        response = device.query("i")
        
        # check if the device is an EZO device
        checkEzo = response.split(",")
        if len(checkEzo) > 0:
            if checkEzo[0].endswith("?I"):
                # yes - this is an EZO device
                moduletype = checkEzo[1]
                response = device.query("name,?").split(",")[1]
                device_list.append(AtlasI2C(address = i, moduletype = moduletype, name = response))
    return device_list


def INI_write(): # function to write an INI file
    global psVoltage, psCurrentMax, psVoltageMax, psVoltage2, psCurrentMax2, psVoltageMax2,runPS, dLogInterval, dAqInterval, dAqON, ovp_advset, ocp_advset, ocp_advset2, ovp_advset2, ps_outputStatus1, ps_outputStatus2, koradports, fileName, data_points_int
    cfgfile = open("INI/psSettings.ini",'w') #INI file creation. I would take this from the final code. This is just for the test
    parser = ConfigParser()
    parser.read("INI/psSettings.ini")

    parser.add_section('Settings')
    parser.set('Settings', 'psVoltage', str(psVoltage))
    parser.set('Settings', 'psCurrent', str(psCurrentMax))
    parser.set('Settings', 'userdefined_MaxPSVoltage', str(psVoltageMax))
    parser.set('Settings', 'psVoltage2', str(psVoltage2))
    parser.set('Settings', 'psCurrent2', str(psCurrentMax2))
    parser.set('Settings', 'userdefined_MaxPSVoltage2', str(psVoltageMax2))
    parser.set('Settings', 'runPS', str(runPS))
    parser.set('Settings', 'dLogInterval', str(dLogInterval))
    parser.set('Settings', 'dAqInterval', str(dAqInterval))
    parser.set('Settings', 'dAqON', str(dAqON))
    parser.set('Settings', 'datalog filename', fileName)
    #print(ovp_advset)
    parser.add_section('Advanced Settings')
    parser.set('Advanced Settings', 'Over Voltage Protection (OVP)', ovp_advset)
    parser.set('Advanced Settings', 'Over Current Protection (OCP)', ocp_advset)
    parser.set('Advanced Settings', 'Over Voltage Protection (OVP) 2', ovp_advset2)
    parser.set('Advanced Settings', 'Over Current Protection (OCP) 2', ocp_advset2)
    parser.set('Advanced Settings', 'PS OUTPUT 1', ps_outputStatus1)
    parser.set('Advanced Settings', 'PS OUTPUT 2', ps_outputStatus2)

    parser.add_section('COM Ports')
    try: # exception catch in case there are no COM ports recognized
        for i in range(len(koradports)):
            parser.set('COM Ports', 'Korad port #%i' %i, str(koradports[i]))

    except Exception:
        pass

    parser.add_section('Plot Settings')
    parser.set('Plot Settings', 'number of data points', str(data_points_int))

    with open("INI/psSettings.ini",'w') as configfile:
        parser.write(configfile)
    configfile.close()

def INI_read(): # function to read an INI file
    global ps, psVoltage, psCurrentMax, psVoltageMax, psVoltage2, psCurrentMax2, psVoltageMax2, runPS, dLogInterval, dAqInterval, dAqON, ocp_advset, ovp_advset, ocp_advset2, ovp_advset2, koradports, fileName, data_points_int
    #cfgfile = open("INI/psSettings.ini",'r') #INI file creation. I would take this from the final code. This is just for the test
    parser = ConfigParser()
    parser.read("INI/psSettings.ini")

    # Acquiring the values from the INI file
    psVoltage = float(parser.get("Settings", 'psVoltage'))
    psCurrentMax = float(parser.get("Settings", 'psCurrent'))
    psVoltageMax = float(parser.get("Settings", 'userdefined_MaxPSVoltage'))
    psVoltage2 = float(parser.get("Settings", 'psVoltage2'))
    psCurrentMax2 = float(parser.get("Settings", 'psCurrent2'))
    psVoltageMax2 = float(parser.get("Settings", 'userdefined_MaxPSVoltage2'))
    runPS = bool(parser.get("Settings", 'runPS'))
    dLogInterval = float(parser.get("Settings", 'dLogInterval'))
    dAqInterval = float(parser.get("Settings", 'dAqInterval'))
    dAqON = bool(parser.get("Settings", 'dAqON'))
    fileName = parser.get("Settings", 'datalog filename')

    ovp_advset = parser.get("Advanced Settings", 'Over Voltage Protection (OVP)')
    ocp_advset = parser.get("Advanced Settings", 'Over Current Protection (OCP)')
    ovp_advset2 = parser.get("Advanced Settings", 'Over Voltage Protection (OVP) 2')
    ocp_advset2 = parser.get("Advanced Settings", 'Over Current Protection (OCP) 2')
    ps_outputStatus1 = parser.get('Advanced Settings','PS OUTPUT 1')
    ps_outputStatus2 = parser.get('Advanced Settings','PS OUTPUT 2')

    try:
        for i in range(len(koradports)):
            koradports.append(parser.get("COM Ports", 'Korad Port #%i' %i))

    except Exception:
        pass

    data_points_int = int(parser.get("Plot Settings", 'number of data points'))


def PS_writeDevice(channel):
    global dev1, dev2
    global psVoltage, psCurrentMax, ocp_advset, ovp_advset
    global psVoltage2, psCurrentMax2, ocp_advset2, ovp_advset2
    
    #if (channel == 1) and not (dev1 == ''):
    if (channel == 1):
        PS = KoradSerial(dev1)
        test = PS.channels[0].output_voltage
        PS.channels[0].voltage = psVoltage
        PS.channels[0].current = psCurrentMax
        
        if ovp_advset == 'on':
            PS.over_voltage_protection.on()

        else:
            PS.over_voltage_protection.off()

        if ocp_advset == 'on':
            PS.over_current_protection.on()

        else:
            PS.over_current_protection.off()
        
    #elif (channel == 2) and not (dev2 == ''):
    elif (channel == 2):
        PS = KoradSerial(dev2)
        test = PS.channels[0].output_voltage
        PS.channels[0].voltage = psVoltage2
        PS.channels[0].current = psCurrentMax2
        
        if ovp_advset2 == 'on':
            PS.over_voltage_protection.on()

        else:
            PS.over_voltage_protection.off()

        if ocp_advset2 == 'on':
            PS.over_current_protection.on()

        else:
            PS.over_current_protection.off()
    
def PS_read():
    global psCurrentOut, psVoltageOut, psStatus
    psCurrentOut = ps.channels[0].output_current * 1000 # retrieve current outputted by PS
    psVoltageOut = ps.channels[0].output_voltage # retrieve volrage outputted by PS
    #psStatus = ps.status.channel1 # retrieve the CC/CV status of the PS

def get_datalog():
    global fileName

    if not os.path.exists("Data_Logs"):
        os.makedirs("Data_Logs")

    if not os.path.exists('Data_Logs/%s' %fileName): # For a new file, the headers are added as the first line
        log = open('Data_Logs/%s' %fileName, "a")
        headers = ['Date', 'Vps_1', 'Ips_1', 'Vps_2', 'Ips_2', 'Temp(Interior)', 'Temp(Exterior)', 'pH']
        headers = ' '.join(headers)
        log.write(headers +'\n') # write headers to file
        log.close()

    log = open('Data_Logs/%s' %fileName, "a")

    return log
#------------------------------------------------------------------------------#
# START-UP ACTIONS
#------------------------------------------------------------------------------#
global ports, koradports, ovp_advset, ocp_advset, data_points_int, runPS
# Creating a folder for the INI file (startup)
if sys.platform.startswith('win'): # if the operating system is windows
    if not os.path.exists(r"C:\KORAD_PS_DAQ"): # and there's no directory folder
        os.makedirs(r"C:\KORAD_PS_DAQ")

    os.chdir(r"C:\KORAD_PS_DAQ")

    if not os.path.exists("INI"):
        os.makedirs("INI")

    if not os.path.exists("UI_Files"):
        os.makedirs("UI_Files")

elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'): # if the operating system is linux
    if not os.path.exists(str(current)+"/KORAD_PS_DAQ"): # and there's no directory folder
        os.makedirs(str(current) + "/KORAD_PS_DAQ")

    os.chdir(str(current)+"/KORAD_PS_DAQ")
    
    if not os.path.exists("INI"):
        os.makedirs("INI")

    if not os.path.exists("UI_Files"):
        os.makedirs("UI_Files")

if not os.path.exists("INI/psSettings.ini"):
    psVoltage = 1.4
    psCurrentMax = 2.0
    psVoltageMax = 20.0
    psVoltage2 = 1.4
    psCurrentMax2 = 2.0
    psVoltageMax2 = 20.0
    dLogInterval = 1.0
    dAqInterval = 1.0
    runPS = False
    dAqON = False
    fileName = 'DataLoggingFile.txt'
    ocp_advset = 'off'
    ovp_advset = 'on'
    ocp_advset2 = 'off'
    ovp_advset2 = 'on'
    ps_outputStatus1 = False
    ps_outputStatus2 = False
    data_points_int = 100
    INI_write() # makes INI file with these standard initial conditions

INI_read()

ports = serial.tools.list_ports.comports() 
koradports = []
koradserials = []
serial_ports = []
dev1 = ''
dev2 = ''
startAcquisition = False
startLogs = False

log = get_datalog() # makes datalog file on first run
log.close() # get_datalog returns opened data log file, closed here

#------------------------------------------------------------------------------#
# GRAPH
#------------------------------------------------------------------------------#
class MplCanvas(FigureCanvas): #PYQT5 Compatible Canvas for matplotlib (Used for main graphs)
    
    def __init__(self, parent=None, width = 4.5, height = 3.3, dpi = 100):
        self.fig = Figure (figsize=(width,height),dpi = dpi, tight_layout=True)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas,self).__init__(self.fig)
        
        
#------------------------------------------------------------------------------#
# DIALOG - No Korad Device Detected
#------------------------------------------------------------------------------#
class NoKoradDetected(QDialog):
    def __init__(self, parent):
        global autoContinueorSelection
        super().__init__(parent)
        
        uic.loadUi("UI_Files/NoKoradDetectedDialog.ui",self)
        self.setWindowIcon(QIcon("/TEST.png"))
        autoContinueorSelection = False
        self.confirm_continue.clicked.connect(self.confirm)
        self.cancel.clicked.connect(self.stop)
        
        self.time = 10
        self.continueTimer = QTimer()
        self.continueTimer.timeout.connect(self.update_button)
        self.continueTimer.start(1000)
        
    def update_button(self):
        self.time -= 1
        self.confirm_continue.setText("Confirm (continues in " + str(self.time) + "s)")
        self.timingLabel.setText("If there is no user selection within " + str(self.time) + "s, polling will be automatically confirmed.")
        
        if self.time == 0:
            self.continueTimer.stop()
            self.confirm_continue.click()
    
    def confirm(self):
        global autoContinueorSelection, dAqON
        
        autoContinueorSelection = True
        dAqON = True
        self.close()
    
    def stop(self):
        global dAqOn
        
        dAqOn = False
        self.close()
#------------------------------------------------------------------------------#
# DIALOG
#------------------------------------------------------------------------------#
class AdvSettings(QDialog):

    def __init__(self, *args, **kwargs):
        super(AdvSettings, self).__init__(*args, **kwargs)
        uic.loadUi("UI_Files/AdvSettings_v2-2a.ui", self)
        self.setWindowIcon(QtGui.QIcon("MECMonitoringIcon.jpeg"))
        self.setWindowTitle(u"Advanced PS 1 Settings")
        
        self.setvoltageDisplay.setText(str(psVoltage))
        self.maxvoltageDisplay.setText(str(psVoltageMax))
        self.maxcurrentDisplay.setText(str(psCurrentMax))

        self.setvoltageDisplay.setStyleSheet('background-color: lightgray')
        self.maxvoltageDisplay.setStyleSheet('background-color: lightgray')
        self.maxcurrentDisplay.setStyleSheet('background-color: lightgray')
        
        self.ocpCheckBox.setEnabled(False)
        self.ovpCheckBox.setEnabled(False)
        self.ovpCheckBox.stateChanged.connect(self.ovp_state_changed)
        self.ocpCheckBox.stateChanged.connect(self.ocp_state_changed)
        
        self.settingsEditButton.clicked.connect(self.editingsettings)
        self.advsetButtonBox.accepted.connect(self.save)
        self.advsetButtonBox.rejected.connect(self.reject)

    def ovp_state_changed(self):
        if self.ovpCheckBox.isChecked() == True:
            self.ocpCheckBox.setChecked(False)
            self.ocpCheckBox.setEnabled(False)

        else:
            self.ocpCheckBox.setEnabled(True)

    def ocp_state_changed(self):
        if self.ocpCheckBox.isChecked() == True:
            self.ovpCheckBox.setChecked(False)
            self.ovpCheckBox.setEnabled(False)

        else:
            self.ovpCheckBox.setEnabled(True)

    def editingsettings(self):
        global is_editing_setvals 
        is_editing_setvals = True

        displayfont = self.setvoltageDisplay.font()
        displayfont.setPointSize(10)

        self.setvoltageDisplay.setReadOnly(False)
        self.setvoltageDisplay.setStyleSheet("background-color: white")
        self.setvoltageDisplay.setFont(displayfont)
        self.maxvoltageDisplay.setReadOnly(False)
        self.maxvoltageDisplay.setStyleSheet("background-color: white")
        self.maxvoltageDisplay.setFont(displayfont)
        self.maxcurrentDisplay.setReadOnly(False)
        self.maxcurrentDisplay.setStyleSheet("background-color: white")
        self.maxcurrentDisplay.setFont(displayfont)
        
        if ovp_advset == 'on':
            self.ovpCheckBox.setEnabled(True)
        elif ocp_advset =='on':
            self.ocpCheckBox.setEnabled(True)
        else:
            self.ovpCheckBox.setEnabled(True)
            self.ocpCheckBox.setEnabled(True)
            
    def save(self):
        global is_editing_setvals, dev1, settingsSaved1, psVoltageMax, psVoltage, psCurrentMax, ovp_advset, ocp_advset

        if is_editing_setvals == False:
            pass
        elif float(self.setvoltageDisplay.text()) > float(psVoltageMax):
            error = QMessageBox.warning(self, 'Max voltage less than set voltage', 'Error: The set voltage must not be greater than the max voltage!')
        else:
            is_editing_setvals = False

            displayfont = self.setvoltageDisplay.font()
            displayfont.setPointSize(10)

            self.setvoltageDisplay.setReadOnly(True)
            self.setvoltageDisplay.setStyleSheet("background-color: lightgray")
            self.setvoltageDisplay.setFont(displayfont)
            
            self.maxvoltageDisplay.setReadOnly(True)
            self.maxvoltageDisplay.setStyleSheet("background-color: lightgray")
            self.maxvoltageDisplay.setFont(displayfont)
            self.maxcurrentDisplay.setReadOnly(True)
            self.maxcurrentDisplay.setStyleSheet("background-color: lightgray")
            self.maxcurrentDisplay.setFont(displayfont)
            
            psVoltage = float(self.setvoltageDisplay.text())
            psVoltageMax = float(self.maxvoltageDisplay.text())
            psCurrentMax = float(self.maxcurrentDisplay.text())
            
            if self.ovpCheckBox.isChecked() == True:
                ovp_advset = 'on'
                ocp_advset = 'off'

            elif self.ocpCheckBox.isChecked() == True:
                ovp_advset = 'off'
                ocp_advset = 'on'

            else:
                ovp_advset = 'off'
                ocp_advset = 'off'
            
            INI_write()
            
            settingsSaved1 = True
            
            self.close()

class AdvSettings2(QDialog):

    def __init__(self, *args, **kwargs):
        super(AdvSettings2, self).__init__(*args, **kwargs)
        uic.loadUi("UI_Files/AdvSettings_v2-2b.ui", self)
        self.setWindowIcon(QtGui.QIcon("MECMonitoringIcon.jpeg"))
        self.setWindowTitle(u"Advanced PS 2 Settings")
        
        self.setvoltageDisplay.setText(str(psVoltage2))
        self.maxvoltageDisplay.setText(str(psVoltageMax2))
        self.maxcurrentDisplay.setText(str(psCurrentMax2))

        self.setvoltageDisplay.setStyleSheet('background-color: lightgray')
        self.maxvoltageDisplay.setStyleSheet('background-color: lightgray')
        self.maxcurrentDisplay.setStyleSheet('background-color: lightgray')
        
        self.ocpCheckBox.setEnabled(False)
        self.ovpCheckBox.setEnabled(False)
        self.ovpCheckBox.stateChanged.connect(self.ovp_state_changed)
        self.ocpCheckBox.stateChanged.connect(self.ocp_state_changed)
        
        self.settingsEditButton.clicked.connect(self.editingsettings)
        self.advsetButtonBox.accepted.connect(self.save)
        self.advsetButtonBox.rejected.connect(self.reject)

    def ovp_state_changed(self):
        if self.ovpCheckBox.isChecked() == True:
            self.ocpCheckBox.setChecked(False)
            self.ocpCheckBox.setEnabled(False)

        else:
            self.ocpCheckBox.setEnabled(True)

    def ocp_state_changed(self):
        if self.ocpCheckBox.isChecked() == True:
            self.ovpCheckBox.setChecked(False)
            self.ovpCheckBox.setEnabled(False)

        else:
            self.ovpCheckBox.setEnabled(True)

    def editingsettings(self):
        global is_editing_setvals2 
        is_editing_setvals2 = True

        displayfont = self.setvoltageDisplay.font()
        displayfont.setPointSize(10)

        self.setvoltageDisplay.setReadOnly(False)
        self.setvoltageDisplay.setStyleSheet("background-color: white")
        self.setvoltageDisplay.setFont(displayfont)
        self.maxvoltageDisplay.setReadOnly(False)
        self.maxvoltageDisplay.setStyleSheet("background-color: white")
        self.maxvoltageDisplay.setFont(displayfont)
        self.maxcurrentDisplay.setReadOnly(False)
        self.maxcurrentDisplay.setStyleSheet("background-color: white")
        self.maxcurrentDisplay.setFont(displayfont)
        
        if ovp_advset2 == 'on':
            self.ovpCheckBox.setEnabled(True)
        elif ocp_advset2 =='on':
            self.ocpCheckBox.setEnabled(True)
        else:
            self.ovpCheckBox.setEnabled(True)
            self.ocpCheckBox.setEnabled(True)
            
    def save(self):
        global is_editing_setvals2, dev2, settingsSaved2, psVoltageMax2, psVoltage2, psCurrentMax2, ovp_advset2, ocp_advset2

        if is_editing_setvals2 == False:
            pass
        elif float(self.setvoltageDisplay.text()) > float(psVoltageMax2):
            error = QMessageBox.warning(self, 'Max voltage less than set voltage', 'Error: The set voltage must not be greater than the max voltage!')
        else:
            is_editing_setvals2 = False

            displayfont = self.setvoltageDisplay.font()
            displayfont.setPointSize(10)

            self.setvoltageDisplay.setReadOnly(True)
            self.setvoltageDisplay.setStyleSheet("background-color: lightgray")
            self.setvoltageDisplay.setFont(displayfont)
            
            self.maxvoltageDisplay.setReadOnly(True)
            self.maxvoltageDisplay.setStyleSheet("background-color: lightgray")
            self.maxvoltageDisplay.setFont(displayfont)
            self.maxcurrentDisplay.setReadOnly(True)
            self.maxcurrentDisplay.setStyleSheet("background-color: lightgray")
            self.maxcurrentDisplay.setFont(displayfont)
            
            psVoltage2 = float(self.setvoltageDisplay.text())
            psVoltageMax2 = float(self.maxvoltageDisplay.text())
            psCurrentMax2 = float(self.maxcurrentDisplay.text())
            
            if self.ovpCheckBox.isChecked() == True:
                ovp_advset2 = 'on'
                ocp_advset2 = 'off'

            elif self.ocpCheckBox.isChecked() == True:
                ovp_advset2 = 'off'
                ocp_advset2 = 'on'

            else:
                ovp_advset2 = 'off'
                ocp_advset2 = 'off'
            
            INI_write()
            
            settingsSaved2 = True
            
            self.close()
            
class DataLogSettings(QDialog):

    def __init__(self, *args, **kwargs):
        super(DataLogSettings, self).__init__(*args, **kwargs)
        uic.loadUi("UI_Files/DataLogSettings_v2-1.ui", self)
        self.setWindowIcon(QtGui.QIcon("MECMonitoringIcon.jpeg"))
        self.setWindowTitle('Data Log Settings')

        dispfileName = fileName.split('.txt') # gets the file ready to show without the .txt ending

        self.filenameLineEdit.setText(dispfileName[0])
        self.intervalLineEdit.setText(str(dLogInterval))
        self.aqintervalLineEdit.setText(str(dAqInterval))

class PlotSettings(QDialog):

    def __init__(self, *args, **kwargs):
        super(PlotSettings, self).__init__(*args, **kwargs)
        self.setWindowIcon(QtGui.QIcon("MECMonitoringIcon.jpeg"))
        self.setWindowTitle('Plot Settings')
        self.setModal(True)
        QBtn = QDialogButtonBox.Ok

        self.buttonbox = QDialogButtonBox(QBtn)
        self.buttonbox.accepted.connect(self.accept)

        self.textlayout = QHBoxLayout()
        self.datapointsLabel = QLabel('# of visible data points on the plot:')
        self.datapointsLineEdit = QLineEdit(self)
        self.datapointsLineEdit.setText(str(data_points_int))

        self.textlayout.addWidget(self.datapointsLabel)
        self.textlayout.addWidget(self.datapointsLineEdit)

        self.layout = QVBoxLayout()
        self.layout.addLayout(self.textlayout)
        #self.layout.addWidget(self.y1ComboBox)
        #self.layout.addWidget(self.y2ComboBox)
        self.layout.addWidget(self.buttonbox)
        self.setLayout(self.layout)

class StartUpDelay(QDialog): # OK Button needs removing for final program
    
    def __init__(self, *args, **kwargs):
        super(StartUpDelay, self).__init__(*args, **kwargs)

        self.setWindowTitle("Initializing program...")
        self.setWindowIcon(QtGui.QIcon("MECMonitoringIcon.jpeg"))
        QBtn = QDialogButtonBox.Ok

        self.buttonbox = QDialogButtonBox(QBtn)
        self.buttonbox.accepted.connect(self.acceptStart)

        self.delaytimerDisplay = QLabel()
        self.delaytimer = QtCore.QTimer(self)
        self.delaytimer.setInterval(1000)
        self.delaytimer.timeout.connect(self.delay_timeout)

        self.progressbar = QProgressBar(self)
        self.progressbar.setMaximum(15)
        self.progressbar.setTextVisible(False) # removes percentage, redundant w timer

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.delaytimerDisplay)
        self.layout.addWidget(self.progressbar)
        self.layout.addWidget(self.buttonbox)
        self.setLayout(self.layout)

        self.delay_start()
        self.update_gui()
    
    def acceptStart(self):
        global mainWindow, dAqON
        
        self.close()
        
        mainWindow.show()
        if dAqON == True:
            mainWindow.startButton.click()

    def delay_start(self):
        self.delaytimeleft = 0
        self.delaytimer.start()
        self.update_gui()

    def delay_timeout(self):
        global mainWindow, dAqON
        self.delaytimeleft += 1
        self.progressbar.setValue(self.delaytimeleft)

        if self.delaytimeleft == 15:
            self.delaytimerDisplay.setText('Initializing program...')
            #time.sleep(1)
            self.delaytimer.stop()
            self.close()
            
            mainWindow.show()
            if dAqON == True:
                mainWindow.startButton.click()

        self.update_gui()
        
    def update_gui(self):
        if self.delaytimeleft == 14:
            self.delaytimerDisplay.setText('Please wait 1 second before using the program.')
        else:
            self.delaytimerDisplay.setText('Please wait %s seconds before using the program.' %str(15 - self.delaytimeleft))
            
#------------------------------------------------------------------------------#
# MAIN WINDOW
#------------------------------------------------------------------------------#
class MainWindow(QMainWindow):
    global ps, psVoltage, psCurrentMax, psVoltageMax, psStatus, polling
    #(Text)
    update_Temp1Signal = pyqtSignal(str)
    #(Text)
    update_Temp2Signal = pyqtSignal(str)
    #(Text)
    update_pHSignal = pyqtSignal(str)
    

    def __init__(self, *args, **kwargs):
        global is_editing_setvals, is_editing_setvals2, y1_label, y2_label, ports, koradports, serial_ports, settingsSaved1, settingsSaved2, dAqON
        super(MainWindow, self).__init__(*args, **kwargs)
        uic.loadUi("UI_Files/RPi_GUI_v1-12.ui", self)

        polling = False
        #self.setWindowIcon(QIcon(r"Icon_Store\icons\lightning.png"))
        self.setWindowTitle('KORAD PS DAQ')
        self.setWindowIcon(QtGui.QIcon("NRCLogo.png"))
        self.tempDisplay1 = self.findChild(QLineEdit,"tempDisplay1")
        self.tempDisplay2 = self.findChild(QLineEdit,"tempDisplay2")
        self.pHDisplay = self.findChild(QLineEdit,"pHDisplay")
        
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1000) # Timer counts down one second
        self.timer.timeout.connect(self.on_timeout)
        self.first_timer_start = True # for start_time assignment check in timer_start

        self.onlineDisplay.textChanged.connect(self.check_onlineDisplay)
        self.onlineDisplay.setText('DATA LOGGING AND POLLING STOPPED') # sets onlineDisplay's default to say it's offline

        self.setvoltageDisplay.setText(str(psVoltage))
        self.setvoltageDisplay.setStyleSheet('background-color: lightgray; font-weight: normal')
        
        self.setvoltageDisplay2.setText(str(psVoltage2))
        self.setvoltageDisplay2.setStyleSheet('background-color: lightgray; font-weight: normal')

        is_editing_setvals = False
        settingsSaved1 = False
        self.settingsEditButton.clicked.connect(self.on_setEdit_button_clicked)
        self.settingsOKButton.clicked.connect(self.on_setOK_button_clicked)
        self.advsetButton.clicked.connect(self.on_advset_button_clicked)
        
        is_editing_setvals2 = False
        settingsSaved2 = False
        self.settingsEditButton2.clicked.connect(self.on_setEdit_button_clicked2)
        self.settingsOKButton2.clicked.connect(self.on_setOK_button_clicked2)
        self.advsetButton2.clicked.connect(self.on_advset_button_clicked2)

        self.datalogButton.clicked.connect(self.on_datalog_button_clicked)
        self.plotsetButton.clicked.connect(self.on_plotset_button_clicked)

        self.startButton.setText('START')
        self.startButton.clicked.connect(self.on_start_button_clicked)
        

        self.statusbar.setStyleSheet('background-color: lightgray; font:italic;')
        
        # initialising the x and y plotting variables (1 = left axis, 2 = right axis)
        self.xplot = []
        self.xplot2 = []
        self.y1plot = []
        self.y2plot = []
        self.y3plot = []
        self.y4plot = []
        self.currentSave = []
        self.voltageSave = []
        self.currentSave2 = []
        self.voltageSave2 = []
        self.currentPlot = []
        self.voltagePlot = []
        self.temp1x = []
        self.temp1Plot = []
        self.temp2x = []
        self.temp2Plot = []
        self.pHx = []
        self.pHPlot = []
        
        self.graphArea = self.findChild(QScrollArea, 'graphingArea')
        
        #Create a scrollable graph area content storage area and intialize empty plots there
        self.contents = QWidget()
        self.store = QVBoxLayout()
        
        self.graph1a = MplCanvas(self,width = 4.5, height = 3.3, dpi =100)
        self.graph1a.axes.set_title("Voltage", fontweight = 'bold')
        self.graph1a.axes.set_xlabel("Time recorded", fontweight = 'bold')
        self.graph1a.axes.set_ylabel('Voltage 1(V)', fontweight = 'bold')
        self.axes1a = self.graph1a.axes.twinx() #Creates a two axes plot
        self.axes1a.set_ylabel('Voltage 2 (V)', fontweight = 'bold')
        self.graph1a.setMinimumSize(self.graph1a.size()) #forces plots to be a uniform size
        self.store.addWidget(self.graph1a) #Add to scrollable content area
        
        self.graph1b = MplCanvas(self,width = 4.5, height = 3.3, dpi =100)
        self.graph1b.axes.set_title("Current", fontweight = 'bold')
        self.graph1b.axes.set_xlabel("Time recorded", fontweight = 'bold')
        self.graph1b.axes.set_ylabel('Current 1 (mA)', fontweight = 'bold')
        self.axes1b = self.graph1b.axes.twinx() #Creates a two axes plot
        self.axes1b.set_ylabel('Current 2 (mA)', fontweight = 'bold')
        self.graph1b.setMinimumSize(self.graph1a.size()) #forces plots to be a uniform size
        self.store.addWidget(self.graph1b) #Add to scrollable content area
        
        self.graph2 = MplCanvas(self,width = 4.5, height = 3.3, dpi =100)
        self.graph2.axes.set_title("Temp$_\mathbf{internal}$ and Temp$_\mathbf{external}$", fontweight = 'bold')
        self.graph2.axes.set_xlabel("Time recorded", fontweight = 'bold')
        self.graph2.axes.set_ylabel('Temp$_\mathbf{internal}$ (C)', fontweight = 'bold')
        self.axes2 = self.graph2.axes.twinx() #Creates a two axes plot
        self.axes2.set_ylabel('Temp$_\mathbf{external}$ (C)', fontweight = 'bold')
        self.graph2.setMinimumSize(self.graph1a.size()) #forces plots to be a uniform size
        self.store.addWidget(self.graph2)
        
        self.graph3 = MplCanvas(self,width = 4.5, height = 3.3, dpi =100)
        self.graph3.axes.set_title("pH", fontweight = 'bold')
        self.graph3.axes.set_xlabel("Time recorded", fontweight = 'bold')
        self.graph3.axes.set_ylabel('pH', fontweight = 'bold')
        self.graph3.setMinimumSize(self.graph1a.size()) #forces plots to be a uniform size
        self.store.addWidget(self.graph3)
        
        self.contents.setLayout(self.store)
        self.graphArea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.graphArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphArea.setWidgetResizable(True)
        self.graphArea.setWidget(self.contents)
        
        self.runcheckDevices()
        self.runMainThread()
        
        self.update_Temp1Signal.connect(self.update_Temp1)
        self.update_Temp2Signal.connect(self.update_Temp2)
        self.update_pHSignal.connect(self.update_pH)
        
    @QtCore.pyqtSlot(str)
    def update_Temp1(self, temp):
        self.tempDisplay1.setText(temp)
        self.tempDisplay1.setReadOnly(True)
        
    @QtCore.pyqtSlot(str)
    def update_Temp2(self, temp):
        self.tempDisplay2.setText(temp)
        self.tempDisplay2.setReadOnly(True)
        
    @QtCore.pyqtSlot(str)
    def update_pH(self, pH):
        self.pHDisplay.setText(pH)
        self.pHDisplay.setReadOnly(True)
    
    def runcheckDevices(self):
        global serialportsChanged
        
        serialportsChanged = False
        
        tCheckDev = threading.Thread(target= self.checkDevices)
        tCheckDev.daemon = True
        tCheckDev.start()
    
    def checkDevices(self):
        global koradports, serial_ports, serial_ports_temp, dev1, dev2, serialportsChanged
        serial_ports = []
        while True:
            test_ports = serial.tools.list_ports.comports()
            serial_ports_temp = []
            
            for i in range(len(test_ports)):
                flag = True
                if test_ports[i].device == '/dev/ttyAMA0': # this is the serial port connected to the RPi's bluetooth
                    pass # skips it
                else:
                    """
                    try:
                        #print(test_ports[i].device)
                        tempPS = KoradSerial(test_ports[i].device)
                        psCurrentOut = tempPS.channels[0].output_current * 1000
                    except Exception:
                        flag = False
                    if flag == True:
                        serial_ports.append(str(test_ports[i].device))
                    """
                    serial_ports_temp.append(str(test_ports[i].device))
            if not set(serial_ports_temp) == set(serial_ports):
                serialportsChanged = True
                serial_ports = serial_ports_temp
            """
            if not dev1 == '':
                try:
                    tempPS = KoradSerial(dev1)
                    tempPS.output.on()
                    psCurrentOut = tempPS.channels[0].output_current * 1000
                except Exception:
                    dev1 = ''
                    
            if not dev2 =='':
                try:
                    tempPS = KoradSerial(dev2)
                    tempPS.output.on()
                    psCurrentOut = tempPS.channels[0].output_current * 1000
                except Exception:
                    dev2 = ''
                    
            for i in range(len(koradports)):
                if dev1 == '' and not (dev2 == koradports[i]):
                    dev1 = koradports[i]
                    #PS SETTINGS ARE SET HERE

                if dev2 == '' and not (dev1 == koradports[i]):
                    dev2 = koradports[i]
                    #PS SETTINGS ARE SET HERE
            """
            time.sleep(1)
            
    def runMainThread(self):    
        tMainThread = threading.Thread(target= self.mainThread)
        tMainThread.daemon = True
        tMainThread.start()
    
    def mainThread(self):
        global koradports, psAval, serialportsChanged, serial_ports
        global dev1, dev2
        global startAcquisition
        global startLogs
        global device_list
        global settingsSaved1, settingsSaved2, psVoltage, psVoltage2
        
        while True:
            device_list = get_devices()
            
            #if serialportsChanged:
            koradports = []
            check = True
            for i in range (len(serial_ports)):
            
                flag = True
                try:
                    tempPS = KoradSerial(serial_ports[i])
                    tempPS.output.on()
                    psCurrentOut = tempPS.channels[0].output_current * 1000
                except Exception:
                    flag = False
                
                if flag == True:
                    if dev1 == '' and not (dev2 == serial_ports[i]):
                        dev1 = serial_ports[i]
                        try:
                            PS_writeDevice(1)
                            #print('1 in')
                        except Exception:
                            dev1 = ''

                    if dev2 == '' and not (dev1 == serial_ports[i]):
                        dev2 = serial_ports[i]
                        try:
                            PS_writeDevice(2)
                            #print('2 in')
                        except Exception:
                            dev2 = ''
                            
                
            if not dev1 == '':
                koradports.append(dev1)
            if not dev2 == '':
                koradports.append(dev2)
            #print(koradports)
            INI_write()
                
            if not dev1 == '':
                try:
                    tempPS = KoradSerial(dev1)
                    tempPS.output.on()
                    psCurrentOut = tempPS.channels[0].output_current * 1000
                except Exception:
                    #print("1 out")
                    dev1 = ''
                    
            if not dev2 =='':
                try:
                    tempPS = KoradSerial(dev2)
                    tempPS.output.on()
                    psCurrentOut = tempPS.channels[0].output_current * 1000
                except Exception:
                    #print("2 out")
                    dev2 = ''
                        
            if dev1 == '' and dev2 == '':
                psAval = False
            else:
                psAval = True
                
            if not (dev1 == ''):
                flag1 = True
                try:
                    PS1 = KoradSerial(dev1)
                    PS1.output.on()
                except Exception:
                    flag1 = False
            else:
                flag1 = False
                
            if not (dev2 == ''):
                flag2 = True
                try:
                    PS2 = KoradSerial(dev2)
                    PS2.output.on()
                except Exception:
                    flag2 = False
            else:
                flag2 = False
            
            if flag1 == True:
                self.settingsEditButton.setEnabled(True)
                self.settingsOKButton.setEnabled(True)
                self.advsetButton.setEnabled(True)
                
                if settingsSaved1 == True:
                    if not (psVoltage == float(self.setvoltageDisplay.text())):
                        self.setvoltageDisplay.setText(str(psVoltage))
                    PS_writeDevice(1)
                    settingsSaved1 = False
            else:
                self.settingsEditButton.setEnabled(False)
                self.settingsOKButton.setEnabled(False)
                self.advsetButton.setEnabled(False)
                
            if flag2 == True:
                self.settingsEditButton2.setEnabled(True)
                self.settingsOKButton2.setEnabled(True)
                self.advsetButton2.setEnabled(True)
                
                if settingsSaved2 == True:
                    if not (psVoltage2 == float(self.setvoltageDisplay2.text())):
                        self.setvoltageDisplay2.setText(str(psVoltage2))
                    PS_writeDevice(2)
                    settingsSaved2 = False
            else:
                self.settingsEditButton2.setEnabled(False)
                self.settingsOKButton2.setEnabled(False)
                self.advsetButton2.setEnabled(False)
                
            if startAcquisition == True:
                self.startButton.setEnabled(False)
                if flag1 == False:
                    self.currentDisplay.setText("Not connected")
                    self.voltageDisplay.setText("Not connected")
                else:
                    
                    try:
                        PS1.output.on()
                    except Exception:
                        pass
                    try:
                        current = (str(PS1.channels[0].output_current * 1000)) # * 1000 for A to mA
                        voltage = (str(PS1.channels[0].output_voltage))
                        if current == str(None) or voltage == str(None):
                            raise Exception
                        else:
                            self.currentDisplay.setText(current) # * 1000 for A to mA
                            self.voltageDisplay.setText(voltage)

                    except Exception:
                        self.currentDisplay.setText("--")
                        self.voltageDisplay.setText("--")
                    
                    
                if flag2 == False:
                    self.currentDisplay2.setText("Not connected")
                    self.voltageDisplay2.setText("Not connected")
                else:
                    try:
                        PS2.output.on()
                    except Exception:
                        pass
                    try:
                        current2 = (str(PS2.channels[0].output_current * 1000)) # * 1000 for A to mA
                        voltage2 = (str(PS2.channels[0].output_voltage))
                        if current2 == str(None) or voltage2 == str(None):
                            raise Exception
                        else:
                            self.currentDisplay2.setText(current2) # * 1000 for A to mA
                            self.voltageDisplay2.setText(voltage2)

                    except Exception:
                        self.currentDisplay2.setText("--")
                        self.voltageDisplay2.setText("--")
                    

                self.pollingStart()
                if not (dev1 == '') and not (self.currentDisplay.text() == "Not connected" or self.currentDisplay.text() == "--"):
                    self.currentSave.append(float(self.currentDisplay.text())*1000) # * 1000 for A to mA
                    self.voltageSave.append(float(self.voltageDisplay.text()))
                    
                if not (dev2 == '') and not (self.currentDisplay2.text() == "Not connected" or self.currentDisplay2.text() == "--"):
                    self.currentSave2.append(float(self.currentDisplay2.text())*1000) # * 1000 for A to mA
                    self.voltageSave2.append(float(self.voltageDisplay2.text()))
                    
                time.sleep(0.2)
                self.check_plot_vars() 
                self.update_plot()
                startAcquisition = False
                self.startButton.setEnabled(True)

                
            if startLogs == True:
                self.write_telem()
                startLogs = False
            
            if flag1 == False:
                self.currentDisplay.setText("Not connected")
                self.voltageDisplay.setText("Not connected")
                self.settingsEditButton.setEnabled(False)
                self.settingsOKButton.setEnabled(False)
                self.advsetButton.setEnabled(False)
                self.statusPS1.setText("Offline")
                self.statusPS1.setStyleSheet("background-color: red")
            else:
                self.settingsEditButton.setEnabled(True)
                self.settingsOKButton.setEnabled(True)
                self.advsetButton.setEnabled(True)
                self.statusPS1.setText("Online")
                self.statusPS1.setStyleSheet("background-color: green")
                if self.currentDisplay.text() == ("Not connected"):
                    self.currentDisplay.setText('--')
                    self.voltageDisplay.setText('--')
                
            if flag2 == False:
                self.currentDisplay2.setText("Not connected")
                self.voltageDisplay2.setText("Not connected")
                self.settingsEditButton2.setEnabled(False)
                self.settingsOKButton2.setEnabled(False)
                self.advsetButton2.setEnabled(False)
                self.statusPS2.setText("Offline")
                self.statusPS2.setStyleSheet("background-color: red")

            else:
                self.settingsEditButton2.setEnabled(True)
                self.settingsOKButton2.setEnabled(True)
                self.advsetButton2.setEnabled(True)
                self.statusPS2.setText("Online")
                self.statusPS2.setStyleSheet("background-color: green")
                if self.currentDisplay2.text() == ("Not connected"):
                    self.currentDisplay2.setText('--')
                    self.voltageDisplay2.setText('--')
            
            time.sleep(0.5)
            
    def write_telem(self):
        global dev1, dev2
        date = str(datetime.datetime.now())[:19]
        # needs all data, including temperature and pH
        
        flag1 = True
        
        try:
            PS1 = KoradSerial(dev1)
            psCurrentOut1 = PS1.channels[0].output_current * 1000
        except Exception:
            flag1 = False
            
        if flag1 == True:
            try:
                psV = PS1.channels[0].output_voltage
            except Exception:
                psV = "--"
            try:
                psC = PS1.channels[0].output_current * 1000 # * 1000 for A to mA
            
            except Exception:
                psC = "--"
            
        else:
            psV = '--'
            psC = '--'
            
        flag2 = True
        
        try:
            PS2 = KoradSerial(dev2)
            psCurrentOut2 = PS2.channels[0].output_current * 1000
        except Exception:
            flag2 = False
            
        if flag2 == True:
            try:
                psV2 = PS2.channels[0].output_voltage
            except Exception:
                psV2 = "--"
            try:
                psC2 = PS2.channels[0].output_current * 1000 # * 1000 for A to mA
            
            except Exception:
                psC2 = "--"
            
        else:
            psV2 = '--'
            psC2 = '--'
            
        if (self.tempDisplay1.text()) == "No probe connected" or self.tempDisplay1.text() == "Not configured":
            temp1_text = '--'
        else:
            temp1_text = self.tempDisplay1.text()
            
        if (self.tempDisplay2.text()) == "No probe connected" or self.tempDisplay2.text() == "Not configured":
            temp2_text = '--'
        else:
            temp2_text = self.tempDisplay1.text()
            
        if (self.pHDisplay.text()) == "No probe connected" or self.pHDisplay.text() == "Not configured":
            pH_text = '--'
        else:
            pH_text = self.pHDisplay.text()
            
        
        data = [str(date),str(psV),str(psC),str(psV2),str(psC2),temp1_text,temp2_text,pH_text]
        data = ' '.join(data)

        log = get_datalog()
        log.write(data + '\n') # write data to file
        log.close()

    def on_setEdit_button_clicked(self):
        global is_editing_setvals
        is_editing_setvals = True

        displayfont = self.setvoltageDisplay.font()
        displayfont.setPointSize(10)

        self.setvoltageDisplay.setReadOnly(False)
        self.setvoltageDisplay.setStyleSheet("background-color: white; font-weight: normal")
        self.setvoltageDisplay.setFont(displayfont)

    def on_setOK_button_clicked(self):
        global is_editing_setvals, runPS, dAqFlag, psVoltage, psVoltageMax, psCurrentMax, settingsSaved1 

        if is_editing_setvals == False:
            pass
        elif float(self.setvoltageDisplay.text()) > float(psVoltageMax):
            self.statusbar.showMessage("Error: The set voltage must not be greater than the max voltage!")
        else:
            is_editing_setvals = False

            displayfont = self.setvoltageDisplay.font()
            displayfont.setPointSize(10)

            self.statusbar.clearMessage()
            self.setvoltageDisplay.setReadOnly(True)
            self.setvoltageDisplay.setStyleSheet("background-color: lightgray; font-weight: normal")
            self.setvoltageDisplay.setFont(displayfont)

            psVoltage = float(self.setvoltageDisplay.text())
            INI_write()
            
            settingsSaved1 = True

    def on_advset_button_clicked(self):
        global ps, ocp_advset, ovp_advset
        self.AdvSettings = AdvSettings()
        self.AdvSettings.show()

        INI_read() # updates advset strings

        if ocp_advset == 'on':
            self.AdvSettings.ocpCheckBox.setChecked(True)
            self.AdvSettings.ovpCheckBox.setChecked(False)

        elif ovp_advset == 'on':
            self.AdvSettings.ocpCheckBox.setChecked(False)
            self.AdvSettings.ovpCheckBox.setChecked(True)

        else:
            self.AdvSettings.ocpCheckBox.setChecked(False)
            self.AdvSettings.ovpCheckBox.setChecked(False)
            
    def on_setEdit_button_clicked2(self):
        global is_editing_setvals2
        is_editing_setvals2 = True

        displayfont = self.setvoltageDisplay.font()
        displayfont.setPointSize(10)

        self.setvoltageDisplay2.setReadOnly(False)
        self.setvoltageDisplay2.setStyleSheet("background-color: white;font-weight: normal")
        self.setvoltageDisplay2.setFont(displayfont)

    def on_setOK_button_clicked2(self):
        global is_editing_setvals2, runPS, dAqFlag, psVoltage2, psVoltageMax2, psCurrentMax2, settingsSaved2 

        if is_editing_setvals2 == False:
            pass
        elif float(self.setvoltageDisplay.text()) > float(psVoltageMax2):
            self.statusbar.showMessage("Error: The set voltage must not be greater than the max voltage!")
        else:
            is_editing_setvals2 = False

            displayfont = self.setvoltageDisplay.font()
            displayfont.setPointSize(10)

            self.statusbar.clearMessage()
            self.setvoltageDisplay2.setReadOnly(True)
            self.setvoltageDisplay2.setStyleSheet("background-color: lightgray;font-weight: normal")
            self.setvoltageDisplay2.setFont(displayfont)

            psVoltage2 = float(self.setvoltageDisplay2.text())
            INI_write()
            
            settingsSaved2 = True

    def on_advset_button_clicked2(self):
        global ps, ocp_advset2, ovp_advset2
        self.AdvSettings2 = AdvSettings2()
        self.AdvSettings2.show()

        INI_read() # updates advset strings

        if ocp_advset2 == 'on':
            self.AdvSettings2.ocpCheckBox.setChecked(True)
            self.AdvSettings2.ovpCheckBox.setChecked(False)

        elif ovp_advset2 == 'on':
            self.AdvSettings2.ocpCheckBox.setChecked(False)
            self.AdvSettings2.ovpCheckBox.setChecked(True)

        else:
            self.AdvSettings2.ocpCheckBox.setChecked(False)
            self.AdvSettings2.ovpCheckBox.setChecked(False)

    def on_plotset_button_clicked(self):
        global data_points_int
        self.PlotSettings = PlotSettings()
        self.PlotSettings.show()

        if self.PlotSettings.exec_():
            data_points_int = int(self.PlotSettings.datapointsLineEdit.text())
            INI_write() # to update y1_var, y2_var, data_points_int in INI

            self.PlotSettings.close()

        else:
            self.PlotSettings.close()
            pass

    def check_plot_vars(self):
        global y1_label, y2_label, data_points_int

        if not (self.tempDisplay1.text() == "No probe connected" or self.tempDisplay1.text() == "Not configured"):
            self.temp1Plot.append(round(float(self.tempDisplay1.text()), 3))
        
        if not (self.tempDisplay2.text() == "No probe connected" or self.tempDisplay2.text() == "Not configured"):
            self.temp2Plot.append(round(float(self.tempDisplay2.text()), 3))
            
        if not (self.pHDisplay.text() == "No probe connected" or self.pHDisplay.text() == "Not configured"):
            self.pHPlot.append(round(float(self.pHDisplay.text()), 3))
        
        self.y1plot = self.voltageSave[-data_points_int:]
        self.y2plot = self.currentSave[-data_points_int:]
        
        self.y3plot = self.voltageSave2[-data_points_int:]
        self.y4plot = self.currentSave2[-data_points_int:]
        
        self.temp1Plot = self.temp1Plot[-data_points_int:]
        self.temp2Plot = self.temp2Plot[-data_points_int:]
        self.pHPlot = self.pHPlot[-data_points_int:]

        # include temperature and pH retrieval here as well
        #self.check_y_labels()
    
    def on_datalog_button_clicked(self):
        global fileName, dLogInterval, dAqInterval
        self.DataLogSettings = DataLogSettings()
        self.DataLogSettings.show()

        if self.DataLogSettings.exec_():
            fileName = self.DataLogSettings.filenameLineEdit.text()+'.txt'
            dLogInterval = float(self.DataLogSettings.intervalLineEdit.text())
            dAqInterval = float(self.DataLogSettings.aqintervalLineEdit.text())

            self.DataLogSettings.close()

            log = get_datalog()
            log.close()

            INI_write()

        else:
            self.DataLogSettings.close()
            pass

    def on_start_button_clicked(self):
        global ps, is_editing_setvals, psStatus, dAqON, runPS, psAval, polling, autoContinueorSelection

        if self.startButton.isChecked() == True:

            if psAval == False:
                #check = QMessageBox.question(self, 'No KORAD device detected', 'Would you like to continue polling for pH and internal/external temperature?', QMessageBox.Yes | QMessageBox.No)
                #check = autoContinueMessageBox.showWithTimeout(5,'Would you like to continue polling for pH and internal/external temperature?' , 'No KORAD device detected', icon = QMessageBox.Question)
                #print(check)
                wait = NoKoradDetected(self)
                wait.exec_()
                
                #if check == QMessageBox.Yes:
                if autoContinueorSelection == True:
                    polling = True
                    dAqOn = True
                    self.startButton.setText('STOP')
                    self.onlineDisplay.setText('POLLING AND DATA LOGGING ONGOING')
                    self.statusbar.setStyleSheet('background-color: lightgray; font:italic; color:red;')
                    self.statusbar.showMessage("Warning: No PS connected")
                    
                    #Change to clear plot function
                    self.xplot = []
                    self.xplot2 = []
                    self.y1plot = []
                    self.y2plot = []
                    self.y3plot = []
                    self.y4plot = []
                    self.currentSave = []
                    self.voltageSave = []
                    self.currentSave2 = []
                    self.voltageSave2 = []
                    self.temp1x = []
                    self.temp1Plot = []
                    self.temp2x = []
                    self.temp2Plot = []
                    self.pHx = []
                    self.pHPlot = []
                    
                    self.startButton.setChecked(True)
                    self.timer_start()
                    
                else:
                    polling = False
                    dAqON = False
                    self.startButton.setText('START')
                    self.onlineDisplay.setText('POLLING AND DATA LOGGING STOPPED')
                    self.statusbar.setStyleSheet('background-color: lightgray; font:italic; color:red;')
                    #self.statusbar.showMessage("Error: Can not connect to PS through specified COM port")
                    self.startButton.setChecked(False)
                    
            else:
                self.startButton.setText('STOP')
                self.onlineDisplay.setText('POLLING AND DATA LOGGING ONGOING')
                INI_read() # applies specifications stored in INI file

                dAqON = True
                runPS = True
                polling = True
                
                #Change to clear plot function
                self.xplot = []
                self.xplot2 = []
                self.y1plot = []
                self.y2plot = []
                self.y3plot = []
                self.y4plot = []
                self.currentSave = []
                self.voltageSave = []
                self.currentSave2 = []
                self.voltageSave2 = []
                self.temp1x = []
                self.temp1Plot = []
                self.temp2x = []
                self.temp2Plot = []
                self.pHx = []
                self.pHPlot = []
                
                #self.runPolling()
                INI_write() # to update dAqON and runPS bools in INI

                self.timer_start()

                self.ps_output_status = 'on'
                self.update_statusbar()

        else: # to stop:
            
            self.startButton.setText('START')
            self.onlineDisplay.setText('POLLING AND DATA LOGGING STOPPED')
            self.timer.stop()
            
            try:
                ps.output.off()
            except Exception:
                pass

            self.ps_output_status = 'off'
            self.update_statusbar()

            dAqON = False
            runPS = False
            polling = False

            INI_write() # to update dAqON and runPS bools in INI

    def pollingStart(self):

        temp1 = self.i2c_readwrite("101")
        temp2 = self.i2c_readwrite("102")
        pH = self.i2c_readwrite("99")
        
        if not temp1 == "Not configured":
            try:
                if(float(temp1) < -126) or (float(temp1)>1254):
                    temp1 = "No probe connected"
            except Exception:
                temp1 = "No probe connected"

        if not temp2 == "Not configured":
            try:
                if(float(temp2) < -126) or (float(temp2)>1254):
                    temp2 = "No probe connected"
            except Exception:
                temp2 = "No probe connected"
        
        
        if not pH == "Not configured":
            try:
                if float(pH) <= 0 or float(pH) > 15 :
                    pH = "No probe connected"
            except Exception: 
                pH = "No probe connected"
            
        
        self.update_Temp1Signal.emit(temp1)
        self.update_Temp2Signal.emit(temp2)
        self.update_pHSignal.emit(pH)

    def i2c_readwrite(self, device_id):
        global device_list
        foundDeviceFlag = False
        
        for dev in device_list:
            text = dev.get_device_info().replace('\x00','')
            temp = re.findall(r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", text)
            testID = temp[0].strip()
            
            if testID == device_id:
                foundDeviceFlag = True
                
                dev.write("R")
                
                timeout = device_list[0].get_command_timeout("R")
                
                if(timeout):
                    time.sleep(timeout)
                    storage = dev.read().replace('\x00','')
                    temp_storage = storage.split(":")
                    return (temp_storage[1].strip())
                
        if foundDeviceFlag == False:
            return "Not configured"
    
    
        
    def timer_start(self):
        global startAcquisition
        global startLogs
        
        if self.first_timer_start == True:
            self.start_time = time.monotonic()
            self.first_timer_start = False # so any future timer_start calls will not assign a start_time
        
        #self.pollingStart()
        #self.get_telem() # retrieves the telemetry from the power source
        startAcquisition = True
        startLogs = True
        self.dlog_time_left_int = int(dLogInterval * 60)  # * 60 seconds -> minutes
        self.daq_time_left_int = int(dAqInterval * 60)# * 60 seconds -> minutes
        self.timer.start()
        self.update_timer_display()
        self.update_acquisitionTimer_display()

    def on_timeout(self):
        global startAcquisition
        global startLogs
        
        self.dlog_time_left_int -= 1
        self.daq_time_left_int -= 1

        if self.dlog_time_left_int == 0: # when the data log timer reaches 0
            self.dlog_time_left_int = int(dLogInterval * 60)# * 60 minutes -> seconds
            startLogs = True

        if self.daq_time_left_int == 0: # when the data acquitistion timer reaches 0
            self.daq_time_left_int = int(dAqInterval * 60)# * 60 minutes -> seconds
            startAcquisition = True


            #time.sleep(1) # 1 sec delay
        
        self.update_timer_display()
        self.update_acquisitionTimer_display()

    def update_timer_display(self):
        self.timerLabel.setText(time.strftime('%M:%S', time.gmtime(self.dlog_time_left_int)))
    
    def update_acquisitionTimer_display(self):
        self.acquisitionTimerLabel.setText(time.strftime('%M:%S',time.gmtime(self.daq_time_left_int)))


    def update_plot(self):
        global data_points_int, y1_label, y2_label, dev1, dev2
        
        tchart = datetime.datetime.now()
        
        #if not (self.currentDisplay.text() == "Not connected") or not (len(self.y1plot) == len(self.xplot)) or not(len(self.y2plot) == len(self.xplot)) :
        if not (self.currentDisplay.text() == "Not connected" or self.currentDisplay.text() == "--") or not (len(self.y1plot) == len(self.xplot)):
            self.xplot.append(tchart)
            self.xplot = self.xplot[-data_points_int:]
            
        if not (self.currentDisplay2.text() == "Not connected" or self.currentDisplay2.text() == "--") or not (len(self.y3plot) == len(self.xplot2)):
            self.xplot2.append(tchart)
            self.xplot2 = self.xplot2[-data_points_int:]
        
        if not (self.tempDisplay1.text() == "No probe connected" or self.tempDisplay1.text() == "Not configured"):
            self.temp1x.append(tchart)
            self.temp1x = self.temp1x[-data_points_int:]
        
        if not (self.tempDisplay2.text() == "No probe connected" or self.tempDisplay2.text() == "Not configured"):
            self.temp2x.append(tchart)
            self.temp2x = self.temp2x[-data_points_int:]
            
        if not (self.pHDisplay.text() == "No probe connected" or self.pHDisplay.text() == "Not configured"):
            self.pHx.append(tchart)
            self.pHx = self.pHx[-data_points_int:]
        
        self.graph1a.axes.cla()
        self.axes1a.cla()
        self.graph1a.axes.set_title("Voltage", fontweight = 'bold')
        self.graph1a.axes.set_xlabel("Time recorded", fontweight = 'bold')
        self.graph1a.axes.set_ylabel('Voltage 1 (V)',color = 'tab:red', fontweight = 'bold')
        self.graph1a.axes.plot(self.xplot, self.y1plot, 'r', label = "Voltage 1", linestyle ='dashed', marker ="o")
        self.graph1a.axes.tick_params(axis='y', labelcolor='tab:red')
        
        self.axes1a.set_ylabel('Voltage 2 (V)', color = 'tab:blue', fontweight = 'bold')
        self.axes1a.plot(self.xplot2, self.y3plot,'b',label = "Voltage 2", linestyle ='dashed', marker = "v")
        self.axes1a.tick_params(axis='y', labelcolor = 'tab:blue')
        plt.setp(self.graph1a.axes.get_xticklabels(), rotation = 30, horizontalalignment = 'right')
        self.graph1a.fig.legend(loc = 'upper right', bbox_to_anchor =(1.2,1.2), fancybox = True, shadow = True, ncol = 1, bbox_transform = self.graph1a.axes.transAxes)
        
        
        self.graph1b.axes.cla()
        self.axes1b.cla()
        self.graph1b.axes.set_title("Current", fontweight = 'bold')
        self.graph1b.axes.set_xlabel("Time recorded", fontweight = 'bold')
        self.graph1b.axes.set_ylabel('Current 1 (mA)',color = 'tab:red', fontweight = 'bold')
        self.graph1b.axes.plot(self.xplot, self.y2plot, 'r', label = "Current 1", linestyle ='dashed', marker ="o")
        self.graph1b.axes.tick_params(axis='y', labelcolor='tab:red')
        
        self.axes1b.set_ylabel('Current 2 (mA)', color = 'tab:blue', fontweight = 'bold')
        self.axes1b.plot(self.xplot2, self.y4plot,'b',label = "Current 2", linestyle ='dashed', marker = "v")
        self.axes1b.tick_params(axis='y', labelcolor = 'tab:blue')
        plt.setp(self.graph1b.axes.get_xticklabels(), rotation = 30, horizontalalignment = 'right')
        self.graph1b.fig.legend(loc = 'upper right', bbox_to_anchor =(1.2,1.2), fancybox = True, shadow = True, ncol = 1, bbox_transform = self.graph1b.axes.transAxes)
        
        
        self.graph2.axes.cla()
        self.axes2.cla()
        self.graph2.axes.set_title("Temp$_\mathbf{internal}$ and Temp$_\mathbf{external}$", fontweight = 'bold')
        self.graph2.axes.set_xlabel("Time recorded", fontweight = 'bold')
        self.graph2.axes.set_ylabel('Temp$_\mathbf{internal}$ (C)', color = 'tab:olive', fontweight = 'bold')
        self.graph2.axes.plot(self.temp1x, self.temp1Plot, 'y', label = 'Temp$_{int}$', linestyle ='dashed', marker ="o")
        self.graph2.axes.tick_params(axis='y', labelcolor='tab:olive')
        
        self.axes2.set_ylabel('Temp$_\mathbf{external}$ (C)', color = 'tab:green', fontweight = 'bold')
        self.axes2.plot(self.temp2x, self.temp2Plot,'g', label = 'Temp$_{ext}$', linestyle ='dashed', marker = "v")
        self.axes2.tick_params(axis='y', labelcolor = 'tab:green')
        plt.setp(self.graph2.axes.get_xticklabels(), rotation = 30, horizontalalignment = 'right')
        self.graph2.fig.legend(loc = 'upper right', bbox_to_anchor =(1.3,1.2), fancybox = True, shadow = True, ncol = 1, bbox_transform = self.graph2.axes.transAxes)
        

        self.graph3.axes.cla()
        self.graph3.axes.set_title("pH", fontweight = 'bold')
        self.graph3.axes.set_xlabel("Time recorded", fontweight = 'bold')
        self.graph3.axes.set_ylabel('pH', color = 'tab:purple', fontweight = 'bold')
        self.graph3.axes.plot(self.pHx, self.pHPlot, 'm', label = 'pH', linestyle ='dashed', marker ="o")
        self.graph3.axes.tick_params(axis='y', labelcolor='tab:purple')
        plt.setp(self.graph3.axes.get_xticklabels(), rotation = 30, horizontalalignment = 'right')
        self.graph3.axes.legend()
        
        self.graph1a.draw_idle()
        self.graph1b.draw_idle()
        self.graph2.draw_idle()
        self.graph3.draw_idle()
        
    def update_statusbar(self):
        global psStatus

        self.statusbar.setStyleSheet('background-color: lightgray; font:italic; color:green;')
        self.statusbar.showMessage('PS Output is: %s' %self.ps_output_status) #| PS Output is: %s' % (ps_const_status, self.ps_output_status))

    def check_onlineDisplay(self):
        if self.onlineDisplay.text() == 'POLLING AND DATA LOGGING STOPPED':
            self.onlineDisplay.setStyleSheet("background-color: red")

        else:
            self.onlineDisplay.setStyleSheet("background-color: green")
#------------------------------------------------------------------------------#
# RUNNING THE APP
#------------------------------------------------------------------------------#
if __name__ == "__main__":
    global mainWindow
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    mainWindow = MainWindow()
    mainWindow.hide()
    
    delay = StartUpDelay()
    delay.show()

    #main.show()
    sys.exit(app.exec())

    try:
        ps.output.off() # for safety reasons in development
        ps.close()

    except NameError:
        pass
