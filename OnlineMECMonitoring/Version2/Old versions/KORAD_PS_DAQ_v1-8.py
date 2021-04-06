## For first run on this machine, please follow Steps 1 to 3. Preferably run Python IDLE 3.7.x
# Step 1: Make sure pyserial module is installed.
# Step 2: Open and run KoradCli.py
# Step 3: Open and run Koradserial.py

## Other details.
# Port open, close and flush are carried out by the wrapper module.
# Computer is automatically locked during remote control. No need to send command to lock.
# Port is released after a timeout of no command from the shell or once the program reaches EOL.
# Tested for one power supply as of Jan 31, 2019.

# All icons used are from https://p.yusukekamiyamane.com/

import sys, glob, serial
from PyQt5 import uic, QtGui, QtCore
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QLabel, QVBoxLayout
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from pyqtgraph import PlotWidget
import pyqtgraph as pg
import time
from unittest import TestCase, main
import datetime
#import threading
import koradserial
from koradserial import KoradSerial
import os
import configparser
from configparser import ConfigParser
from random import randint # DEMO ONLY

global dLogInterval, dAqInterval, dAqON, runPS1, fileName, koradports, ports

#------------------------------------------------------------------------------#
# FUNCTIONS
#------------------------------------------------------------------------------#
def serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result

def INI_write(): # function to write an INI file
    global ps1Voltage, ps1CurrentMax, ps1VoltageMax, runPS1, dLogInterval, dAqInterval, dAqON, ovp_advset, ocp_advset, koradports, fileName, y1_var, y2_var, data_points_int
    cfgfile = open("INI/psSettings.ini",'w') #INI file creation. I would take this from the final code. This is just for the test
    parser = ConfigParser()
    parser.read("INI/psSettings.ini")

    parser.add_section('Settings')
    parser.set('Settings', 'ps1Voltage', str(ps1Voltage))
    parser.set('Settings', 'ps1Current', str(ps1CurrentMax))
    parser.set('Settings', 'userdefined_MaxPS1Voltage', str(ps1VoltageMax))
    parser.set('Settings', 'runPS1', str(runPS1))
    parser.set('Settings', 'dLogInterval', str(dLogInterval))
    parser.set('Settings', 'dAqInterval', str(dAqInterval))
    parser.set('Settings', 'dAqON', str(dAqON))
    parser.set('Settings', 'datalog filename', fileName)

    parser.add_section('Advanced Settings')
    parser.set('Advanced Settings', 'Over Voltage Protection (OVP)', ovp_advset)
    parser.set('Advanced Settings', 'Over Current Protection (OCP)', ocp_advset)

    parser.add_section('COM Ports')
    try: # exception catch in case there are no COM ports recognized
        for i in range(len(koradports)):
            parser.set('COM Ports', 'Korad port #%i' %i, str(koradports[i]))

    except Exception:
        pass

    parser.add_section('Plot Settings')
    parser.set('Plot Settings', 'y1', y1_var)
    parser.set('Plot Settings', 'y2', y2_var)
    parser.set('Plot Settings', 'number of data points', str(data_points_int))

    with open("INI/psSettings.ini",'w') as configfile:
        parser.write(configfile)
    configfile.close()

def INI_read(): # function to read an INI file
    global ps1, ps1Voltage, ps1CurrentMax, ps1VoltageMax, runPS1, dLogInterval, dAqInterval, dAqON, ocp_advset, ovp_advset, koradports, fileName, y1_var, y2_var, data_points_int
    #cfgfile = open("INI/psSettings.ini",'r') #INI file creation. I would take this from the final code. This is just for the test
    parser = ConfigParser()
    parser.read("INI/psSettings.ini")

    # Acquiring the values from the INI file
    ps1Voltage = float(parser.get("Settings", 'ps1Voltage'))
    ps1CurrentMax = float(parser.get("Settings", 'ps1Current'))
    ps1VoltageMax = float(parser.get("Settings", 'userdefined_MaxPS1Voltage'))
    runPS1 = parser.get("Settings", 'runPS1')
    dLogInterval = float(parser.get("Settings", 'dLogInterval'))
    dAqInterval = float(parser.get("Settings", 'dAqInterval'))
    dAqON = parser.get("Settings", 'dAqON')
    fileName = parser.get("Settings", 'datalog filename')

    ovp_advset = parser.get("Advanced Settings", 'Over Voltage Protection (OVP)')
    ocp_advset = parser.get("Advanced Settings", 'Over Current Protection (OCP)')

    try:
        for i in range(len(koradports)):
            koradports.append(parser.get("COM Ports", 'Korad Port #%i' %i))

    except Exception:
        pass

    y1_var = parser.get("Plot Settings", 'y1')
    y2_var = parser.get("Plot Settings", 'y2')
    data_points_int = int(parser.get("Plot Settings", 'number of data points'))

def PS_check(comport):
    global ps1, koradports
    ps1 = KoradSerial(comport) # sets serial port to be the COM1/2/3/4 selected by user in combobox

    if ps1:
        ps1Aval = True
        if ps1.is_open == False:
            ps1.open()

        else:
            pass

    else:
        ps1Aval = False

    return ps1Aval

def PS_write():
    global ps1, ps1Voltage, ps1CurrentMax, ocp_advset, ovp_advset
    ps1.channels[0].voltage = ps1Voltage
    ps1.channels[0].current = ps1CurrentMax

    if ovp_advset == 'on':
        ps1.over_voltage_protection.on()

    else:
        ps1.over_voltage_protection.off()

    if ocp_advset == 'on':
        ps1.over_current_protection.on()

    else:
        ps1.over_current_protection.off()

def PS_read():
    global ps1CurrentOut, ps1VoltageOut, ps1Status
    ps1CurrentOut = ps1.channels[0].output_current * 1000 # retrieve current outputted by PS
    ps1VoltageOut = ps1.channels[0].output_voltage # retrieve volrage outputted by PS
    #ps1Status = ps1.status.channel1 # retrieve the CC/CV status of the PS

def get_datalog():
    global fileName

    if not os.path.exists("Data_Logs"):
        os.makedirs("Data_Logs")

    if not os.path.exists('Data_Logs/%s' %fileName): # For a new file, the headers are added as the first line
        log = open('Data_Logs/%s' %fileName, "a")
        headers = ['Date', 'Vps1', 'Ips1']
        headers = ' '.join(headers)
        log.write(headers +'\n') # write headers to file
        log.close()

    log = open('Data_Logs/%s' %fileName, "a")

    return log
#------------------------------------------------------------------------------#
# START-UP ACTIONS
#------------------------------------------------------------------------------#
global ports, koradports, ovp_advset, ocp_advset, y1_var, y2_var, data_points_int

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
    if not os.path.exists("/home/pi/KORAD_PS_DAQ"): # and there's no directory folder
        os.makedirs("/home/pi/KORAD_PS_DAQ")

    os.chdir("/home/pi/KORAD_PS_DAQ")

    if not os.path.exists("INI"):
        os.makedirs("INI")

    if not os.path.exists("UI_Files"):
        os.makedirs("UI_Files")

if not os.path.exists("INI/psSettings.ini"):
    ps1Voltage = 1.4
    ps1CurrentMax = 2.0
    ps1VoltageMax = 3.0
    dLogInterval = 20.0
    dAqInterval = 1.0
    runPS1 = False
    dAqON = False
    fileName = 'DataLoggingFile.txt'
    ocp_advset = 'off'
    ovp_advset = 'on'
    y1_var = 'Current'
    y2_var = 'Voltage'
    data_points_int = 1500
    INI_write() # makes INI file with these standard initial conditions

INI_read()

ports = serial_ports()
koradports = []
koradserials = []
if ports: # if there are ports detected
    for i in range(len(ports)):
        if ports[i] == '/dev/ttyAMA0': # this is the serial port connected to the RPi's bluetooth
            pass # skips it

        else:
            koradports.append(str(ports[i]))

    INI_write()


try:
    ps1Aval = PS_check(koradports[0]) # checks if a PS is available, also defines ps1

    if ps1Aval == True:
        PS_read()
        PS_write()

        if runPS1 == 'False':
            ps1.output.off()
        else:
            ps1.output.on()

except Exception:
    pass

cfgfile = open("INI/psSettings.ini",'r') #INI file creation. I would take this from the final code. This is just for the test
parser = ConfigParser()
parser.read("INI/psSettings.ini")

log = get_datalog() # makes datalog file on first run
log.close() # get_datalog returns opened data log file, closed here
#------------------------------------------------------------------------------#
# DIALONG BOXES
#------------------------------------------------------------------------------#
class AdvSettings(QDialog):
    global ps1, ocp_advset, ovp_advset

    def __init__(self, *args, **kwargs):
        super(AdvSettings, self).__init__(*args, **kwargs)
        uic.loadUi("UI_Files/AdvSettings_v2-1.ui", self)

        self.setWindowTitle(u"Advanced PS Settings")

        self.ovpCheckBox.stateChanged.connect(self.ovp_state_changed)
        self.ocpCheckBox.stateChanged.connect(self.ocp_state_changed)

        self.advsetButtonBox.accepted.connect(self.accept)
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

class DataLogSettings(QDialog):

    def __init__(self, *args, **kwargs):
        super(DataLogSettings, self).__init__(*args, **kwargs)
        uic.loadUi("UI_Files/DataLogSettings_v2-1.ui", self)

        self.setWindowTitle('Data Log Settings')

        dispfileName = fileName.split('.txt') # gets the file ready to show without the .txt ending

        self.filenameLineEdit.setText(dispfileName[0])
        self.intervalLineEdit.setText(str(dLogInterval))
        self.aqintervalLineEdit.setText(str(dAqInterval))

class PlotSettings(QDialog):

    def __init__(self, *args, **kwargs):
        super(PlotSettings, self).__init__(*args, **kwargs)

        self.setWindowTitle('Plot Settings')

        QBtn = QDialogButtonBox.Ok

        self.buttonbox = QDialogButtonBox(QBtn)
        self.buttonbox.accepted.connect(self.accept)

        self.textlayout = QHBoxLayout()
        self.datapointsLabel = QLabel('# of visible data points on the plot:')
        self.datapointsLineEdit = QLineEdit(self)
        self.datapointsLineEdit.setText(str(data_points_int))

        self.textlayout.addWidget(self.datapointsLabel)
        self.textlayout.addWidget(self.datapointsLineEdit)

        self.boxlists = ['Current', 'Voltage']

        self.y1ComboBox = QComboBox(self)
        self.y1ComboBox.addItems(self.boxlists)

        if y1_var == 'Current':
            self.y1ComboBox.setCurrentText('Current')
        elif y1_var == 'Voltage':
            self.y1ComboBox.setCurrentText('Voltage')

        self.y2ComboBox = QComboBox(self)
        self.y2ComboBox.addItems(self.boxlists)

        if y2_var == 'Current':
            self.y2ComboBox.setCurrentText('Current')
        elif y2_var == 'Voltage':
            self.y2ComboBox.setCurrentText('Voltage')

        self.layout = QVBoxLayout()
        self.layout.addLayout(self.textlayout)
        self.layout.addWidget(self.y1ComboBox)
        self.layout.addWidget(self.y2ComboBox)
        self.layout.addWidget(self.buttonbox)
        self.setLayout(self.layout)

class StartUpDelay(QDialog): # OK Button needs removing for final program

    def __init__(self, *args, **kwargs):
        super(StartUpDelay, self).__init__(*args, **kwargs)

        self.setWindowTitle("Initializing program...")

        QBtn = QDialogButtonBox.Ok

        self.buttonbox = QDialogButtonBox(QBtn)
        self.buttonbox.accepted.connect(self.accept)

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

    def delay_start(self):
        self.delaytimeleft = 0
        self.delaytimer.start()
        self.update_gui()

    def delay_timeout(self):
        self.delaytimeleft += 1
        self.progressbar.setValue(self.delaytimeleft)

        if self.delaytimeleft == 15:
            self.delaytimerDisplay.setText('Initializing program...')
            time.sleep(1)
            self.delaytimer.stop()
            self.close()

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
    global ps1, ps1Voltage, ps1CurrentMax, ps1VoltageMax, ps1Status

    def __init__(self, *args, **kwargs):
        global is_editing_setvals, koradports
        super(MainWindow, self).__init__(*args, **kwargs)
        uic.loadUi("UI_Files/RPi_GUI_v1-6.ui", self)

        #self.setWindowIcon(QIcon(r"Icon_Store\icons\lightning.png"))
        self.setWindowTitle('KORAD PS DAQ')

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1000) # Timer counts down one second
        self.timer.timeout.connect(self.on_timeout)
        self.first_timer_start = True # for start_time assignment check in timer_start

        self.onlineDisplay.textChanged.connect(self.check_onlineDisplay)
        self.onlineDisplay.setText('DATA LOGGING OFFLINE') # sets onlineDisplay's default to say it's offline

        self.setvoltageDisplay.setText(str(ps1Voltage))
        self.maxvoltageDisplay.setText(str(ps1VoltageMax))
        self.maxcurrentDisplay.setText(str(ps1CurrentMax))

        self.setvoltageDisplay.setStyleSheet('background-color: lightgray')
        self.maxvoltageDisplay.setStyleSheet('background-color: lightgray')
        self.maxcurrentDisplay.setStyleSheet('background-color: lightgray')

        is_editing_setvals = False
        self.settingsEditButton.clicked.connect(self.on_setEdit_button_clicked)
        self.settingsOKButton.clicked.connect(self.on_setOK_button_clicked)
        self.advsetButton.clicked.connect(self.on_advset_button_clicked)

        self.datalogButton.clicked.connect(self.on_datalog_button_clicked)
        self.plotsetButton.clicked.connect(self.on_plotset_button_clicked)

        self.startButton.clicked.connect(self.on_start_button_clicked)
        self.startButton.setText('START')

        self.findPSButton.clicked.connect(self.on_findPS_button_clicked)

        for i in range(len(koradports)):
            self.comBox.addItem(str(koradports[i])) # use this to save them to INI too?

        self.statusbar.setStyleSheet('background-color: lightgray')

        # initialising the x and y plotting variables (1 = left axis, 2 = right axis)
        self.x = []
        self.y1 = []
        self.y2 = []
        self.y1plot = []
        self.y2plot = []

        color = self.palette().color(QtGui.QPalette.Window)  # Get the default window background,
        self.graphWidget.setBackground(color)
        # Add Title
        self.graphWidget.setTitle('MEC Data', color="k", size="12pt")
        # Making plot's axis lines black
        axispen = pg.mkPen(color='k')
        self.graphWidget.plotItem.getAxis('left').setPen(axispen)
        self.graphWidget.plotItem.getAxis('right').setPen(axispen)
        self.graphWidget.plotItem.getAxis('bottom').setPen(axispen)
        self.graphWidget.plotItem.showAxis('right', show=True)
        #Add legend
        self.graphWidget.addLegend()
        #Add grid
        self.graphWidget.showGrid(x=True, y=True)

        self.pen1 = pg.mkPen(color = 'r', width = 4, marker = '.')
        self.pen2 = pg.mkPen(color = 'b', width = 4, marker = '.')
        self.data_line1 = self.graphWidget.plot(self.x, self.y1, pen = self.pen1, symbolBrush = 'r', symbol = 'o')
        self.data_line2 = self.graphWidget.plot(self.x, self.y2, pen = self.pen2, symbolBrush = 'b', symbol = 'o')

        self.graphWidget.addLegend()

    def on_findPS_button_clicked(self):
        global koradports
        ports = serial_ports()
        koradports = []
        koradserials = []

        if ports: # if there are ports detected
            self.statusbar.clearMessage()
            for coms in ports:
                try:
                    KoradSerial(coms)
                    koradserials.append(str(coms))

                except Exception:
                    pass

                for i in range(len(koradserials)):
                    koradports.append(str(koradserials[i]))

            if not koradports: # if no koradports are found
                self.statusbar.showMessage("No korad serial ports detected!")

        else:
            self.statusbar.showMessage("No serial ports detected!")

    def on_setEdit_button_clicked(self):
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

    def on_setOK_button_clicked(self):
        global is_editing_setvals, runPS1, dAqFlag, ps1Voltage, ps1VoltageMax, ps1CurrentMax

        if is_editing_setvals == False:
            pass
        elif float(self.setvoltageDisplay.text()) > float(self.maxvoltageDisplay.text()):
            self.statusbar.showMessage("Error: The set voltage must not be greater than the max voltage!")
        else:
            is_editing_setvals = False

            displayfont = self.setvoltageDisplay.font()
            displayfont.setPointSize(10)

            self.statusbar.clearMessage()
            self.setvoltageDisplay.setReadOnly(True)
            self.setvoltageDisplay.setStyleSheet("background-color: lightgray")
            self.setvoltageDisplay.setFont(displayfont)
            self.maxvoltageDisplay.setReadOnly(True)
            self.maxvoltageDisplay.setStyleSheet("background-color: lightgray")
            self.maxvoltageDisplay.setFont(displayfont)
            self.maxcurrentDisplay.setReadOnly(True)
            self.maxcurrentDisplay.setStyleSheet("background-color: lightgray")
            self.maxcurrentDisplay.setFont(displayfont)

            ps1Voltage = float(self.setvoltageDisplay.text())
            ps1VoltageMax = float(self.maxvoltageDisplay.text())
            ps1CurrentMax = float(self.maxcurrentDisplay.text())

            INI_write()
            PS_write()

    def on_advset_button_clicked(self):
        global ps1, ocp_advset, ovp_advset
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

        if self.AdvSettings.exec_(): # if the user clicks OK
            self.check_advset() # checks which boxes are selected, updates INI file

        else: # if the user clicks Cancel
            pass

    def check_advset(self):
        global ps1, ovp_advset, ocp_advset

        if self.AdvSettings.ovpCheckBox.isChecked() == True:
            ovp_advset = 'on'
            ocp_advset = 'off'

        elif self.AdvSettings.ocpCheckBox.isChecked() == True:
            ovp_advset = 'off'
            ocp_advset = 'on'

        else:
            ovp_advset = 'off'
            ocp_advset = 'off'

        INI_write() # updates INI file

    def on_plotset_button_clicked(self):
        global y1_var, y2_var, data_points_int
        self.PlotSettings = PlotSettings()
        self.PlotSettings.show()

        if self.PlotSettings.exec_():
            data_points_int = int(self.PlotSettings.datapointsLineEdit.text())
            y1_var = self.PlotSettings.y1ComboBox.currentText()
            y2_var = self.PlotSettings.y2ComboBox.currentText()

            INI_write() # to update y1_var, y2_var, data_points_int in INI

            self.PlotSettings.close()

        else:
            self.PlotSettings.close()
            pass

    def check_plot_vars(self):
        global y1_var, y2_var, y1_label, y2_label

        if y1_var == 'Current':
            self.y1 = ps1.channels[0].output_current * 1000 # * 1000 for A to mA
            y1_label = 'Current, mA'

        elif y1_var == 'Voltage':
            self.y1 = ps1.channels[0].output_voltage
            y1_label = 'Voltage, V'

        if y2_var == 'Current':
            self.y2 = ps1.channels[0].output_current * 1000 # * 1000 for A to mA
            y2_label = 'Current, mA'

        elif y2_var == 'Voltage':
            self.y2 = ps1.channels[0].output_voltage
            y2_label = 'Voltage, V'

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
        global ps1, is_editing_setvals

        if self.startButton.isChecked() == True:
            if is_editing_setvals == True:
                self.statusBar.showMessage("Can not start a run when editing the PS Settings!")

            else:
                ps1Aval = PS_check(self.comBox.currentText())

                if ps1Aval == False:
                    self.startButton.setText('START')
                    self.onlineDisplay.setText('DATA LOGGING OFFLINE')
                    self.statusbar.showMessage("Error: Can not connect to PS through specified COM port")
                    pass

                else:
                    self.startButton.setText('STOP')
                    self.onlineDisplay.setText('DATA LOGGING ONLINE')
                    INI_read() # applies specifications stored in INI file

                    try:
                        ps1.open() # opens ps1 port

                    except Exception: # if ps1 port is already open; returns error
                        pass # skips this error

                    dAqON = True
                    runPS1 = True
                    INI_write() # to update dAqON and runPS1 bools in INI

                    PS_read()
                    PS_write()
                    ps1.output.on()

                    #self.statusbar.showMessage(str(ps1Status)) # displays cc/cv
                    self.timer_start()

        else: # to stop:
            self.startButton.setText('START')
            self.onlineDisplay.setText('DATA LOGGING OFFLINE')
            self.timer.stop()
            ps1.output.off()

            dAqON = False
            runPS1 = False

            INI_write() # to update dAqON and runPS1 bools in INI

    def timer_start(self):
        if self.first_timer_start == True:
            self.start_time = time.monotonic()
            self.first_timer_start = False # so any future timer_start calls will not assign a start_time

        self.get_telem() # retrieves the telemetry from the power source
        self.dlog_time_left_int = int(dLogInterval * 60) # * 60 minutes -> seconds
        self.daq_time_left_int = int(dAqInterval * 60) # * 60 minutes -> seconds
        self.timer.start()
        self.update_timer_display()

        self.currentDisplay.setText(str(ps1.channels[0].output_current * 1000)) # * 1000 for A to mA
        self.voltageDisplay.setText(str(ps1.channels[0].output_voltage))

        self.check_plot_vars() # to get y1 and y2 variables
        time_xaxis = time.monotonic() - self.start_time
        self.update_plot(time_xaxis, self.y1, self.y2)

    def on_timeout(self):
        self.dlog_time_left_int -= 1
        self.daq_time_left_int -= 1

        if self.dlog_time_left_int == 0: # when the data log timer reaches 0
            self.dlog_time_left_int = int(dLogInterval * 60) # * 60 minutes -> seconds
            self.get_telem() # retrieves the telemetry from the power source

        if self.daq_time_left_int == 0: # when the data acquitistion timer reaches 0
            self.daq_time_left_int = int(dAqInterval * 60) # * 60 minutes -> seconds

            self.currentDisplay.setText(str(ps1.channels[0].output_current * 1000)) # * 1000 for A to mA
            self.voltageDisplay.setText(str(ps1.channels[0].output_voltage))

            self.check_plot_vars() # to get y1 and y2 variables
            time_xaxis = time.monotonic() - self.start_time
            self.update_plot(time_xaxis, self.y1, self.y2)

        self.update_timer_display()

    def update_timer_display(self):
        self.timerLabel.setText(time.strftime('%M:%S', time.gmtime(self.dlog_time_left_int)))

    def get_telem(self):
        date = datetime.datetime.now()
        # needs all data, including temperature and pH
        ps1V = ps1.channels[0].output_voltage
        ps1C = ps1.channels[0].output_current * 1000 # * 1000 for A to mA

        data = [str(date),str(ps1V),str(ps1C)]
        data = ' '.join(data)

        log = get_datalog()
        log.write(data + '\n') # write data to file
        log.close()

    def update_plot(self, date, y1, y2):
        global data_points_int, y1_label, y2_label

        if len(self.y1plot) == data_points_int: # if the plot has the max # of data points
            self.y1plot = self.y1plot[1:] # removes 1st element of the y1 array
            self.y2plot = self.y2plot[1:] # removes 1st element of the y2 array
            self.x = self.x[1:] # removes 1st element of the x array

        self.stringaxis = pg.AxisItem(orientation='bottom')
        self.x.append(time.strftime("%M:%S", time.localtime(date)))
        self.xplot = dict(enumerate(self.x))
        self.stringaxis.setTicks([self.xplot.items()])
        self.graphWidget.plotItem.setAxisItems(axisItems = {'bottom' : self.stringaxis})
        self.xplot = list(self.xplot.keys())

        self.graphWidget.setLabel("bottom", "Time, date", **{"color": "k", "font-size": "10pt"})
        self.graphWidget.setLabel("left", y1_label, **{"color": "k", "font-size": "10pt"})
        self.graphWidget.setLabel("right", y2_label, **{"color": "k", "font-size": "10pt"})

        self.y1plot.append(y1)
        self.y2plot.append(y2)

        self.data_line1.setData(self.xplot, self.y1plot)
        self.data_line2.setData(self.xplot, self.y2plot)



    def check_onlineDisplay(self):
        if self.onlineDisplay.text() == 'DATA LOGGING OFFLINE':
            self.onlineDisplay.setStyleSheet("background-color: red")

        else:
            self.onlineDisplay.setStyleSheet("background-color: green")
#------------------------------------------------------------------------------#
# RUNNING THE APP
#------------------------------------------------------------------------------#
app = QApplication(sys.argv)
main = MainWindow()
delay = StartUpDelay()
delay.show()

if delay.exec_():
    main.show()
else:
    main.show()

app.exec_()

try:
    ps1.output.off() # for safety reasons in development
    ps1.close()

except NameError:
    pass
