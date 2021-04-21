#!/usr/bin/env python2
import sys
import subprocess

subprocess.check_call([sys.executable, '-m', 'pip', 'uninstall', 'pyserial'])
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyserial'])
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'matplotlib'])
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'scipy'])
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'xlrd==1.2.0'])
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pandas'])
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'sklearn'])
