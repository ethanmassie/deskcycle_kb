#!/usr/bin/python
from dataclasses import dataclass, field
from enum import Enum
from typing import List
from os import path

from marshmallow import ValidationError
from marshmallow_dataclass import class_schema
from serial import Serial
from pyautogui import keyDown, keyUp, typewrite, press, isValidKey
import argparse
import json

CONF_PATH = '{}/.config/deskcycle_kb'.format(path.expanduser('~'))


class KeyType(Enum):
    HOLD_KEY = 'HOLD_KEY'
    TOGGLE_KEY = 'TOGGLE_KEY'
    TYPEWRITE_KEY = 'TYPEWRITE_KEY'


@dataclass
class KeySpeedRange:
    """
    An individual key speed range configuration
        Attributes:
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


@dataclass
class ConfiguredKeys:
    """ Class representation of json structure for key configuration """
    keys: List[KeySpeedRange] = field(default_factory=list)


# Schema for deserializing json key configuration
ConfiguredKeysSchema = class_schema(ConfiguredKeys)


def main(key_speed_ranges: List[KeySpeedRange], dev_name: str):
    """
    Main loop of program
        Parameters:
            key_speed_ranges List of type KeySpeedRange containing keys and range they should be pressed in
            dev_name str name of the DeskCycle Speedo device file
    """
    with Serial(dev_name, 9600, timeout=1) as cycle:
        try:
            while True:
                # request speed
                cycle.write(b's')
                try:
                    # read the speed, decode the bytes, convert to float
                    speed = float(cycle.readline().decode())
                except ValueError:
                    # there will likely be a few empty strings returned at first causing a ValueError
                    continue

                # check for keyboard inputs to perform
                for key_speed_range in key_speed_ranges:
                    # Check if in range
                    if key_speed_range.min_speed <= speed <= key_speed_range.max_speed:

                        if key_speed_range.key_type == KeyType.HOLD_KEY and not key_speed_range.down:
                            keyDown(key_speed_range.key_name)
                            key_speed_range.down = True
                        elif key_speed_range.key_type == KeyType.TOGGLE_KEY and not key_speed_range.toggled:
                            press(key_speed_range.key_name)
                            key_speed_range.toggled = True
                        elif key_speed_range.key_type == KeyType.TYPEWRITE_KEY:
                            typewrite(key_speed_range.key_name)
                    # Out of range, if held down then do a keyUp
                    elif key_speed_range.down:
                        keyUp(key_speed_range.key_name)
                        key_speed_range.down = False
                    # if toggled press the key again and un-toggle
                    elif key_speed_range.toggled:
                        press(key_speed_range.key_name)
                        key_speed_range.toggled = False

        except KeyboardInterrupt:
            # clean up held down keys when users interrupts program
            for key_speed_range in key_speed_ranges:
                if key_speed_range.down:
                    keyUp(key_speed_range.key_name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Use speed of DeskCycle Speedo to create keyboard inputs')
    parser.add_argument('--file', '-f', dest='keyboard_config', type=str, required=True,
                        help='Path to json file with input configuration or name of file in ~/.config/deskcycle_kb')
    parser.add_argument('--device', '-d', dest="device", type=str,
                        help="Path to DeskCycle Speedo device file default=/dev/ttyACM0",
                        default='/dev/ttyACM0')
    args = parser.parse_args()

    # find path to config file
    file_path = None
    conf_dir_file = '{}/{}'.format(CONF_PATH, args.keyboard_config)
    if path.exists(args.keyboard_config):
        file_path = args.keyboard_config
    elif path.exists(conf_dir_file):
        file_path = conf_dir_file
    else:
        print('Cannot find valid config file')
        exit(1)

    # deserialize configuration file
    with open(file_path) as keyboard_config_file:
        try:
            configured_keys = ConfiguredKeysSchema().load(json.load(keyboard_config_file))
        except ValidationError as e:
            print(e)
            exit(2)

    main(configured_keys.keys, args.device)
