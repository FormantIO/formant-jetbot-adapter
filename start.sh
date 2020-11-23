#!/usr/bin/env bash

# Update the system time
ntpdate us.pool.ntp.org

# Start the jetbot adapter
bash -c "python3 /home/jetbot/formant-jetbot-adapter/main.py"