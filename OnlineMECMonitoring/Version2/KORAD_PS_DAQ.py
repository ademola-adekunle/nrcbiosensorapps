##time.sleep## For first run on this machine, please follow Steps 1 to 3. Preferably run Python IDLE 3.7.x
# Step 1: Make sure pyserial module is installed.
# Step 2: Open and run KoradCli.py
# Step 3: Open and run Koradserial.py

## Other details.
# Port open, close and flush are carried out by the wrapper module.
# Computer is automatically locked during remote control. No need to send command to lock.
# Port is released after a timeout of no command from the shell or once the program reaches EOL.
# Tested for two power supplies as of April 6th, 2021.

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
from qtwidgets import AnimatedToggle

import time, datetime
from koradserial import KoradSerial
from configparser import ConfigParser

import numpy as np
import pandas as pd
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
def print_devices(device_list, device): #Print i2c devices adresses from i2c device list
    for i in device_list:
        if(i == device):
            print(("--> " + i.get_device_info()).replace('\x00','')) #Indicate user selected device and replace null characters in string
        else:
            print((" - " + i.get_device_info()).replace('\x00','')) #Otherwise print all other devices and replace null characters in string
            
def get_devices(): #Function to find compatible ezo circuit devices via a list of i2c addresses
    device = AtlasI2C() #Sets device as AtlasI2C
    device_address_list = device.list_i2c_devices() #Finds list of i2c addresses
    device_list = [] #Starts empty list of devices

    for i in device_address_list: #For every i2c device
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

def splitSerToArr(ser):
    #From series -> return [series index, series values]
    return [ser.index, ser.values]

def INI_write(): # function to write an INI file
    global psVoltage, psCurrentMax, psVoltageMax, psVoltage2, psCurrentMax2, psVoltageMax2,runPS, dLogInterval, dAqInterval, dAqON, ovp_advset, ocp_advset, ocp_advset2, ovp_advset2, ps_outputStatus1, ps_outputStatus2, koradports, fileName, data_points_int
    cfgfile = open("INI/psSettings.ini",'w') #INI file creation. I would take this from the final code. This is just for the test
    parser = ConfigParser()
    parser.read("INI/psSettings.ini")
    
    """
    INI FILE Settings section
    psVoltage, psCurrent, userdefine_MaxPSVoltage are variables for PS1 for voltage, current and max voltage respectively
    psVoltage2, psCurrent2, userdefine_MaxPSVoltage2 are variables for PS2 for voltage, current and max voltage respectively
    dLogInterval and dAqInterval determine interval between each log and each acquisition
    dAqON checks if acquisition/logging is currently ongoing (True) else, false
    fileName is a user selected file name to write params into
    """
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
    
    """
    INI FILE Advanced Settings section
    OVP parameter is a boolean which indicates if OVP is turned on in the PS
    OCP parameter is a boolean which indicates if OCP is turned on in the PS
    psoutput parameter is a booolean which indicates if output is turned on in the PS
    The above set of parameters applies to PS1 and a different set applies to PS2
    """
    parser.add_section('Advanced Settings')
    parser.set('Advanced Settings', 'Over Voltage Protection (OVP)', ovp_advset)
    parser.set('Advanced Settings', 'Over Current Protection (OCP)', ocp_advset)
    parser.set('Advanced Settings', 'Over Voltage Protection (OVP) 2', ovp_advset2)
    parser.set('Advanced Settings', 'Over Current Protection (OCP) 2', ocp_advset2)
    parser.set('Advanced Settings', 'psoutput_1', str(ps_outputStatus1))
    parser.set('Advanced Settings', 'psoutput_2', str(ps_outputStatus2))
    
    """
    INI FILE COM ports section
    Finds list of previously active koradports
    """
    parser.add_section('COM Ports')
    try: # exception catch in case there are no COM ports recognized
        for i in range(len(koradports)):
            parser.set('COM Ports', 'Korad port #%i' %i, str(koradports[i]))

    except Exception:
        pass
    
    """
    INI FILE Plot Settings section
    Max number of data points allowed for each line of data.
    """
    parser.add_section('Plot Settings')
    parser.set('Plot Settings', 'number of data points', str(data_points_int))

    with open("INI/psSettings.ini",'w') as configfile:
        parser.write(configfile)
    configfile.close()

def INI_read(): # function to read an INI file
    global ps, psVoltage, psCurrentMax, psVoltageMax, psVoltage2, psCurrentMax2, psVoltageMax2, runPS, dLogInterval, dAqInterval, dAqON, ocp_advset, ovp_advset, ocp_advset2, ovp_advset2, ps_outputStatus1, ps_outputStatus2, koradports, fileName, data_points_int
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
    runPS = (parser.getboolean("Settings", 'runPS'))
    dLogInterval = float(parser.get("Settings", 'dLogInterval'))
    dAqInterval = float(parser.get("Settings", 'dAqInterval'))
    dAqON = (parser.getboolean("Settings", 'dAqON'))
    fileName = parser.get("Settings", 'datalog filename')

    ovp_advset = parser.get("Advanced Settings", 'Over Voltage Protection (OVP)')
    ocp_advset = parser.get("Advanced Settings", 'Over Current Protection (OCP)')
    ovp_advset2 = parser.get("Advanced Settings", 'Over Voltage Protection (OVP) 2')
    ocp_advset2 = parser.get("Advanced Settings", 'Over Current Protection (OCP) 2')
    ps_outputStatus1 = (parser.getboolean('Advanced Settings','psoutput_1'))
    ps_outputStatus2 = (parser.getboolean('Advanced Settings','psoutput_2'))


    try:
        for i in range(len(koradports)):
            koradports.append(parser.get("COM Ports", 'Korad Port #%i' %i))

    except Exception:
        pass

    data_points_int = int(parser.get("Plot Settings", 'number of data points'))


def PS_writeDevice(channel):
    global dev1, dev2 #Korad serial addresses
    global psVoltage, psCurrentMax, ocp_advset, ovp_advset
    global psVoltage2, psCurrentMax2, ocp_advset2, ovp_advset2
    
    #If channel 1 was selected -> Write into PS1 new settings
    if (channel == 1):
        PS = KoradSerial(dev1)
        PS.channels[0].voltage = psVoltage #Set PS voltage to psVoltage
        PS.channels[0].current = psCurrentMax #Set PS current to psCurrent Max
        
        
        #If OVP is turned on -> turn on PS OVP, else: turn it off
        if ovp_advset == 'on':
            PS.over_voltage_protection.on()

        else:
            PS.over_voltage_protection.off()
        #If OCP is turned on -> Turn on PS OCP, else: turn it off
        if ocp_advset == 'on':
            PS.over_current_protection.on()

        else:
            PS.over_current_protection.off()
    
    #If channel 2 was selected -> Write into PS2 new settings
    elif (channel == 2):
        PS = KoradSerial(dev2)
        PS.channels[0].voltage = psVoltage2 #Set PS voltage to psVoltage
        PS.channels[0].current = psCurrentMax2 #Set PS current to psCurrent Max
        
        #If OVP is turned on -> turn on PS OVP, else: turn it off
        if ovp_advset2 == 'on':
            PS.over_voltage_protection.on()

        else:
            PS.over_voltage_protection.off()
            
        #If OCP is turned on -> Turn on PS OCP, else: turn it off
        if ocp_advset2 == 'on':
            PS.over_current_protection.on()

        else:
            PS.over_current_protection.off()

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
    runPS = '0'
    dAqON = '0'
    fileName = 'DataLoggingFile.txt'
    ocp_advset = 'off'
    ovp_advset = 'on'
    ocp_advset2 = 'off'
    ovp_advset2 = 'on'
    ps_outputStatus1 = "0"
    ps_outputStatus2 = "0"
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
        self.setWindowIcon(QIcon("UI_Files/MECMonitoringIcon.ico")) # Set ICONS
        autoContinueorSelection = False #By default autocontinue is false
        self.confirm_continue.clicked.connect(self.confirm) #If confirm is clicked -> enter confirm function
        self.cancel.clicked.connect(self.exiting) # If cancel is clicked -> enter exiting function
        
        self.time = 10 #Set max time to 10 seconds and start timer
        self.continueTimer = QTimer()
        self.continueTimer.timeout.connect(self.update_button) #On timeout connect to update_button
        self.continueTimer.start(1000) #Time out every 1 second
        
    def update_button(self):
        self.time -= 1 
        self.confirm_continue.setText("Confirm (continues in " + str(self.time) + "s)")
        self.timingLabel.setText("If there is no user selection within " + str(self.time) + "s, polling will be automatically confirmed.")
        
        #If time hits 0 -> Stop timer and auto click confirm_continue (Enters confirm function)
        if self.time == 0:
            self.continueTimer.stop()
            self.confirm_continue.click()
    
    #Confirm function -> Sets dAqON -> data acquisition to true and confirms that autocontinue/selection has been done
    def confirm(self):
        global autoContinueorSelection, dAqON
        
        autoContinueorSelection = True
        dAqON = True
        self.close()
        
    #If cancel is selected->Sets dAqON -> data acquisition is false
    def exiting(self):
        global dAqOn
        
        dAqOn = False
        self.close()
        
#------------------------------------------------------------------------------#
# SwitchButton Classed - Heike from stack overflow
#------------------------------------------------------------------------------#
class ON_OFFSwitch(QtWidgets.QPushButton):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setMinimumWidth(120)
        self.setMinimumHeight(22)

    def paintEvent(self, event):
        label = "ON" if self.isChecked() else "OFF"
        bg_color = Qt.green if self.isChecked() else Qt.red

        radius = 10
        width = 60
        center = self.rect().center()

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.translate(center)
        painter.setBrush(QtGui.QColor(0,0,0))

        pen = QtGui.QPen(Qt.black)
        pen.setWidth(2)
        painter.setPen(pen)

        painter.drawRoundedRect(QRect(-width, -radius, 2*width, 2*radius), radius, radius)
        painter.setBrush(QtGui.QBrush(bg_color))
        sw_rect = QRect(-radius, -radius, width + radius, 2*radius)
        if not self.isChecked():
            sw_rect.moveLeft(-width)
        painter.drawRoundedRect(sw_rect, radius, radius)
        painter.drawText(sw_rect, Qt.AlignCenter, label)

class CustomVLine(QFrame):
    def __init__(self):
        super(CustomVLine,self).__init__()
        self.setFrameShape(self.VLine|self.Sunken)

#------------------------------------------------------------------------------#
# DIALOG
#------------------------------------------------------------------------------#
class AdvSettings(QDialog):

    def __init__(self, *args, **kwargs):
        global ps_outputStatus1
        super(AdvSettings, self).__init__(*args, **kwargs)
        uic.loadUi("UI_Files/AdvSettings_v2-3a.ui", self)
        self.setWindowIcon(QIcon("UI_Files/MECMonitoringIcon.ico")) # Set ICONS
        self.setWindowTitle(u"Advanced PS 1 Settings")
        
        #Sets displays to responding ini file params
        self.setvoltageDisplay.setValue((psVoltage))
        self.maxvoltageDisplay.setValue((psVoltageMax))
        self.maxcurrentDisplay.setValue((psCurrentMax))
        
        #Sets bg to gray
        self.setvoltageDisplay.setStyleSheet('background-color: lightgray')
        self.maxvoltageDisplay.setStyleSheet('background-color: lightgray')
        self.maxcurrentDisplay.setStyleSheet('background-color: lightgray')
        
        #Initialize custom on_off switch -> If outputStatus is true -> set checked to true, otherwise false
        self.on_off = ON_OFFSwitch()
        if ps_outputStatus1:
            self.on_off.setChecked(True)
            self.temp = True
        else:
            self.on_off.setChecked(False)
            self.temp = False
            
        #Connect switch with function
        self.on_off.clicked.connect(self.updatePS_Status)
        #Disable button -> until edit has been pressed
        self.on_off.setEnabled(False)
        self.on_off.setStyleSheet("background-color: lightgray")
        self.infoLayout.addWidget(self.on_off, 3, 1)
        
        #Disable checkbox until state has been changed
        self.ocpCheckBox.setEnabled(False)
        self.ovpCheckBox.setEnabled(False)
        self.ovpCheckBox.stateChanged.connect(self.ovp_state_changed)
        self.ocpCheckBox.stateChanged.connect(self.ocp_state_changed)
        
        #Connect buttons to following functions
        self.settingsEditButton.clicked.connect(self.editingsettings)
        self.advsetButtonBox.accepted.connect(self.save)
        self.advsetButtonBox.rejected.connect(self.reject)
    
    #Depending on PS_status change self.temp varaible
    def updatePS_Status(self):
        if self.on_off.isChecked():
            self.temp = True
        else:
            self.temp = False
    
    #If OVP changed -> Check if is checked -> disable opposite button. If not checked -> enabled both
    def ovp_state_changed(self):
        if self.ovpCheckBox.isChecked() == True:
            self.ocpCheckBox.setChecked(False)
            self.ocpCheckBox.setEnabled(False)

        else:
            self.ocpCheckBox.setEnabled(True)
    
    #If OCP changed -> Check if is checked -> disable opposite button. If not checked -> enabled both
    def ocp_state_changed(self):
        if self.ocpCheckBox.isChecked() == True:
            self.ovpCheckBox.setChecked(False)
            self.ovpCheckBox.setEnabled(False)

        else:
            self.ovpCheckBox.setEnabled(True)
    
    #If edit button has been pressed
    def editingsettings(self):
        global is_editing_setvals 
        is_editing_setvals = True #Set editing to true

        #Enable switch and clean stylesheet
        self.on_off.setEnabled(True)
        self.on_off.setStyleSheet("")
        
        self.setvoltageDisplay.setReadOnly(False)
        self.setvoltageDisplay.setStyleSheet("background-color: white")
        self.maxvoltageDisplay.setReadOnly(False)
        self.maxvoltageDisplay.setStyleSheet("background-color: white")
        self.maxcurrentDisplay.setReadOnly(False)
        self.maxcurrentDisplay.setStyleSheet("background-color: white")
        
        if ovp_advset == 'on':
            self.ovpCheckBox.setEnabled(True)
        elif ocp_advset =='on':
            self.ocpCheckBox.setEnabled(True)
        else:
            self.ovpCheckBox.setEnabled(True)
            self.ocpCheckBox.setEnabled(True)
            
    def save(self):
        global is_editing_setvals, dev1, settingsSaved1, psVoltageMax, psVoltage, psCurrentMax, ovp_advset, ocp_advset, ps_outputStatus1

        if is_editing_setvals == False:
            pass
        elif float(self.setvoltageDisplay.value()) > float(self.maxvoltageDisplay.value()):
            error = QMessageBox.warning(self, 'Max voltage less than set voltage', 'Error: The set voltage must not be greater than the max voltage!')
        else:
            is_editing_setvals = False

            self.setvoltageDisplay.setReadOnly(True)
            self.setvoltageDisplay.setStyleSheet("background-color: lightgray")
            self.maxvoltageDisplay.setReadOnly(True)
            self.maxvoltageDisplay.setStyleSheet("background-color: lightgray")
            self.maxcurrentDisplay.setReadOnly(True)
            self.maxcurrentDisplay.setStyleSheet("background-color: lightgray")
            self.on_off.setEnabled(False)
            
            ps_outputStatus1 = self.temp
            psVoltage = float(self.setvoltageDisplay.value())
            psVoltageMax = float(self.maxvoltageDisplay.value())
            psCurrentMax = float(self.maxcurrentDisplay.value())
            
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
            #Settings saved1 flag
            settingsSaved1 = True
            
            self.close()

class AdvSettings2(QDialog):

    def __init__(self, *args, **kwargs):
        global ps_outputStatus2
        super(AdvSettings2, self).__init__(*args, **kwargs)
        uic.loadUi("UI_Files/AdvSettings_v2-3b.ui", self)
        self.setWindowIcon(QIcon("UI_Files/MECMonitoringIcon.ico")) # Set ICONS
        self.setWindowTitle(u"Advanced PS 2 Settings")
        
        #Sets displays to responding ini file params
        self.setvoltageDisplay.setValue((psVoltage2))
        self.maxvoltageDisplay.setValue((psVoltageMax2))
        self.maxcurrentDisplay.setValue((psCurrentMax2))
        
        #Sets displays backgrounds to respective colors
        self.setvoltageDisplay.setStyleSheet('background-color: lightgray')
        self.maxvoltageDisplay.setStyleSheet('background-color: lightgray')
        self.maxcurrentDisplay.setStyleSheet('background-color: lightgray')
        
        #Initialize custom on_off switch -> If outputStatus is true -> set checked to true, otherwise false
        self.on_off = ON_OFFSwitch()
        if ps_outputStatus2:
            self.on_off.setChecked(True)
            self.temp = True
        else:
            self.on_off.setChecked(False)
            self.temp = False
            
        #Connect switch with function
        self.on_off.clicked.connect(self.updatePS_Status)
        #Disable button -> until edit has been pressed
        self.on_off.setEnabled(False)
        self.on_off.setStyleSheet("background-color: lightgray")
        self.infoLayout.addWidget(self.on_off, 3, 1)
        
        #Disable checkbox until state has been changed
        self.ocpCheckBox.setEnabled(False)
        self.ovpCheckBox.setEnabled(False)
        self.ovpCheckBox.stateChanged.connect(self.ovp_state_changed)
        self.ocpCheckBox.stateChanged.connect(self.ocp_state_changed)
        
        self.settingsEditButton.clicked.connect(self.editingsettings)
        self.advsetButtonBox.accepted.connect(self.save)
        self.advsetButtonBox.rejected.connect(self.reject)
        
    def updatePS_Status(self):
        if self.on_off.isChecked():
            self.temp = True
        else:
            self.temp = False

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

        self.on_off.setEnabled(True)
        self.on_off.setStyleSheet("")
        
        self.setvoltageDisplay.setReadOnly(False)
        self.setvoltageDisplay.setStyleSheet("background-color: white")
        self.maxvoltageDisplay.setReadOnly(False)
        self.maxvoltageDisplay.setStyleSheet("background-color: white")
        self.maxcurrentDisplay.setReadOnly(False)
        self.maxcurrentDisplay.setStyleSheet("background-color: white")
        
        if ovp_advset2 == 'on':
            self.ovpCheckBox.setEnabled(True)
        elif ocp_advset2 =='on':
            self.ocpCheckBox.setEnabled(True)
        else:
            self.ovpCheckBox.setEnabled(True)
            self.ocpCheckBox.setEnabled(True)
            
    def save(self):
        global is_editing_setvals2, dev2, settingsSaved2, psVoltageMax2, psVoltage2, psCurrentMax2, ovp_advset2, ocp_advset2, ps_outputStatus2

        if is_editing_setvals2 == False:
            pass
        elif float(self.setvoltageDisplay.value()) > float(self.maxvoltageDisplay.value()):
            error = QMessageBox.warning(self, 'Max voltage less than set voltage', 'Error: The set voltage must not be greater than the max voltage!')
        else:
            is_editing_setvals2 = False

            self.setvoltageDisplay.setReadOnly(True)
            self.setvoltageDisplay.setStyleSheet("background-color: lightgray")
            self.maxvoltageDisplay.setReadOnly(True)
            self.maxvoltageDisplay.setStyleSheet("background-color: lightgray")
            self.maxcurrentDisplay.setReadOnly(True)
            self.maxcurrentDisplay.setStyleSheet("background-color: lightgray")
            self.on_off.setEnabled(False)

            psVoltage2 = float(self.setvoltageDisplay.value())
            psVoltageMax2 = float(self.maxvoltageDisplay.value())
            psCurrentMax2 = float(self.maxcurrentDisplay.value())
            
            if self.ovpCheckBox.isChecked() == True:
                ovp_advset2 = 'on'
                ocp_advset2 = 'off'

            elif self.ocpCheckBox.isChecked() == True:
                ovp_advset2 = 'off'
                ocp_advset2 = 'on'

            else:
                ovp_advset2 = 'off'
                ocp_advset2 = 'off'
                
            ps_outputStatus2 = self.temp
            
            INI_write()
            
            settingsSaved2 = True
            
            self.close()
            
class DataLogSettings(QDialog):

    def __init__(self, *args, **kwargs):
        global dLogInterval, dAqInterval
        super(DataLogSettings, self).__init__(*args, **kwargs)
        uic.loadUi("UI_Files/DataLogSettings_v2-2.ui", self)
        self.setWindowIcon(QIcon("UI_Files/MECMonitoringIcon.ico")) # Set ICONS
        self.setWindowTitle('Data Log Settings')

        dispfileName = fileName.split('.txt') # gets the file ready to show without the .txt ending
        
        #Set file name, dLog and dAq intervals and sets values
        self.filenameLineEdit.setText(dispfileName[0])
        self.intervalSpinBox.setValue((dLogInterval))
        self.aqintervalSpinBox.setValue((dAqInterval))
        
        self.aqintervalSpinBox.valueChanged.connect(self.changeMin)
        
    def changeMin(self):
        global dLogInterval, dAqInterval
        self.intervalSpinBox.setMinimum(self.aqintervalSpinBox.value())
        
        if self.intervalSpinBox.value() < self.aqintervalSpinBox.value():
            self.intervalSpinBox.setValue(self.aqintervalSpinBox.value())

class PlotSettings(QDialog):

    def __init__(self, *args, **kwargs):
        super(PlotSettings, self).__init__(*args, **kwargs)
        self.setWindowIcon(QIcon("UI_Files/MECMonitoringIcon.ico")) # Set ICONS
        self.setWindowTitle('Plot Settings')
        self.setModal(True)
        QBtn = QDialogButtonBox.Ok

        self.buttonbox = QDialogButtonBox(QBtn)
        self.buttonbox.accepted.connect(self.accept)
        
        #Finds max number of visible data points
        self.textlayout = QHBoxLayout()
        self.datapointsLabel = QLabel('# of visible data points on the plot:')
        self.datapointsLabel.setToolTip("Sets maximum number of visible data points for each line of data")
        self.datapointsLineEdit = QLineEdit(self)
        self.datapointsLineEdit.setText(str(data_points_int))

        self.textlayout.addWidget(self.datapointsLabel)
        self.textlayout.addWidget(self.datapointsLineEdit)

        self.layout = QVBoxLayout()
        self.layout.addLayout(self.textlayout)
        self.layout.addWidget(self.buttonbox)
        self.setLayout(self.layout)

class StartUpDelay(QDialog): # OK Button needs removing for final program
    
    def __init__(self, *args, **kwargs):
        super(StartUpDelay, self).__init__(*args, **kwargs)

        self.setWindowTitle("Loading program...")
        self.setWindowIcon(QIcon("UI_Files/MECMonitoringIcon.ico")) # Set ICONS
        QBtn = QDialogButtonBox.Ok

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
        self.setLayout(self.layout)

        self.delay_start()
        self.update_gui()
    

    def delay_start(self):
        self.delaytimeleft = 0
        self.delaytimer.start()
        self.update_gui()

    def delay_timeout(self):
        global mainWindow, dAqON
        self.delaytimeleft += 1
        self.progressbar.setValue(self.delaytimeleft)

        if self.delaytimeleft == 15:
            self.delaytimerDisplay.setText('Program starting...')
            self.delaytimer.stop()
            self.close()
            
            mainWindow.show()
            if dAqON == True:
                mainWindow.startButton.click()

        self.update_gui()
        
    def update_gui(self):
        
        self.delaytimerDisplay.setText('Please wait while program is loading...')
            
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
    #(Text,bool, Text, bool)
    update_statusBarSignal = pyqtSignal(str,bool, str, bool)
    
    #(Text)
    update_PS_stat1Signal = pyqtSignal(str)
    update_PS_stat2Signal = pyqtSignal(str)
    

    def __init__(self, *args, **kwargs):
        global is_editing_setvals, is_editing_setvals2, y1_label, y2_label, ports, koradports, serial_ports, settingsSaved1, settingsSaved2, dAqON, ps_outputStatus1, ps_outputStatus2, data_points_int
        super(MainWindow, self).__init__(*args, **kwargs)
        uic.loadUi("UI_Files/RPi_GUI_v1-12.ui", self)
        polling = False
        #self.setWindowIcon(QIcon(r"Icon_Store\icons\lightning.png"))
        self.setWindowTitle('KORAD PS DAQ')
        self.setWindowIcon(QIcon("UI_Files/MECMonitoringIcon.ico")) # Set ICONS
        self.tempDisplay1 = self.findChild(QLineEdit,"tempDisplay1")
        self.tempDisplay2 = self.findChild(QLineEdit,"tempDisplay2")
        self.pHDisplay = self.findChild(QLineEdit,"pHDisplay")
        
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1000) # Timer counts down one second
        self.timer.timeout.connect(self.on_timeout)
        self.first_timer_start = True # for start_time assignment check in timer_start

        self.onlineDisplay.textChanged.connect(self.check_onlineDisplay)
        if dAqON == False:
            self.onlineDisplay.setText('POLLING AND DATA LOGGING STOPPED') # sets onlineDisplay's default to say it's offline
        else:
            self.onlineDisplay.setText('POLLING AND DATA LOGGING ONGOING')
        self.check_onlineDisplay()
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
        
        self.ps1StatusLabel = QLabel("Power source 1 -")
        self.ps1StatusLabel.setStyleSheet("border:0 ; color: black; font:italic;")
        self.ps1StatusConnection = QLabel("Connected: ")
        self.ps1StatusConnection.setStyleSheet("border:0 ; color: black; font:italic;")
        self.ps1StatusOutput = QLabel("Output: ")
        self.ps1StatusOutput.setStyleSheet("border:0 ; color: black; font:italic;")
        self.ps2StatusLabel = QLabel("Power source 2 -")
        self.ps2StatusLabel.setStyleSheet("border:0 ; color: black; font:italic;")
        self.ps2StatusConnection = QLabel("Connected: ")
        self.ps2StatusConnection.setStyleSheet("border:0 ; color: black; font:italic;")
        self.ps2StatusOutput = QLabel("Output: ")
        self.ps2StatusOutput.setStyleSheet("border:0 ; color: black; font:italic;")

        self.statusbar.reformat()
        self.statusbar.setStyleSheet('border: 0; background-color: lightgray; font:italic;')
        self.statusbar.setStyleSheet("QStatusBar::item {border: none;}")
        
        self.statusbar.addPermanentWidget(CustomVLine())
        self.statusbar.addPermanentWidget(self.ps1StatusLabel)
        self.statusbar.addPermanentWidget(self.ps1StatusConnection)
        self.statusbar.addPermanentWidget(self.ps1StatusOutput)
        self.statusbar.addPermanentWidget(CustomVLine())
        self.statusbar.addPermanentWidget(self.ps2StatusLabel)
        self.statusbar.addPermanentWidget(self.ps2StatusConnection)
        self.statusbar.addPermanentWidget(self.ps2StatusOutput)
        self.statusbar.addPermanentWidget(CustomVLine())
        
        # Clear graph settings
        self.xplot = []
        self.xplot2 = []
        self.y1plot = []
        self.y2plot = []
        self.y3plot = []
        self.y4plot = []
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
        self.graph2.axes.set_ylabel('Temp$_\mathbf{internal}$ ($\circ$C)', fontweight = 'bold')
        self.axes2 = self.graph2.axes.twinx() #Creates a two axes plot
        self.axes2.set_ylabel('Temp$_\mathbf{external}$ ($\circ$C)', fontweight = 'bold')
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
        
        #Start threads
        self.runcheckDevices()
        self.runMainThread()
        
        self.update_Temp1Signal.connect(self.update_Temp1)
        self.update_Temp2Signal.connect(self.update_Temp2)
        self.update_pHSignal.connect(self.update_pH)
        self.update_statusBarSignal.connect(self.update_StatusBar)
        self.update_PS_stat1Signal.connect(self.update_stat1)
        self.update_PS_stat2Signal.connect(self.update_stat2)
        
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
    
    @QtCore.pyqtSlot(str,bool,str,bool)
    def update_StatusBar(self, status1, connected1, status2, connected2):
        if connected1 == True:
            self.ps1StatusConnection.setStyleSheet("border:0 ; color: green; font:italic;")
            self.ps1StatusConnection.setText("Connected")
            
            if status1 == "on":
                self.ps1StatusOutput.setText("Output: " + status1)
                self.ps1StatusOutput.setStyleSheet("border:0 ; color: green; font:italic;")
            else:
                self.ps1StatusOutput.setText("Output: " + status1)
                self.ps1StatusOutput.setStyleSheet("border:0 ; color: red; font:italic;")
            
        else:
            self.ps1StatusConnection.setStyleSheet("border:0 ; color: red; font:italic;")
            self.ps1StatusConnection.setText("Not connected")
            self.ps1StatusOutput.setText("Output: off")
            self.ps1StatusOutput.setStyleSheet("border:0 ; color: red; font:italic;")
        
        if connected2 == True:
            self.ps2StatusConnection.setStyleSheet("border:0 ; color: green; font:italic;")
            self.ps2StatusConnection.setText("Connected")
            
            if status2 == "on":
                self.ps2StatusOutput.setText("Output: " + status2)
                self.ps2StatusOutput.setStyleSheet("border:0 ; color: green; font:italic;")
            else:
                self.ps2StatusOutput.setText("Output: " + status2)
                self.ps2StatusOutput.setStyleSheet("border:0 ; color: red; font:italic;")
            
        else:
            self.ps2StatusConnection.setStyleSheet("border:0 ; color: red; font:italic;")
            self.ps2StatusConnection.setText("Not connected")
            self.ps2StatusOutput.setText("Output: off")
            self.ps2StatusOutput.setStyleSheet("border:0 ; color: red; font:italic;")
            
    @QtCore.pyqtSlot(str)
    def update_stat1(self, text):
        if text == "Connected":
            self.statusPS1.setStyleSheet("background-color: lightgreen")
        else:
            self.statusPS1.setStyleSheet("background-color: red")
        self.statusPS1.setText(text)
        
    @QtCore.pyqtSlot(str)
    def update_stat2(self, text):
        if text == "Connected":
            self.statusPS2.setStyleSheet("background-color: lightgreen")
        else:
            self.statusPS2.setStyleSheet("background-color: red")
        self.statusPS2.setText(text)
        
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
                    serial_ports_temp.append(str(test_ports[i].device))
            
            #Serial ports temp is different then serial_ports
            if not set(serial_ports_temp) == set(serial_ports):
                serialportsChanged = True
                serial_ports = serial_ports_temp
                
            time.sleep(1)
            
    def runMainThread(self):    
        tMainThread = threading.Thread(target= self.mainThread)
        tMainThread.daemon = True
        tMainThread.start()
    
    def mainThread(self):
        global koradports, psAval, serialportsChanged, serial_ports, ps_outputStatus1, ps_outputStatus2
        global dev1, dev2
        global startAcquisition
        global startLogs
        global device_list
        global settingsSaved1, settingsSaved2, psVoltage, psVoltage2
        global endThread, threadEnded
        
        #Sets endThread and threadEnded to false
        endThread = False
        threadEnded = False
        
        while True:
            device_list = get_devices() #Finds I2C devices
            
            """
            Checking for KoradSerial Compatible ports below based on list of serial ports
            If found -> set to dev1 or dev2 respectively
            Then append dev1 and/or dev2 to korad ports
            Write new information to INI file
            """
            koradports = []
            check = True
            for i in range (len(serial_ports)): #Check all serial ports for Korad compatible ports#
            
                flag = True
                try:
                    tempPS = KoradSerial(serial_ports[i])
                    psCurrentOut = tempPS.channels[0].output_current * 1000
                except Exception:
                    flag = False
                
                if flag == True: #If found -> set to dev1 if dev1 is empty and address is not equal to dev2
                    if dev1 == '' and not (dev2 == serial_ports[i]):
                        dev1 = serial_ports[i]
                        try:
                            PS_writeDevice(1)
                        except Exception:
                            dev1 = ''
                    # set to dev2 if dev2 is empty and address is not equal to dev1
                    if dev2 == '' and not (dev1 == serial_ports[i]):
                        dev2 = serial_ports[i]
                        try:
                            PS_writeDevice(2)
                        except Exception:
                            dev2 = ''
                            
                
            if not dev1 == '':
                koradports.append(dev1)
            if not dev2 == '':
                koradports.append(dev2)
                
            INI_write()
            
            """
            Power source checking -> If dev1 exists -> try to communicate -> if failed -> dev1 does not exist
            Same thing for dev2
            """
            if not dev1 == '':
                try:
                    tempPS = KoradSerial(dev1)
                    psCurrentOut = tempPS.channels[0].output_current * 1000
                except Exception:
                    dev1 = ''
                    
            if not dev2 =='':
                try:
                    tempPS = KoradSerial(dev2)
                    psCurrentOut = tempPS.channels[0].output_current * 1000
                except Exception:
                    dev2 = ''
            
            """
            If dev1 and dev2 do not exist -> psAval = False, otherwise true
            """
            if dev1 == '' and dev2 == '':
                psAval = False
            else:
                psAval = True
            
            """
            Power source output on or off
            if dev1 exists and output variable is on -> turn on, else turn off
                -> If turning on or off command works -> Flag1 = true, else Flag1 = False
            if dev2 exists and output variable is on -> turn on, else turn off
                -> If turning on or off command works -> Flag2 = true, else Flag2 = False
            """
            if not (dev1 == ''):
                flag1 = True
                try:
                    PS1 = KoradSerial(dev1)
                    if ps_outputStatus1:
                        PS1.output.on()
                    else:
                        PS1.output.off()
                except Exception:
                    flag1 = False
            else:
                flag1 = False
                
            if not (dev2 == ''):
                flag2 = True
                try:
                    PS2 = KoradSerial(dev2)
                    if ps_outputStatus2:
                        PS2.output.on()
                    else:
                        PS2.output.off()
                except Exception:
                    flag2 = False
            else:
                flag2 = False
            
            """
            Writing new settings to device and enabling buttons for power source
            If flag1 is true, enabled all the settings button
                If settingsflag1 has been changed to true -> set voltageDisplay to psVoltage
                Write new settings to Powersource 1
                turn flag to false
            Else: Keep the buttons disabled
            
            Same logic for power source 2
            """
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
                
            """
            If start acquisition flag is triggered -> Start acquisition process
            """
            if startAcquisition == True:
                self.startButton.setEnabled(False)
                
                """
                If flag 1 is false -> setText to not connected
                else:
                    if output is on -> find current and voltage
                        if current or voltage is none -> failed reading is triggered
                        else -> set text to voltage and current
                        
                        if exception was raised -> set text to ("--")
                    if output is off -> set text to ("Output off")
                
                Same logic applies for flag 2 with dev2
                """
                if flag1 == False:
                    self.currentDisplay.setText("Not connected")
                    self.voltageDisplay.setText("Not connected")
                else:
                    if ps_outputStatus1:
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
                    else:
                        self.currentDisplay.setText('Output off')
                        self.voltageDisplay.setText('Output off')
            
                if flag2 == False:
                    self.currentDisplay2.setText("Not connected")
                    self.voltageDisplay2.setText("Not connected")
                else:
                    if ps_outputStatus2:
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
                    else:
                        self.currentDisplay2.setText('Output off')
                        self.voltageDisplay2.setText('Output off')
                
                #Polling I2C data function
                self.pollingStart()
                
                #Updating plot vars -> If displays are values -> append to plot, else append None
                if not (self.currentDisplay.text() == "Not connected" or self.currentDisplay.text() == "--" or self.currentDisplay.text() == "Output off"):
                    self.y2plot.append(float(self.currentDisplay.text()))
                    self.y1plot.append(float(self.voltageDisplay.text()))
                else:
                    self.y2plot.append(None)
                    self.y1plot.append(None)
                    
                if not (self.currentDisplay2.text() == "Not connected" or self.currentDisplay2.text() == "--" or self.currentDisplay2.text() == "Output off"):
                    self.y4plot.append(float(self.currentDisplay2.text()))
                    self.y3plot.append(float(self.voltageDisplay2.text()))
                else:
                    self.y4plot.append(None) 
                    self.y3plot.append(None)
                    
                time.sleep(0.2)
                
                #Update i2c plot vars and modify sizes of y-values
                self.check_plot_vars()
                #Update plot function
                self.update_plot()
                
                #Set flag to false and enabled startButton
                startAcquisition = False
                self.startButton.setEnabled(True)

            #If startLogs flag is triggered -> Begin writing telem data (flag is then set to false)
            if startLogs == True:
                self.write_telem()
                startLogs = False
            
            #If flag1 is false -> Disable buttons and emit signal to change PS1 status
            #else -> enable buttons and emit signal to change PS1 status to connected
                #-> if text is not connected and output is true -> set to '--'
                #-> if output is off -> set to 'output off'
                #-> if text is not connected or output off and output is true -> set to '--'
            if flag1 == False:
                self.currentDisplay.setText("Not connected")
                self.voltageDisplay.setText("Not connected")
                self.settingsEditButton.setEnabled(False)
                self.settingsOKButton.setEnabled(False)
                self.advsetButton.setEnabled(False)
                self.update_PS_stat1Signal.emit("Not connected")
            else:
                self.settingsEditButton.setEnabled(True)
                self.settingsOKButton.setEnabled(True)
                self.advsetButton.setEnabled(True)
                self.update_PS_stat1Signal.emit("Connected")
                if self.currentDisplay.text() == ("Not connected") and ps_outputStatus1:
                    self.currentDisplay.setText('--')
                    self.voltageDisplay.setText('--')
                elif not ps_outputStatus1:
                    self.currentDisplay.setText('Output off')
                    self.voltageDisplay.setText('Output off')
                
                elif(self.currentDisplay.text() == "Not connected"  or self.currentDisplay.text() == 'Output off') and ps_outputStatus1:
                    self.currentDisplay.setText('--')
                    self.voltageDisplay.setText('--')
            
            #If flag2 is false -> Disable buttons and emit signal to change PS2 status
            #else -> enable buttons and emit signal to change PS2 status to connected
                #-> if text is not connected and output is true -> set to '--'
                #-> if output is off -> set to 'output off'
                #-> if text is not connected or output off and output is true -> set to '--'
            if flag2 == False:
                self.currentDisplay2.setText("Not connected")
                self.voltageDisplay2.setText("Not connected")
                self.settingsEditButton2.setEnabled(False)
                self.settingsOKButton2.setEnabled(False)
                self.advsetButton2.setEnabled(False)
                self.update_PS_stat2Signal.emit("Not connected")

            else:
                self.settingsEditButton2.setEnabled(True)
                self.settingsOKButton2.setEnabled(True)
                self.advsetButton2.setEnabled(True)
                self.update_PS_stat2Signal.emit("Connected")
                if self.currentDisplay2.text() == ("Not connected") and ps_outputStatus2:
                    self.currentDisplay2.setText('--')
                    self.voltageDisplay2.setText('--')
                elif not ps_outputStatus2:
                    self.currentDisplay2.setText('Output off')
                    self.voltageDisplay2.setText('Output off')
                elif(self.currentDisplay2.text() == "Not connected"  or self.currentDisplay2.text() == 'Output off') and ps_outputStatus2:
                    self.currentDisplay2.setText('--')
                    self.voltageDisplay2.setText('--')
            
            #If outputStatus1 is on -> ps1stat = on, else off
            #If outputStatus2 is on -> ps2stat = on, else off
            ps1stat = ''
            ps2stat = ''
            if ps_outputStatus1:
                ps1stat = "on"
            else:
                ps1stat = "off"
            if ps_outputStatus2:
                ps2stat = 'on'
            else:
                ps2stat = 'off'
            #Emit signal to modify status bar
            self.update_statusBarSignal.emit(ps1stat, flag1, ps2stat, flag2)
            
            #If endThread is triggered -> set threadEnded to True
            if endThread:
                threadEnded = True
                
            time.sleep(1)
    
    """
    Save current acquisition data to logs
    """
    def write_telem(self):
        global dev1, dev2
        global ps_outputStatus1, ps_outputStatus2
        date = str(datetime.datetime.now())[:19]
        
        """
        Start with dev1 -> Test if KoradSerial -> set flag1 to false if false
        """
        flag1 = True
        
        try:
            PS1 = KoradSerial(dev1)
            psCurrentOut1 = PS1.channels[0].output_current * 1000
        except Exception:
            flag1 = False
        
        """
        If dev1 is KoradSerial -> test channel outputs -> If failed -> reading = -- 
        """
        if flag1 == True:
            if ps_outputStatus1:
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
            
        else:
            psV = '--'
            psC = '--'
        
        
        """
        Start with dev2 -> Test if KoradSerial -> set flag2 to false if false
        """
        flag2 = True
        
        try:
            PS2 = KoradSerial(dev2)
            psCurrentOut2 = PS2.channels[0].output_current * 1000
        except Exception:
            flag2 = False
        
        """
        If dev2 is KoradSerial -> test channel outputs -> If failed -> reading = -- 
        """
        if flag2 == True:
            if ps_outputStatus2:
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
        else:
            psV2 = '--'
            psC2 = '--'
        
        #Depending on Polling display text -> set entries to respective value or '--'
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
            
        #Append data 
        data = [str(date),str(psV),str(psC),str(psV2),str(psC2),temp1_text,temp2_text,pH_text]
        data = ' '.join(data)
        
        #Write to log
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
        
        try:
            if is_editing_setvals == False:
                pass
            elif float(self.setvoltageDisplay.text()) < 0.01:
                error = QMessageBox.warning(self, "Error!", "The set voltage must be greater than 0 (At least 10mV)")
            elif float(self.setvoltageDisplay.text()) > float(psVoltageMax):
                error = QMessageBox.warning(self, "Error!", "The set voltage must not be greater than the max voltage.")
            else:
                is_editing_setvals = False

                displayfont = self.setvoltageDisplay.font()
                displayfont.setPointSize(10)

                self.setvoltageDisplay.setReadOnly(True)
                self.setvoltageDisplay.setStyleSheet("background-color: lightgray; font-weight: normal")
                self.setvoltageDisplay.setFont(displayfont)

                psVoltage = float(self.setvoltageDisplay.text())
                INI_write()
                
                settingsSaved1 = True
                
        except ValueError:
            error = QMessageBox.warning(self, "Value Error!", "Please enter an appropriate value in the set voltage section!")
            self.setvoltageDisplay.setText(str(psVoltage))


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

        self.setvoltageDisplay2.setReadOnly(False)
        self.setvoltageDisplay2.setStyleSheet("background-color: white;font-weight: normal")

    def on_setOK_button_clicked2(self):
        global is_editing_setvals2, runPS, dAqFlag, psVoltage2, psVoltageMax2, psCurrentMax2, settingsSaved2 
        
        try:
            if is_editing_setvals2 == False:
                pass
            elif float(self.setvoltageDisplay2.text()) < 0.01:
                    error = QMessageBox.warning(self, "Error!", "The set voltage must be greater than 0 (At least 10mV)")
            elif float(self.setvoltageDisplay2.text()) > float(psVoltageMax2):
                error = QMessageBox.warning(self, "Error!", "The set voltage must not be greater than the max voltage.")
            else:
                is_editing_setvals2 = False

                self.setvoltageDisplay2.setReadOnly(True)
                self.setvoltageDisplay2.setStyleSheet("background-color: lightgray;font-weight: normal")

                psVoltage2 = float(self.setvoltageDisplay2.text())
                INI_write()
                
                #Settings saved flag
                settingsSaved2 = True
                
        except ValueError:
            error = QMessageBox.warning(self, "Value Error!", "Please enter an appropriate value in the set voltage section!")
            self.setvoltageDisplay2.setText(str(psVoltage2))
            
            
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
        else:
            self.temp1Plot.append(None)
        if not (self.tempDisplay2.text() == "No probe connected" or self.tempDisplay2.text() == "Not configured"):
            self.temp2Plot.append(round(float(self.tempDisplay2.text()), 3))
        else:
            self.temp2Plot.append(None)
        if not (self.pHDisplay.text() == "No probe connected" or self.pHDisplay.text() == "Not configured"):
            self.pHPlot.append(round(float(self.pHDisplay.text()), 3))
        else:
            self.pHPlot.append(None)
        
        self.y1plot = self.y1plot[-data_points_int:]
        self.y2plot = self.y2plot[-data_points_int:]
        
        self.y3plot = self.y3plot[-data_points_int:]
        self.y4plot = self.y4plot[-data_points_int:]
        
        self.temp1Plot = self.temp1Plot[-data_points_int:]
        self.temp2Plot = self.temp2Plot[-data_points_int:]
        self.pHPlot = self.pHPlot[-data_points_int:]
    

    def on_datalog_button_clicked(self):
        global fileName, dLogInterval, dAqInterval
        self.DataLogSettings = DataLogSettings()
        self.DataLogSettings.show()

        if self.DataLogSettings.exec_():
            fileName = self.DataLogSettings.filenameLineEdit.text()+'.txt'
            dLogInterval = (self.DataLogSettings.intervalSpinBox.value())
            dAqInterval = (self.DataLogSettings.aqintervalSpinBox.value())

            self.DataLogSettings.close()

            log = get_datalog()
            log.close()

            INI_write()

        else:
            self.DataLogSettings.close()
            pass

    def on_start_button_clicked(self):
        global ps, is_editing_setvals, psStatus, dAqON, runPS, psAval, polling, autoContinueorSelection, data_points_int

        if self.startButton.isChecked() == True:

            if psAval == False:
                wait = NoKoradDetected(self)
                wait.exec_()
                
                if autoContinueorSelection == True:
                    polling = True
                    dAqOn = True
                    self.startButton.setText('STOP')
                    self.onlineDisplay.setText('POLLING AND DATA LOGGING ONGOING')
                    
                    
                    #Change to clear plot function
                    self.xplot = []
                    self.xplot2 = []
                    self.y1plot = []
                    self.y2plot = []
                    self.y3plot = []
                    self.y4plot = []
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
                    self.tempDisplay1.setText('--')
                    self.tempDisplay2.setText('--')
                    self.pHDisplay.setText('--')
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
                self.temp1x = []
                self.temp1Plot = []
                self.temp2x = []
                self.temp2Plot = []
                self.pHx = []
                self.pHPlot = []
                
                INI_write() # to update dAqON and runPS bools in INI

                self.timer_start()

        else: # to stop:
            
            self.startButton.setText('START')
            self.onlineDisplay.setText('POLLING AND DATA LOGGING STOPPED')
            self.timer.stop()
            
            try:
                ps.output.off()
            except Exception:
                pass

            dAqON = False
            runPS = False
            polling = False
            
            self.tempDisplay1.setText('--')
            self.tempDisplay2.setText('--')
            self.pHDisplay.setText('--')

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

        self.update_timer_display()
        self.update_acquisitionTimer_display()

    def update_timer_display(self):
        self.timerLabel.setText(time.strftime('%M:%S', time.gmtime(self.dlog_time_left_int)))
    
    def update_acquisitionTimer_display(self):
        self.acquisitionTimerLabel.setText(time.strftime('%M:%S',time.gmtime(self.daq_time_left_int)))


    def update_plot(self):
        global data_points_int, y1_label, y2_label, dev1, dev2, data_points_int
        
        tchart = datetime.datetime.now()
        
        self.xplot.append(tchart)
        self.xplot = self.xplot[-data_points_int:]
            
        self.xplot2.append(tchart)
        self.xplot2 = self.xplot2[-data_points_int:]
        
        self.temp1x.append(tchart)
        self.temp1x = self.temp1x[-data_points_int:]
        
        self.temp2x.append(tchart)
        self.temp2x = self.temp2x[-data_points_int:]
            
        self.pHx.append(tchart)
        self.pHx = self.pHx[-data_points_int:]
        
        line1 = pd.Series(self.y1plot, self.xplot)
        line2 = pd.Series(self.y2plot, self.xplot2)
        line3 = pd.Series(self.y3plot, self.xplot)
        line4 = pd.Series(self.y4plot, self.xplot2)
        temp1Line = pd.Series(self.temp1Plot, self.temp1x)
        temp2Line = pd.Series(self.temp2Plot, self.temp2x)
        pHLine = pd.Series(self.pHPlot, self.pHx)
        
        self.graph1a.axes.cla()
        self.axes1a.cla()
        self.graph1a.axes.set_title("Voltage", fontweight = 'bold')
        self.graph1a.axes.set_xlabel("Time recorded", fontweight = 'bold')
        self.graph1a.axes.set_ylabel('Voltage 1 (V)',color = 'tab:red', fontweight = 'bold')
        self.graph1a.axes.plot(*splitSerToArr(line1.dropna()), 'r', label = "Voltage 1", linestyle ='dashed', marker ="o")
        self.graph1a.axes.tick_params(axis='y', labelcolor='tab:red')
        
        self.axes1a.set_ylabel('Voltage 2 (V)', color = 'tab:blue', fontweight = 'bold')
        self.axes1a.plot(*splitSerToArr(line3.dropna()),'b',label = "Voltage 2", linestyle ='dashed', marker = "v")
        self.axes1a.tick_params(axis='y', labelcolor = 'tab:blue')
        plt.setp(self.graph1a.axes.get_xticklabels(), rotation = 30, horizontalalignment = 'right')
        self.graph1a.fig.legend(loc = 'upper right', bbox_to_anchor =(1.2,1.2), fancybox = True, shadow = True, ncol = 1, bbox_transform = self.graph1a.axes.transAxes)
        
        self.graph1b.axes.cla()
        self.axes1b.cla()
        self.graph1b.axes.set_title("Current", fontweight = 'bold')
        self.graph1b.axes.set_xlabel("Time recorded", fontweight = 'bold')
        self.graph1b.axes.set_ylabel('Current 1 (mA)',color = 'tab:red', fontweight = 'bold')
        self.graph1b.axes.plot(*splitSerToArr(line2.dropna()), 'r', label = "Current 1", linestyle ='dashed', marker ="o")
        self.graph1b.axes.tick_params(axis='y', labelcolor='tab:red')
        
        self.axes1b.set_ylabel('Current 2 (mA)', color = 'tab:blue', fontweight = 'bold')
        self.axes1b.plot(*splitSerToArr(line4.dropna()),'b',label = "Current 2", linestyle ='dashed', marker = "v")
        self.axes1b.tick_params(axis='y', labelcolor = 'tab:blue')
        plt.setp(self.graph1b.axes.get_xticklabels(), rotation = 30, horizontalalignment = 'right')
        self.graph1b.fig.legend(loc = 'upper right', bbox_to_anchor =(1.2,1.2), fancybox = True, shadow = True, ncol = 1, bbox_transform = self.graph1b.axes.transAxes)
        
        
        self.graph2.axes.cla()
        self.axes2.cla()
        self.graph2.axes.set_title("Temp$_\mathbf{internal}$ and Temp$_\mathbf{external}$", fontweight = 'bold')
        self.graph2.axes.set_xlabel("Time recorded", fontweight = 'bold')
        self.graph2.axes.set_ylabel('Temp$_\mathbf{internal}$ ($\circ$C)', color = 'tab:olive', fontweight = 'bold')
        self.graph2.axes.plot(*splitSerToArr(temp1Line.dropna()), 'y', label = 'Temp$_{int}$', linestyle ='dashed', marker ="o")
        self.graph2.axes.tick_params(axis='y', labelcolor='tab:olive')
        
        self.axes2.set_ylabel('Temp$_\mathbf{external}$ ($\circ$C)', color = 'tab:green', fontweight = 'bold')
        self.axes2.plot(*splitSerToArr(temp2Line.dropna()),'g', label = 'Temp$_{ext}$', linestyle ='dashed', marker = "v")
        self.axes2.tick_params(axis='y', labelcolor = 'tab:green')
        plt.setp(self.graph2.axes.get_xticklabels(), rotation = 30, horizontalalignment = 'right')
        self.graph2.fig.legend(loc = 'upper right', bbox_to_anchor =(1.3,1.2), fancybox = True, shadow = True, ncol = 1, bbox_transform = self.graph2.axes.transAxes)
        

        self.graph3.axes.cla()
        self.graph3.axes.set_title("pH", fontweight = 'bold')
        self.graph3.axes.set_xlabel("Time recorded", fontweight = 'bold')
        self.graph3.axes.set_ylabel('pH', color = 'tab:purple', fontweight = 'bold')
        self.graph3.axes.plot(*splitSerToArr(pHLine.dropna()), 'm', label = 'pH', linestyle ='dashed', marker ="o")
        self.graph3.axes.tick_params(axis='y', labelcolor='tab:purple')
        plt.setp(self.graph3.axes.get_xticklabels(), rotation = 30, horizontalalignment = 'right')
        self.graph3.axes.legend()
        
        self.graph1a.draw_idle()
        self.graph1b.draw_idle()
        self.graph2.draw_idle()
        self.graph3.draw_idle()
        
    def check_onlineDisplay(self):
        if self.onlineDisplay.text() == 'POLLING AND DATA LOGGING STOPPED':
            self.onlineDisplay.setStyleSheet("background-color: red")

        else:
            self.onlineDisplay.setStyleSheet("background-color: green")
    
    def closeEvent(self,event):
        global dev1, dev2
        global ps_outputStatus1, ps_outputStatus2
        global endThread, threadEnded
        exiting = QMessageBox.question(self, 'Exit Program', "Power supply outputs will be automatically turned off, are you sure you want to exit the program?", QMessageBox.Yes|QMessageBox.No)
        
        if exiting == QMessageBox.Yes:
            wait = QDialog()
            wait.setWindowTitle("Closing Application...")
            width = 500
            height = 100
            wait.setFixedSize(width,height)
            wait.setWindowIcon(QIcon("UI_Files/MECMonitoringIcon.ico")) # Set ICONS
            
            waitText = QLabel(wait)
            waitText.setGeometry(QRect(50,30,650,200))
            waitText.setStyleSheet('font: Century Gothic')
            waitText.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
            waitText.setText("Please wait as your application automatically exits")
            
            wait.show()
            
            endThread = True
            if not (dev1 == ''):
                PS1 = KoradSerial(dev1)
                PS1.output.off()
            
            if not (dev2 == ''):
                PS2 = KoradSerial(dev2)
                PS2.output.off()
                
            ps_outputStatus1 = False
            ps_outputStatus2 = False
            
            INI_write()
            
            while True:
                if threadEnded == True:
                    break
                loop = QEventLoop()
                QTimer.singleShot(1000, loop.quit)
                loop.exec_()
            event.accept()
        else:
            if not type(event) == bool:
                event.ignore()
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
