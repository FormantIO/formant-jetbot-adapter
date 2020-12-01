import sys
import time
import threading
import collections
from statistics import mean, stdev

import cv2
from formant.sdk.agent.v1 import Client as FormantClient

from jetbot import Robot, INA219


MAX_CHARGING_VOLTAGE = 12.6
MIN_CHARGING_VOLTAGE = 11.0
MAX_DISCHARGING_VOLTAGE = 12.1
MIN_DISCHARGING_VOLTAGE = 10.0
DEFAULT_MAX_SPEED = 0.7
DEFAULT_MIN_SPEED = 0.1
DEFAULT_START_SPEED = 0.1
DEFAULT_SPEED_DEADZONE = 0.25
DEFAULT_SPEED_INCREMENT = 0.025
DEFAULT_ANGULAR_REDUCTION = 0.50
DEFAULT_LATITUDE = 41.322937  # The pyramid of Enver Hoxha
DEFAULT_LONGITUDE = 19.820896
DEFAULT_GST_STRING = (
    "nvarguscamerasrc ! "
    "video/x-raw(memory:NVMM), width=(int)640, height=(int)480, format=(string)NV12, framerate=(fraction)30/1 ! "
    "nvvidconv ! "
    "video/x-raw, width=(int)640, height=(int)480, format=(string)BGRx ! "
    "videoconvert ! "
    "appsink "
)


class FormantJetBotAdapter:
    def __init__(self):
        print("INFO: Starting Formant JetBot Adapter")

        # Set global params
        self.max_speed = DEFAULT_MAX_SPEED
        self.min_speed = DEFAULT_MIN_SPEED
        self.speed_deadzone = DEFAULT_SPEED_DEADZONE
        self.speed_increment = DEFAULT_SPEED_INCREMENT
        self.angular_reduction = DEFAULT_ANGULAR_REDUCTION
        self.latitude = DEFAULT_LATITUDE
        self.longitude = DEFAULT_LONGITUDE
        self.gst_string = DEFAULT_GST_STRING
        self.start_speed = DEFAULT_START_SPEED
        self.speed = self.start_speed
        self.is_shutdown = False

        # Store frame rate information to publish
        self.camera_width = 0
        self.camera_height = 0
        self.camera_frame_timestamps = collections.deque([], maxlen=100)
        self.camera_frame_sizes = collections.deque([], maxlen=100)

        # Create clients
        self.robot = Robot()
        self.ina219 = INA219(addr=0x41)
        self.fclient = FormantClient(ignore_throttled=True, ignore_unavailable=True)

        self.update_from_app_config()
        self.publish_online_event()

        self.fclient.register_command_request_callback(self.handle_command_request)

        self.fclient.register_teleop_callback(
            self.handle_teleop, ["Joystick", "Buttons"]
        )

        print("INFO: Starting speed thread")
        threading.Thread(target=self.publish_speed, daemon=True).start()

        print("INFO: Starting motor states thread")
        threading.Thread(target=self.publish_motor_states, daemon=True).start()

        print("INFO: Starting location thread")
        threading.Thread(target=self.publish_location, daemon=True).start()

        print("INFO: Starting battery state thread")
        threading.Thread(target=self.publish_battery_state, daemon=True).start()

        print("INFO: Starting camera stats thread")
        threading.Thread(target=self.publish_camera_stats, daemon=True).start()

        # Start the camera feed
        self.publish_camera_feed()

    def __del__(self):
        self.is_shutdown = True

    def publish_speed(self):
        while not self.is_shutdown:
            # self.fclient.post_numeric("speed", self.speed)
            self.fclient.post_numericset(
                "Speed", {"speed": (self.speed + self.speed_deadzone, "m/s")},
            )
            time.sleep(1.0)

    def publish_motor_states(self):
        while not self.is_shutdown:
            self.fclient.post_numeric(
                "Motor Speed", self.robot.left_motor.value, {"value": "left"}
            )
            self.fclient.post_numeric(
                "Motor Speed", self.robot.right_motor.value, {"value": "right"}
            )
            time.sleep(0.5)

    def publish_location(self):
        while not self.is_shutdown:
            self.fclient.post_geolocation("Location", self.latitude, self.longitude)
            time.sleep(10.0)

    def publish_battery_state(self):
        while not self.is_shutdown:
            bus_voltage = self.ina219.getBusVoltage_V()
            shunt_voltage = self.ina219.getShuntVoltage_mV() / 1000
            current = self.ina219.getCurrent_mA() / 1000

            charging = False
            if shunt_voltage > 0.01 and current > 0.01:
                charging = True

            # approximate battery charge percentage calibration
            now = bus_voltage - MIN_DISCHARGING_VOLTAGE
            full = MAX_DISCHARGING_VOLTAGE - MIN_DISCHARGING_VOLTAGE
            charge_percentage = now / full * 100
            if charging:
                now = bus_voltage - MIN_CHARGING_VOLTAGE
                full = MAX_CHARGING_VOLTAGE - MIN_CHARGING_VOLTAGE
                charge_percentage = now / full * 100

            if charge_percentage >= 100:
                charge_percentage = 100

            self.fclient.post_battery(
                "Battery State", charge_percentage, voltage=bus_voltage, current=current
            )

            self.fclient.post_bitset(
                "Battery Charging", {"charging": charging, "discharging": not charging}
            )

            time.sleep(1.0)

    def publish_camera_stats(self):
        while not self.is_shutdown:
            length = len(self.camera_frame_timestamps)
            if length > 2:
                size_mean = mean(self.camera_frame_sizes)
                size_stdev = stdev(self.camera_frame_sizes)
                jitter = self.calculate_jitter(self.camera_frame_timestamps)
                oldest = self.camera_frame_timestamps[0]
                newest = self.camera_frame_timestamps[-1]
                diff = newest - oldest
                if diff > 0:
                    hz = length / diff
                    self.fclient.post_numericset(
                        "Camera Statistics",
                        {
                            "Rate": (hz, "Hz"),
                            "Mean Size": (size_mean, "bytes"),
                            "Std Dev": (size_stdev, "bytes"),
                            "Mean Jitter": (jitter, "ms"),
                            "Width": (self.camera_width, "pixels"),
                            "Height": (self.camera_height, "pixels"),
                        },
                    )
            time.sleep(5.0)

    def publish_camera_feed(self):
        cap = cv2.VideoCapture(self.gst_string, cv2.CAP_GSTREAMER)
        if cap is None:
            print("ERROR: Could not read from video capture source.")
            sys.exit()

        while not self.is_shutdown:
            _, image = cap.read()

            encoded = cv2.imencode(".jpg", image)[1].tostring()
            self.fclient.post_image("Camera", encoded)

            # Track stats for publishing
            self.camera_frame_timestamps.append(time.time())
            self.camera_frame_sizes.append(len(encoded) * 3 / 4)
            self.camera_width = image.shape[1]
            self.camera_height = image.shape[0]

    def publish_online_event(self):
        try:
            commit_hash_file = (
                "/home/jetbot/formant-jetbot-adapter/.git/refs/heads/main"
            )
            with open(commit_hash_file) as f:
                commit_hash = f.read()
        except Exception:
            print(
                "ERROR: formant-jetbot-adapter repo must be installed at "
                "/home/jetbot/formant-jetbot-adapter to receive online event"
            )

        self.fclient.create_event(
            "Formant JetBot adapter online",
            notify=False,
            tags={"hash": commit_hash.strip()},
        )

    def update_from_app_config(self):
        print("INFO: Updating configuration ...")
        self.max_speed = float(
            self.fclient.get_app_config("max_speed", DEFAULT_MAX_SPEED)
        )
        self.min_speed = float(
            self.fclient.get_app_config("min_speed", DEFAULT_MIN_SPEED)
        )
        self.speed_deadzone = float(
            self.fclient.get_app_config("speed_deadzone", DEFAULT_SPEED_DEADZONE)
        )
        self.speed_increment = float(
            self.fclient.get_app_config("speed_increment", DEFAULT_SPEED_INCREMENT)
        )
        self.angular_reduction = float(
            self.fclient.get_app_config("angular_reduction", DEFAULT_ANGULAR_REDUCTION)
        )
        self.latitude = float(
            self.fclient.get_app_config("latitude", DEFAULT_ANGULAR_REDUCTION)
        )
        self.longitude = float(
            self.fclient.get_app_config("longitude", DEFAULT_ANGULAR_REDUCTION)
        )
        self.gst_string = self.fclient.get_app_config("gst_string", DEFAULT_GST_STRING)
        self.start_speed = float(
            self.fclient.get_app_config("start_speed", DEFAULT_START_SPEED)
        )

    def handle_command_request(self, request):
        if request.command == "jetbot.nudge_forward":
            self._handle_nudge_forward()
            self.fclient.send_command_response(request.id, success=True)
        elif request.command == "jetbot.nudge_backward":
            self._handle_nudge_backward()
            self.fclient.send_command_response(request.id, success=True)
        elif request.command == "jetbot.update_config":
            self.update_from_app_config()
            self.fclient.send_command_response(request.id, success=True)
        else:
            self.fclient.send_command_response(request.id, success=False)

    def handle_teleop(self, control_datapoint):
        if control_datapoint.stream == "Joystick":
            self.handle_joystick(control_datapoint)
        elif control_datapoint.stream == "Buttons":
            self.handle_buttons(control_datapoint)

    def handle_joystick(self, joystick):
        left_motor_value = 0.0
        right_motor_value = 0.0

        # Add contributions from the joysticks
        # TODO: turn this into a circle, not a square
        left_motor_value += (
            self.speed * joystick.twist.angular.z * self.angular_reduction
        )
        right_motor_value += (
            -self.speed * joystick.twist.angular.z * self.angular_reduction
        )

        left_motor_value += self.speed * joystick.twist.linear.x
        right_motor_value += self.speed * joystick.twist.linear.x

        # Improve the deadzone
        if left_motor_value > 0:
            left_motor_value += self.speed_deadzone
        elif left_motor_value < 0:
            left_motor_value -= self.speed_deadzone

        if right_motor_value > 0:
            right_motor_value += self.speed_deadzone
        elif right_motor_value < 0:
            right_motor_value -= self.speed_deadzone

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
        self.fclient.post_text("Commands", "nudge forward")
        self.robot.forward(self.speed)
        time.sleep(0.5)
        self.robot.stop()

    def _handle_nudge_backward(self):
        self.fclient.post_text("Commands", "nudge backward")
        self.robot.backward(self.speed)
        time.sleep(0.5)
        self.robot.stop()

    def _handle_start(self):
        self.fclient.post_text("Commands", "start")
        self.robot.forward(self.speed)

    def _handle_stop(self):
        self.fclient.post_text("Commands", "stop")
        self.robot.stop()

    def _handle_increase_speed(self):
        self.fclient.post_text("Commands", "increase speed")
        if self.speed + self.speed_increment <= self.max_speed:
            self.speed += self.speed_increment
        else:
            self.speed = self.max_speed

    def _handle_decrease_speed(self):
        self.fclient.post_text("Commands", "decrease speed")
        if self.speed - self.speed_increment >= self.min_speed:
            self.speed -= self.speed_increment
        else:
            self.speed = self.min_speed

    def calculate_jitter(self, timestamps):
        length = len(self.camera_frame_timestamps)
        oldest = self.camera_frame_timestamps[0]
        newest = self.camera_frame_timestamps[-1]
        step_value = (newest - oldest) / length

        # Make a list of the difference between the expected and actual step sizes
        jitters = []
        for n in range(length - 1):
            if n > 0:
                jitter = abs((timestamps[n] - timestamps[n - 1]) - step_value)
                jitters.append(jitter)

        return mean(jitters)


if __name__ == "__main__":
    adapter = FormantJetBotAdapter()
