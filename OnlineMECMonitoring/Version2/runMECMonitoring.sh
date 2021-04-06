#!/bin/bash
sleep 5
cd $HOME
cd ..
cd ..
cd usr
cd share
cd "OnlineMECMonitoring"
cd "Version2"
sudo -E  python3 "/usr/share/OnlineMECMonitoring/Version2/KORAD_PS_DAQ.py"
