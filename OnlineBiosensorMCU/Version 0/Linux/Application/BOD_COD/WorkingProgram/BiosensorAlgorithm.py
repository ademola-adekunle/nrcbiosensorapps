import matplotlib
matplotlib.use ("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.figure import Figure
import matplotlib.animation as animation
import matplotlib as plt
plt.rcParams['keymap.save']=''
plt.rcParams['keymap.pan']=''
plt.rcParams['keymap.yscale']=''
plt.rcParams['keymap.xscale']=''
import threading
from threading import Thread
from multiprocessing import Process, Queue, Pool
import Tkinter
from Tkinter import *
from Tkinter import Tk
import tkFileDialog
from tkFileDialog import askopenfilename
import tkMessageBox
import ttk
import datetime
import os
import random
#import u3
import time #use time.time()atical calculations
from scipy.integrate import simps #for mathematical calculations
from numpy import trapz #for mathematical calculations
import numpy as np
import threading
import xlrd
import math
import pandas as pd
import tkSimpleDialog
from matplotlib import pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures, FunctionTransformer
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from functools import partial
import ConfigParser
from ConfigParser import SafeConfigParser
parser = SafeConfigParser()
parser2 = SafeConfigParser()
pd.set_option("xlsx", "openpyxl")
import sys
import glob
import serial
import serial.tools.list_ports
import io
import time

#parser.read ("/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/Configuration/biosensorconfig.ini") #location of biosensor configuration/parameters for floating sensor #raspberry pi
#parser2.read ("/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/Configuration/biosensorconfig2.ini") #location of biosensor configuration/parameters for flow through sensor #raspberry pi

global configfile1path
global configfile2path
global BiosensingDataFolder
global BODExcelLocation

#the filepaths are applicable for Windows
##configfile1path = r'C:\\Users\adekunlea\Documents\OnlineBiosensorLinux_BOD_COD\Configuration\biosensorconfig.ini'
##configfile2path = r'C:\\Users\adekunlea\Documents\OnlineBiosensorLinux_BOD_COD\Configuration\biosensorconfig2.ini'
##BiosensingDataFolder = r'C:\Users\adekunlea\Documents\OnlineBiosensorLinux_BOD_COD\BiosensingData'
##BODExcelLocation = r'C:\Users\adekunlea\Documents\OnlineBiosensorLinux_BOD_COD\BiosensingData\BOD_Calibration_Data - Copy - Copy.xlsx' #Windows. need to change for Raspberry Pi

#these are the filepaths for Debian/Raspberry Pi
configfile1path = r'/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/Configuration/biosensorconfig.ini'
configfile2path = r'/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/Configuration/biosensorconfig2.ini'
BiosensingDataFolder = r'/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/BiosensingData'
BODExcelLocation = r'/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/BiosensingData/Calibration_Data.xlsx'

#Sheet and tab names
calib_data_sheet_name = 'Values'
COD_BOD_calibration_file = pd.ExcelFile(BODExcelLocation)

#Configure SERIAL PORTS
ports = serial.tools.list_ports.comports()

biosensor_ports = []

serial_objects = []

for ps in ports:
    if '0483:374B' in ps.hwid:
        biosensor_ports.append(ps.device)

for b in biosensor_ports:
    ser = serial.Serial(
        port = b,
        baudrate = 921600,
        parity = serial.PARITY_NONE,
        stopbits = serial.STOPBITS_ONE,
        bytesize = serial.EIGHTBITS,
        timeout=0.1,
        write_timeout=5.0,
        inter_byte_timeout=1.0
    )
    serial_objects.append(ser)

def GetRload(channel):
    time.sleep(0.05)
    serial_objects[channel].reset_input_buffer()
    serial_objects[channel].write(b"GetParam RLoad\r")
    serial_objects[channel].read_until(b"Value:")
    text = serial_objects[channel].read_until(b" O")
    text = text.strip(b"O")
    text = text.strip().decode()
    return(text)

global calib_rows
global calib_columns
global dfs
global dfs_old

dfs_old = dfs = pd.read_excel(BODExcelLocation, sheet_name=calib_data_sheet_name, header=0, delim_whitespace=True, skipinitialspace=True)
(calib_rows, calib_columns) = dfs.shape
print calib_rows
print calib_columns

parser.read(configfile1path)
parser2.read(configfile2path)

#read initialization file for floating MFC
tolerance = float(parser.get ("Parameters",'tolerance')) #value to change
Vmin = float(parser.get ("Parameters",'vmin'))#lower boundary
alpha1 = float (parser.get ("Parameters",'alpha1')) #voltage filter
graphspan = float (parser.get  ("Parameters",'graphspan')) #span of graph
filesaveflag = float (parser.get ("Parameters",'filesaveflag')) #default is not to save
restarter = float (parser.get ("Parameters",'restarter')) #does the program need to start acquisition?
delay = float(parser.get ("Parameters",'delay'))#time to wait for signal to stabilize when connected
y2limit = float(parser.get ("Parameters",'y2limit'))#ylim of graph
y3limit = float(parser.get ("Parameters",'y3limit'))#ylim of graph
y5limit = float(parser.get ("Parameters",'y5limit'))#ylim of graph
y6limit = float(parser.get ("Parameters",'y6limit'))#ylim of graph
vminacq = float(parser.get ("Parameters",'vminacq'))#speed
vmaxacq = float(parser.get ("Parameters",'vmaxacq'))#vmin acq speed
steadyrepeat = float(parser.get ("Parameters",'steadyrepeat'))#repeat values n times to determine steady state for vmax
datalog = float(parser.get ("Parameters",'datalog')) #datalog in s
ocvwait = float(parser.get ("Parameters",'ocvwait')) #datalog in s
vminwait = float(parser.get ("Parameters",'vminwait')) #datalog in s
steadyrepeatvmin = float(parser.get ("Parameters",'steadyrepeatvmin'))#repeat values n times to determine steady state for vmin
pumprate = float(parser.get  ("Parameters",'pumpratemlpermin'))#currentpumprate
targetpumprate = float(parser.get ("Parameters",'targetpumpratemlperday'))#targetpumprate
rload = float(GetRload(0)) #Resistorload
Vmax_Est = 0.00
Vmin_Est = 0.00
MFCreading = 0.00
tempV = 0.00
bodV = 0.00
codV = 0.00
global sensoroutput
Sensoroutput = 0.00
timevec = [0]
sensorvec = [0]
vmaxvec = [0]
estbodvec =[0]
estcodvec = [0]
vminvec = [0]
vmintimevec = [0]
##y2limit=500
##y3limit=300
##y4limit=300
pumpcontroloff = round((pumprate*1440)/targetpumprate)*15
pumpcontrolon = 1 *15
global flag
flag=0.00 #program always start off
if restarter==1:
    flag = 1
global flag_pump
flag_pump = 1 #pump always starts on
global counterpump
counterpump = 0
##global ainValue
##global ainValue2
##ainValue2=0
##ainValue=0



#read initialization file for flow-through MFC
tolerance2 = float(parser2.get ("Parameters",'tolerance')) #value to change
Vmin2 = float(parser2.get ("Parameters",'vmin'))#lower boundary
alpha1_2 = float (parser2.get ("Parameters",'alpha1')) #voltage filter
graphspan2 = float (parser2.get  ("Parameters",'graphspan')) #span of graph
filesaveflag_2 = float (parser2.get ("Parameters",'filesaveflag')) #default is not to save
restarter2 = float (parser2.get ("Parameters",'restarter')) #does the program need to start acquisition?
delay2 = float(parser2.get ("Parameters",'delay'))#time to wait for signal to stabilize when connected
y2limit2 = float(parser2.get ("Parameters",'y2limit'))#ylim of graph
y3limit2 = float(parser2.get ("Parameters",'y3limit'))#ylim of graph
vminacq2 = float(parser2.get ("Parameters",'vminacq'))#speed
vmaxacq2 = float(parser2.get ("Parameters",'vmaxacq'))#vmin acq speed
steadyrepeat2 = float(parser2.get ("Parameters",'steadyrepeat'))#repeat values n times to determine steady state for vmax
datalog2 = float(parser2.get ("Parameters",'datalog')) #datalog in s
ocvwait2 = float(parser2.get ("Parameters",'ocvwait')) #datalog in s
vminwait2 = float(parser2.get ("Parameters",'vminwait')) #datalog in s
steadyrepeatvmin2 = float(parser2.get ("Parameters",'steadyrepeatvmin'))#repeat values n times to determine steady state for vmin
pumpcontrolon2 = float(parser2.get  ("Parameters",'pumpcontrolon'))#how many seconds on
pumpcontroloff2 = float(parser2.get ("Parameters",'pumpcontroloff'))#
rload2 = float(parser2.get("Parameters","rload"))#Resistor Load flow through
if(len(serial_objects) == 2):
    rload2 = float(GetRload(1))
rload_Flag = 0
rload2_Flag = 0
Vmax_Est2 = 0.00
Vmin_Est2 = 0.00
MFCreading2 = 0.00
tempV2 = 0.00
global sensoroutput2
Sensoroutput2 = 0.00
timevec2 = [0]
sensorvec2 = [0]
vmaxvec2 = [0]
vminvec2 = [0]
vmintimevec2 = [0]
##y2limit2=500
##y3limit2=300
##y4limit2=300
#pumpcontroloff2=round((pumprate*1440)/targetpumprate)*15
#pumpcontrolon2 = 1 *15
global flag_2
flag_2 = 0.00 #program always start off
if restarter2== 1:
    flag_2 = 1
global flag_pump_2
flag_pump_2 = 1 #pump always starts on
global counterpump_2
counterpump_2 = 0
global state
global state2
state = 0
state2 = 0
global new_calibration
new_calibration = False
global bad_calibration
bad_calibration = False




class simpleapp_tk(Tkinter.Tk):
    global self
    def __init__(self,parent):
        Tkinter.Tk.__init__(self,parent)
        self.parent=parent
        self.initialize()
    global self
    def initialize(self): #initialize GUI
        self.grid() #Layout manager

    #CALIBRATION FUNCTION IN FLOATING BIOSENSOR
    def OnCalibrationClick(self): #what to do when the button is clicked, proceed to add as a command to the button above
        self.calibration = Tkinter.Toplevel()
        self.calibration.title("Calibration Data")
        global BODwindow
        BODwindow = self.calibration
        global calib_rows
        global calib_columns
        global dfs
        global new_calibration
        new_calibration = False
        dfs = pd.read_excel(BODExcelLocation, sheet_name=calib_data_sheet_name, header=None)
        (calib_rows, calib_columns) = dfs.shape
        dfs_old = dfs
        populate_headers(self)
        saved_calibration(self)

    #BOD estimation functions
    global all_children
    def all_children (self) :
        _list = self.winfo_children()
        for item in _list :
            if item.winfo_children() :
                _list.extend(item.winfo_children())

        return _list

    global clearFrame
    def clearFrame(self):
        widget_list = all_children(self.calibration)
        for item in widget_list:
            item.destroy()
            #item.grid_forget()

    global createnewdfs
    def createnewdfs(): #empties the dataframe
        global calib_rows
        print calib_rows
        global dfs
        dfs = pd.DataFrame(0, index=np.arange(calib_rows-1), columns=['S/N', 'Average_Vmin(mV)', 'Average_Temperature(C)', 'BOD measured(mg/L)', 'COD measured(mg/L)'])
        print dfs
        print dfs.iloc[0,1]

    global calibration_save
    def calibration_save(self):
        global calib_rows
        global calib_columns
        global dfs
        global dfs_old
        global bad_calibration

        createnewdfs()
        for i in range(calib_rows):
            for j in range(calib_columns):
                if j == 0 and i > 0:
                    dfs.iloc[i-1,0] = i
                if j > 0 and i > 0:
                    z = self.calibration.grid_slaves(row=i, column=j)[0] #calls the entry widget at the specified position
                    new_data = z.get() #gets the data in that widget
                    dfs.iloc[i-1,j] = new_data #replaces the data in the dataframe
        print dfs #comment out later
        BOD_regression(self)
        if bad_calibration == True:
            dfs = dfs_old
            (calib_rows, calib_columns) = dfs.shape
            bad_calibration = False

        with pd.ExcelWriter(BODExcelLocation, mode='w') as writer:
            dfs.to_excel(writer,sheet_name = calib_data_sheet_name, index=False, header=['S/N', 'Average_Vmin(mV)', 'Average_Temperature(C)', 'BOD measured(mg/L)', 'COD measured(mg/L)'])

        clearFrame(self)
        dfs = pd.read_excel(BODExcelLocation, sheet_name=calib_data_sheet_name, header=None)
        (calib_rows, calib_columns) = dfs.shape
        populate_headers(self)
        saved_calibration(self)


    global calibration_close
    def calibration_close(self):
        add = 1+1
        print add
        self.calibration.destroy()

    global new_calibration_perform
    def new_calibration_perform(self):
        global calib_rows
        global calib_columns
        global new_calibration
        new_calibration = True
        calib_rows_new = tkSimpleDialog.askinteger('New Calibration', 'Enter number of data points',parent=self.calibration,initialvalue=(calib_rows-1),minvalue=2,maxvalue=10)
        try:
            calib_rows = calib_rows_new+1
        except TypeError:
            calib_rows = calib_rows
        new_calibration_table(self)


    global populate_headers
    def populate_headers(self):
        BOD_regression(self)
        global r2_BOD
        global BOD_fit_eqn
        global BOD_fit_type
        global r2_COD
        global COD_fit_eqn
        global COD_fit_type

        global new_calibration
        global bad_calibration
        global dfs
        (calib_rows, calib_columns) = dfs.shape

        if new_calibration == True:
            r2_BOD = '-'
            BOD_fit_type = '-'
            BOD_fit_eqn = '-'
            r2_COD = '-'
            COD_fit_type = '-'
            COD_fit_eqn = '-'
            new_calibration = False

        if bad_calibration == True:
            dfs = dfs_old
            (calib_rows, calib_columns) = dfs.shape
            bad_calibration = False

        for i in range(calib_rows): #calib_rows
            for j in range(calib_columns):
                if i == 0: #Headers
                    b = Label(self.calibration, text="S/N")
                    b.grid(row=0, column=0)
                    b = Label(self.calibration, text="Average_Vmin (mV)")
                    b.grid(row=0, column=1)
                    b = Label(self.calibration, text=u"Average_Temperature (\u2070C)")
                    b.grid(row=0, column=2)
                    b = Label(self.calibration, text="BOD (mg/L)")
                    b.grid(row=0, column=3)
                    b = Label(self.calibration, text="COD (mg/L)")
                    b.grid(row=0, column=4)

                if j == 0 : #Place preset data and buttons
                    h = Label(self.calibration, text=i)#for the serial number
                    h.grid(row=i, column=j)
                    new_calibration_button = partial(new_calibration_perform,self)
                    #global new_calibration_perform
                    h = Button(self.calibration, text="New Calibration", command= new_calibration_button)
                    h.grid(row=calib_rows+2, column=j+4)
                    h = Label(self.calibration, text = "BOD Regression Equation :")
                    h.grid(row=calib_rows+3, column=j+1)
                    h = Label(self.calibration, text = BOD_fit_eqn)
                    h.grid(row=calib_rows+3, column=j+2)
                    h = Label(self.calibration, text = u"BOD Coefficient of Determination (R\u00B2) :")
                    h.grid(row=calib_rows+4, column=j+1)
                    h = Label(self.calibration, text = r2_BOD)
                    h.grid(row=calib_rows+4, column=j+2)
                    h = Label(self.calibration, text = u"BOD Regression Fit Type :")
                    h.grid(row=calib_rows+5, column=j+1)
                    h = Label(self.calibration, text = BOD_fit_type)
                    h.grid(row=calib_rows+5, column=j+2)
                    h = Label(self.calibration, text = "COD Regression Equation :")
                    h.grid(row=calib_rows+6, column=j+1)
                    h = Label(self.calibration, text = COD_fit_eqn)
                    h.grid(row=calib_rows+6, column=j+2)
                    h = Label(self.calibration, text = u"COD Coefficient of Determination (R\u00B2) :")
                    h.grid(row=calib_rows+7, column=j+1)
                    h = Label(self.calibration, text = r2_BOD)
                    h.grid(row=calib_rows+7, column=j+2)
                    h = Label(self.calibration, text = u"COD Regression Fit Type :")
                    h.grid(row=calib_rows+8, column=j+1)
                    h = Label(self.calibration, text = COD_fit_type)
                    h.grid(row=calib_rows+8, column=j+2)


    global saved_calibration
    def saved_calibration(self):
        dfs = pd.read_excel(BODExcelLocation, sheet_name=calib_data_sheet_name, header=None)
        (calib_rows, calib_columns) = dfs.shape
        for i in range(calib_rows): #calib_rows
            for j in range(calib_columns):
                if j > 0 : #Populate data table with saved data
                    data = dfs.iloc[i,j]
                    v =  StringVar()
                    f = Label(self.calibration, textvariable = v)
                    f.grid(row = i, column = j)
                    v.set(str(data))

    global new_calibration_table
    def new_calibration_table(self):
        clearFrame(self)
        populate_headers(self)
        global calib_rows
        global calib_columns
        for i in range(calib_rows): #calib_rows
            for j in range(calib_columns):
                if j == 0 and i > 0 : #Place preset data and buttons
                    h = Label(self.calibration, text = i)#for the serial number
                    h.grid(row=i, column=j)
                    new_calibration_save_button = partial(calibration_save,self)
                    h = Button(self.calibration, text = "Save", command = new_calibration_save_button)
                    h.grid(row=calib_rows+2, column=j+2)
                    new_calibration_close_button = partial(calibration_close,self)
                    h = Button(self.calibration, text = "Cancel", command = new_calibration_close_button)
                    h.grid(row=calib_rows+2, column=j+3)

                elif j > 0 and i > 0: #Empty
                    v =  StringVar()
                    f = Entry(self.calibration, textvariable = v)
                    f.grid(row = i, column = j)
                    v.set(str(2))

    global AprilPoly
    def AprilPoly(T): #Function for calculation Y. Program currently uses March-April GPRC polynomial
        return 0.016072*(T**3)-1.29312*(T**2)+36.04835*(T)+143.2215

    global BOD_regression
    def BOD_regression(self):
        global r2_BOD
        global BOD_fit_eqn
        global BOD_fit_type
        global BOD_lin_coefs
        global BOD_lin_inter
        global BOD_poly2_coefs
        global BOD_poly2_inter
        global BOD_exp_coefs
        global dfs_old
        global bad_calibration

        r2_BOD = 0.0
        BOD_fit_eqn ='-'
        BOD_fit_type = '-'

        dfs = pd.read_excel(BODExcelLocation, sheet_name=calib_data_sheet_name, header=0)
        (calib_rows, calib_columns) = dfs.shape

        #EXTRACT VALUES FROM CALIBRATION TABLE
        V_avgs = dfs['Average_Vmin(mV)'].values
        BOD_input = dfs['BOD measured(mg/L)'].values
        T_avgs = dfs['Average_Temperature(C)'].values


        #CALCULATE Ys
        Y_avgs = V_avgs/AprilPoly(T_avgs)

        #this can be integrated into the pandas
        if np.amin(BOD_input) > 3: #checks if there is a "0 point" in the given data (<3 considered enough a zero; BOD of 2 taken as a "0" for these fits)
            BOD_input = np.append(BOD_input,0.1) #adds a "0" point for BOD; 0.1 because it cannot do log calc with a 0 value
            Y_avgs = np.append(Y_avgs,0) #adds a "0" point for Y_avgs

        try:
            #FIT TO LOG & EXPONENTIAL REGRESSIONS THEN SAVE COEFFICIENTS
            bad_calibration = False
            BOD_exp_coefs = np.polyfit(Y_avgs,np.log(BOD_input),1,w=np.sqrt(BOD_input))

            #EXTRACT R-squared score
            BOD_r2_exp = r2_score(BOD_input, np.exp(BOD_exp_coefs[1])*np.exp(BOD_exp_coefs[0]*Y_avgs))
            BOD_r2_exp = round(BOD_r2_exp, 2)
            print BOD_r2_exp

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
                    BOD_lin_coefs = BOD_modelo.steps[1][1].coef_
                    BOD_lin_inter = BOD_modelo.steps[1][1].intercept_
                    print BOD_r2_lin

                if i == 2:
                    BOD_r2_poly2 = r2_score(BOD_input,BOD_poly_pred) #r2 score for 2nd order polynomial
                    BOD_r2_poly2 = round(BOD_r2_poly2, 2)
                    BOD_poly2_coefs = BOD_modelo.steps[1][1].coef_
                    BOD_poly2_inter = BOD_modelo.steps[1][1].intercept_
                    print BOD_r2_poly2


            if BOD_r2_exp > BOD_r2_lin: #if the r2 of the exp is greater than the linear, the exp is initally taken as the best fit
                Is_Negative = False
                for i in [float(j)/100 for j in range(0,100,1)]: #checks if there are any negative values for Y = 0 to 0.99
                    if np.exp(BOD_exp_coefs[1])*np.exp(BOD_exp_coefs[0]*i) < 0:
                        Is_Negative = True
                        break
                if Is_Negative == False:
                    r2_BOD = BOD_r2_exp
                    BOD_fit_eqn = "BOD = exp(%f)*exp(%f*Y)" % (BOD_exp_coefs[1],BOD_exp_coefs[0])
                    BOD_fit_type = 'Exponential'
                    print BOD_fit_eqn
                    print Is_Negative

            if BOD_r2_exp <= BOD_r2_lin: #if this is not the case, then the linear is initially taken as the best fit
                Is_Negative = False
                for i in [float(j)/100 for j in range(0,100,1)]: #checks if there are any negative values for Y = 0 to 0.99
                    if BOD_lin_inter+BOD_lin_coefs[0][1]*i < 0:
                        Is_Negative = True
                        break
                if Is_Negative == False:
                    r2_BOD = BOD_r2_lin
                    BOD_fit_eqn = "BOD = %f + %f*Y" % (BOD_lin_inter,BOD_lin_coefs[0][1])
                    BOD_fit_type = 'Linear'


            if BOD_r2_poly2 > max(BOD_r2_lin,BOD_r2_exp): #checks that the r2 of poly4 is greater than all other r2s
                Is_Negative = False
                for i in [float(j)/100 for j in range(0,100,1)]: #checks if there are any negative values for Y = 0 to 0.99
                    if BOD_poly2_inter+BOD_poly2_coefs[0][1]*i+BOD_poly2_coefs[0][2]*(i**2) < 0:
                        Is_Negative = True
                        break
                if Is_Negative == True:
                    r2_BOD = BOD_r2_poly2
                    BOD_fit_eqn = "BOD = %f + %f*Y + %f*Y^2" % (BOD_poly2_inter,BOD_poly2_coefs[0][1],BOD_poly2_coefs[0][2])
                    BOD_fit_type = 'Polynomial'
                    print r2_BOD

            print(r2_BOD)
            print(BOD_fit_eqn)
            print(BOD_fit_type) #can use BOD_fit_type check as a means of knowing which equation to estimate BOD wit
            COD_regression(self)

        except Exception as ex1:
            #print "BAD Calibration Data, Revert to OLD Data"
            tkMessageBox.showerror("Error", "Bad Calibration Data, Reverting to old data")
            bad_calibration = True
            dfs = dfs_old
            print dfs
            with pd.ExcelWriter(BODExcelLocation, mode='w') as writer:
                dfs.to_excel(writer,sheet_name=calib_data_sheet_name,index=False, header=['S/N', 'Average_Vmin(mV)', 'Average_Temperature(C)', 'BOD measured(mg/L)', 'COD measured(mg/L)'])
            BOD_regression(self)


    global COD_regression
    def COD_regression(self):
        global r2_COD
        global COD_fit_eqn
        global COD_fit_type
        global COD_lin_coefs
        global COD_lin_inter
        global COD_poly2_coefs
        global COD_poly2_inter
        global COD_exp_coefs
        global dfs_old
        global bad_calibration
        global filesaveflag

        r2_COD = 0.0
        COD_fit_eqn ='-'
        COD_fit_type = '-'

        dfs = pd.read_excel(BODExcelLocation, sheet_name=calib_data_sheet_name, header=0)
        (calib_rows, calib_columns) = dfs.shape

        #EXTRACT VALUES FROM CALIBRATION TABLE
        V_avgs = dfs['Average_Vmin(mV)'].values
        COD_input = dfs['COD measured(mg/L)'].values
        T_avgs = dfs['Average_Temperature(C)'].values


        #CALCULATE Ys
        Y_avgs = V_avgs/AprilPoly(T_avgs)

        #this can be integrated into the pandas
        if np.amin(COD_input) > 3: #checks if there is a "0 point" in the given data (<3 considered enough a zero; COD of 2 taken as a "0" for these fits)
            COD_input = np.append(COD_input,0.1) #adds a "0" point for COD; 0.1 because it cannot do log calc with a 0 value
            Y_avgs = np.append(Y_avgs,0) #adds a "0" point for Y_avgs

        try:
            #FIT TO LOG & EXPONENTIAL REGRESSIONS THEN SAVE COEFFICIENTS
            bad_calibration = False
            COD_exp_coefs = np.polyfit(Y_avgs,np.log(COD_input),1,w=np.sqrt(COD_input))

            #EXTRACT R-squared score
            COD_r2_exp = r2_score(COD_input, np.exp(COD_exp_coefs[1])*np.exp(COD_exp_coefs[0]*Y_avgs))
            COD_r2_exp = round(COD_r2_exp, 2)
            print COD_r2_exp

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
                    COD_lin_coefs = COD_modelo.steps[1][1].coef_
                    COD_lin_inter = COD_modelo.steps[1][1].intercept_
                    print COD_r2_lin
                    r2_COD = COD_r2_lin
                    COD_fit_eqn = "COD = %f + %f*Y" % (COD_lin_inter,COD_lin_coefs[0][1])
                    COD_fit_type = 'Linear'

                if i == 2:
                    COD_r2_poly2 = r2_score(COD_input,COD_poly_pred) #r2 score for 2nd order polynomial
                    COD_r2_poly2 = round(COD_r2_poly2, 2)
                    COD_poly2_coefs = COD_modelo.steps[1][1].coef_
                    COD_poly2_inter = COD_modelo.steps[1][1].intercept_
                    print COD_r2_poly2


            if COD_r2_exp > COD_r2_lin: #if the r2 of the exp is greater than the linear, the exp is initally taken as the best fit
                Is_Negative = False
                for i in [float(j)/100 for j in range(0,100,1)]: #checks if there are any negative values for Y = 0 to 0.99
                    if np.exp(COD_exp_coefs[1])*np.exp(COD_exp_coefs[0]*i) < 0:
                        Is_Negative = True
                        break
                if Is_Negative == False:
                    r2_COD = COD_r2_exp
                    COD_fit_eqn = "COD = exp(%f)*exp(%f*Y)" % (COD_exp_coefs[1],COD_exp_coefs[0])
                    COD_fit_type = 'Exponential'
                    print COD_fit_eqn
                    print Is_Negative

            if COD_r2_exp <= COD_r2_lin: #if this is not the case, then the linear is initially taken as the best fit
                Is_Negative = False
                for i in [float(j)/100 for j in range(0,100,1)]: #checks if there are any negative values for Y = 0 to 0.99
                    if COD_lin_inter+COD_lin_coefs[0][1]*i < 0:
                        Is_Negative = True
                        break
                if Is_Negative == False:
                    r2_COD = COD_r2_lin
                    COD_fit_eqn = "COD = %f + %f*Y" % (COD_lin_inter,COD_lin_coefs[0][1])
                    COD_fit_type = 'Linear'


            if COD_r2_poly2 > max(COD_r2_lin,COD_r2_exp): #checks that the r2 of poly4 is greater than all other r2s
                Is_Negative = False
                for i in [float(j)/100 for j in range(0,100,1)]: #checks if there are any negative values for Y = 0 to 0.99
                    if COD_poly2_inter+COD_poly2_coefs[0][1]*i+COD_poly2_coefs[0][2]*(i**2) < 0:
                        Is_Negative = True
                        break
                if Is_Negative == True:
                    r2_COD = COD_r2_poly2
                    COD_fit_eqn = "COD = %f + %f*Y + %f*Y^2" % (COD_poly2_inter,COD_poly2_coefs[0][1],COD_poly2_coefs[0][2])
                    COD_fit_type = 'Polynomial'
                    print r2_COD

            print(r2_COD)
            print(COD_fit_eqn)
            print(COD_fit_type) #can use BOD_fit_type check as a means of knowing which equation to estimate BOD wit
            print ('finished')

            #save calibration data
            if filesaveflag == 1:
                timeofsave6 = (str(datetime.datetime.now()))[:19]
                datastr6 = (timeofsave6 +' ' + COD_fit_eqn+' ' + BOD_fit_eqn)
                save_file6 = open(filename6,"a") #openfile to save
                save_file6.write(datastr6 +'\n') #write data to file
                save_file6.close() #close



        except Exception as ex1:
            #print "BAD Calibration Data, Revert to OLD Data"
            tkMessageBox.showerror("Error", "Bad Calibration Data, Reverting to old data")
            bad_calibration = True
            dfs = dfs_old
            print dfs
            with pd.ExcelWriter(BODExcelLocation, mode='w') as writer:
                dfs.to_excel(writer,sheet_name=calib_data_sheet_name,index=False, header=['S/N', 'Average_Vmin(mV)', 'Average_Temperature(C)', 'BOD measured(mg/L)', 'COD measured(mg/L)'])
            BOD_regression(self)

    #BPARAMETER FUNCTION IN FLOATING BIOSENSOR
    def OnParameterClick(self): #what to do when the button is clicked, proceed to add as a command to the button above
        self.parameter = Tkinter.Toplevel()
        self.parameter.title("Floating biosensor parameters")


        #TOLERANCE
        self.parameter.tolerance = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        tolerance_label = Tkinter.Label(self.parameter,textvariable=self.parameter.tolerance,
                              anchor="w",fg="black",bg=defaultbg)
        tolerance_label.grid(column=0,row=0,columnspan=1,sticky='EW') #label position
        self.parameter.tolerance.set(u"Tolerance") #default value in display
        self.parameter.tolerancev = Tkinter.StringVar() #variable to call text entry
        tolerance_value = Tkinter.Entry(self.parameter,textvariable=self.parameter.tolerancev) #text entry
        tolerance_value.grid(column=1,row=0,sticky='NW') #text entry location
        self.parameter.tolerancev.set(str(tolerance)) #default text prompt

        #VMIN
        self.parameter.vmin = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        vmin_label = Tkinter.Label(self.parameter,textvariable=self.parameter.vmin,
                              anchor="w",fg="black",bg=defaultbg)
        vmin_label.grid(column=0,row=1,columnspan=1,sticky='EW') #label position
        self.parameter.vmin.set(u"Vmin (mV)") #default value in display
        self.parameter.vminv = Tkinter.StringVar() #variable to call text entry
        vmin_value= Tkinter.Entry(self.parameter,textvariable=self.parameter.vminv) #text entry
        vmin_value.grid(column=1,row=1,sticky='NW') #text entry location
        self.parameter.vminv.set(str(Vmin)) #default text prompt

        #VFILTER
        self.parameter.vfilter = Tkinter.DoubleVar() #variable to call label
        defaultbg = self.cget('bg')
        vfilter_label = Tkinter.Label(self.parameter,textvariable=self.parameter.vfilter,
                              anchor="w",fg="black",bg=defaultbg)
        vfilter_label.grid(column=0,row=2,columnspan=1,sticky='EW') #label position
        self.parameter.vfilter.set(u"Vfilter(alpha)") #default value in display
        self.parameter.vfilterv = Tkinter.StringVar() #variable to call text entry
        vfilter_value = Tkinter.Entry(self.parameter,textvariable=self.parameter.vfilterv) #text entry
        vfilter_value.grid(column=1,row=2,sticky='NW') #text entry location
        self.parameter.vfilterv.set(str(alpha1)) #default text prompt

        #GRAPH SPAN
        self.parameter.gspan = Tkinter.DoubleVar() #variable to call label
        defaultbg = self.cget('bg')
        gspan_label = Tkinter.Label(self.parameter,textvariable=self.parameter.gspan,
                              anchor="w",fg="black",bg=defaultbg)
        gspan_label.grid(column=0,row=3,columnspan=1,sticky='EW') #label position
        self.parameter.gspan.set(u"Graph Span (h)") #default value in display
        self.parameter.gspan = Tkinter.StringVar() #variable to call text entry
        gspan_value = Tkinter.Entry(self.parameter,textvariable=self.parameter.gspan) #text entry
        gspan_value.grid(column=1,row=3,sticky='NW') #text entry location
        self.parameter.gspan.set(str(graphspan)) #default text prompt

        #DELAY
        self.parameter.delay = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        delay_label = Tkinter.Label(self.parameter,textvariable=self.parameter.delay,
                              anchor="w",fg="black",bg=defaultbg)
        delay_label.grid(column=0,row=4,columnspan=1,sticky='EW') #label position
        self.parameter.delay.set(u"delay(s)") #default value in display
        self.parameter.delayv = Tkinter.StringVar() #variable to call text entry
        delay_value = Tkinter.Entry(self.parameter,textvariable=self.parameter.delayv) #text entry
        delay_value.grid(column=1,row=4,sticky='NW') #text entry location
        self.parameter.delayv.set(str(delay)) #default text prompt


        #Y2LIMIT
        self.parameter.y2limit = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        y2limit_label = Tkinter.Label(self.parameter,textvariable=self.parameter.y2limit,
                              anchor="w",fg="black",bg=defaultbg)
        y2limit_label.grid(column=3,row=0,columnspan=1,sticky='EW') #label position
        self.parameter.y2limit.set(u"Vmax_yaxis") #default value in display
        self.parameter.y2limitv = Tkinter.StringVar() #variable to call text entry
        y2limit_value= Tkinter.Entry(self.parameter,textvariable=self.parameter.y2limitv) #text entry
        y2limit_value.grid(column=4,row=0,sticky='NW') #text entry location
        self.parameter.y2limitv.set(str(y2limit)) #default text prompt

        #Y3LIMIT
        self.parameter.y3limit = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        y3limit_label = Tkinter.Label(self.parameter,textvariable=self.parameter.y3limit,
                              anchor="w",fg="black",bg=defaultbg)
        y3limit_label.grid(column=3,row=1,columnspan=1,sticky='EW') #label position
        self.parameter.y3limit.set(u"Vmin_yaxis") #default value in display
        self.parameter.y3limitv = Tkinter.StringVar() #variable to call text entry
        y3limit_value= Tkinter.Entry(self.parameter,textvariable=self.parameter.y3limitv) #text entry
        y3limit_value.grid(column=4,row=1,sticky='NW') #text entry location
        self.parameter.y3limitv.set(str(y3limit)) #default text prompt


        #Y5LIMIT
        self.parameter.y5limit = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        y5limit_label = Tkinter.Label(self.parameter,textvariable=self.parameter.y5limit,
                              anchor="w",fg="black",bg=defaultbg)
        y5limit_label.grid(column=3,row=2,columnspan=1,sticky='EW') #label position
        self.parameter.y5limit.set(u"BOD_yaxis") #default value in display
        self.parameter.y5limitv = Tkinter.StringVar() #variable to call text entry
        y5limit_value= Tkinter.Entry(self.parameter,textvariable=self.parameter.y5limitv) #text entry
        y5limit_value.grid(column=4,row=2,sticky='NW') #text entry location
        self.parameter.y5limitv.set(str(y5limit)) #default text prompt




        #Y6LIMIT
        self.parameter.y6limit = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        y6limit_label = Tkinter.Label(self.parameter,textvariable=self.parameter.y6limit,
                              anchor="w",fg="black",bg=defaultbg)
        y6limit_label.grid(column=3,row=3,columnspan=1,sticky='EW') #label position
        self.parameter.y6limit.set(u"COD_yaxis") #default value in display
        self.parameter.y6limitv = Tkinter.StringVar() #variable to call text entry
        y6limit_value= Tkinter.Entry(self.parameter,textvariable=self.parameter.y6limitv) #text entry
        y6limit_value.grid(column=4,row=3,sticky='NW') #text entry location
        self.parameter.y6limitv.set(str(y6limit)) #default text prompt

        #RLoad
        self.parameter.rload = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        rload_label = Tkinter.Label(self.parameter,textvariable=self.parameter.rload,
                              anchor="w",fg="black",bg=defaultbg)
        rload_label.grid(column=3,row=4,columnspan=1,sticky='EW') #label position
        self.parameter.rload.set(u"RLoad") #default value in display
        self.parameter.rloadv = Tkinter.StringVar() #variable to call text entry
        rload_value= Tkinter.Entry(self.parameter,textvariable=self.parameter.rloadv) #text entry
        rload_value.grid(column=4,row=4,sticky='NW') #text entry location
        self.parameter.rloadv.set(str(rload)) #default text prompt

        #ACQSPEEDVMIN
        self.parameter.vminacq = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        vminacq_label = Tkinter.Label(self.parameter,textvariable=self.parameter.vminacq,
                              anchor="w",fg="black",bg=defaultbg)
        vminacq_label.grid(column=0,row=6,columnspan=1,sticky='EW') #label position
        self.parameter.vminacq.set(u"vminacq (s)") #default value in display
        self.parameter.vminacqv = Tkinter.StringVar() #variable to call text entry
        vminacq_value= Tkinter.Entry(self.parameter,textvariable=self.parameter.vminacqv) #text entry
        vminacq_value.grid(column=1,row=6,sticky='NW') #text entry location
        self.parameter.vminacqv.set(str(vminacq)) #default text prompt

        #ACQSPEEDVMAX
        self.parameter.vmaxacq = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        vmaxacq_label = Tkinter.Label(self.parameter,textvariable=self.parameter.vmaxacq,
                              anchor="w",fg="black",bg=defaultbg)
        vmaxacq_label.grid(column=0,row=7,columnspan=1,sticky='EW') #label position
        self.parameter.vmaxacq.set(u"vmaxacq (s)") #default value in display
        self.parameter.vmaxacqv = Tkinter.StringVar() #variable to call text entry
        vmaxacq_value= Tkinter.Entry(self.parameter,textvariable=self.parameter.vmaxacqv) #text entry
        vmaxacq_value.grid(column=1,row=7,sticky='NW') #text entry location
        self.parameter.vmaxacqv.set(str(vmaxacq)) #default text prompt

        #PSEUDO STATE REPITITON VMAX
        self.parameter.steadyrepeat = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        steadyrepeat_label = Tkinter.Label(self.parameter,textvariable=self.parameter.steadyrepeat,
                              anchor="w",fg="black",bg=defaultbg)
        steadyrepeat_label.grid(column=0,row=8,columnspan=1,sticky='EW') #label position
        self.parameter.steadyrepeat.set(u"pseudo state repeat (n)") #default value in display
        self.parameter.steadyrepeatv = Tkinter.StringVar() #variable to call text entry
        steadyrepeat_value= Tkinter.Entry(self.parameter,textvariable=self.parameter.steadyrepeatv) #text entry
        steadyrepeat_value.grid(column=1,row=8,sticky='NW') #text entry location
        self.parameter.steadyrepeatv.set(str(steadyrepeat)) #default text prompt

        #MFC DATA SAVE
        self.parameter.datalog = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        datalog_label = Tkinter.Label(self.parameter,textvariable=self.parameter.datalog,
                              anchor="w",fg="black",bg=defaultbg)
        datalog_label.grid(column=0,row=9,columnspan=1,sticky='EW') #label position
        self.parameter.datalog.set(u"Data Point Log (s)") #default value in display
        self.parameter.datalogv = Tkinter.StringVar() #variable to call text entry
        datalog_value= Tkinter.Entry(self.parameter,textvariable=self.parameter.datalogv) #text entry
        datalog_value.grid(column=1,row=9,sticky='NW') #text entry location
        self.parameter.datalogv.set(str(datalog)) #default text prompt

        #OCV WAIT
        self.parameter.ocvwait = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        ocvwait_label = Tkinter.Label(self.parameter,textvariable=self.parameter.ocvwait,
                              anchor="w",fg="black",bg=defaultbg)
        ocvwait_label.grid(column=0,row=10,columnspan=1,sticky='EW') #label position
        self.parameter.ocvwait.set(u"OCV wait (s)") #default value in display
        self.parameter.ocvwaitv = Tkinter.StringVar() #variable to call text entry
        ocvwait_value= Tkinter.Entry(self.parameter,textvariable=self.parameter.ocvwaitv) #text entry
        ocvwait_value.grid(column=1,row=10,sticky='NW') #text entry location
        self.parameter.ocvwaitv.set(str(ocvwait)) #default text prompt

        #VMIN WAIT
        self.parameter.vminwait = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        vminwait_label = Tkinter.Label(self.parameter,textvariable=self.parameter.vminwait,
                              anchor="w",fg="black",bg=defaultbg)
        vminwait_label.grid(column=0,row=11,columnspan=1,sticky='EW') #label position
        self.parameter.vminwait.set(u"VMIN wait (s)") #default value in display
        self.parameter.vminwaitv = Tkinter.StringVar() #variable to call text entry
        vminwait_value= Tkinter.Entry(self.parameter,textvariable=self.parameter.vminwaitv) #text entry
        vminwait_value.grid(column=1,row=11,sticky='NW') #text entry location
        self.parameter.vminwaitv.set(str(vminwait)) #default text prompt

        #PSEUDO STATE REPITITON VMIN
        self.parameter.steadyrepeatvmin = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        steadyrepeatvmin_label = Tkinter.Label(self.parameter,textvariable=self.parameter.steadyrepeatvmin,
                              anchor="w",fg="black",bg=defaultbg)
        steadyrepeatvmin_label.grid(column=0,row=12,columnspan=1,sticky='EW') #label position
        self.parameter.steadyrepeatvmin.set(u"pseudo state repeat vmin(n)") #default value in display
        self.parameter.steadyrepeatvminv = Tkinter.StringVar() #variable to call text entry
        steadyrepeatvmin_value= Tkinter.Entry(self.parameter,textvariable=self.parameter.steadyrepeatvminv) #text entry
        steadyrepeatvmin_value.grid(column=1,row=12,sticky='NW') #text entry location
        self.parameter.steadyrepeatvminv.set(str(steadyrepeatvmin)) #default text prompt

        #PUMPRATE
        self.parameter.pumprate = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        pumprate_label = Tkinter.Label(self.parameter,textvariable=self.parameter.pumprate,
                              anchor="w",fg="black",bg=defaultbg)
        pumprate_label.grid(column=0,row=13,columnspan=1,sticky='EW') #label position
        self.parameter.pumprate.set(u"Pumprate (mL/min)") #default value in display
        self.parameter.pumpratev = Tkinter.StringVar() #variable to call text entry
        pumprate_value= Tkinter.Entry(self.parameter,textvariable=self.parameter.pumpratev) #text entry
        pumprate_value.grid(column=1,row=13,sticky='NW') #text entry location
        self.parameter.pumpratev.set(str(pumprate)) #default text prompt

        #TARGETPUMPRATE
        self.parameter.targetpumprate = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        targetpumprate_label = Tkinter.Label(self.parameter,textvariable=self.parameter.targetpumprate,
                              anchor="w",fg="black",bg=defaultbg)
        targetpumprate_label.grid(column=0,row=14,columnspan=1,sticky='EW') #label position
        self.parameter.targetpumprate.set(u"Target pumprate (mL/d)") #default value in display
        self.parameter.targetpumpratev = Tkinter.StringVar() #variable to call text entry
        targetpumprate_value= Tkinter.Entry(self.parameter,textvariable=self.parameter.targetpumpratev) #text entry
        targetpumprate_value.grid(column=1,row=14,sticky='NW') #text entry location
        self.parameter.targetpumpratev.set(str(targetpumprate)) #default text prompt

        #SAVE BUTTON
        save_button2 =Tkinter.Button(self.parameter,text=u"save changes",
                               command=self.OnSaveClick) #button entry
        save_button2.grid(column=1, row=15) #button entry location


####### PARAMETER BUTTON FOR FLOW-THROUGH MFC
    def OnParameterClick2(self): #what to do when the button is clicked, proceed to add as a command to the button above
        self.parameter2=Tkinter.Toplevel()
        self.parameter2.title("Flow-through biosensor parameters")

        #TOLERANCE
        self.parameter2.tolerance2 = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        tolerance_label2 = Tkinter.Label(self.parameter2,textvariable=self.parameter2.tolerance2,
                              anchor="w",fg="black",bg=defaultbg)
        tolerance_label2.grid(column=0,row=0,columnspan=1,sticky='EW') #label position
        self.parameter2.tolerance2.set(u"Tolerance") #default value in display
        self.parameter2.tolerancev2 = Tkinter.StringVar() #variable to call text entry
        tolerance_value2= Tkinter.Entry(self.parameter2,textvariable=self.parameter2.tolerancev2) #text entry
        tolerance_value2.grid(column=1,row=0,sticky='NW') #text entry location
        self.parameter2.tolerancev2.set(str(tolerance2)) #default text prompt

        #VMIN
        self.parameter2.vmin2 = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        vmin_label2 = Tkinter.Label(self.parameter2,textvariable=self.parameter2.vmin2,
                              anchor="w",fg="black",bg=defaultbg)
        vmin_label2.grid(column=0,row=1,columnspan=1,sticky='EW') #label position
        self.parameter2.vmin2.set(u"Vmin (mV)") #default value in display
        self.parameter2.vminv2 = Tkinter.StringVar() #variable to call text entry
        vmin_value2= Tkinter.Entry(self.parameter2,textvariable=self.parameter2.vminv2) #text entry
        vmin_value2.grid(column=1,row=1,sticky='NW') #text entry location
        self.parameter2.vminv2.set(str(Vmin2)) #default text prompt

        #VFILTER
        self.parameter2.vfilter2 = Tkinter.DoubleVar() #variable to call label
        defaultbg = self.cget('bg')
        vfilter_label2 = Tkinter.Label(self.parameter2,textvariable=self.parameter2.vfilter2,
                              anchor="w",fg="black",bg=defaultbg)
        vfilter_label2.grid(column=0,row=2,columnspan=1,sticky='EW') #label position
        self.parameter2.vfilter2.set(u"Vfilter(alpha)") #default value in display
        self.parameter2.vfilterv2 = Tkinter.StringVar() #variable to call text entry
        vfilter_value2= Tkinter.Entry(self.parameter2,textvariable=self.parameter2.vfilterv2) #text entry
        vfilter_value2.grid(column=1,row=2,sticky='NW') #text entry location
        self.parameter2.vfilterv2.set(str(alpha1_2)) #default text prompt

        #GRAPH SPAN
        self.parameter2.gspan2 = Tkinter.DoubleVar() #variable to call label
        defaultbg = self.cget('bg')
        gspan_label2 = Tkinter.Label(self.parameter2,textvariable=self.parameter2.gspan2,
                              anchor="w",fg="black",bg=defaultbg)
        gspan_label2.grid(column=0,row=3,columnspan=1,sticky='EW') #label position
        self.parameter2.gspan2.set(u"Graph Span (h)") #default value in display
        self.parameter2.gspan2 = Tkinter.StringVar() #variable to call text entry
        gspan_value2= Tkinter.Entry(self.parameter2,textvariable=self.parameter2.gspan2) #text entry
        gspan_value2.grid(column=1,row=3,sticky='NW') #text entry location
        self.parameter2.gspan2.set(str(graphspan2)) #default text prompt

        #DELAY
        self.parameter2.delay2 = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        delay_label2 = Tkinter.Label(self.parameter2,textvariable=self.parameter2.delay2,
                              anchor="w",fg="black",bg=defaultbg)
        delay_label2.grid(column=0,row=4,columnspan=1,sticky='EW') #label position
        self.parameter2.delay2.set(u"delay(s)") #default value in display
        self.parameter2.delayv2 = Tkinter.StringVar() #variable to call text entry
        delay_value2= Tkinter.Entry(self.parameter2,textvariable=self.parameter2.delayv2) #text entry
        delay_value2.grid(column=1,row=4,sticky='NW') #text entry location
        self.parameter2.delayv2.set(str(delay2)) #default text prompt


        #Y2LIMIT
        self.parameter2.y2limit2 = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        y2limit_label2 = Tkinter.Label(self.parameter2,textvariable=self.parameter2.y2limit2,
                              anchor="w",fg="black",bg=defaultbg)
        y2limit_label2.grid(column=3,row=0,columnspan=1,sticky='EW') #label position
        self.parameter2.y2limit2.set(u"Vmax_yaxis") #default value in display
        self.parameter2.y2limitv2 = Tkinter.StringVar() #variable to call text entry
        y2limit_value2= Tkinter.Entry(self.parameter2,textvariable=self.parameter2.y2limitv2) #text entry
        y2limit_value2.grid(column=4,row=0,sticky='NW') #text entry location
        self.parameter2.y2limitv2.set(str(y2limit2)) #default text prompt

        #Y3LIMIT
        self.parameter2.y3limit2 = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        y3limit_label2 = Tkinter.Label(self.parameter2,textvariable=self.parameter2.y3limit2,
                              anchor="w",fg="black",bg=defaultbg)
        y3limit_label2.grid(column=3,row=1,columnspan=1,sticky='EW') #label position
        self.parameter2.y3limit2.set(u"Vmin_yaxis") #default value in display
        self.parameter2.y3limitv2 = Tkinter.StringVar() #variable to call text entry
        y3limit_value2= Tkinter.Entry(self.parameter2,textvariable=self.parameter2.y3limitv2) #text entry
        y3limit_value2.grid(column=4,row=1,sticky='NW') #text entry location
        self.parameter2.y3limitv2.set(str(y3limit2)) #default text prompt

        #RLoad2
        self.parameter2.rload2 = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        rload_label2 = Tkinter.Label(self.parameter2,textvariable=self.parameter2.rload2,
                              anchor="w",fg="black",bg=defaultbg)
        rload_label2.grid(column=3,row=2,columnspan=1,sticky='EW') #label position
        self.parameter2.rload2.set(u"RLoad") #default value in display
        self.parameter2.rloadv2 = Tkinter.StringVar() #variable to call text entry
        rload_value2= Tkinter.Entry(self.parameter2,textvariable=self.parameter2.rloadv2) #text entry
        rload_value2.grid(column=4,row=2,sticky='NW') #text entry location
        self.parameter2.rloadv2.set(str(rload2)) #default text prompt

        #ACQSPEEDVMIN
        self.parameter2.vminacq2 = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        vminacq_label2 = Tkinter.Label(self.parameter2,textvariable=self.parameter2.vminacq2,
                              anchor="w",fg="black",bg=defaultbg)
        vminacq_label2.grid(column=0,row=6,columnspan=1,sticky='EW') #label position
        self.parameter2.vminacq2.set(u"vminacq (s)") #default value in display
        self.parameter2.vminacqv2 = Tkinter.StringVar() #variable to call text entry
        vminacq_value2 = Tkinter.Entry(self.parameter2,textvariable=self.parameter2.vminacqv2) #text entry
        vminacq_value2.grid(column=1,row=6,sticky='NW') #text entry location
        self.parameter2.vminacqv2.set(str(vminacq2)) #default text prompt

        #ACQSPEEDVMAX
        self.parameter2.vmaxacq2 = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        vmaxacq_label2 = Tkinter.Label(self.parameter2,textvariable=self.parameter2.vmaxacq2,
                              anchor="w",fg="black",bg=defaultbg)
        vmaxacq_label2.grid(column=0,row=7,columnspan=1,sticky='EW') #label position
        self.parameter2.vmaxacq2.set(u"vmaxacq (s)") #default value in display
        self.parameter2.vmaxacqv2 = Tkinter.StringVar() #variable to call text entry
        vmaxacq_value2= Tkinter.Entry(self.parameter2,textvariable=self.parameter2.vmaxacqv2) #text entry
        vmaxacq_value2.grid(column=1,row=7,sticky='NW') #text entry location
        self.parameter2.vmaxacqv2.set(str(vmaxacq2)) #default text prompt

        #PSEUDO STATE REPITITON VMAX
        self.parameter2.steadyrepeat2 = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        steadyrepeat_label2 = Tkinter.Label(self.parameter2,textvariable=self.parameter2.steadyrepeat2,
                              anchor="w",fg="black",bg=defaultbg)
        steadyrepeat_label2.grid(column=0,row=8,columnspan=1,sticky='EW') #label position
        self.parameter2.steadyrepeat2.set(u"pseudo state repeat (n)") #default value in display
        self.parameter2.steadyrepeatv2 = Tkinter.StringVar() #variable to call text entry
        steadyrepeat_value2= Tkinter.Entry(self.parameter2,textvariable=self.parameter2.steadyrepeatv2) #text entry
        steadyrepeat_value2.grid(column=1,row=8,sticky='NW') #text entry location
        self.parameter2.steadyrepeatv2.set(str(steadyrepeat2)) #default text prompt

        #MFC DATA SAVE
        self.parameter2.datalog2 = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        datalog_label2 = Tkinter.Label(self.parameter2,textvariable=self.parameter2.datalog2,
                              anchor="w",fg="black",bg=defaultbg)
        datalog_label2.grid(column=0,row=9,columnspan=1,sticky='EW') #label position
        self.parameter2.datalog2.set(u"Data Point Log (s)") #default value in display
        self.parameter2.datalogv2 = Tkinter.StringVar() #variable to call text entry
        datalog_value2= Tkinter.Entry(self.parameter2,textvariable=self.parameter2.datalogv2) #text entry
        datalog_value2.grid(column=1,row=9,sticky='NW') #text entry location
        self.parameter2.datalogv2.set(str(datalog2)) #default text prompt

        #OCV WAIT
        self.parameter2.ocvwait2 = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        ocvwait_label2 = Tkinter.Label(self.parameter2,textvariable=self.parameter2.ocvwait2,
                              anchor="w",fg="black",bg=defaultbg)
        ocvwait_label2.grid(column=0,row=10,columnspan=1,sticky='EW') #label position
        self.parameter2.ocvwait2.set(u"OCV wait (s)") #default value in display
        self.parameter2.ocvwaitv2 = Tkinter.StringVar() #variable to call text entry
        ocvwait_value2 = Tkinter.Entry(self.parameter2,textvariable=self.parameter2.ocvwaitv2) #text entry
        ocvwait_value2.grid(column=1,row=10,sticky='NW') #text entry location
        self.parameter2.ocvwaitv2.set(str(ocvwait2)) #default text prompt

        #VMIN WAIT
        self.parameter2.vminwait2 = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        vminwait_label2 = Tkinter.Label(self.parameter2,textvariable=self.parameter2.vminwait2,
                              anchor="w",fg="black",bg=defaultbg)
        vminwait_label2.grid(column=0,row=11,columnspan=1,sticky='EW') #label position
        self.parameter2.vminwait2.set(u"VMIN wait (s)") #default value in display
        self.parameter2.vminwaitv2 = Tkinter.StringVar() #variable to call text entry
        vminwait_value2= Tkinter.Entry(self.parameter2,textvariable=self.parameter2.vminwaitv2) #text entry
        vminwait_value2.grid(column=1,row=11,sticky='NW') #text entry location
        self.parameter2.vminwaitv2.set(str(vminwait2)) #default text prompt

        #PSEUDO STATE REPITITON VMIN
        self.parameter2.steadyrepeatvmin2 = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        steadyrepeatvmin_label2 = Tkinter.Label(self.parameter2,textvariable=self.parameter2.steadyrepeatvmin2,
                              anchor="w",fg="black",bg=defaultbg)
        steadyrepeatvmin_label2.grid(column=0,row=12,columnspan=1,sticky='EW') #label position
        self.parameter2.steadyrepeatvmin2.set(u"pseudo state repeat vmin(n)") #default value in display
        self.parameter2.steadyrepeatvminv2 = Tkinter.StringVar() #variable to call text entry
        steadyrepeatvmin_value2= Tkinter.Entry(self.parameter2,textvariable=self.parameter2.steadyrepeatvminv2) #text entry
        steadyrepeatvmin_value2.grid(column=1,row=12,sticky='NW') #text entry location
        self.parameter2.steadyrepeatvminv2.set(str(steadyrepeatvmin2)) #default text prompt

        #PUMPCONTROLON
        self.parameter2.pumpcontrolon2 = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        pumpcontrolon_label2 = Tkinter.Label(self.parameter2,textvariable=self.parameter2.pumpcontrolon2,
                              anchor="w",fg="black",bg=defaultbg)
        pumpcontrolon_label2.grid(column=0,row=13,columnspan=1,sticky='EW') #label position
        self.parameter2.pumpcontrolon2.set(u"PUMP:ON (s)") #default value in display
        self.parameter2.pumpcontrolonv2 = Tkinter.StringVar() #variable to call text entry
        pumpcontrolon_value2= Tkinter.Entry(self.parameter2,textvariable=self.parameter2.pumpcontrolonv2) #text entry
        pumpcontrolon_value2.grid(column=1,row=13,sticky='NW') #text entry location
        self.parameter2.pumpcontrolonv2.set(str(pumpcontrolon2)) #default text prompt

        #PUMPCONTROLOFF
        self.parameter2.pumpcontroloff2 = Tkinter.StringVar() #variable to call label
        defaultbg = self.cget('bg')
        pumpcontroloff_label2 = Tkinter.Label(self.parameter2,textvariable=self.parameter2.pumpcontroloff2,
                              anchor="w",fg="black",bg=defaultbg)
        pumpcontroloff_label2.grid(column=0,row=14,columnspan=1,sticky='EW') #label position
        self.parameter2.pumpcontroloff2.set(u"PUMP:OFF (s)") #default value in display
        self.parameter2.pumpcontroloffv2 = Tkinter.StringVar() #variable to call text entry
        pumpcontroloff_value2= Tkinter.Entry(self.parameter2,textvariable=self.parameter2.pumpcontroloffv2) #text entry
        pumpcontroloff_value2.grid(column=1,row=14,sticky='NW') #text entry location
        self.parameter2.pumpcontroloffv2.set(str(pumpcontroloff2)) #default text prompt

        #SAVE BUTTON
        save_button4 =Tkinter.Button(self.parameter2,text=u"save changes",
                               command=self.OnSaveClick2) #button entry
        save_button4.grid(column=1, row=15) #button entry location




#########DEFINITIONS OF COMMANDS FOR FLOATING SENSOR
    def OnAutoCalibrationClick(self): #what happens when calibration file is already available
        calibration_path = tkFileDialog.askopenfilename()
        print(calibration_path) # to be deleted
        # based on the datafile imported, summarize the data and save dates in selectable format

    # def OnManualCalibrationClick(self):
    #     a==b# what happens when the user wants to enter data, populate a table

        # based on the datafile imported, summarize the data and save dates in selectable format


    def OnSaveClick(self): #this save is in the parameter box
        global tolerance
        global Vmin
        global alpha1
        global graphspan
        global delay
        global y2limit
        global y3limit
        global y5limit
        global y6limit
        global vminacq
        global vmaxacq
        global steadyrepeat
        global steadyrepeatvmin
        global datalog
        global ocvwait
        global vminwait
        global pumprate
        global targetpumprate
        global pumpcontroloff
        global pumpcontrolon
        global configfile1path
        global configfile2path
        global BiosensingDataFolder
        global rload
        global rload_Flag

        self.parameter.tolerancev.set(self.parameter.tolerancev.get())
        tolerance=float(self.parameter.tolerancev.get())
        self.parameter.vminv.set(self.parameter.vminv.get())
        Vmin=float(self.parameter.vminv.get())
        self.parameter.vfilterv.set(self.parameter.vfilterv.get())
        alpha1=float(self.parameter.vfilterv.get())
        self.parameter.destroy()
        graphspan=float(self.parameter.gspan.get())
        self.parameter.destroy()
        delay=float(self.parameter.delayv.get())
        self.parameter.destroy()
        y2limit=float(self.parameter.y2limitv.get())
        self.parameter.destroy()
        y3limit=float(self.parameter.y3limitv.get())
        self.parameter.destroy()
        y5limit=float(self.parameter.y5limitv.get())
        self.parameter.destroy()
        y6limit=float(self.parameter.y6limitv.get())
        self.parameter.destroy()
        rload = float(self.parameter.rloadv.get())
        self.parameter.destroy()
        rload_Flag = 1
        vminacq=float(self.parameter.vminacqv.get())
        self.parameter.destroy()
        vmaxacq=float(self.parameter.vmaxacqv.get())
        self.parameter.destroy()
        steadyrepeat=float(self.parameter.steadyrepeatv.get())
        self.parameter.destroy()
        steadyrepeatvmin=float(self.parameter.steadyrepeatvminv.get())
        self.parameter.destroy()
        datalog=float(self.parameter.datalogv.get())
        self.parameter.destroy()
        ocvwait=float(self.parameter.ocvwaitv.get())
        self.parameter.destroy()
        vminwait=float(self.parameter.vminwaitv.get())
        self.parameter.destroy()
        pumprate=float(self.parameter.pumpratev.get())
        self.parameter.destroy()
        targetpumprate=float(self.parameter.targetpumpratev.get())
        self.parameter.destroy()
        pumpcontroloff=round((pumprate*1440)/targetpumprate)*60
        pumpcontrolon = 1 *60
        parser.set('Parameters','tolerance',str(tolerance))
        parser.set('Parameters','vmin', str(Vmin))
        parser.set('Parameters','alpha1', str(alpha1))
        parser.set('Parameters','graphspan', str(graphspan))
        parser.set('Parameters','filesaveflag', str(filesaveflag))
        parser.set('Parameters','restarter', str(restarter))
        parser.set('Parameters','delay', str(delay))
        parser.set('Parameters','y2limit', str(y2limit))
        parser.set('Parameters','y3limit', str(y3limit))
        parser.set('Parameters','y5limit', str(y5limit))
        parser.set('Parameters','y6limit', str(y6limit))
        parser.set('Parameters','vminacq', str(vminacq))
        parser.set('Parameters','vmaxacq', str(vmaxacq))
        parser.set('Parameters','steadyrepeat', str(steadyrepeat))
        parser.set('Parameters','steadyrepeatvmin', str(steadyrepeatvmin))
        parser.set('Parameters','datalog', str(datalog))
        parser.set('Parameters','ocvwait', str(ocvwait))
        parser.set('Parameters','vminwait', str(vminwait))
        parser.set('Parameters','pumpratemlpermin', str(pumprate))
        parser.set('Parameters','targetpumpratemlperday', str(targetpumprate))
        parser.set("Parameters","rload",str(rload))
        with open ('/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/Configuration/biosensorconfig.ini', 'w') as configfile: #RPi
            parser.write(configfile)
        configfile.close()



###        with open(configfile1path, 'w') as configfile: #Windows
###            parser.write(configfile)
###        configfile.close()



    def OnPumpClick(self): #when pump button is clicked
        global flag_pump
        global pump_button
        if flag_pump==1:
            pump_button['text']= 'PUMP OFF'
            #d.getFeedback(u3.BitStateWrite(7, 0)) # Set FIO7 to output low to turn off pump
            flag_pump=0

        elif flag_pump==0:
            pump_button['text']= 'PUMP ON'
            #d.getFeedback(u3.BitStateWrite(7, 1)) # Set FIO7 to output high to turn on pump
            flag_pump=1
        #print flag_pump

    def OnStartStopClick(self): #when start is clicked
        global flag
        global start_stop_button
        global basetime
        global start_time
        global timevec
        global sensorvec
        global vmaxvec
        global estbodvec
        global estcodvec
        global vmaxvec
        global vminvec
        global vmintimevec
        global filesaveflag
        global restarter
        global state
        global configfile1path
        global configfile2path
        global BiosensingDataFolder
        global COD_fit_type
        global BOD_fit_type


        if flag==1:
            start_stop_button['text']= 'START'
            start_stop_button['bg']="green"
            flag=0
            restarter=0
            state=1

        elif flag==0:
            start_stop_button['text']= 'STOP'
            start_stop_button['bg']="red"
            flag=1
            restarter=1
            state=0


        basetime=0
        start_time=time.time()
        timevec=[0]
        sensorvec=[0]
        vmaxvec=[0]
        vminvec=[0]
        estcodvec = [0]
        estbodvec = [0]
        vmintimevec=[0]
        filesaveflag=var1.get()
        BOD_regression(self)

        if not os.path.exists('/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/BiosensingData'): #RPi
                            os.makedirs('/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/BiosensingData') #create folder for documents if it doesnt exist
        os.chmod("/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/BiosensingData", 0777) #make folder write and readable for all


        #WINDOWS

##        if not os.path.exists(BiosensingDataFolder):
##                            os.makedirs(BiosensingDataFolder) #create folder for documents if it doesnt exist
##        os.chmod(BiosensingDataFolder, 0777) #make folder write and readable for all



        parser.set('Parameters','tolerance',str(tolerance))
        parser.set('Parameters','vmin', str(Vmin))
        parser.set('Parameters','alpha1', str(alpha1))
        parser.set('Parameters','graphspan', str(graphspan))
        parser.set('Parameters','filesaveflag', str(filesaveflag))
        parser.set('Parameters','restarter', str(restarter))
        parser.set('Parameters','delay', str(delay))
        parser.set('Parameters','y2limit', str(y2limit))
        parser.set('Parameters','y3limit', str(y3limit))
        parser.set('Parameters','y5limit', str(y5limit))
        parser.set('Parameters','y6limit', str(y6limit))
        parser.set('Parameters','vminacq', str(vminacq))
        parser.set('Parameters','vmaxacq', str(vmaxacq))
        parser.set('Parameters','steadyrepeat', str(steadyrepeat))
        parser.set('Parameters','steadyrepeatvmin', str(steadyrepeatvmin))
        parser.set('Parameters','datalog', str(datalog))
        parser.set('Parameters','ocvwait', str(ocvwait))
        parser.set('Parameters','vminwait', str(vminwait))
        parser.set('Parameters','pumpratemlpermin', str(pumprate))
        parser.set('Parameters','targetpumpratemlperday', str(targetpumprate))
        parser.set("Parameters","rload",str(rload))

        with open ('/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/Configuration/biosensorconfig.ini', 'w') as configfile: #Pi
##        with open (configfile1path, 'w') as configfile: #Windows
            parser.write(configfile)
        configfile.close()



    def OnButtonClick(self):
        global filesaveflag
        filesaveflag=var1.get()


#---------------------------------------------------------------------------------------------------------------------------
##FUNCTIONS FOR FLOW_THROUGH
#DEFINITIONS OF COMMANDS

    def OnSaveClick2(self): #this save is in the parameter box
        global tolerance2
        global Vmin2
        global alpha1_2
        global graphspan2
        global delay2
##        global ylimit2
        global y2limit2
        global y3limit2
##        global y4limit2
        global vminacq2
        global vmaxacq2
        global steadyrepeat2
        global steadyrepeatvmin2
        global datalog2
        global ocvwait2
        global vminwait2
        global pumpcontroloff2
        global pumpcontrolon2
        global configfile1path
        global configfile2path
        global BiosensingDataFolder
        global rload2
        global rload2_Flag
        self.parameter2.tolerancev2.set(self.parameter2.tolerancev2.get())
        tolerance2=float(self.parameter2.tolerancev2.get())
        self.parameter2.vminv2.set(self.parameter2.vminv2.get())
        Vmin2=float(self.parameter2.vminv2.get())
        self.parameter2.vfilterv2.set(self.parameter2.vfilterv2.get())
        alpha1_2=float(self.parameter2.vfilterv2.get())
        self.parameter2.destroy()
        graphspan2=float(self.parameter2.gspan2.get())
        self.parameter2.destroy()
        delay2 =float(self.parameter2.delayv2.get())
        self.parameter2.destroy()
##        ylimit2=float(self.parameter2.ylimitv2.get())
##        self.parameter2.destroy()
        y2limit2=float(self.parameter2.y2limitv2.get())
        self.parameter2.destroy()
        y3limit2=float(self.parameter2.y3limitv2.get())
        self.parameter2.destroy()
        rload2=float(self.parameter2.rloadv2.get())
        self.parameter2.destroy()
        rload2_Flag = 1
##        y4limit2=float(self.parameter2.y4limitv2.get())
##        self.parameter2.destroy()
        vminacq2=float(self.parameter2.vminacqv2.get())
        self.parameter2.destroy()
        vmaxacq2=float(self.parameter2.vmaxacqv2.get())
        self.parameter2.destroy()
        steadyrepeat2=float(self.parameter2.steadyrepeatv2.get())
        self.parameter2.destroy()
        steadyrepeatvmin2=float(self.parameter2.steadyrepeatvminv2.get())
        self.parameter2.destroy()
        datalog2=float(self.parameter2.datalogv2.get())
        self.parameter2.destroy()
        ocvwait2=float(self.parameter2.ocvwaitv2.get())
        self.parameter2.destroy()
        vminwait2=float(self.parameter2.vminwaitv2.get())
        self.parameter2.destroy()
        pumpcontrolon2=float(self.parameter2.pumpcontrolonv2.get())
        self.parameter2.destroy()
        pumpcontroloff2=float(self.parameter2.pumpcontroloffv2.get())
        self.parameter2.destroy()
        parser2.set('Parameters','tolerance',str(tolerance2))
        parser2.set('Parameters','vmin', str(Vmin2))
        parser2.set('Parameters','alpha1', str(alpha1_2))
        parser2.set('Parameters','graphspan', str(graphspan2))
        parser2.set('Parameters','filesaveflag', str(filesaveflag_2))
        parser2.set('Parameters','restarter', str(restarter2))
        parser2.set('Parameters','delay', str(delay2))
        parser2.set('Parameters','y2limit', str(y2limit2))
        parser2.set('Parameters','y3limit', str(y3limit2))
        #parser2.set('Parameters','y5limit', str(y5limit2))
        #parser2.set('Parameters','y6limit', str(y6limit2))
        parser2.set('Parameters','vminacq', str(vminacq2))
        parser2.set('Parameters','vmaxacq', str(vmaxacq2))
        parser2.set('Parameters','steadyrepeat', str(steadyrepeat2))
        parser2.set('Parameters','steadyrepeatvmin', str(steadyrepeatvmin2))
        parser2.set('Parameters','datalog', str(datalog2))
        parser2.set('Parameters','ocvwait', str(ocvwait2))
        parser2.set('Parameters','vminwait', str(vminwait2))
        parser2.set('Parameters','pumpcontrolon', str(pumpcontrolon2))
        parser2.set('Parameters','pumpcontroloff', str(pumpcontroloff2))
        parser2.set("Parameters","rload",str(rload2))

        with open ('/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/Configuration/biosensorconfig2.ini', 'w') as configfile2:
            parser2.write(configfile2)
        configfile2.close()

      #WINDOWS
#        with open (configfile2path, 'w') as configfile2:
#            parser2.write(configfile2)
#        configfile2.close()

 #       configfile1path

    def OnPumpClick2(self): #when pump button is clicked
        global flag_pump_2
        global pump_button_2
        if flag_pump_2==1:
            pump_button_2['text']= 'PUMP OFF'
            flag_pump_2=0

        elif flag_pump_2==0:
            pump_button_2['text']= 'PUMP ON'
            flag_pump_2=1

    def OnStartStopClick2(self): #when start is clicked
        global flag_2
        global start_stop_button2
        global basetime2
        global start_time2
        global timevec2
        global sensorvec2
        global vmaxvec2
        global vmaxvec2
        global vminvec2
        global vmintimevec2
        global filesaveflag_2
        global restarter2
        global state2
        global configfile1path
        global configfile2path
        global BiosensingDataFolder

        if flag_2==1:
            start_stop_button2['text']= 'START'
            start_stop_button2['bg']="yellowgreen"
            flag_2=0
            restarter2=0
            state2=1


        elif flag_2==0:
            start_stop_button2['text']= 'STOP'
            start_stop_button2['bg']="orangered"
            flag_2=1
            restarter2=1
            state2=0

        sensorvec2=[0]
        basetime2=0
        start_time2=time.time()
        timevec2=[0]
        sensorvec2=[0]
        vmaxvec2=[0]
        vminvec2=[0]
        vmintimevec2=[0]
        filesaveflag_2=var2.get()

        if not os.path.exists(BiosensingDataFolder):
                            os.makedirs(BiosensingDataFolder) #create folder for documents if it doesnt exist
        os.chmod(BiosensingDataFolder, 0777) #make folder write and readable for all
        parser2.set('Parameters','tolerance',str(tolerance2))
        parser2.set('Parameters','vmin', str(Vmin2))
        parser2.set('Parameters','alpha1', str(alpha1_2))
        parser2.set('Parameters','graphspan', str(graphspan2))
        parser2.set('Parameters','filesaveflag', str(filesaveflag_2))
        parser2.set('Parameters','restarter', str(restarter2))
        parser2.set('Parameters','delay', str(delay2))
        parser2.set('Parameters','y2limit', str(y2limit2))
        parser2.set('Parameters','y3limit', str(y3limit2))
        parser2.set('Parameters','vminacq', str(vminacq2))
        parser2.set('Parameters','vmaxacq', str(vmaxacq2))
        parser2.set('Parameters','steadyrepeat', str(steadyrepeat2))
        parser2.set('Parameters','steadyrepeatvmin', str(steadyrepeatvmin2))
        parser2.set('Parameters','datalog', str(datalog2))
        parser2.set('Parameters','ocvwait', str(ocvwait2))
        parser2.set('Parameters','vminwait', str(vminwait2))
        parser2.set('Parameters','pumpcontrolon', str(pumpcontrolon2))
        parser2.set('Parameters','pumpcontroloff', str(pumpcontroloff2))
        parser2.set("Parameters","rload",str(rload2))
        with open ('/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/Configuration/biosensorconfig2.ini', 'w') as configfile2:##
##        with open (configfile2path, 'w') as configfile2: #Windows
            parser2.write(configfile2)
        configfile2.close()


    def OnButtonClick2(self):
        global filesaveflag_2
        filesaveflag_2=var2.get()


if __name__ == "__main__": #creation of main. This is where you put your main code
    app = simpleapp_tk(None)
    app.title('MFC Based Online Biosensor') #title of application
    app.geometry("720x420")
    app.configure(background='lightgray')

    tab_parent=ttk.Notebook(app)
    tab1 = ttk.Frame(tab_parent,width = 600,height = 800,)
    tab2 = ttk.Frame(tab_parent, width = 500,height = 700)
    tab3 = ttk.Frame(tab_parent,width = 500,height = 700)
    #tab4 = ttk.Frame(tab_parent,width = 500,height = 700)

    tab_parent.add(tab1, text="Biosensors summary")
    tab_parent.add(tab2, text="Graphs for floating biosensor outputs")
    tab_parent.add(tab3, text="Graphs for flow through biosensor outputs")
    #tab_parent.add(tab4, text="Estimated BOD Graph")


    frame1 = Tkinter.LabelFrame(tab1, text ='Floating biosensor', font='Arial 10 bold')
    frame1.grid(column=0, row=0, columnspan=5, sticky='W', padx=5, pady=5, ipadx=5, ipady=5)
    frame2 = Tkinter.LabelFrame(tab1, text ='Flow-through biosensor', font='Arial 10 bold')
    frame2.grid(column=0, row=7, columnspan=5, sticky='W', padx=5, pady=10, ipadx=5, ipady=5)





    ##SENSOR SUMMARY WIDGETS
    ## ----------------------------------------------------------------------
    ## FLOATING HEADINGS

    #STATUS
    app.sensorvlabelvariable= Tkinter.StringVar() #variable to call label
    defaultbg = app.cget('bg')
    sensorv_label = Tkinter.Label(frame1,textvariable=app.sensorvlabelvariable,
                          anchor="w",fg="black",bg=defaultbg)
    sensorv_label.grid(column=0,row=1,sticky='W') #label position
    app.sensorvlabelvariable.set(u"STATUS")

    #SENSOR_DISPLAY
    app.sensordisplay = Tkinter.StringVar() #variable to call label
    global statusdisplay
    statusdisplay=app.sensordisplay
    sensordisplaylabel = Tkinter.Label(frame1,textvariable=app.sensordisplay,
                          anchor="center",fg="white",bg="gray", width=42) #putting a label behind the labels. Labels display text
    sensordisplaylabel.grid(column=1,row=1,columnspan=4,sticky='WE') #label position
    sensordisplaylabel.grid_propagate(False)
    app.sensordisplay.set(u"OFF") #default value in display

    #MFC VOLTAGE VALUE DISPLAY
    app.mfcdisplayvariable = Tkinter.StringVar() #variable to call label
    global voltageset
    voltageset=app.mfcdisplayvariable
    mfcdisplay_label = Tkinter.Label(frame1,textvariable=app.mfcdisplayvariable,
                                     anchor="w",fg="black",bg="ivory", width=6)
    mfcdisplay_label.grid(column=1,row=2,sticky='NESW') #label position
    app.mfcdisplayvariable.set(str(MFCreading)) #default value in display

    #MFCV_LABEL
    app.mfclabelvariable = Tkinter.StringVar() #variable to call label
    defaultbg = app.cget('bg')
    mfc_label = Tkinter.Label(frame1,textvariable=app.mfclabelvariable,
                          anchor="w",fg="black",bg=defaultbg)
    mfc_label.grid(column=0,row=2,sticky='NESW') #label position
    app.mfclabelvariable.set(u"MFC voltage (mV)") #default value in display

    #VMAX_EST LABEL
    app.vmaxlabelvariable = Tkinter.StringVar() #variable to call label
    defaultbg = app.cget('bg')
    vmax_label = Tkinter.Label(frame1,textvariable=app.vmaxlabelvariable,
                          anchor="w",fg="black",bg=defaultbg)
    vmax_label.grid(column=0,row=3,sticky='W') #label position
    app.vmaxlabelvariable.set(u"Vmax (mV)") #default value in display

    #VMIN_EST LABEL
    app.vminlabelvariable = Tkinter.StringVar() #variable to call label
    defaultbg = app.cget('bg')
    vmin_label = Tkinter.Label(frame1,textvariable=app.vminlabelvariable,
                          anchor="w",fg="black",bg=defaultbg)
    vmin_label.grid(column=0,row=4,sticky='W') #label position
    app.vminlabelvariable.set(u"Vmin (mV)") #default value in display

    #VMAX_EST DISPLAY
    app.vmaxdisplayvariable = Tkinter.StringVar() #variable to call label
    global vmaxset
    vmaxset=app.vmaxdisplayvariable
    vmaxdisplay_label = Tkinter.Label(frame1,textvariable=app.vmaxdisplayvariable,
                                     anchor="w",fg="black",bg="linen")
    vmaxdisplay_label.grid(column=1,row=3,sticky='NESW') #label position
    app.vmaxdisplayvariable.set(str(0)) #default value in display

    #VMIN_EST DISPLAY
    app.vminvdisplayvariable = Tkinter.StringVar() #variable to call label
    global vminvset
    vminvset=app.vminvdisplayvariable
    vminvdisplay_label = Tkinter.Label(frame1,textvariable=app.vminvdisplayvariable,
                                     anchor="w",fg="black",bg="linen")
    vminvdisplay_label.grid(column=1,row=4,sticky='NESW') #label position
    app.vminvdisplayvariable.set(str(0)) #default value in display

    #TEMP LABEL
    app.templabelvariable = Tkinter.StringVar() #variable to call label
    defaultbg = app.cget('bg')
    temp_label = Tkinter.Label(frame1,textvariable=app.templabelvariable,
                          anchor="w",fg="black",bg=defaultbg)
    temp_label.grid(column=0,row=5,sticky='W') #label position
    app.templabelvariable.set(u"Ambient Temp \N{DEGREE SIGN}C") #default value in display

    #TEMPERATURE DISPLAY
    app.tempvdisplayvariable = Tkinter.StringVar() #variable to call label
    global tempvset
    tempvset=app.tempvdisplayvariable
    tempvdisplay_label = Tkinter.Label(frame1,textvariable=app.tempvdisplayvariable,
                                     anchor="w",fg="black",bg="lavender")
    tempvdisplay_label.grid(column=1,row=5,sticky='NESW') #label position
    app.tempvdisplayvariable.set(str(tempV)) #default value in display

    #BOD LABEL
    app.bodlabelvariable = Tkinter.StringVar() #variable to call label
    defaultbg = app.cget('bg')
    bod_label = Tkinter.Label(frame1,textvariable=app.bodlabelvariable,
                          anchor="w",fg="black",bg=defaultbg)
    bod_label.grid(column=0,row=6,sticky='W') #label position
    app.bodlabelvariable.set(u"Estimated BOD (mg/L): ") #default value in display

    #BOD DISPLAY
    app.bodvdisplayvariable = Tkinter.StringVar() #variable to call label
    global bodvset
    bodvset=app.bodvdisplayvariable
    bodvdisplay_label = Tkinter.Label(frame1,textvariable=app.bodvdisplayvariable,
                                     anchor="w",fg="black",bg="lavender")
    bodvdisplay_label.grid(column=1,row=6,sticky='NESW') #label position
    app.bodvdisplayvariable.set(str(bodV)) #default value in display

    #COD LABEL
    app.codlabelvariable = Tkinter.StringVar() #variable to call label
    defaultbg = app.cget('bg')
    cod_label = Tkinter.Label(frame1,textvariable=app.codlabelvariable,
                          anchor="w",fg="black",bg=defaultbg)
    cod_label.grid(column=0,row=7,sticky='W') #label position
    app.codlabelvariable.set(u"Estimated COD (mg/L): ") #default value in display

    #COD DISPLAY
    app.codvdisplayvariable = Tkinter.StringVar() #variable to call label
    global codvset
    codvset=app.codvdisplayvariable
    codvdisplay_label = Tkinter.Label(frame1,textvariable=app.codvdisplayvariable,
                                     anchor="w",fg="black",bg="lavender")
    codvdisplay_label.grid(column=1,row=7,sticky='NESW') #label position
    app.codvdisplayvariable.set(str(codV)) #default value in display

    ## CALIBRATION BUTTON
    parameter_button = Tkinter.Button(frame1,text=u"BOD/COD CALIBRATION",
                           command=app.OnCalibrationClick) #button entry
    parameter_button.grid(column=5,row=2,sticky='W') #button entry location


    ## PARAMETER BUTTON
    parameter_button =Tkinter.Button(frame1,text=u"SETTINGS",
                           command=app.OnParameterClick) #button entry
    parameter_button.grid(column=5,row=3,sticky='W') #button entry location

    #SAVE checkBUTTON
    global var1
    global self
    var1 = Tkinter.IntVar()
    save_button =Tkinter.Checkbutton(frame1,text=u"SAVE DATA",variable=var1,command=app.OnButtonClick) #button entry
    save_button.select()
    save_button.grid(column=5, row=1) #button entry location

    #START_STOP BUTTON
    global start_stop_button
    start_stop_button =Tkinter.Button(frame1,text=u"START",
                           command=app.OnStartStopClick, bg="green") #button entry
    start_stop_button.grid(column=5,row=5,sticky='EW') #button entry location

    global f
    global a
    global a2
    f = Figure(figsize=(4,4), dpi=72, tight_layout=True)
    #FIRST GRAPH
    a = f.add_subplot(111)
    a2= a.twinx()
    a.set_title('Biosensor outputs')
    a.set_xlabel('time (h)')
    a.set_ylabel('$V_{max}$',color='tab:red')
    a.tick_params(axis='y', labelcolor='tab:red')
    a.set_ylim([0,y2limit])
    a2.set_ylabel('$V_{min}$',color='tab:green')
    a2.tick_params(axis='y', labelcolor='tab:green')
    a2.set_ylim([0,y3limit])
    global canvas
    canvas=FigureCanvasTkAgg (f, tab2)
    canvas.draw()
    canvas.get_tk_widget().grid(column=0,row=0,columnspan=3,rowspan=4, sticky='NSEW',padx=20, pady=20) #graph position
##    toolbar1= Frame(tab2, width=42)   #New frame to bypass the pack limitation
##    toolbar1.grid(column=1,row=16,columnspan=4,sticky='NESW')
##    toolbar1.grid_propagate(False)
##    toolbar1=NavigationToolbar2TkAgg(canvas,toolbar1)
##    toolbar1.update()

    global f3
    global k
    global k2
    f3 = Figure(figsize=(4,4), dpi=72, tight_layout=True)

    k = f3.add_subplot(111)
    k2 = k.twinx()
    k.set_title('Estimated BOD & COD')
    k.set_xlabel('time (h)')
    k.set_ylabel('$BOD_{est} mg/L$',color='tab:blue')
    k.tick_params(axis='y', labelcolor='tab:blue')
    k.set_ylim([0,y5limit])
    k2.set_ylabel('$COD_{est} mg/L$',color='tab:purple')
    k2.tick_params(axis='y', labelcolor='tab:purple')
    k2.set_ylim([0,y6limit])
    global canvas3
    canvas3 = FigureCanvasTkAgg (f3, tab2)
    canvas3.draw()
    canvas3.get_tk_widget().grid(column=3,row=0,columnspan=3,rowspan=4, sticky='NSEW',padx=20, pady=20) #graph position
    ##    toolbar1= Frame(tab2, width=42)   #New frame to bypass the pack limitation
    ##    toolbar1.grid(column=2,row=16,columnspan=4,sticky='NESW')
    ##    toolbar1.grid_propagate(False)
    ##    toolbar1=NavigationToolbar2TkAgg(canvas,toolbar1)
    ##    toolbar1.update()



#-----------------------------------------------------------------------------------------------------
    ## FLOW THROUGH SUMMARY WIDGETS

    #STATUS
    app.sensorvlabelvariable2 = Tkinter.StringVar() #variable to call label
    defaultbg = app.cget('bg')
    sensorv_label2 = Tkinter.Label(frame2,textvariable=app.sensorvlabelvariable2,
                          anchor="w",fg="black",bg=defaultbg)
    sensorv_label2.grid(column=0,row=9,sticky='W') #label position
    app.sensorvlabelvariable2.set(u"STATUS")

    #SENSOR_DISPLAY
    app.sensordisplay2 = Tkinter.StringVar() #variable to call label
    global statusdisplay2
    statusdisplay2=app.sensordisplay2
    sensordisplaylabel2 = Tkinter.Label(frame2,textvariable=app.sensordisplay2,
                          anchor="center",fg="white",bg="gray",width=42) #putting a label behind the labels. Labels display text
    sensordisplaylabel2.grid(column=1,row=9,columnspan=4,sticky='WE') #label position
    sensordisplaylabel2.grid_propagate(False)
    app.sensordisplay2.set(u"OFF") #default value in display

    #MFCV_LABEL
    app.mfclabelvariable2 = Tkinter.StringVar() #variable to call label
    defaultbg = app.cget('bg')
    mfc_label2 = Tkinter.Label(frame2,textvariable=app.mfclabelvariable2,
                          anchor="w",fg="black",bg=defaultbg)
    mfc_label2.grid(column=0,row=10,sticky='E') #label position
    app.mfclabelvariable2.set(u"MFC voltage (mV)") #default value in display

    #MFC VOLTAGE VALUE DISPLAY
    app.mfcdisplayvariable2 = Tkinter.StringVar() #variable to call label
    global voltageset2
    voltageset2=app.mfcdisplayvariable2
    mfcdisplay_label2 = Tkinter.Label(frame2,textvariable=app.mfcdisplayvariable2,
                                     anchor="w",fg="black",bg="ivory", width=6)
    mfcdisplay_label2.grid(column=1,row=10,sticky='NESW') #label position
    app.mfcdisplayvariable2.set(str(MFCreading)) #default value in display

    #VMAX_EST LABEL
    app.vmaxlabelvariable2 = Tkinter.StringVar() #variable to call label
    defaultbg = app.cget('bg')
    vmax_label2 = Tkinter.Label(frame2,textvariable=app.vmaxlabelvariable2,
                          anchor="w",fg="black",bg=defaultbg)
    vmax_label2.grid(column=0,row=11,sticky='W') #label position
    app.vmaxlabelvariable2.set(u"Vmax (mV)") #default value in display

    #VMIN_EST LABEL
    app.vminlabelvariable2 = Tkinter.StringVar() #variable to call label
    defaultbg = app.cget('bg')
    vmin_label2 = Tkinter.Label(frame2,textvariable=app.vminlabelvariable2,
                          anchor="w",fg="black",bg=defaultbg)
    vmin_label2.grid(column=0,row=12,sticky='W') #label position
    app.vminlabelvariable2.set(u"Vmin (mV)") #default value in display

    #VMAX_EST DISPLAY
    app.vmaxdisplayvariable2 = Tkinter.StringVar() #variable to call label
    global vmaxset2
    vmaxset2=app.vmaxdisplayvariable2
    vmaxdisplay_label2 = Tkinter.Label(frame2,textvariable=app.vmaxdisplayvariable2,
                                     anchor="w",fg="black",bg="linen", width=6)
    vmaxdisplay_label2.grid(column=1,row=11,sticky='NESW') #label position
    app.vmaxdisplayvariable2.set(str(0)) #default value in display

    #VMIN_EST DISPLAY
    app.vminvdisplayvariable2 = Tkinter.StringVar() #variable to call label
    global vminvset2
    vminvset2=app.vminvdisplayvariable2
    vminvdisplay_label2 = Tkinter.Label(frame2,textvariable=app.vminvdisplayvariable2,
                                     anchor="w",fg="black",bg="linen",width=6)
    vminvdisplay_label2.grid(column=1,row=12,sticky='NESW') #label position
    app.vminvdisplayvariable2.set(str(0)) #default value in display

    #TEMP LABEL
    app.templabelvariable2 = Tkinter.StringVar() #variable to call label
    defaultbg = app.cget('bg')
    temp_label2 = Tkinter.Label(frame2,textvariable=app.templabelvariable2,
                          anchor="w",fg="black",bg=defaultbg)
    temp_label2.grid(column=0,row=13,sticky='W') #label position
    app.templabelvariable2.set(u"Ambient Temp \N{DEGREE SIGN}C") #default value in display

    #TEMPERATURE DISPLAY
    app.tempvdisplayvariable2 = Tkinter.StringVar() #variable to call label
    global tempvset2
    tempvset2=app.tempvdisplayvariable2
    tempvdisplay_label2 = Tkinter.Label(frame2,textvariable=app.tempvdisplayvariable2,
                                     anchor="w",fg="black",bg="lavender")
    tempvdisplay_label2.grid(column=1,row=13,sticky='NESW') #label position
    app.tempvdisplayvariable2.set(str(tempV)) #default value in display


    ## PARAMETER BUTTON
    parameter_button2 =Tkinter.Button(frame2,text=u"SETTINGS",
                           command=app.OnParameterClick2) #button entry
    parameter_button2.grid(column=5,row=11,sticky='W') #button entry location

    #PUMP
    global pump_button_2
    pump_button_2 =Tkinter.Button(frame2,text=u"PUMP_ON",
                           command=app.OnPumpClick2, bg="lightskyblue") #button entry
    pump_button_2.grid(column=5,row=12,sticky='EW') #button entry location

    #tab_parent.grid(column=1,row=0,columnspan=8, rowspan=15, sticky='NW')

    #SAVE checkBUTTON
    global var2
    global self
    var2 = Tkinter.IntVar()
    save_button3 =Tkinter.Checkbutton(frame2,text=u"SAVE DATA",variable=var2,command=app.OnButtonClick2) #button entry
    save_button3.select()
    save_button3.grid(column=5, row=9) #button entry location


    #START/STOP BUTTON
    global start_stop_button2
    start_stop_button2 =Tkinter.Button(frame2,text=u"START",
                           command=app.OnStartStopClick2, bg="yellowgreen") #button entry
    start_stop_button2.grid(column=5,row=13,sticky='EW') #button entry location


    #SECOND GRAPH
    global f5
    f5 = Figure(figsize=(4,4), dpi=72, tight_layout=True)
    global p
    p = f5.add_subplot(111)
    p2= p.twinx()
    p.set_title('Biosensor outputs')
    p.set_xlabel('time (h)')
    p.set_ylabel('$V_{max}$',color='tab:red')
    p.tick_params(axis='y', labelcolor='tab:red')
    p.set_ylim([0,y2limit2])
    p2.set_ylabel('$V_{min}$',color='tab:green')
    p2.tick_params(axis='y', labelcolor='tab:green')
    p2.set_ylim([0,y3limit2])
    global canvas5
    canvas5=FigureCanvasTkAgg (f5, tab3)
    canvas5.draw()
    canvas5.get_tk_widget().grid(column=1,row=0,columnspan=4, rowspan=4, sticky='NSEW',padx=20, pady=20) #graph position


    app.grid_columnconfigure(0,weight=0) #configure column 0 to not resize)
    app.grid_columnconfigure(1,weight=0) #configure column 1 to not resize)
    app.grid_columnconfigure(2,weight=0) #configure column 2 to not resize)
    app.grid_columnconfigure(3,weight=0) #configure column 3 to resize with a weight of 1
    app.grid_columnconfigure(4,weight=0) #configure column 2 to not resize)
    app.grid_columnconfigure(5,weight=0) #configure column 2 to not resize)
    app.grid_columnconfigure(6,weight=0) #configure column 2 to not resize)
    app.resizable(False,False) #a constraints not allowing tkinter resizeable along horizontally(column)
                                #(false) but vertically(rows)--false)

    app.update()
    app.geometry(app.geometry())       #prevents the window from resizing all the time

    tab_parent.grid(column=0,row=0,columnspan=10, rowspan=15, sticky='NW') #for all the tabs





## PUMP THREAD
    global self
    def __init__(self,parent):
        Tkinter.Tk.__init__(self,parent)
        self.parent=parent
        self.initialize()

    # Thread that controls pump
    def pump_control_2():
        time.sleep(1)
        global counterpump_2
        global flag_pump_2
        global pumpcontrolon2
        global pumpcontroloff2

        while True:
            if flag_pump_2==1:
                print 'PUMP ON'
                print counterpump_2
                counterpump_2=0
               # d.getFeedback(u3.BitStateWrite(7, 0)) # Set FIO7 to output high to turn on pumpainV
                start_pause=time.time()
                while (time.time()-start_pause < pumpcontrolon2) and flag_pump_2==1:
                    time.sleep(1)
              #  d.getFeedback(u3.BitStateWrite(7, 1)) # Set FIO7 to output low to turn off pump
                start_pause=time.time()
                print ('PUMP working but algorithm set to off')
                while (time.time()-start_pause < pumpcontroloff2) and flag_pump_2==1:
                    time.sleep(1)

            if flag_pump_2==0:
                if counterpump_2 <2:
                    print 'PUMP OFF'
                counterpump_2=counterpump_2+1
                print counterpump_2



    def floating(self):  #Biosensing algorithm
        savecounter=0 # define all local variable here or it will repeat after every true.
        profilesaver=10 # this will enable profiles to be saved for 20 minutes in the begining.
        saveprofile=0
        saveprofile2=0
        #profilesaver2=datalog # save data every 20 minutes
        #global self
        global flag
        global state
        global restarter
        global filenameprefix
        global filesaveflag
        global start_time
        start_time=time.time()
        global Sensoroutput
        global basetime
        global tempV
        global configfile1path
        global configfile2path
        global BiosensingDataFolder
        global bodV
        global codV
        global BOD_lin_coefs
        global BOD_lin_inter
        global BOD_poly2_coefs
        global BOD_poly2_inter
        global BOD_exp_coefs
        global BOD_fit_type
        global r2_BOD
        global COD_fit_eqn
        global COD_fit_type
        global COD_lin_coefs
        global COD_lin_inter
        global COD_poly2_coefs
        global COD_poly2_inter
        global COD_exp_coefs
        global dfs_old
        global BOD_regression
        global filename6
        global headers6
        basetime=0




        while True:
            dataacq=1 #data acquisition time during open circuit mode
            global flag
            global state
            if flag==1:
                start_stop_button['bg']="red"
                start_stop_button['text']= 'STOP'
                if filesaveflag==1:
                    savecounter=savecounter+1
                    if savecounter==1: #helps to save header and filename only once after initialization
                        print "floating biosensor operation and data saving has started..."
                        if not os.path.exists('/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/BiosensingData'):  #Pi
                            os.makedirs('/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/BiosensingData') #create folder for documents if it doesnt exist
                        os.chdir('/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/BiosensingData') #change directory to this new folder and save files here

##                        if not os.path.exists(BiosensingDataFolder): #Windows
##                            os.makedirs(BiosensingDataFolder) #create folder for documents if it doesnt exist
##                        os.chdir(BiosensingDataFolder) #change directory to this new folder and save files here




                        programstarttime=str(datetime.datetime.now()) #get date and time program starts
                        programstart=time.time()
                        profiletimelast=programstart
                        filesuffix=programstarttime[:10]
                        filenameprefixnow='floatingbiosensordata'
                        filename= filenameprefixnow + '.txt' #each file will be used # name will have.txt as type for now
                        filename3='temp&vMFClog' + '.txt' #filename to save MFC profile
                        filename=filename
                        os.chmod("/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/BiosensingData", 0777) #make folder write and readable for all #Pi
#                        os.chmod(BiosensingDataFolder, 0777) #make folder write and readable for all #Windows
                        save_file= open(filename,"a") #for calling the filename where data has been saved
                        headers=['Date', 'Time', 'Vmax_Est', 'Area', 'OCV_time(s)','Tolerance', 'Vmin', 'alpha1','Vmin_Est', 'prev_discharge_time', 'DischargeArea', 'Ambient_Temperature', 'BOD_Est',\
                        'Est_COD', 'Y_calculated', 'Vmax/Vmin', 'OCVwait', 'Vminwait', 'steadystaterepeatocv', 'steadystaterepeatVmin', 'pumprate', 'rload']
                        headers=' '.join(headers)
                        save_file.write(headers +'\n') #write headers to file
                        save_file.close()
                        filename2=filename
                        save_file2=open(filename3,"a") #for calling the filename where profile has been saved
                        headers2=['Date', 'Time', 'VMFC', 'Temperature']
                        headers2=' '.join(headers2)
                        save_file2.write(headers2 +'\n') #write headers to file
                        save_file2.close()

                        #for calibration data
                        filename6='calibration_results' + '.txt' #filename to save results of calibration
                        save_file6=open(filename6,"a")
                        headers6=['Date', 'Time', 'COD_fit_eqn', 'BOD_fit_eqn']
                        headers6=' '.join(headers6)
                        save_file6.write(headers6 +'\n') #write headers to file
                        save_file6.close()
                        BOD_regression(self)

                        filename4=filename3
                    else:
                        filename=filename2



                if state==0:  #MFC is about to be connected to resistor

                    #REINITIALIZE VARIABLES FOR BOTH CHARGE & DISCHARGE CYCLE
                    plateaucounter=0
                    displateaucounter=0
                    voltagelog=[] #initialize voltage log
                    disvoltagelog=[]
                    graphingtime=[] #intialize graphing time
                    timelog=[]
                    distimelog=[]
                    acquisitionspeed_closed=vminacq
                    acquisitionspeed_open=vmaxacq
                    acquire1=0
                    acquire2=0

                    #START DISCHARGE CYCLE
                    discharge_start=time.time()
                    programtimenow=time.time()
                    discounter=0 #counter for discharge cycle


                    #DELAY CONDITION
                    if 1.0<=Sensoroutput and Sensoroutput<=1.01: #wait for a while if discharge isnt that fast
                            statusdisplay.set(u'BIOSENSOR ON, Resistor Connected, Delay Active, Saving ')
                            time.sleep(delay)

                    #global programstart
                    if (programtimenow-programstart)< profilesaver or savecounter==1: #check if the time for profile saving has elapsed
                        saveprofile=1
                        #profilesaver=profilesaver+profilesaver


                    while state==0: #while MFC is connected to resistor

                        if (acquisitionspeed_closed >=vminacq) and (q.empty()==False):
                            ainValue=q.get()
                            acquisitionspeed_closed=0
                            acquire1=time.time()
                            MFCreading=round(ainValue,2)
                            tempV=round(tempV,2)
                            voltageset.set(str(MFCreading)) #default value in display
                            tempvset.set(str(tempV)) #default value in display

                            programtimenow=time.time()
                            if (programtimenow-profiletimelast)>= datalog: #check if the time for profile saving has elapsed
                                saveprofile2=1
                                profiletimelast=time.time()

                            if ainValue<=Vmin: #to prevent error
                                ainValue=Vmin
                                Vmin_Est=round(ainValue,2)
                                vminvset.set(str(Vmin_Est)) #display vmin
                                Disarea_curve=trapz(disvoltagelog,distimelog) #integrate and calculate area under dischareg curv
                                discounter=discounter+1
                                discharge_timenow=time.time()
                                discharge_timeelapsed=discharge_timenow-discharge_start
                                MFCreading=round(ainValue,2)
                                voltageset.set(str(MFCreading)) #default value in display
                                discharge_end=time.time()
                                discharge_time=discharge_end-discharge_start
                                state=1
                                #d.close() #close labjack
                                break
                            discounter=discounter+1
                            discharge_timenow=time.time()
                            discharge_timeelapsed=discharge_timenow-discharge_start
                            MFCreading=round(ainValue,2)
                            voltageset.set(str(MFCreading)) #default value in display

                            #CHECK IF CONDITION TO CONTINUE SAVING EXISTS
                            if saveprofile==1 or saveprofile2==1:
                                profiletime=(str(datetime.datetime.now()))[:19]
                                profilestr= (profiletime +' ' + str(MFCreading) +' '+ str(tempV))
                                save_file2= open(filename3,"a") #openfile to save
                                save_file2.write(profilestr +'\n') #write data to file
                                save_file2.close() #close
                                saveprofile2=0

                            #DECIDE WHAT TO DISPLAY ON GUI BASED ON SELECTION
                            if filesaveflag==1:
                                statusdisplay.set(u'BIOSENSOR ON, Resistor Connected, Saving Enabled')
                            else:
                                statusdisplay.set(u'BIOSENSOR ON, Resistor Connected, Saving Disabled')

                            #CHECK IF STOP BUTTON HAS BEEN CALLED
                            if flag==0:         #stop button value check
                                break

                            #FILTER VALUES
                            if discounter==1:
                                ainValue_ftrd=ainValue
                            else:
                                ainValue_ftrd=((alpha1*ainValue)+((1-alpha1)*disvoltagelog[-1]))

                            #TEMPORARILY STORE VALUES
                            disvoltagelog=disvoltagelog+[ainValue_ftrd] #store discharge voltage in log list initiated earlier
                            distimelog=distimelog+[discharge_timeelapsed]

                            #CHECK PLATEAU CONDITIONS & DO NECESSARY CALCULATIONS

                            if discharge_timeelapsed>vminwait:
                                if len(disvoltagelog)>2:
                                    discheck_state=(1-(disvoltagelog[-1]/disvoltagelog[-2]))
                                    if (discheck_state >= 0 and discheck_state<=tolerance) or ainValue<Vmin :
                                        displateaucounter=displateaucounter+1
                                    else:
                                        displateaucounter=0
                                    #IF PLATEAU CONDITION IS REACHED 3 CONSECUTIVE TIMES
                                    if displateaucounter==steadyrepeatvmin: #wait for at specified repeat of the vmin
                                        discharge_end=time.time()
                                        discharge_time=discharge_end-discharge_start
                                        discharge_time=round(discharge_time,2) #round to 2 decimal places
                                        Vmin_Est=disvoltagelog[-1] #estimated Vmin
                                        Vmin_Est=round(Vmin_Est,2)
                                        vminvset.set(str(Vmin_Est)) #display vmin
                                        Disarea_curve=trapz(disvoltagelog,distimelog) #integrate and calculate area under dischareg curve
                                        state=1
                                        #d.close() #close labjack
                                        break
                        acquire2=time.time()
                        time.sleep(0.05)
                        acquisitionspeed_closed=acquire2-acquire1

                if (state==1):    #MFC is now going into open circuit mode
                    OCV_start=time.time()
                    counter=0 #reset counter


                    while state==1:
                        if acquisitionspeed_open>=vmaxacq and (q.empty()==False):
                            acquire1=time.time()
                            acquisitionspeed_open=0
                            ainValue=q.get()
                            OCV_timenow=time.time()
                            OCVtime_elapsed=OCV_timenow-OCV_start #calculate time elapsed
                            MFCreading=round(ainValue,2)
                            voltageset.set(str(MFCreading)) #display value in display
                            programtimenow=time.time()

                            if (programtimenow-profiletimelast)>= datalog: #check if the time for profile saving has elapsed
                                saveprofile2=1
                                profiletimelast=time.time()


                            #saveprofile=1
                            if saveprofile==1 or saveprofile2==1:
                                profiletime=(str(datetime.datetime.now()))[:19]
                                profilestr= (profiletime +' ' + str(MFCreading) +' '+ str(tempV))
                                save_file2= open(filename3,"a") #openfile to save
                                save_file2.write(profilestr +'\n') #write data to file
                                save_file2.close() #close
                                saveprofile2=0
                            if filesaveflag==1:
                                statusdisplay.set(u'BIOSENSOR ON, Open Circuit, Saving Enabled')
                            else:
                                statusdisplay.set(u'BIOSENSOR ON, Open Circuit, Saving Disabled')
                            counter=counter+1 #record it as a step
                            if flag==0: #stop button value check
                                break
                            #apply filter to voltage
                            if counter==1:
                                ainValue_ftrd=ainValue
                            else:
                                ainValue_ftrd=((alpha1*ainValue)+((1-alpha1)*voltagelog[-1]))
                            voltagelog=voltagelog+[ainValue_ftrd] #store voltage in voltage log list initiated earlier
                            timelog=timelog+[OCVtime_elapsed]


                            #check for plateauing condition after a minimum of specified time for Vmax estimation
                            if OCVtime_elapsed>ocvwait and len(voltagelog)>2:
                                check_state=((voltagelog[-1]/voltagelog[-2])-1)
                                if check_state<0:
                                    check_state=-check_state
                                if check_state<tolerance: # and (voltagelog[-1]-voltagelog[-2])>=0:   #if condition of assumed Vmax attainment has been reached also make sure that negative voltages don't cause switching
                                    plateaucounter=plateaucounter+1
                                else:
                                    plateaucounter=0
                                if plateaucounter==steadyrepeat: #wait for at least 3 of this plateau conditions to be satisfied simultaneously
                                    OCV_end=time.time() #time at this moment of plateau

                                    telapsed=OCV_end-start_time #elapsedtime since start
                                    tchart=round(((telapsed+basetime)/3600),2) #time in hours since  plotting started

                                    global timevec
                                    timevec=timevec
                                    global sensorvec
                                    sensorvec=sensorvec
                                    global vmaxvec
                                    vmaxvec = vmaxvec
                                    global estbodvec
                                    estbodvec = estbodvec
                                    global estcodvec
                                    estcodvec = estcodvec
                                    global vminvec
                                    vminvec=vminvec
                                    global vmintimevec
                                    vmintimevec=vmintimevec
                                    global y2limit
                                    global y3limit
                                    global y5limit
                                    global y6limit
##                                    global y4limit
                                    global pumprate
                                    global targetpumprate

                                    timevec_checker=timevec
                                    timevec_checker=timevec_checker+[tchart]
                                    check=timevec_checker[-1]-timevec_checker[0]

                                    OCV_time=OCV_end-OCV_start #calulate time to reach this estimated Vmax
                                    OCV_time=round(OCV_time,2) #round to 2 decimal places
                                    Vmax_Est=voltagelog[-1] #save this estimated Vmax as the last subject
                                    Vmax_Est=round(Vmax_Est,2)
                                    vmaxset.set(str(Vmax_Est))

                                    Area_curve=trapz(voltagelog,timelog) #integrate and calculate area under curve

                                    if Vmin_Est==0:
                                        Vmin_Est=0.1

                                    Sensoroutput=round((Vmax_Est/Vmin_Est),2)

                                    #calculate Y
                                    Y_calculated = Vmin_Est/AprilPoly(tempV)

                                    #Estimate BOD
                                    if BOD_fit_type == 'Linear':
                                        bodV = BOD_lin_inter[0] + BOD_lin_coefs[0][0]*Y_calculated
                                        bodV = round(bodV, 2)
                                        bodvset.set(str(bodV))

                                    if BOD_fit_type == 'Exponential':
                                        bodV = math.exp(BOD_exp_coefs[1]) * math.exp(BOD_exp_coefs[0]*Y_calculated)
                                        bodV = round(bodV, 2)
                                        bodvset.set(str(bodV))

                                    if BOD_fit_type == 'Polynomial':
                                        bodV = BOD_poly2_inter[0] + (BOD_poly2_coefs[0][1] *Y_calculated)  + (BOD_poly2_coefs[0][2] * (Y_calculated * Y_calculated))
                                        bodV = round(bodV, 2)
                                        bodvset.set(str(bodV))

                                    #Estimate COD
                                    if COD_fit_type == 'Linear':
                                        codV = COD_lin_inter[0] + COD_lin_coefs[0][0]*Y_calculated
                                        codV = round(codV, 2)
                                        codvset.set(str(codV))

                                    if COD_fit_type == 'Exponential':
                                        codV = math.exp(COD_exp_coefs[1]) * math.exp(COD_exp_coefs[0]*Y_calculated)
                                        codV = round(codV, 2)
                                        codvset.set(str(codV))

                                    if COD_fit_type == 'Polynomial':
                                        codV = COD_poly2_inter[0] + (COD_poly2_coefs[0][1] *Y_calculated)  + (COD_poly2_coefs[0][2] * (Y_calculated * Y_calculated))
                                        codV = round(codV, 2)
                                        codvset.set(str(codV))


                                    #sensorvset.set(str(Sensoroutput)) #display value in display

                                    if check <=graphspan:

                                        sensorvec = sensorvec + [Sensoroutput]
                                        vmaxvec = vmaxvec + [Vmax_Est]
                                        vminvec = vminvec + [Vmin_Est]
                                        estbodvec = estbodvec + [bodV]
                                        estcodvec = estcodvec + [codV]
                                        vmintimevec = vmintimevec + [discharge_time]
                                        timevec = timevec + [tchart]

                                    else:
                                        aux1 = sensorvec
                                        sensorvec = aux1[2:]+[Sensoroutput]
                                        aux2 = timevec
                                        timevec=aux2[2:]+[tchart]
                                        aux3 = vmaxvec
                                        vmaxvec = aux3[2:]+[Vmax_Est]
                                        aux4 = vminvec
                                        vminvec = aux4[2:]+[Vmin_Est]
                                        aux5 = vmintimevec
                                        vmintimevec = aux5[2:]+[discharge_time]
                                        aux6 = estbodvec
                                        estbodvec = aux6[2:] + [bodV]
                                        aux7 = estcodvec
                                        estcodvec = aux7[2:] + [codV]

                                    #print len(sensorvec)
                                    #print len(timevec)

                                    #later improvements to check
##                                    if max(vmaxvec) >500:
##                                        y2limit = max(vmaxvec) + (0.5*max(vmaxvec))
##                                    if max(vminvec)> 300:
##                                        y3limit = max(vminvec) + (0.5*max(vminvec))
##                                    if max(vmintimevec)>300:
##                                        y4limit = max(vmintimevec) + (0.5*max(vmintimevec))


                                    a = f.add_subplot(111)
                                    a.clear()
                                    a2.clear()
                                    a.set_title('Biosensor outputs')
                                    a.set_xlabel('time (h)')
                                    a.set_ylabel('$V_{max}$',color='tab:red')
                                    a.tick_params(axis='y', labelcolor='tab:red')
                                    a.set_ylim([0,y2limit])
                                    a.plot(timevec,vmaxvec, 'k:', ls=':', marker='o', color='tab:red')
                                    a2.set_ylabel('$V_{min}$',color='tab:green')
                                    a2.plot(timevec,vminvec, 'k:', ls=':', marker='o', color='tab:green')
                                    a2.tick_params(axis='y', labelcolor='tab:green')
                                    a2.set_ylim([0,y3limit])
                                    canvas=FigureCanvasTkAgg (f, tab2)
                                    canvas.draw()
                                    canvas.get_tk_widget().grid(column=0,row=0,columnspan=3,rowspan=4, sticky='NSEW',padx=20, pady=20) #graph position
                                    ##

                                    k = f3.add_subplot(111)
                                    k.clear()
                                    k2.clear()
                                    k.set_title('Estimated BOD & COD')
                                    k.set_xlabel('time (h)')
                                    k.set_ylabel('$BOD_{est} mg/L$',color='tab:blue')
                                    k.tick_params(axis='y', labelcolor='tab:blue')
                                    k.set_ylim([0,y5limit]) #define ylimit5 for BOD data
                                    k.plot(timevec,estbodvec, 'k:', ls=':', marker='o', color='tab:blue')
                                    k2.set_ylabel('$COD_{est} mg/L$',color='tab:purple')
                                    k2.plot(timevec,estcodvec, 'k:', ls=':', marker='o', color='tab:purple')
                                    k2.tick_params(axis = 'y', labelcolor='tab:purple')
                                    k2.set_ylim([0,y6limit]) #define ylimit6 for BOD data
                                    canvas3 = FigureCanvasTkAgg (f3, tab2)
                                    canvas3.draw()
                                    canvas3.get_tk_widget().grid(column=3,row=0,columnspan=3,rowspan=4, sticky='NSEW',padx=20, pady=20) #graph position
                                  ##    t
##
                                    #record all data
                                    if filesaveflag == 1:
                                        timeofsave = (str(datetime.datetime.now()))[:19]
                                        datastr = (timeofsave +' ' + str(Vmax_Est)+' ' + str(Area_curve)+
                                                  ' ' + str(OCV_time)+' ' +str(tolerance)+' '+str(Vmin)+' '+str(alpha1)+' '+str(Vmin_Est)+' '+str(discharge_time)+' '+str(Disarea_curve)+' '+str(tempV)+' '+str(bodV) +' ' +str(codV)+' '+str(Y_calculated)+\
                                                  ' '+ str(Sensoroutput)+' '+str(ocvwait)+' '+str(vminwait)+' '+str(steadyrepeat)+' '+str(steadyrepeatvmin)+' '+ str(targetpumprate) +' '+str(rload))
                                        save_file = open(filename,"a") #openfile to save
                                        save_file.write(datastr +'\n') #write data to file
                                        save_file.close() #close
                                    saveprofile = 0; #reset save profile decider
                                    state = 0 #turn state to open circuit
                                    plateaucounter = 0
                        acquire2 = time.time()
                        time.sleep(0.05)
                        acquisitionspeed_open = acquire2-acquire1


            if flag==0:
                #d.getFeedback(u3.BitStateWrite(4, 0)) #SET FI04 to output low to disconnect resistor
                offperiod=time.time()
                start_stop_button['text']= 'START'
                start_stop_button['bg']="green"

                if not os.path.exists('/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/BiosensingData'):  #RPi
                    os.makedirs('/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/BiosensingData') #create folder for documents if it doesnt exist
                os.chdir('/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/BiosensingData') #change directory to this new folder and save files here

#                if not os.path.exists(BiosensingDataFolder): #Windows
#                    os.makedirs(BiosensingDataFolder) #create folder for documents if it doesnt exist
#                os.chdir(BiosensingDataFolder) #change directory to this new folder and save files here


                filename3='temp&vMFClog' + '.txt' #filename to save MFC profile
                save_file2=open(filename3,"a") #for calling the filename where profile has been saved
                headers2=['Date', 'Time', 'VMFC']
                headers2=' '.join(headers2)
                save_file2.write(headers2 +'\n') #write headers to file
                save_file2.close()
                saveprofile2=0
                profiletimelast=offperiod
                #BOD_regression(self)

                #for calibration data
                filename6='calibration_results' + '.txt' #filename to save results of calibration
                save_file6=open(filename6,"a")
                headers6=['Date', 'Time', 'COD_fit_eqn', 'BOD_fit_eqn']
                headers6=' '.join(headers6)
                save_file6.write(headers6 +'\n') #write headers to file
                save_file6.close()
                BOD_regression(self)

                print 'OFF'
                while flag==0:
                    #print 'OFF'
                    statusdisplay.set(u'FLOATING BIOSENSOR OPERATION-OFF')
                    Sensoroutput=0.00
                    #sensorvset.set(str(Sensoroutput)) #display value in display
                    ainValue=q.get()
                    MFCreading=round(ainValue,2)
                    tempV=round(tempV,2)
                    bodV = 0.0
                    codV = 0.0
                    voltageset.set(str(MFCreading)) #default value in display
                    tempvset.set(str(tempV)) #default value in display
                    bodvset.set(str(bodV))
                    codvset.set(str(codV))
                    programtimenow=time.time()

                    if (programtimenow-profiletimelast)>= datalog: #check if the time for profile saving has elapsed
                            saveprofile2=1
                            profiletimelast=time.time()

                    if saveprofile2==1:
                            profiletime=(str(datetime.datetime.now()))[:19]
                            profilestr= (profiletime +' ' + str(MFCreading) +' '+ str(tempV))
                            save_file2= open(filename3,"a") #openfile to save
                            save_file2.write(profilestr +'\n') #write data to file
                            save_file2.close() #close
                            saveprofile2=0
                    time.sleep(vminacq)
                    savecounter=0



    def flowthrough(q2):  #Biosensing algorithm
        ainValue2=q2.get
        #CONFIGURE LABJACK
        savecounter2=0 # define all local variable here or it will repeat after every true.
        profilesaver2=10 # this will enable profiles to be saved for 20 minutes in the begining.
        saveprofile2=0
        saveprofile2=0
        #profilesaver2=datalog # save data every 20 minutes
        global flag_2
        global state2
        global restarter2
        global filenameprefix2
        global start_time2
        start_time2=time.time()
        global Sensoroutput2
        global basetime2
        global tempV
        global configfile1path
        global configfile2path
        global BiosensingDataFolder
        #global ainValue2
        basetime2=0



        while True:
            dataacq2=1 #data acquisition time during open circuit mode
            global flag_2
            global state2
            #ainValue2=q2.get()
            time.sleep(0.5)


            #state2=0
            if flag_2==1:
                start_stop_button2['bg']="orangered"
                start_stop_button2['text']= 'STOP'

                if filesaveflag_2==1:
                    savecounter2=savecounter2+1
                    if savecounter2==1: #helps to save header and filename only once after initialization
                        print "Flow-through biosensor operation and data saving has started..."

                        if not os.path.exists('/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/BiosensingData'): #Pi
                            os.makedirs('/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/BiosensingData') #create folder for documents if it doesnt exist
                        os.chdir('/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/BiosensingData') #change directory to this new folder and save files here

##                        if not os.path.exists(BiosensingDataFolder): #Windows
##                           os.makedirs(BiosensingDataFolder) #create folder for documents if it doesnt exist
##                        os.chdir(BiosensingDataFolder) #change directory to this new folder and save files here





                        programstarttime2=str(datetime.datetime.now()) #get date and time program starts
                        programstart2=time.time()
                        profiletimelast2=programstart2
                        filesuffix2=programstarttime2[:10]
                        filenameprefixnow2='flowthroughdata'
                        filename2= filenameprefixnow2 + '.txt' #each file will be used # name will have.txt as type for now
                        filename3_2='flowthroughtemp&vMFClog' + '.txt' #filename to save MFC profile
                        filename2=filename2

                        os.chmod("/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/BiosensingData", 0777) #make folder write and readable for all
##                        os.chmod(BiosensingDataFolder, 0777) #make folder write and readable for all #Windows

                        save_file2= open(filename2,"a") #for calling the filename where data has been saved


                        headers2=['Date', 'Time', 'Vmax_Est', 'Area', 'OCV_time(s)','Tolerance', 'Vmin', 'alpha1','Vmin_Est','prev_discharge_time','DischargeArea','Ambient_Temperature','Vmax/Vmin','OCVwait','Vminwait','steadystaterepeatocv','steadystaterepeatVmin','pumprate', 'rload']
                        headers2=' '.join(headers2)
                        save_file2.write(headers2 +'\n') #write headers to file
                        save_file2.close()
                        filename2_2=filename2
                        save_file2_2=open(filename3_2,"a") #for calling the filename where profile has been saved
                        headers2_2=['Date', 'Time', 'VMFC', 'Temperature']
                        headers2_2=' '.join(headers2_2)
                        save_file2_2.write(headers2_2 +'\n') #write headers to file
                        save_file2_2.close()
                        filename4_2=filename3_2
                    else:
                        filename2=filename2_2


                if (state2==0):  #MFC is about to be connected to resistor

                    #REINITIALIZE VARIABLES FOR BOTH CHARGE & DISCHARGE CYCLE
                    plateaucounter2=0
                    displateaucounter2=0
                    voltagelog2=[] #initialize voltage log
                    disvoltagelog2=[]
                    graphingtime2=[] #intialize graphing time
                    timelog2=[]
                    distimelog2=[]
                    read2=1
                    acquisitionspeed_closed2=vminacq2
                    acquisitionspeed_open2=vmaxacq2
                    acquire1_2=0
                    acquire2_2=0

                    #START DISCHARGE CYCLE
                    #d.getFeedback(u3.BitStateWrite(5, 1)) # Set FIO5 to output high therefore connecting resistor & discharging
                    discharge_start2=time.time()
                    programtimenow2=time.time()
                    discounter2=0 #counter for discharge cycle


                    #DELAY CONDITION
                    if 1.0<=Sensoroutput2 and Sensoroutput2<=1.01: #wait for a while if discharge isnt that fast
                            statusdisplay2.set(u'BIOSENSOR ON, Resistor Connected, Delay Active, Saving ')
                            time.sleep(delay2)

                    #global programstart
                    if (programtimenow2-programstart2)< profilesaver2 or savecounter2==1: #check if the time for profile saving has elapsed
                        saveprofile2=1
                        #profilesaver=profilesaver+profilesaver


                    while state2==0: #while MFC is connected to resistor

                        if (acquisitionspeed_closed2 >=vminacq2) and (q2.empty()==False):
                            acquire1_2=time.time()
                            acquisitionspeed_closed2=0
                            ainValue2=q2.get()
                            MFCreading2=round(ainValue2,2)
                            tempV2=round(tempV,2)
                            voltageset2.set(str(MFCreading2)) #default value in display
                            tempvset2.set(str(tempV2)) #default value in display
                            programtimenow2=time.time()

                            if (programtimenow2-profiletimelast2)>= datalog2: #check if the time for profile saving has elapsed
                                saveprofile2_2=1
                                profiletimelast2=time.time()

                            if ainValue2<=Vmin2: #to prevent error
                                ainValue2=Vmin2
                                Vmin_Est2=round(ainValue2,2)
                                vminvset2.set(str(Vmin_Est2)) #display vmin
                                Disarea_curve2=trapz(disvoltagelog2,distimelog2) #integrate and calculate area under dischareg curv
                                discounter2=discounter2+1
                                discharge_timenow2=time.time()
                                discharge_timeelapsed2=discharge_timenow2-discharge_start2
                                MFCreading2=round(ainValue2,2)
                                voltageset2.set(str(MFCreading2)) #default value in display

                                discharge_end2=time.time()
                                discharge_time2=discharge_end2-discharge_start2
                                state2=1
                                break

                            discounter2=discounter2+1
                            discharge_timenow2=time.time()
                            discharge_timeelapsed2=discharge_timenow2-discharge_start2
                            MFCreading2=round(ainValue2,2)
                            voltageset2.set(str(MFCreading2)) #default value in display

                            #CHECK IF CONDITION TO CONTINUE SAVING EXISTS
                            if saveprofile2==1 or saveprofile2==1:
                                profiletime2=(str(datetime.datetime.now()))[:19]
                                profilestr2= (profiletime2 +' ' + str(MFCreading2) +' '+ str(tempV2))
                                save_file2_2= open(filename3_2,"a") #openfile to save
                                save_file2_2.write(profilestr2 +'\n') #write data to file
                                save_file2_2.close() #close
                                saveprofile2_2=0

                            #DECIDE WHAT TO DISPLAY ON GUI BASED ON SELECTION
                            if filesaveflag_2==1:
                                statusdisplay2.set(u'BIOSENSOR ON, Resistor Connected, Saving Enabled')
                            else:
                                statusdisplay2.set(u'BIOSENSOR ON, Resistor Connected, Saving Disabled')

                            #CHECK IF STOP BUTTON HAS BEEN CALLED
                            if flag_2==0:         #stop button value check
                                break

                            #FILTER VALUES
                            if discounter2==1:
                                ainValue_ftrd2=ainValue2
                            else:
                                ainValue_ftrd2=((alpha1_2*ainValue2)+((1-alpha1_2)*disvoltagelog2[-1]))

                            #TEMPORARILY STORE VALUES
                            disvoltagelog2=disvoltagelog2+[ainValue_ftrd2] #store discharge voltage in log list initiated earlier
                            distimelog2=distimelog2+[discharge_timeelapsed2]

                            #CHECK PLATEAU CONDITIONS & DO NECESSARY CALCULATIONS

                            if discharge_timeelapsed2>vminwait2:
                                if len(disvoltagelog2)>2:
                                    discheck_state2=(1-(disvoltagelog2[-1]/disvoltagelog2[-2]))
                                    if (discheck_state2 >= 0 and discheck_state2<=tolerance2) or ainValue2<Vmin2 :
                                        displateaucounter2=displateaucounter2+1
                                    else:
                                        displateaucounter2=0
                                    #IF PLATEAU CONDITION IS REACHED 3 CONSECUTIVE TIMES
                                    if displateaucounter2==steadyrepeatvmin2: #wait for at specified repeat of the vmin
                                        discharge_end2=time.time()
                                        discharge_time2=discharge_end2-discharge_start2
                                        discharge_time2=round(discharge_time2,2) #round to 2 decimal places
                                        Vmin_Est2=disvoltagelog2[-1] #estimated Vmin
                                        Vmin_Est2=round(Vmin_Est2,2)
                                        vminvset2.set(str(Vmin_Est2)) #display vmin
                                        Disarea_curve2=trapz(disvoltagelog2,distimelog2) #integrate and calculate area under dischareg curve
                                        state2=1
                                        break
                        acquire2_2=time.time()
                        time.sleep(0.05)
                        acquisitionspeed_closed2=acquire2_2-acquire1_2


                if state2==1:    #MFC is now going into open circuit mode
                    OCV_start2=time.time()
                    counter2=0 #reset counter

                    while state2==1:

                        if (acquisitionspeed_open2>=vmaxacq2 and (q2.empty()==False)):
                            acquire1_2=time.time()
                            acquisitionspeed_open2=0
                            ainValue2=q2.get()
                            #time.sleep(dataacq) #wait 1 seconds before every reading in the open circuit phase
                            OCV_timenow2=time.time()
                            OCVtime_elapsed2=OCV_timenow2-OCV_start2 #calculate time elapsed
                            MFCreading2=round(ainValue2,2)
                            voltageset2.set(str(MFCreading2)) #display value in display
                            programtimenow2=time.time()

                            if (programtimenow2-profiletimelast2)>= datalog2: #check if the time for profile saving has elapsed
                                saveprofile2_2=1
                                profiletimelast2=time.time()

                            #saveprofile=1
                            if saveprofile2==1 or saveprofile2_2==1:
                                profiletime2=(str(datetime.datetime.now()))[:19]
                                profilestr2= (profiletime2 +' ' + str(MFCreading2) +' '+ str(tempV2))
                                save_file2_2= open(filename3_2,"a") #openfile to save
                                save_file2_2.write(profilestr2 +'\n') #write data to file
                                save_file2_2.close() #close
                                saveprofile2_2=0
                            if filesaveflag_2==1:
                                statusdisplay2.set(u'BIOSENSOR ON, Open Circuit, Saving Enabled')
                            else:
                                statusdisplay2.set(u'BIOSENSOR ON, Open Circuit, Saving Disabled')
                            counter2=counter2+1 #record it as a step
                            if flag_2==0: #stop button value check
                                break
                            #apply filter to voltage
                            if counter2==1:
                                ainValue_ftrd2=ainValue2
                            else:
                                ainValue_ftrd2=((alpha1_2*ainValue2)+((1-alpha1_2)*voltagelog2[-1]))
                            voltagelog2=voltagelog2+[ainValue_ftrd2] #store voltage in voltage log list initiated earlier
                            timelog2=timelog2+[OCVtime_elapsed2]


                            #check for plateauing condition after a minimum of specified time for Vmax estimation
                            if OCVtime_elapsed2>ocvwait2 and len(voltagelog2)>2:
                                check_state2=((voltagelog2[-1]/voltagelog2[-2])-1)
                                if check_state2<0:
                                    check_state2=-check_state2
                                if check_state2<tolerance2: # and (voltagelog[-1]-voltagelog[-2])>=0:   #if condition of assumed Vmax attainment has been reached also make sure that negative voltages don't cause switching
                                    plateaucounter2=plateaucounter2+1
                                else:
                                    plateaucounter2=0
                                if plateaucounter2==steadyrepeat2: #wait for at least 3 of this plateau conditions to be satisfied simultaneously
                                    OCV_end2=time.time() #time at this moment of plateau

                                    telapsed2=OCV_end2-start_time2 #elapsedtime since start
                                    tchart2=round(((telapsed2+basetime2)/3600),2) #time in hours since  plotting started

                                    global timevec2
                                    timevec2=timevec2
                                    global sensorvec2
                                    sensorvec2=sensorvec2
                                    global vmaxvec2
                                    vmaxvec2=vmaxvec2
                                    global vminvec2
                                    vminvec2=vminvec2
                                    global vmintimevec2
                                    vmintimevec2=vmintimevec2
                                    global y2limit2
                                    global y3limit2
                                    global y4limit2
                                    global pumprate2
                                    global targetpumprate2

                                    timevec_checker2=timevec2
                                    timevec_checker2=timevec_checker2+[tchart2]
                                    check2=timevec_checker2[-1]-timevec_checker2[0]


                                    OCV_time2=OCV_end2-OCV_start2 #calulate time to reach this estimated Vmax
                                    OCV_time2=round(OCV_time2,2) #round to 2 decimal places
                                    Vmax_Est2=voltagelog2[-1] #save this estimated Vmax as the last subject
                                    Vmax_Est2=round(Vmax_Est2,2)
                                    vmaxset2.set(str(Vmax_Est2))

                                    Area_curve2=trapz(voltagelog2,timelog2) #integrate and calculate area under curve

                                    if Vmin_Est2==0:
                                        Vmin_Est2=0.1

                                    Sensoroutput2=round((Vmax_Est2/Vmin_Est2),2)


                                    #sensorvset2.set(str(Sensoroutput2)) #display value in display

                                    if check2<=graphspan2:
                                        sensorvec2=sensorvec2+[Sensoroutput2]
                                        vmaxvec2=vmaxvec2+[Vmax_Est2]
                                        vminvec2=vminvec2+[Vmin_Est2]
                                        vmintimevec2=vmintimevec2+[discharge_time2]
                                        timevec2=timevec2+[tchart2]

                                    else:
                                        aux1=sensorvec2
                                        sensorvec2=aux1[2:]+[Sensoroutput2]
                                        aux2=timevec2
                                        timevec2=aux2[2:]+[tchart2]
                                        aux3=vmaxvec2
                                        vmaxvec2=aux3[2:]+[Vmax_Est2]
                                        aux4=vminvec2
                                        vminvec2=aux4[2:]+[Vmin_Est2]
                                        aux5=vmintimevec2
                                        vmintimevec2=aux5[2:]+[discharge_time2]

##
##                                    #later improvements to check
##                                    if max(vmaxvec2) > 500:
##                                        y2limit2 = max(vmaxvec2) + (0.5*max(vmaxvec2))
##                                    if max(vminvec2)> 300:
##                                        y3limit2 = max(vminvec2) + (0.5*max(vminvec2))
##                                    if max(vmintimevec2)>300:
##                                        y4limit2 = max(vmintimevec2) + (0.5*max(vmintimevec2))


                                    p = f5.add_subplot(111)
                                    p.clear()
                                    p2.clear()
                                    p.set_title('$Biosensor outputs$')
                                    p.set_xlabel('time (h)')
                                    p.set_ylabel('$V_{max}$',color='tab:red')
                                    p.tick_params(axis='y', labelcolor='tab:red')
                                    p.set_ylim([0,y2limit2])
                                    p.plot(timevec2,vmaxvec2, 'k:', ls=':', marker='o', color='tab:red')
                                    p2.set_ylabel('$V_{min}$',color='tab:green')
                                    p2.tick_params(axis='y', labelcolor='tab:green')
                                    p2.plot(timevec2,vminvec2, 'k:', ls=':', marker='o', color='tab:green')
                                    p2.set_ylim([0,y3limit2])
                                    canvas5.draw()
                                    canvas.get_tk_widget().grid(column=1,row=14,columnspan=3,sticky='NSEW') #graph position


                                    #record all data
                                    if filesaveflag_2==1:
                                        timeofsave2=(str(datetime.datetime.now()))[:19]
                                        datastr2= (timeofsave2 +' ' + str(Vmax_Est2)+' ' + str(Area_curve2)+
                                                  ' ' + str(OCV_time2)+' ' + str(tolerance2)+' '+str(Vmin2)+' '+str(alpha1_2)+' '+str(Vmin_Est2)+' '+str(discharge_time2)+' '+str(Disarea_curve2)+' '+str(tempV2)+' '+str(Sensoroutput2)+' '+str(ocvwait2)+' '+str(vminwait2)+' '+str(steadyrepeat2)+' '+str(steadyrepeatvmin2)+str(pumpcontrolon2)+' '+str(rload2))
                                        save_file2= open(filename2,"a") #openfile to save
                                        save_file2.write(datastr2 +'\n') #write data to file
                                        save_file2.close() #close
                                    saveprofile2=0; #reset save profile decider
                                    state2=0 #turn state to open circuit
                                    plateaucounter2=0

                        acquire2_2=time.time()
                        time.sleep(0.05)
                        acquisitionspeed_open2=acquire2_2-acquire1_2



            if flag_2==0:
                #d.getFeedback(u3.BitStateWrite(5, 0)) #SET FI04 to output low to disconnect resistor
                offperiod2=time.time()
                start_stop_button2['text']= 'START'
                start_stop_button2['bg']="yellowgreen"

                if not os.path.exists('/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/BiosensingData'): #Pi
                    os.makedirs('/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/BiosensingData') #create folder for documents if it doesnt exist
                os.chdir('/home/pi/Documents/OnlineBiosensorLinux_BOD_COD/BiosensingData') #change directory to this new folder and save files here

             #   if not os.path.exists(BiosensingDataFolder): #Windows
         #           os.makedirs(BiosensingDataFolder) #create folder for documents if it doesnt exist
           #     os.chdir(BiosensingDataFolder) #change directory to this new folder and save files here


                filename3_2='flowthroughtemp&vMFClog' + '.txt' #filename to save MFC profile
                save_file2_2=open(filename3_2,"a") #for calling the filename where profile has been saved
                headers2_2=['Date', 'Time', 'VMFC']
                headers2_2=' '.join(headers2_2)
                save_file2_2.write(headers2_2 +'\n') #write headers to file
                save_file2_2.close()
                saveprofile2_2=0
                profiletimelast2=offperiod2

                print 'OFF'
                while flag_2==0:
                    #print 'OFF'
                    statusdisplay2.set(u'FLOW-THROUGH BIOSENSOR OPERATION-OFF')
                    Sensoroutput2=0.00
                    ainValue2=q2.get()
                    #sensorvset2.set(str(Sensoroutput2)) #display value in display
                    MFCreading2=round(ainValue2,2)
                    tempV2=round(tempV,2)
                    voltageset2.set(str(MFCreading2)) #default value in display
                    tempvset2.set(str(tempV2)) #default value in display

                    programtimenow2=time.time()

                    if (programtimenow2-profiletimelast2)>= datalog2: #check if the time for profile saving has elapsed
                            saveprofile2_2=1
                            profiletimelast2=time.time()

                    if saveprofile2_2==1:
                            profiletime2=(str(datetime.datetime.now()))[:19]
                            profilestr2= (profiletime2 +' ' + str(MFCreading2) +' '+ str(tempV2))
                            save_file2_2= open(filename3_2,"a") #openfile to save
                            save_file2_2.write(profilestr2 +'\n') #write data to file
                            save_file2_2.close() #close
                            saveprofile2_2=0
                    time.sleep(vminacq2)
                    savecounter2=0


    def dataacqusition():

        def GetMfcVoltage(channel):
            time.sleep(0.05)
            serial_objects[channel].reset_input_buffer()
            serial_objects[channel].write(b"GetMfcVoltage\r")
            serial_objects[channel].read_until(b"MFC voltage=")
            text = serial_objects[channel].read_until(b" ")
            text = text.strip().decode()
            return text

        def ConnectLoad(channel):
            time.sleep(0.05)
            serial_objects[channel].reset_input_buffer()
            serial_objects[channel].write(b"ConnectLoad\r")
            text = serial_objects[channel].readline()
            #text = text.strip().decode()
            #return(text)

        def DisconnectLoad(channel):
            time.sleep(0.05)
            serial_objects[channel].reset_input_buffer()
            serial_objects[channel].write(b"DisconnectLoad\r")
            text = serial_objects[channel].readline()
            #text = text.strip().decode()
            #return(text)

        def GetTemperature(channel):
            time.sleep(0.05)
            serial_objects[channel].reset_input_buffer()
            serial_objects[channel].write(b"GetTemperature\r")
            time.sleep(0.65)
            serial_objects[channel].read_until(b"Temperature:")
            text = serial_objects[channel].readline()
            text = text.strip().decode()
            return(text)

        def SetRLoad(channel, value):
            time.sleep(0.05)
            serial_objects[channel].reset_input_buffer()
            serial_objects[channel].reset_output_buffer()
            value = str(value)
            value = value.encode()
            
            serial_objects[channel].write(b"SetDigitalPot " + value + b"\r")
            time.sleep(0.05)
            text = serial_objects[channel].readline()
            text = text.decode()
            temp = re.findall(r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", text)
            value = temp[0].strip()
            value = value.strip().encode()
            time.sleep(0.05)
            serial_objects[channel].write(b"SetParam RLoad "+ value + b"\r")
            time.sleep(0.01)
            text = serial_objects[channel].readline()
            
            #SetDigitalPot
            serial_objects[channel].write(b"SetParam RLoad "+ value + b"\r")
            text = serial_objects[channel].readline()
            time.sleep(0.05)
            #text = text.strip().decode()
            #return(text)

        global d
        global counterpump_2
        global flag_pump_2
        global flag
        global flag_2
        global tempV
        global state
        global state2
        global rload_Flag
        global rload2_Flag
        global mfcvaluesstoreclosed
        global mfcvaluesstoreclosed2


        mfcvaluesstoreclosed=[]
        mfcvaluesstoreclosed2=[]
        #tempvaluesstoreclosed=[]



        while True:

            if(rload_Flag == 1):
                SetRLoad(0,rload)
                rload_Flag = 0
            if(rload2_Flag == 1):
                SetRLoad(0,rload2)
                rload2_Flag = 0

            if flag==1:
                if state==0:
                    ConnectLoad(0) # Set FIO4 to output high therefore connecting resistor & discharging (ConnectLoad)
                else:
                    DisconnectLoad(0) # Set FIO4 to output low therefore open circuit mode (DisconnectLoad)

            elif flag==0:
                DisconnectLoad(0) #SET FI04 to output low to disconnect resistor #OFF MODE (DisconnecT)

            if(len(serial_objects) == 2):
                if flag_2==1:
                    if state2==0:
                        ConnectLoad(1) # Set FIO5 to output high therefore connecting resistor & discharging
                    else:
                        DisconnectLoad(1) # Set FIO5 to output low, therefore open circuit mode

                elif flag_2==0:
                    DisconnectLoad(1) #SET FI05 to output low to disconnect resistor #OFF MODE



            read=1
            while read==1:
                valuesready=0
                #tempValuetemp = d.getAIN(2) #get the analog input value from FIO6 which has the temperature sensor
                #tempVtemp=(55.56*tempValuetemp)+255.37-273.5  #recalculate temp value as specified by the manufacturer
                try:
                    ainValuetemp = float(GetMfcVoltage(0)) #get the analog input value from channel 1, hence AIN(1)-FLOATING
                except Exception:
                    ainValuetemp= ainValuetemp
                if(len(serial_objects) == 2):
                    ainValue2temp = float(GetMfcVoltage(1)) #get the analog input value from channel 2, hence AIN(2)-FLOW THROUGH
                    mfcvaluesstoreclosed2=mfcvaluesstoreclosed2 + [ainValue2temp]
                mfcvaluesstoreclosed=mfcvaluesstoreclosed + [ainValuetemp]

                time.sleep(0.05)
                acquisframe=len(mfcvaluesstoreclosed) #to acquire 5 readings and average
                if acquisframe>10:      #acquire at least 10 readings and average
                    read=0
                    valuesready=1
                    ainValue=(np.mean(mfcvaluesstoreclosed))
                    if(len(serial_objects) == 2):
                        ainValue2=(np.mean(mfcvaluesstoreclosed2))
                    mfcvaluesstoreclosed=[]
                    mfcvaluesstoreclosed2=[]
                    try:
                        tempV = float(GetTemperature(0))

                    except Exception:
                        tempV=tempV
                    try:
                        q.put(ainValue, False)
                    except Exception:
                        sys.exc_clear()
                        pass

                    if(len(serial_objects) == 2):
                        try:
                            q2.put(ainValue2, False)
                        except Exception:
                            sys.exc_clear
                            pass
                        print ainValue2 #MFCvoltage
                    print ainValue  #MFCvoltage2
                    time.sleep(0.05)




    q=Queue(maxsize=1)
    q2=Queue(maxsize=1)

    t1=threading.Timer(1,floating,args=(q,)) #executes maincode
    t2=threading.Timer(1,pump_control_2) #executes pump control
    t3=threading.Timer(1,flowthrough,args=(q2,)) #executes maincode
    t4=threading.Timer(0.001,dataacqusition) #executes maincode
    #make measuring thread terminate when the user exits the window
    t1.daemon = True
    t2.daemon = True
    t3.daemon = True
    t4.daemon = True
    t1.start()
    t2.start()
    t3.start()
    t4.start()
    app.mainloop() #tells the application to loop
