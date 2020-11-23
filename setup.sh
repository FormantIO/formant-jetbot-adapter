# enable all Ubuntu packages:
sudo apt-add-repository universe
sudo apt-add-repository multiverse
sudo apt-add-repository restricted

# install python3 dependencies
sudo apt-get update
sudo apt-get -y install python3-pip

# install the formant python module
pip3 install formant

# install additional dependencies
sudo apt install -y tmux ntpdate

# install the service
sudo cp /home/jetbot/formant-jetbot-adapter/formant-jetbot-adapter.service /etc/systemd/system/formant-jetbot-adapter.service

# enable the script to run at boot
sudo systemctl enable formant-jetbot-adapter

# run the start script now
sudo systemctl start formant-jetbot-adapter