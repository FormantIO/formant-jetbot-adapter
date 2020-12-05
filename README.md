# Formant JetBot Adapter
This adapter will connect a JetBot's interfaces to the Formant Agent so that it can record telemetry and be teleoperated.

Never leave a robot in a situation where someone's unexpected teleoperation inputs can send it flying off of a table.

## Hardware
| Item | Price |
|------|-------|
| [Waveshare JetBot Kit](https://www.amazon.com/Waveshare-JetBot-AI-Kit-Intelligent/dp/B07V8JL4TF/) | $240.99 |
| [18650 Batteries (with bonus flashlight)](https://www.amazon.com/Tactical-Flashlight-Rechargeable-Batteries-Resistant/dp/B07SQLRMQH/) | $20.97 |

## Setup

### Set up the JetBot image
This package uses the JetBot base image.

Follow steps 1, 2, and 3 here: https://github.com/NVIDIA-AI-IOT/jetbot/wiki/software-setup

STOP after step 3. This adapter uses the `waveshare/jetbot` repo, not the `NVIDIA-AI-IOT/jetbot` repo as those instructions specify. This allows us to pull information about the battery.

### Install the jetbot code repository
```
cd && git clone https://github.com/waveshare/jetbot.git
cd jetbot
sudo python3 setup.py install
```

### Install the Formant agent
The agent should be installed before the adapter setup script is run.

On the Formant Settings -> Devices page, click `ADD DEVICE` in the top right. 

Name the device `jetbot.xyz` where `xyz` is an unused three-digit number.

Click on `Show advanced settings` and select the following:
| Name                   | Value              |
|------------------------|--------------------|
| Tags                   | `hardware: jetbot` |
| Configuration Template | `jetbot`           |

Follow the provided instructions to walk through the installation and provisioning process. Do not set a Catkin workspace if asked.

### Install the Formant JetBot Adapter
Once the JetBot image is installed, on wifi, updated, and connected to Formant, run this script to clone this repository to your home directory:
```
cd && git clone https://github.com/FormantIO/formant-jetbot-adapter.git
```
Run the setup script (this could take a very long time while building `grpcio`):
```
sudo formant-jetbot-adapter/setup.sh
```

### Set reboot permissions (optional)
To use the `reboot.sh` and `update.sh` scripts via Formant commands, the following directive must be added to the sudoers file. To edit the sudoers, run:
```
sudo visudo
```
...and add the line:
```
formant  ALL=NOPASSWD:/sbin/reboot
```

## Commands
The following commands can be used with the adapter:
| Name | Description |
|------------------------|--------------------|
| `reboot jetbot` | Runs the `reboot.sh` script to restart the jetbot |
| `update jetbot` | Runs the `update.sh` script to pull changes from the main branch of this code repository rand restart |
| `update config` | Refreshes the configuration from app config without rebooting |
| `nudge forward` | Moves the robot forward for 500ms |
| `nudge backward` | Moves the robot backward for 500ms |

## Configuration

### Set a location
The JetBot devices don't ship with a GPS module, but the device will publish a configured GPS location at regular intervals.

To set this location, go to the device's configuration page in Formant, and find the `Application Configuration` section. Create two new configuration parameters: `latitude` and `longitude`, and set them to your desired location (in decimal notation).

### Configuration parameters and defaults
Default configuration values can be overridden with agent application configuration variables. The `udpdate config` command must be run or the adapter must be restarted to pick up changes. The following configuration parameters can be set via Application Configuration:

| Name | Default Value | Description |
|------------------------|--------------------|--------------------|
| `max_speed` | `0.7` | The maximum value that the speed will increase to (not counting deadzone) |
| `min_speed` | `0.1` | The minimum value that the speed will decrease to (not counting deadzone) |
| `start_speed` | `0.1` | The initial speed on adapter startup |
| `speed_deadzone` | `0.25` | The baseline value to be added to the motors to reduce the deadzone |
| `speed_increment` | `0.025` | The amount that `speed +` and `speed -` affect the speed |
| `angular_reduction` | `0.50` | The amount to reduce turning speed relative to linear speed |
| `latitude` | `41.322937` | The latitude to publish |
| `longitude` | `19.820896` | The longitude to publish |
| `gst_string` | `nvarguscamerasrc ! video/x-raw(memory:NVMM), width=(int)640, height=(int)480, format=(string)NV12, framerate=(fraction)30/1 ! nvvidconv ! video/x-raw, width=(int)640, height=(int)480, format=(string)BGRx ! videoconvert ! appsink` | The string to use for GStreamer |
