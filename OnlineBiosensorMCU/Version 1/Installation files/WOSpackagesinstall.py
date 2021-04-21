#!/usr/bin/env python3
import sys
import subprocess
from subprocess import call
#WIP

call("pip install --upgrade " + 'pip')
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'PyQt5'])
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyqt5-tools'])
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyserial'])
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'scikit-learn'])
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pandas'])
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'matplotlib'])
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'scipy'])
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'numpy'])

