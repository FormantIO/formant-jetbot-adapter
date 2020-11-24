import cv2
import time
import random
import logging
import threading
import traitlets
import numpy as np
from jetbot import Robot, Camera, Heartbeat
from Adafruit_MotorHAT import Adafruit_MotorHAT
from formant.sdk.agent.v1 import Client as FormantClient

DEADZONE = 0.15
MAX_SPEED = 0.75
MIN_SPEED = 0.175
START_SPEED = 0.25
SPEED_INCREMENT = 0.025
ANGULAR_REDUCTION = 0.5
GST_STRING = 'nvarguscamerasrc ! video/x-raw(memory:NVMM), width=(int)1280, height=(int)720, format=(string)NV12, framerate=(fraction)21/1 ! nvvidconv ! video/x-raw, width=(int)1280, height=(int)720, format=(string)BGRx ! videoconvert ! appsink'


class FormantJetBotAdapter():
    def __init__(self):
        print("INFO: Starting Formant JetBot Adapter")

        # Set global params
        self.speed = START_SPEED

        # Create clients
        self.robot = Robot()
        self.fclient = FormantClient(ignore_throttled=True, ignore_unavailable=True)

        self.fclient.register_teleop_callback(
            self.handle_teleop, ["Joystick", "Buttons"]
        )

        # Create the speed publisher
        try:
            speed_thread = threading.Thread(target=self.publish_speed, daemon=True)
            speed_thread.start()
            print("INFO: Speed thread started")
        except:
            print("ERROR: Unable to start speed thread")

        # Start the camera feed
        self.publish_camera_feed()

    def publish_speed(self):
        while True:
            #self.fclient.post_numeric("speed", self.speed)
            self.fclient.post_numericset(
                "speed",
                {
                    "speed": (self.speed, "m/s")
                },
            )
            time.sleep(1.0)

    def publish_camera_feed(self):
        cap = cv2.VideoCapture(GST_STRING, cv2.CAP_GSTREAMER)
        if cap is None:
            sys.exit()

        while True:
            _, image = cap.read()
            try:
                encoded = cv2.imencode(".jpg", image)[1].tostring()
            except:
                print("ERROR: Encoding failed")
            
            try:
                self.fclient.post_image("camera", encoded)
            except:
                print("ERROR: Camera ingestion failed")

    def handle_teleop(self, control_datapoint):
        #print("got teleop message:", control_datapoint)
        if control_datapoint.stream == "Joystick":
            self.handle_joystick(control_datapoint)
        elif control_datapoint.stream == "Buttons":
            self.handle_buttons(control_datapoint)

    def handle_joystick(self, joystick):
        left_motor_value = 0.0
        right_motor_value = 0.0

        # Add contributions from the joysticks
        left_motor_value = self.speed * joystick.twist.angular.z * ANGULAR_REDUCTION
        right_motor_value = -self.speed * joystick.twist.angular.z * ANGULAR_REDUCTION

        left_motor_value += self.speed * joystick.twist.linear.x
        right_motor_value += self.speed * joystick.twist.linear.x

        # Set the motor values
        self.robot.left_motor.value = left_motor_value
        self.robot.right_motor.value = right_motor_value

    def handle_buttons(self, _):
        if _.bitset.bits[0].key == "nudge forward":
            self._handle_nudge_forward()
        elif _.bitset.bits[0].key == "nudge backward":
            self._handle_nudge_backward()
        elif _.bitset.bits[0].key == "start":
            self._handle_start()
        elif _.bitset.bits[0].key == "stop":
            self._handle_stop()
        elif _.bitset.bits[0].key == "speed +":
            self._handle_increase_speed()
        elif _.bitset.bits[0].key == "speed -":
            self._handle_decrease_speed()

    def _handle_nudge_forward(self):
        self.fclient.post_text("commands", "nudge forward")
        self.robot.forward(self.speed)
        time.sleep(0.5)
        self.robot.stop()

    def _handle_nudge_backward(self):
        self.fclient.post_text("commands", "nudge backward")
        self.robot.backward(self.speed)
        time.sleep(0.5)
        self.robot.stop()

    def _handle_start(self):
        self.fclient.post_text("commands", "start")
        self.robot.forward(self.speed)

    def _handle_stop(self):
        self.fclient.post_text("commands", "stop")
        self.robot.stop()

    def _handle_increase_speed(self):
        self.fclient.post_text("commands", "increase speed")
        if self.speed + SPEED_INCREMENT <= MAX_SPEED:
            self.speed += SPEED_INCREMENT
        else:
            self.speed = MAX_SPEED
    
    def _handle_decrease_speed(self):
        self.fclient.post_text("commands", "decrease speed")
        if self.speed - SPEED_INCREMENT >= MIN_SPEED:
            self.speed -= SPEED_INCREMENT
        else:
            self.speed = MIN_SPEED


if __name__=="__main__":
    adapter = FormantJetBotAdapter()