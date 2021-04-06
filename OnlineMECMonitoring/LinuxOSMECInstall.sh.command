#!/bin/sh

#Installing packages
cd $HOME
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install python3-pip -y
sudo apt-get install qtcreator -y
sudo apt-get install qt5-default -y
sudo apt-get install pyqt5-dev -y
sudo apt-get install pyqt5-dev-tools -y
sudo apt-get install stlink-tools -y
sudo apt-get install rpm -y
sudo apt-get install libusb-1.0 -y
sudo apt-get install libqt5serialport5-dev -y
sudo apt-get install python3-pyqt5.qtserialport -y
sudo apt-get install python3-pandas -y
sudo apt-get install python3-matplotlib -y
sudo apt-get install python3-numpy -
sudo apt-get install python3-smbus
sudo apt-get install i2c-tools
sudo pip3 install atlas-i2c
sudo pip3 install qtwidgets

#Modifying Raspi-config for i2c
sudo cat /boot/cmdline.txt
sudo raspi-config nonint do_i2c 0
sudo cat /boot/cmdline.txt

#Clone Repository
cd #HOME
git clone https://github.com/ademola-adekunle/OnlineMECMonitoring.git
cd OnlineMECMonitoring
sudo cp -r "Version2" /usr/share
cd $HOME
sudo rm -r OnlineMECMonitoring

sudo chmod +x "/usr/share/Version2/runMECMonitoring.sh"

mkdir -p /home/pi/.config/autostart/
echo '[Desktop Entry]'>/home/pi/.config/autostart/MECMonitoring.desktop
echo 'Type=Application'>>/home/pi/.config/autostart/MECMonitoring.desktop
echo 'Name=MEC Monitoring'>>/home/pi/.config/autostart/MECMonitoring.desktop
echo 'Exec="/usr/share/Version2/runMECMonitoring.sh"'>>/home/pi/.config/autostart/MECMonitoring.desktop

cd $HOME
cd Desktop
ln -s "/usr/share/Version2/KORAD_PS_DAQ/Data_Logs" "MEC Monitoring Data Logs"
ln -s "/usr/share/Version2/KORAD_PS_DAQ/INI" "MEC Monitoring Settings"

cd $HOME
cd ..
cd ..
cd usr
cd share
cd applications
echo '[Desktop Entry]' | sudo tee /usr/share/applications/MECMonitoringApplication.desktop
echo 'Type = Application' | sudo tee -a /usr/share/applications/MECMonitoringApplication.desktop
echo 'Encoding = UTF-8' | sudo tee -a /usr/share/applications/MECMonitoringApplication.desktop
echo 'Name = MEC Monitoring ' | sudo tee -a /usr/share/applications/MECMonitoringApplication.desktop
echo 'Comment = MEC Monitoring' | sudo tee -a /usr/share/applications/MECMonitoringApplication.desktop
echo 'Exec = "/usr/share/Version2/runMECMonitoring.sh"' | sudo tee -a /usr/share/applications/MECMonitoringApplication.desktop
echo 'Icon = /usr/share/Version2/NRCLogo.png' | sudo tee -a /usr/share/applications/MECMonitoringApplication.desktop
echo 'Terminal = false' | sudo tee -a /usr/share/applications/MECMonitoringApplication.desktop

sudo lxpanelctl restart

sleep 3

sudo reboot
