#!/bin/sh

#Removing Repository
cd $HOME
cd ../..
cd usr/share
sudo rm -r "OnlineMECMonitoring"


#Removing Start Menu option
cd "applications"
sudo rm "MECMonitoringApplication.desktop"

#Cleaning up desktop
cd $HOME
cd Desktop
rm "MEC Monitoring Data Logs"
rm "MEC Monitoring Settings"

#Cleaning up autostart
cd $HOME
cd .config
cd autostart
rm "MECMonitoring.desktop"

sudo lxpanelctl restart
sleep 5