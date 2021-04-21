#!/bin/sh

#Removing Repository
cd $HOME
cd ../..
cd usr/share
sudo rm -r "Source files"

#Removing STM32
sudo rm -r "stm32"

#Removing Start Menu option
cd "applications"
sudo rm "BiosensorApplication.desktop"

#Cleaning up desktop
cd $HOME
cd Desktop
rm "BiosensorApplication.desktop"
rm "Biosensor Channel1 Data"
rm "Biosensor Channel2 Data"

#Cleaning up autostart
cd $HOME
cd .config
cd autostart
rm "biosensor.desktop"

sudo lxpanelctl restart
sleep 5