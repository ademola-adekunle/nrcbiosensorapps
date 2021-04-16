import sys, glob, serial, os
import serial.tools.list_ports

import PyQt5
from PyQt5 import QtWidgets, QtCore, QtGui, uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

import fcntl
import time, datetime
from AtlasI2C import (
     AtlasI2C
)

import io
import re
import copy
import string
import numpy as np
import pandas as pd

#Used to find file path
import pathlib
from pathlib import Path

current = pathlib.Path().absolute()

uis = current / "UI_Files"


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

def i2c_readwrite(device_id, command):
        global device_list
        foundDeviceFlag = False
        
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
                
        if foundDeviceFlag == False:
            return "No device found"

#------------------------------------------------------------------------------#
# DIALOGS
#------------------------------------------------------------------------------#
class CalibrationForm(QDialog):
    
    def __init__(self):
        global pumpAddress, calibrationCancelled
        super().__init__()
        uic.loadUi(str(uis) +'/calibrationForm.ui',self)
        
        self.testVolume = self.findChild(QDoubleSpinBox, 'testVolume')
        self.saveForm = self.findChild(QPushButton, 'saveForm')
        self.cancel = self.findChild(QPushButton, "cancel")
        calibrationCancelled = True
        
        self.saveForm.clicked.connect(self.startCalibration)
        self.cancel.clicked.connect(self.close)
    
    def startCalibration(self):
        global pumpAddress
        
        if self.testVolume.value() < 0.5:
            wrongValue = QMessageBox.warning(self, 'Error! Dispense Value too low', 'Dispense value is too low.\nThe minimum dispensing value is 0.5 mL.')
        else:
            self.close()
            formattedFloat = "{:.2f}".format(self.testVolume.value())
            msg = i2c_readwrite(pumpAddress, "D," + str(self.testVolume.value()))
            
            #Wait text
            wait = QDialog()
            wait.setModal(True)
            wait.setWindowTitle("Dispensing")
            width = 500
            height = 100
            wait.setFixedSize(width, height)
            #wait.setWindowIcon(QtGui.QIcon(str(uis) + '/NRCLogo.ico'))
            
            #Set DialogText Settings and stlying
            waitText = QLabel(wait)
            waitText.setGeometry(QRect(50, 30, 500, 200))
            waitText.setStyleSheet("font-family: Century Gothic")
            waitText.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
            waitText.setText("Dispensing... \nPlease wait until the operation is over.")
            
            #Show Text and wait until loaded parameter is true (Aka, main page is done loading)
            wait.show()
            loop = QEventLoop()
            QTimer.singleShot(500, loop.quit) #Pauses UI for half a second and loops
            loop.exec_()

            while True:
                msg = i2c_readwrite(pumpAddress, "D,?")
                if msg == "?D,"+ formattedFloat +",0":
                    break
                
            wait.close()
            
            calibEntry = CalibrationEntry()
            
            try:
                calibEntry.exec_()
            except Exception:
                warning = QMessageBox.warning(self,"Dialog failed to execute","Calibration Entry failed to open.\nCheck file permissions and file locations")

            
class CalibrationEntry(QDialog):
    
    def __init__(self):
        global pumpAddress, calibrationCancelled
        super().__init__()
        uic.loadUi(str(uis) +'/calibrationEntry.ui',self)
        
        self.actualVolume = self.findChild(QDoubleSpinBox, 'actualVolume')
        self.saveForm = self.findChild(QPushButton, 'saveForm')
        self.cancel = self.findChild(QPushButton, "cancel")
        calibrationCancelled = True
        self.saveForm.clicked.connect(self.calibrationEntry)
        self.cancel.clicked.connect(self.close)
        
    def calibrationEntry(self):
        global pumpAddress, calibrationCancelled
        
        if self.actualVolume.value() < 0.5:
            wrongValue = QMessageBox.warning(self, 'Error! Dispense Value too low', 'Dispense value is too low.\nThe minimum dispensing value is 0.5 mL.')
        else:
            msg = i2c_readwrite(pumpAddress, "Cal," + str(self.actualVolume.value()))
        calibrationCancelled = False
        self.close()

class OtherDispensingOptions(QDialog):
    
    def __init__(self):
        super().__init__()
        uic.loadUi(str(uis) +'/OtherDispensingOptionsDialog.ui',self)
#------------------------------------------------------------------------------#
# Main Window
#------------------------------------------------------------------------------#
class PumpMainPage(QMainWindow):
    update_statusbarSignal = pyqtSignal(str,bool)

    def __init__(self):
        global device_list, pumpAddress, continuousDispensing
        super().__init__()
        
        device_list = get_devices()
        
        
        PMPDevices = []
        for dev in device_list:
            text = str(dev.get_device_info().replace('\x00',''))
            if "PMP" in text:
                temp = re.findall(r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", text)
                ID = temp[0].strip()
                PMPDevices.append(ID)
        if len(PMPDevices) == 0:
            warning = QMessageBox.warning(self, 'Error! No EZO pump found.', 'EZO pump not found.\nMake sure it is running in I2C mode and is connected properly.')
            self.close()
            
        pumpAddress = PMPDevices[0]
        
        temp = i2c_readwrite(pumpAddress, "Dstart,?")
        text = re.findall(r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", temp.strip())
        defaultStartUpDispense = float(text[0])
        
        uic.loadUi(str(uis) +"/EzoMainPage.ui", self)
        
        continuousDispensing = False
        
        self.calibratePumpButton = self.findChild(QPushButton,"calibratePumpButton")
        self.openOtherOptions = self.findChild(QPushButton, 'openOtherOptions')
        self.start_stopButton = self.findChild(QPushButton, 'start_stopButton')
        self.saveStartUpDispense = self.findChild(QPushButton, 'saveStartUpDispense')
        
        self.statusbar = self.findChild(QStatusBar, 'statusbar')
        
        self.startupVol = self.findChild(QDoubleSpinBox, 'startupVol')
        self.startupVol.setValue(defaultStartUpDispense)
        
        self.start_stopButton.setStyleSheet("background-color: green")
        self.start_stopButton.setText('START')
        
        self.update_statusbarSignal.connect(self.update_statusbar)

        self.calibratePumpButton.clicked.connect(self.calibratePump)
        self.openOtherOptions.clicked.connect(self.openOtherOptionsDialog)
        self.start_stopButton.clicked.connect(self.continuousReading)
        self.saveStartUpDispense.clicked.connect(self.startupDispense)
        
    @QtCore.pyqtSlot(str,bool)
    def update_statusbar(self,text, flag):
        if flag == True:
            self.statusbar.setStyleSheet("color: green; font:italic;")
        else:
            self.statusbar.setStyleSheet("color: red; font:italic;")
        self.statusbar.showMessage(text)
    
    def calibratePump(self):
        global continuousDispensing, calibrationCancelled, pumpAddress
        contCalib = QMessageBox.question(self, 'Pump Calibration', 'Pump calibration will stop all dispensing operations.\nWould you like to calibrate the pump?', QMessageBox.Yes | QMessageBox.No)
        
        if contCalib == QMessageBox.Yes:
            if continuousDispensing == True:
                self.start_stopButton.toggle()
                self.start_stopButton.setStyleSheet("background-color: green")
                self.start_stopButton.setText('START')
                msg = i2c_readwrite(pumpAddress, "X")
            
            calibForm = CalibrationForm()
        
            
            try:
                calibForm.exec_()
            except Exception:
                warning = QMessageBox.warning(self,"Dialog failed to execute","Calib form failed to open.\nCheck file permissions and file locations")
            
            if calibrationCancelled == True:
                self.update_statusbarSignal.emit("Calibration failed", False)
            else:
                self.update_statusbarSignal.emit("Calibration sucessful", True)


    def openOtherOptionsDialog(self):
        optionsDialog = OtherDispensingOptions()
        
        try:
            optionsDialog.exec_()
        except Exception:
            warning = QMessageBox.warning(self,"Dialog failed to execute","Options dialog failed to open.\nCheck file permissions and file locations")
            
    def continuousReading(self):
        global continuousDispensing, pumpAddress
        
        if self.start_stopButton.isChecked():
            self.start_stopButton.setEnabled(False)
            self.start_stopButton.setStyleSheet("background-color: red")
            self.start_stopButton.setText('STOP')
            continuousDispensing = True
            msg = i2c_readwrite(pumpAddress, "D,*")
            self.start_stopButton.setEnabled(True)
            self.update_statusbarSignal.emit("Continuous dispensing start", True)

        else:
            self.start_stopButton.setEnabled(False)
            self.start_stopButton.setStyleSheet("background-color: green")
            self.start_stopButton.setText('START')
            continuousDispensing = False
            msg = i2c_readwrite(pumpAddress, "X")
            self.start_stopButton.setEnabled(True)
            self.update_statusbarSignal.emit("Continuous dispensing stopped", False)

    
    def startupDispense(self):
        global pumpAddress
        if self.startupVol.value() < 0.5:
            wrongValue = QMessageBox.warning(self, 'Error! Dispense Value too low', 'Dispense value is too low.\nThe minimum dispensing value is 0.5 mL.')
            self.update_statusbarSignal.emit("Error! Low dispense value", False)
        else:
            msg = i2c_readwrite(pumpAddress, "Dstart," + str(self.startupVol.value()))
            if msg == "255" or msg == "254":
                self.update_statusbarSignal.emit("Writing error. Please try again!", False)
            else:
                self.update_statusbarSignal.emit("Dispense " + str(self.startupVol.value()) + "mL on start-up sucessfully saved", True)

        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    mainPage = PumpMainPage()
    mainPage.show()
    sys.exit(app.exec())