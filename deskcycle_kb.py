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
    down: bool
        State boolean set to True if a HOLD_KEY is being held down
    toggled: bool
        State boolean set to True if a TOGGLE_KEY has been pressed
    """
    key_name: str
    min_speed: float
    max_speed: float = float('inf')
    key_type: KeyType = KeyType.HOLD_KEY
    down: bool = False
    toggled: bool = False

    def __post_init__(self):
        if self.key_type != KeyType.TYPEWRITE_KEY and not isValidKey(self.key_name):
            raise ValidationError('Invalid Key {} for key type {}'.format(self.key_name, self.key_type))
        self.down = False
        self.toggled = False

    def is_in_range(self, speed: float) -> bool:
        return self.min_speed <= speed <= self.max_speed

    def activate(self):
        if self.key_type == KeyType.HOLD_KEY and not self.down:
            keyDown(self.key_name)
            self.down = True
            logging.debug("Holding {}".format(self.key_name))
        elif self.key_type == KeyType.TOGGLE_KEY and not self.toggled:
            press(self.key_name)
            self.toggled = True
            logging.debug("Pressed {}".format(self.key_name))
        elif self.key_type == KeyType.TYPEWRITE_KEY:
            typewrite(self.key_name)
            logging.debug("Wrote {}".format(self.key_name))

    def deactivate(self):
        if self.down:
            keyUp(self.key_name)
            self.down = False
            logging.debug("Released {}".format(self.key_name))
            # if toggled press the key again and un-toggle
        elif self.toggled:
            press(self.key_name)
            self.toggled = False
            logging.debug("Pressed {} Again".format(self.key_name))


@dataclass
class ConfiguredKeys:
    """ Class representation of json structure for key configuration """
    keys: List[KeySpeedRange] = field(default_factory=list)


# Schema for deserializing json key configuration
ConfiguredKeysSchema = class_schema(ConfiguredKeys)


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
            try:
                # read the speed, decode the bytes, convert to float
                speed = float(desk_cycle.readline().decode())
            except ValueError:
                # there will likely be a few empty strings returned at first causing a ValueError
                continue

            # calculate distance traveled for this loop
            now = time.time()
            delta_time = now - previous_time
            distance_traveled += (speed / SECONDS_IN_HOUR) * delta_time
            previous_time = now

            # check for keyboard inputs to perform
            for key_speed_range in key_speed_ranges:
                # Check if in range
                if key_speed_range.is_in_range(speed):
                    key_speed_range.activate()
                # Out of range so deactivate the key
                else:
                    key_speed_range.deactivate()

    except KeyboardInterrupt:
        # ensure all keys are deactivated
        for key_speed_range in key_speed_ranges:
            key_speed_range.deactivate()

    print("\nYou biked {:.2f} miles".format(distance_traveled))


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

    if args.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.ERROR

    logging.basicConfig(level=log_level, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%I:%M:%S')

    # find path to config file
    file_path = None
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
        desk_cycle_dev = discover_device()
        main(configured_keys.keys, desk_cycle_dev)
        desk_cycle_dev.close()
    except RuntimeError as e:
        logging.error(e)
        exit(3)
