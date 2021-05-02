# OnlineBiosensorMCU
Version 1 is currently tested on python 2.7. It is functional on the Raspberry Pi 3 and on Windows. 
Version 2 is currently tested on python 3.7 and python 3.8. It is also functional on the Raspberry Pi 3/4 and on Windows.

## Version 0
This folder contains the old biosensor data acquisition program. It features 4 separate working programs: two for Linux (TOX and BODCOD) and two for Windows (TOX and BODCOD)

## Version 1
This folder contains the new biosensor data acquisition program. It contains 3 main folders: BiosensorApplication, InstallationScripts, WindowsApplication

- ### BiosensorApplication
  This is where your program is contained and where most of the testing and debugging is done

  This folder contains:
  - The `BiosensorMain.py` file which is the base python program
  - The `UI_Forms` folder which contains all the UI elements and icons
  - `Channel1` and `Channel2` respectively which houses your data logs and MCU params
  - `defaults.txt` which tells the program what your navigation dialog default behaviour is
  - `runBiosensor.sh` which is the shell script to run BiosensorMain.py

- ### Installation Scripts
  This folder contains shell scripts used to automated the installation/uninstallation process
  
  This folder contains:
  - `LinuxInstallationScript.sh.command` which is used to configure the raspberry pi and install all the packages to run the python program
  - `UninstallationScript.sh.command` which is used to remove all data folders and shortcuts used by the python program
  - `WindowsInstallationScript.py` which is used to install all the python packages required to test the python program on Windows. This is only useful if you intend to code python on Windows and you want to have access to an easy tool to set-up your python environment

- ### Windows Application
  This folder contains the shell script used to compile my installation file and the installation file is located here.
  
  This folder contains:
  - `BiosensorInstallationScript.iss` which is the inno setup file which designed my installation file
  - `Output` folder, inside this folder contains `setupBiosensorApplication.exe` which is used to install the executable application

## OnlineBiosensorMCU_Documentation.docx
This word file contains all the required documentation on how to install the program on either operating system. It also offers fixes to common issues and a developers guide to help with some of the issues I faced when debugging.
