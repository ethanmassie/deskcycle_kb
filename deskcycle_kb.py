#!/usr/bin/python
from dataclasses import dataclass, field
from enum import Enum
from typing import List
from pathlib import Path
import platform
import time
import logging

from marshmallow import ValidationError
from marshmallow_dataclass import class_schema
from serial import Serial
from pyautogui import keyDown, keyUp, typewrite, press, isValidKey
import argparse
import json
import serial.tools.list_ports

CONF_PATH = ''
if platform.system() == 'Linux' or platform.system() == 'Darwin':
    CONF_PATH = '{}/.config/deskcycle_kb'.format(Path.home())
elif platform.system() == 'Windows':
    CONF_PATH = '{}/AppData/Local/deskcycle_kb'.format(Path.home())

DEV_NAME = b'DeskCycle Speedo\r\n'
SECONDS_IN_HOUR = 3600


class KeyType(Enum):
    """
    Enumeration of possible key types
    """
    HOLD_KEY = 'HOLD_KEY'
    TOGGLE_KEY = 'TOGGLE_KEY'
    TYPEWRITE_KEY = 'TYPEWRITE_KEY'


@dataclass
class KeySpeedRange:
    """
    An individual key speed range configuration
    key_name: str
        Valid name of key
    min_speed: float
        Minimum speed in range where key should be pressed
    max_speed: float
        Maximum speed in range where key should be pressed. Default Infinity
    key_type: KeyType
        Enum type of key determining behavior. Default HOLD_KEY
    """
    key_name: str
    min_speed: float
    max_speed: float = float('inf')
    key_type: KeyType = KeyType.HOLD_KEY

    def __post_init__(self):
        # everything other than typewrite key requires a valid key
        if self.key_type != KeyType.TYPEWRITE_KEY and not isValidKey(self.key_name):
            raise ValidationError('Invalid Key {} for key type {}'.format(self.key_name, self.key_type))

        # set the activate and deactivate functions based on type and set up the default state where necessary
        if self.key_type == KeyType.HOLD_KEY:
            self._is_pressed = False
            self.activate = self._hold_key_activate
            self.deactivate = self._hold_key_deactivate
        elif self.key_type == KeyType.TOGGLE_KEY:
            self._is_toggled = False
            self.activate = self._toggle_key_activate
            self.deactivate = self._toggle_key_deactivate
        elif self.key_type == KeyType.TYPEWRITE_KEY:
            self.activate = self._typewrite_key_activate
            self.deactivate = self._typewrite_key_deactivate
        else:
            self.activate = self._default_activate
            self.deactivate = self._default_deactivate

    def is_in_range(self, speed: float) -> bool:
        """
        Check if the given speed is within the min_speed and max_speed properties
        :param speed: floating point speed to compare against
        :return: boolean result of comparison
        """
        return self.min_speed <= speed <= self.max_speed

    def _hold_key_activate(self):
        """
        Handle activation for a hold key. Performs a key down on the key if it isn't already down
        :return:
        """
        if not self._is_pressed:
            keyDown(self.key_name)
            self._is_pressed = True
            logging.debug("Holding {}".format(self.key_name))

    def _toggle_key_activate(self):
        """
        Handle activation for a toggle key. Only presses the key if it isn't already toggled
        """
        if not self._is_toggled:
            press(self.key_name)
            self._is_toggled = True
            logging.debug("Pressed {}".format(self.key_name))

    def _typewrite_key_activate(self):
        """
        Handle activation for a typewrite key. Simply call typewrite with the key_name
        :return:
        """
        typewrite(self.key_name)
        logging.debug("Wrote {}".format(self.key_name))

    def _default_activate(self):
        """
        perform activation for key based on it's type
        """
        pass

    def _hold_key_deactivate(self):
        """
        Handle deactivation for a hold key. Performs a key up if the key is already down.
        """
        if self._is_pressed:
            keyUp(self.key_name)
            self._is_pressed = False
            logging.debug("Released {}".format(self.key_name))

    def _toggle_key_deactivate(self):
        """
        Handle deactivation for a toggle key. Only presses the key if it is already toggled effectively un-toggling it.
        """
        if self._is_toggled:
            press(self.key_name)
            self._is_toggled = False
            logging.debug("Pressed {} Again".format(self.key_name))

    def _typewrite_key_deactivate(self):
        """
        Handle deactivation for typewrite key. Noop since nothing needs to be deactivated.
        """
        pass

    def _default_deactivate(self):
        """
        perform deactivation for key based on it's type
        """
        pass


@dataclass
class ConfiguredKeys:
    """ Class representation of json structure for key configuration """
    keys: List[KeySpeedRange] = field(default_factory=list)


# Schema for deserializing json key configuration
ConfiguredKeysSchema = class_schema(ConfiguredKeys)


def calculate_delta_time(previous_time):
    """
    Get the delta time based on the previous_time argument and the current time
    :param previous_time: Time to compare against now
    :return: difference between previous_time and now, now
    """
    now = time.time()
    delta_time = now - previous_time
    return delta_time, now


def main(key_speed_ranges: List[KeySpeedRange], desk_cycle: Serial):
    """
    Main loop of program
    key_speed_ranges List of type KeySpeedRange containing keys and range they should be pressed in
    desk_cycle Serial device with an open desk cycle speedo
    """
    logging.debug('Starting main loop')
    print('Press Ctr + C to stop')
    distance_traveled = 0.0
    previous_time = time.time()
    try:
        while True:
            # request speed
            desk_cycle.write(b's')
            speed = float(desk_cycle.readline().decode())

            # calculate distance traveled for this loop
            delta_time, previous_time = calculate_delta_time(previous_time)
            distance_traveled += (speed / SECONDS_IN_HOUR) * delta_time

            print(f'\tCurrent Speed: {speed:.2f} mph \tDistance Traveled: {distance_traveled:.2f} miles', end='\r', flush=True)
            # check for keyboard inputs to perform
            for key_speed_range in key_speed_ranges:
                key_speed_range.activate() if key_speed_range.is_in_range(speed) else key_speed_range.deactivate()
    except KeyboardInterrupt:
        print()
        # ensure all keys are deactivated
        for key_speed_range in key_speed_ranges:
            key_speed_range.deactivate()


def discover_device():
    """
    Find a DeskCycle Speedo device
    :return: Open Serial device
    """
    for port in serial.tools.list_ports.comports():
        device = Serial(port.device, 9600, timeout=0.3)
        attempt = 0
        while attempt < 3:
            device.write(b'h')
            handshake = device.readline()
            if handshake == DEV_NAME:
                logging.debug('Found desk cycle at {}'.format(port.device))
                return device
            else:
                attempt += 1
        device.close()
    raise RuntimeError('failed to find desk cycle device')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Use speed of DeskCycle Speedo to create keyboard inputs')
    parser.add_argument('--file', '-f', dest='keyboard_config', type=str, required=True,
                        help='Full path to json config or path relative to {}'.format(CONF_PATH))
    parser.add_argument('--debug', '-d', dest='debug', action='store_true',
                        help='set if you want more logging info')
    args = parser.parse_args()

    # setup logger
    log_level = logging.DEBUG if args.debug else logging.ERROR
    logging.basicConfig(level=log_level, format='\n%(asctime)s [%(levelname)s] %(message)s', datefmt='%I:%M:%S')

    # find path to config file
    conf_dir_file = '{}/{}'.format(CONF_PATH, args.keyboard_config)
    if Path(args.keyboard_config).exists():
        file_path = args.keyboard_config
    elif Path(conf_dir_file).exists():
        file_path = conf_dir_file
    else:
        logging.error('cannot find valid config file')
        exit(1)

    # deserialize configuration file
    with open(file_path) as keyboard_config_file:
        try:
            configured_keys = ConfiguredKeysSchema().load(json.load(keyboard_config_file))
        except ValidationError as e:
            logging.error(e)
            exit(2)

    try:
        with discover_device() as desk_cycle_dev:
            main(configured_keys.keys, desk_cycle_dev)
    except RuntimeError as e:
        logging.error(e)
        exit(3)
