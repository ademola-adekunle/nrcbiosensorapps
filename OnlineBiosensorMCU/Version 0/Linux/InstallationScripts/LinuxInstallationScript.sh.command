#!/bin/sh

#Installing packages
#PACKAGES = "qtcreator qt5-default pyqt5-dev pyqt5-dev-tools stlink-tools rpm libusb-1.0 libqt5serialport5-dev devscripts debhelper"

sudo apt-get update 
sudo apt-get upgrade -y
#sudo apt-get install $PACKAGES -y
sudo apt-get install qtcreator -y
sudo apt-get install qt5-default -y
sudo apt-get install pyqt5-dev -y
sudo apt-get install pyqt5-dev-tools -y
sudo apt-get install stlink-tools -y
sudo apt-get install rpm -y
sudo apt-get install libusb-1.0 -y
sudo apt-get install libqt5serialport5-dev -y
sudo apt-get install python3-pyqt5.qtserialport -y
sudo apt-get install devscripts -y
sudo apt-get install debhelper -y
sudo apt-get install python-matplotlib -y
sudo apt-get install python-scipy -y
sudo apt-get install python-numpy -y
sudo apt-get install python-xlrd -y
sudo apt-get install python-pandas -y
sudo apt-get install python-sklearn -y
sudo apt-get install python3-sklearn -y
sudo apt-get install python3-openpyxl -y
sudo apt-get install python3-pandas -y
sudo apt-get install python3-xlrd -y
sudo apt-get install python3-matplotlib -y
sudo apt-get install python3-scipy -y
sudo apt-get install python3-numpy -y
sudo apt-get install python3-xlwt -y
#Consider XlsxWriter


#Configuring St-Link
cd $HOME
mkdir $HOME/stm32
cd stm32
git clone https://github.com/stlink-org/stlink.git
cd stlink
sudo make clear
sudo make release
sudo make debug
cd config
cd udev
cd rules.d
sudo cp *.rules /etc/udev/rules.d
cd $HOME
sudo udevadm control --reload-rules
sudo udevadm trigger


#Modifying Raspi-config for serial
sudo cat /boot/cmdline.txt
sudo raspi-config nonint do_serial 0
sudo cat /boot/cmdline.txt


#Modifying Configuration UART
sudo cat /boot/config.txt
dtoverlay=pi3-miniuart-bt
sudo cat /boot/config.txt
enable_uart=1
sudo cat /boot/config.txt

mkdir -p /home/pi/.config/autostart/
echo '[Desktop Entry]'>/home/pi/.config/autostart/biosensor.desktop
echo 'Type=Application'>>/home/pi/.config/autostart/biosensor.desktop
echo 'Name=Biosensor'>>/home/pi/.config/autostart/biosensor.desktop
echo 'Exec=/home/pi/runBiosensor.sh'>>/home/pi/.config/autostart/biosensor.desktop

chmod +x /home/pi/runBiosensor.sh

cd $HOME
cd Desktop
echo '[Desktop Entry]' > /home/pi/Desktop/BiosensorApplication.desktop
echo 'Type = Application' >> /home/pi/Desktop/BiosensorApplication.desktop
echo 'Encoding = UTF-8' >> /home/pi/Desktop/BiosensorApplication.desktop
echo 'Name = Biosensor Data Acquisition ' >> /home/pi/Desktop/BiosensorApplication.desktop
echo 'Comment = Biosensor Data Acquisition' >> /home/pi/Desktop/BiosensorApplication.desktop
echo 'Exec = /home/pi/runBiosensor.sh' >> /home/pi/Desktop/BiosensorApplication.desktop
echo 'Icon = /home/pi/SerialCommunicationBiosensor/NRCLogo.png' >> /home/pi/Desktop/BiosensorApplication.desktop
echo 'Terminal = false' >> /home/pi/Desktop/BiosensorApplication.desktop

ln -s /home/pi/SerialCommunicationBiosensor/Channel1 Biosensor_Channel1_Data
ln -s /home/pi/SerialCommunicationBiosensor/Channel2 Biosensor_Channel2_Data



sudo reboot