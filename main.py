import cv2
import time
import thread
import random
import traitlets
import numpy as np
from jetbot import Robot, Camera, Heartbeat
from Adafruit_MotorHAT import Adafruit_MotorHAT
from formant.sdk.agent.v1 import Client as FormantClient


DEADZONE = 0.05
GST_STRING = 'nvarguscamerasrc ! video/x-raw(memory:NVMM), width=816, height=616, format=(string)NV12, framerate=(fraction)21/1 ! nvvidconv ! video/x-raw, width=(int)1280, height=(int)720, format=(string)BGRx ! videoconvert ! appsink'
NUMPY_TYPE_TO_CVTYPE = {'uint8': '8U', 'int8': '8S', 'uint16': '16U', 'int16': '16S', 'int32': '32S', 'float32': '32F', 'float64': '64F'}
CVTYPE_TO_NAME = {}

class FormantJetBotAdapter():
    def __init__(self):
        print("INFO: Starting the Formant JetBot Adapter...")
        self.fclient = FormantClient(ignore_throttled=True, ignore_unavailable=True)

        fclient.register_teleop_callback(
            handle_teleop, ["joystick", "buttons"]
        )

        # Start the camera thread
        try:
            thread.start_new_thread(publish_camera_feed)
        except:
            print("ERROR: Unable to start thread")

    def publish_camera_feed(self):
        #camera = cv2.VideoCapture(GST_STRING, cv2.CAP_GSTREAMER)
        cap = cv2.VideoCapture(0)
        if cap is None:
            sys.exit()

        while True:
            _, image = cap.read()
            encoded = cv2.imencode(".jpg", image)[1].tostring()
            self.fclient.post_image("camera", encoded)

    def handle_teleop(self, control_datapoint):
    if control_datapoint.stream == "joystick":
        handle_joystick(control_datapoint)
    elif control_datapoint.stream == "buttons":
        handle_buttons(control_datapoint)

    def handle_joystick(self, _):
        print(_.stream)
        print(_.timestamp)
        print(_.twist.linear.x)
        print(_.twist.angular.z)

    def handle_buttons(self, _):
        print(_.stream)
        print(_.timestamp)
        print(_.bitset.bits)

    def _handle_stop_motors(self, msg):
        print("stop motors")
        self.robot.stop()

    def _handle_step_forwards(self, msg):
        print("step forwards")
        self.robot.forward(0.25)
        time.sleep(0.5)
        self.robot.stop()

    def _handle_step_backwards(self, msg):
        print("step backwards")
        self.robot.backwards(0.25)
        time.sleep(0.5)
        self.robot.stop()


if __name__=="__main__":
    adapter = FormantJetBotAdapter()