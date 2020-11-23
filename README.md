# Formant JetBot Adapter

## Hardware
| Item | Price |
|------|-------|
| [Waveshare JetBot Kit](https://www.amazon.com/Waveshare-JetBot-AI-Kit-Intelligent/dp/B07V8JL4TF/) | $240.99 |
| [18650 Batteries (with bonus flashlight)](https://www.amazon.com/Tactical-Flashlight-Rechargeable-Batteries-Resistant/dp/B07SQLRMQH/) | $20.97 |

## Setup

### Set up the JetBot image
This package uses the JetBot base image in order to get some nice default packages and configuration.

Follow steps 1, 2, and 3 here: https://github.com/NVIDIA-AI-IOT/jetbot/wiki/software-setup

### Install the Formant JetBot Adapter
Once the JetBot image is installed, on wifi, and updated, clone this repository to your home directory:
```
cd && git clone git@github.com:FormantIO/formant-jetbot-adapter.git
```
Run the setup script:
```
sudo formant-jetbot-adapter/setup.sh
```

### Set reboot permissions (optional)
To use the `reboot.sh` script from the Formant agent, the following directive must be added to the sudoers file using `sudo visudo`:
```
formant  ALL=NOPASSWD:/sbin/reboot
```