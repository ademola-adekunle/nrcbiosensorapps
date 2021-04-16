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
import copy
import string
import platform

if platform.system() == 'Linux':
    import fcntl
    from AtlasI2C import (
         AtlasI2C
    )

import matplotlib
matplotlib.use('QT5Agg')
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

current = pathlib.Path().absolute()

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

#Define resource path to access external files when using pyinstaller
def resourcepath(relative_path):
    #Get absolute path to resource and then appends correct file prefix
    try:
        #PYinstaller temp folder
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
        
    return os.path.join(base_path, relative_path)

def i2c_pHFunctions(device_id, check):
    global device_list
    foundDeviceFlag = False
    
    if platform.system() == 'Linux':
        for dev in device_list:
            text = dev.get_device_info().replace('\x00','')
            temp = re.findall(r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", text)
            testID = temp[0].strip()
            
            if testID == device_id:
                foundDeviceFlag = True
                
                if check == True:
                    dev.write("Cal,?")
                
                timeout = device_list[0].get_command_timeout("R")
                
                if(timeout):
                    time.sleep(timeout)
                    storage = dev.read().replace('\x00','')
                    temp_storage = storage.split(":")
                    temp = temp_storage[1].strip()
                    temp = temp.strip("?CAL,")
                    return (temp)
                
        if foundDeviceFlag == False:
            return "Not configured"
    else:
        return "Not configured"

if platform.system() == "Linux":
    uis = current / "KORAD_PS_DAQ/UI_Files"

elif platform.system() == "Windows":
    uis = "KORAD_PS_DAQ/UI_Files"
#------------------------------------------------------------------------------#
# Dialog
#------------------------------------------------------------------------------#
class pHNavigation(QDialog):
    
    def __init__(self, parent = None):
        global device_list, pHDevices
        super().__init__(parent)
        
        uic.loadUi(resourcepath(str(uis) + "/pHNavigation.ui"),self)
        self.setWindowIcon(QIcon(resourcepath(str(uis) + "/MECMonitoringIcon.ico"))) # Set ICONS
        
        flag = False
        if platform.system() == 'Linux':
            device_list = get_devices() #Finds I2C devices
            pHDevices = []
            for dev in device_list:
                text = str(dev.get_device_info().replace('\x00',''))
                if "pH" in text:
                    temp = re.findall(r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", text)
                    ID = temp[0].strip()
                    pHDevices.append(ID)
            
            pH = self.i2c_readwrite(pHDevices[0])
            if pH == "Not configured":
                warning = QMessageBox.warning(self, 'Error!', 'pH EZO circuit board not configured.\nMake sure it is running in I2C mode and is connected properly.')
            elif not pH == "Not configured":
                try:
                    if float(pH) <= 0 or float(pH) > 15 :
                        pH = "No probe connected"
                except Exception: 
                    pH = "No probe connected"
                    
            if not pH == "No probe connected":
                calCheck = i2c_pHFunctions(pHDevices[0],True)
                if calCheck == "Not configured":
                    warning = QMessageBox.warning(self, 'Error!', 'pH EZO circuit board not configured.\nMake sure it is running in I2C mode and is connected properly.')
                else:
                    flag = True
            else:
                warning = QMessageBox.warning(self, 'Error, probe not connected!', 'Probe is not connected.\nPlease make sure it is connected before trying again.')
        
        elif platform.system() == "Windows":
            warning = QMessageBox.warning(self, 'Platform error!', 'I2C functionality is not compatible with Windows.')
            
        if flag == False:
            sys.exit() #IN PROGRAM MEC, MAKE IT self.close()
            
        self.single = self.findChild(QPushButton,'single')
        self.two = self.findChild(QPushButton,'two')
        self.three = self.findChild(QPushButton,'three')
        self.cancel = self.findChild(QPushButton,'cancel')
        self.pHSelection = self.findChild(QComboBox,'pHSelection')
        
        for x in range(len(pHDevices)):
            self.pHSelection.addItem(pHDevices[x])
        
        self.single.clicked.connect(lambda: self.checkSelections(1, pHDevices[self.pHSelection.currentIndex()]))
        self.two.clicked.connect(lambda: self.checkSelections(2, pHDevices[self.pHSelection.currentIndex()]))
        self.three.clicked.connect(lambda: self.checkSelections(3, pHDevices[self.pHSelection.currentIndex()]))
        self.cancel.clicked.connect(self.close)
        
    def checkSelections(self, points, address):
        calCheck = i2c_pHFunctions(address,True)
        
        if calCheck == "0":
            prevCalib = QMessageBox.question(self, 'pH Calibration', 'There is no previous calibration data.\nWould you like to calibrate pH?', QMessageBox.Yes | QMessageBox.No)
        elif calCheck == "1":
            prevCalib = QMessageBox.question(self, 'Overwrite previous calibration?', 'There is previous calibration data.\nWould you like to overwrite the previous single point calibration?', QMessageBox.Yes | QMessageBox.No)
        elif calCheck == "2":
            prevCalib = QMessageBox.question(self, 'Overwrite previous calibration?', 'There is previous calibration data.\nWould you like to overwrite the previous two point calibration?', QMessageBox.Yes | QMessageBox.No)
        elif calCheck == "3":
            prevCalib = QMessageBox.question(self, 'Overwrite previous calibration?', 'There is previous calibration data.\nWould you like to overwrite the previous three point calibration?', QMessageBox.Yes | QMessageBox.No)
        else:
            warning = QMessageBox.warning(self, 'Error!', 'pH EZO circuit board not configured.\nMake sure it is running in I2C mode and is connected properly.')
            self.close()
            
        if prevCalib == QMessageBox.Yes:
            #EXEC CALIBRATION PROGRAM DIALOG -> Adjust based on points
            self.close()
            calib_dlg = CalibrationDialog(self, points, address)
            try:
                calib_dlg.show()
            except Exception:
                error = QMessageBox.warning(self, 'Error!', 'Calibration Settings Failed to Open')
        else:
            self.close()
        
    def i2c_readwrite(self, device_id):
        global device_list
        foundDeviceFlag = False
        
        if platform.system() == 'Linux':
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
        else:
            return "Not configured"
        
class CalibrationDialog(QDialog):
    update_TextSignal = pyqtSignal(str)
    update_statusSignal = pyqtSignal(str)
    messageBox_Signal = pyqtSignal(bool)
    
    def __init__(self, parent, points, address):
        super().__init__(parent)
        
        uic.loadUi(resourcepath(str(uis) + "/pHCalibration.ui"),self)
        self.setWindowIcon(QIcon(resourcepath(str(uis) + "/MECMonitoringIcon.ico"))) # Set ICONS
        
        self.points = int(points)
        self.address = str(address)
        
        self.status = self.findChild(QLabel,'status')
        self.i2cOutput = self.findChild(QTextEdit,'i2cOutput')
        self.i2cOutput.setReadOnly(True)
        self.i2cOutput.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)

        self.pHContinueMid = pHMessageBox(self, 1)
        self.pHContinueLow = pHMessageBox(self, 2)
        self.pHContinueHigh = pHMessageBox(self, 3)
        self.textEdit = ''
        self.update_TextSignal.connect(self.update_Text)
        self.update_statusSignal.connect(self.update_Status)
        self.messageBox_Signal.connect(self.showMessageBox)
        #Start threads
        self.runCalibThread()
    
    @QtCore.pyqtSlot(bool)
    def showMessageBox(self, failed):
        if failed == False:
            warning = QMessageBox.information(self, 'Calibration Finished', "The pH probe has been calibrated. You may exit safely now.")
            self.close()
        else:
            warning = QMessageBox.information(self, 'Calibration Failed', "Please close program and try again.")
            self.close()
            
    @QtCore.pyqtSlot(str)
    def update_Status(self,text):
        self.status.setText(text)
        
    @QtCore.pyqtSlot(str)
    def update_Text(self,text):
        self.i2cOutput.setText(text)
        self.i2cOutput.setReadOnly(True)
        self.i2cOutput.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    
    def runCalibThread(self):
        #self.pHContinueMid.exec_()
        tCalibThread = threading.Thread(target= self.calibThread1)
        tCalibThread.daemon = True
        tCalibThread.start()
                    
    def calibThread1(self):
        global calibcont, calibFailed, calibExit, calibWaiting, calibFinished
        calibExit = True
        calibFailed = False
        calibWaiting = False
        calibFinished = False
        
        if self.points >= 1 and calibFailed == False:
            calibcont = False
            self.pHContinueMid.show()
            while calibcont == False:
                time.sleep(1)
                
            if calibExit == False:
                self.stabilized = False
                self.textEdit = ''
                self.update_statusSignal.emit("pH Sensor Readings - Reaching steady state (Midpoint calibration)")

                prev = float(self.i2c_readwrite(self.address, "R"))
                self.textEdit += 'pH = '+ str(prev) + '\n'
                self.update_TextSignal.emit(self.textEdit)
                while self.stabilized == False:
                    time.sleep(0.2)
                    val = self.steadyStateTest(prev, 0)
                    self.stabilized = True
                
                if calibFailed == False and calibExit == False:
                    self.i2c_readwrite(self.address,"cal,mid,7")
                    self.update_statusSignal.emit("pH Sensor Readings - Steady state attained and new midpoint calibrated")
        
        if calibExit == False:
            if self.points >= 2 and calibFailed == False:
                calibcont = False
                calibExit = True
                self.pHContinueLow.show()
                while calibcont == False:
                    time.sleep(1)
                    
                if calibExit == False:
                    self.stabilized = False
                    self.textEdit = ''
                    self.update_statusSignal.emit("pH Sensor Readings - Reaching steady state (Lowpoint calibration)")
                    prev = float(self.i2c_readwrite(self.address, "R"))
                    self.textEdit += 'pH = '+ str(prev) + '\n'
                    self.update_TextSignal.emit(self.textEdit)
                    while self.stabilized == False:
                        time.sleep(0.2)
                        val = self.steadyStateTest(prev, 0)
                        self.stabilized = True
                    
                    if calibFailed == False and calibExit == False:
                        self.i2c_readwrite(self.address,"cal,low,4")
                        self.update_statusSignal.emit("pH Sensor Readings - Steady state attained and new lowpoint calibrated")
                        
        if calibExit == False:
            if self.points >= 3 and calibFailed == False:
                calibcont = False
                calibExit = True
                self.pHContinueHigh.show()
                while calibcont == False:
                    time.sleep(1)
                if calibExit == False:
                    self.stabilized = False
                    self.textEdit = ''
                    self.update_statusSignal.emit("pH Sensor Readings - Reaching steady state (Highpoint calibration)")
                    
                    prev = float(self.i2c_readwrite(self.address, "R"))
                    self.textEdit += 'pH = '+ str(prev) + '\n'
                    self.update_TextSignal.emit(self.textEdit)
                    while self.stabilized == False:
                        time.sleep(0.2)
                        val = self.steadyStateTest(prev, 0)
                        self.stabilized = True
                    
                    if calibFailed == False and calibExit == False:
                        self.i2c_readwrite(self.address,"cal,high,10")
                        self.update_statusSignal.emit("pH Sensor Readings - Steady state attained and new highpoint calibrated")
        
        calibFinished = True
        if calibExit == False:
            self.messageBox_Signal.emit(calibFailed)
        else:
            self.close()
            
    def closeEvent(self, event):
        global calibExit, calibWaiting, calibFinished
        
        if calibFinished == True:
            event.accept()
        
        else:
            calibWaiting = True
            exiting = QMessageBox.question(self, 'Cancel pH calibration', 'Are you sure you want to cancel pH calibration?', QMessageBox.Yes | QMessageBox.No)
        
            #If yes was selected
            if exiting == QMessageBox.Yes:
                calibExit = True
                calibWaiting = False
                event.accept()
            else:
                if not type(event) == bool:
                    calibWaiting = False
                    event.ignore()
        
    def i2c_readwrite(self, device_id, command):
        global device_list
        foundDeviceFlag = False
        
        if platform.system() == 'Linux':
            for dev in device_list:
                text = dev.get_device_info().replace('\x00','')
                temp = re.findall(r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", text)
                testID = temp[0].strip()
                
                if testID == device_id:
                    foundDeviceFlag = True
                    
                    dev.write(command)
                    
                    timeout = device_list[0].get_command_timeout("R")
                    
                    if(timeout):
                        time.sleep(timeout)
                        storage = dev.read().replace('\x00','')
                        temp_storage = storage.split(":")
                        return (temp_storage[1].strip())

    def steadyStateTest(self, previous, iterations):
        global calibFailed, calibWaiting, calibExit
        current = float(self.i2c_readwrite(self.address, "R"))
        self.textEdit += 'pH = '+ str(current) + '\n'
        self.update_TextSignal.emit(self.textEdit)
        
        while calibWaiting == True:
            loop = QEventLoop()
            QTimer.singleShot(500, loop.quit)
            loop.exec_()
            
        if calibExit == True:
            return 0
        
        if str(current) == "255" or str(current) == "254":
            self.textEdit += 'Calibration Error!\n'
            self.update_TextSignal.emit(self.textEdit)
            calibFailed = True
            return 0
        #If iterations == user entered iterations -> Return current MFC voltage value
        if iterations == 3:
            return current
        
        #If percent difference is within user selected tolerance (increase consecutive succesful iteration by 1) and repeat
        elif (self.percentDifference(previous, current)) <= 2:
            iterations+=1
            #Try to run it again recursively -> If stack overflow (Return current value) -> Treat current as previous for next iteration
            try:
                return self.steadyStateTest(current, iterations)
            except Exception:
                return current
        #Otherwise, reset consecutive succesful iteration to 0 and repeat
        else:
            iterations = 0
            #Try to run it again recursively -> If stack overflow (Return current value)
            try:
                return self.steadyStateTest(current, iterations)
            except Exception:
                return current
    
    def percentDifference(self, previous, current):
        if current == previous:
            return 0
        
        try:
            return(abs(current-previous)/previous)*100
        
        except ZeroDivisionError:
            return float('inf')
            

class pHMessageBox(QDialog):
    
    def __init__(self, parent, point):
        super().__init__(parent)
        
        uic.loadUi(resourcepath(str(uis) + "/pHContinueDialog.ui"),self)
        self.setWindowIcon(QIcon(resourcepath(str(uis) + "/MECMonitoringIcon.ico"))) # Set ICONS
        self.setModal(True)
        self.text = self.findChild(QLabel, "userInfo")
        self.cont = self.findChild(QPushButton, "cont")
        
        if point == 1:
            self.setWindowTitle("pH Calibration - Midpoint Test (pH = 7.00)")
            self.text.setText("Insert pH probe into pH 7.00 calibration solution. Press continue once you are ready.")
        elif point == 2:
            self.setWindowTitle("pH Calibration - Lowpoint Test (pH = 4.00)")
            self.text.setText("Insert pH probe into pH 4.00 calibration solution. Press continue once you are ready.")
        elif point == 3:
            self.setWindowTitle("pH Calibration - Highpoint Test (pH = 10.00)")
            self.text.setText("Insert pH probe into pH 10.00 calibration solution. Press continue once you are ready.")
        
        self.cont.clicked.connect(self.confirm)
    
    def confirm(self):
        global calibExit
        calibExit = False
        self.close()

    
    def closeEvent(self,event):
        global calibcont
        calibcont = True
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    pHNav = pHNavigation()
    pHNav.show()
    sys.exit(app.exec())