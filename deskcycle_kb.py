#!/usr/bin/python
from typing import List

from serial import Serial
from pyautogui import keyDown, keyUp, typewrite, press, isValidKey
import argparse
import json

TYPEWRITE_KEY = 'TYPEWRITE_KEY'
TOGGLE_KEY = 'TOGGLE_KEY'
HOLD_KEY = 'HOLD_KEY'


class KeySpeedRange:
    def __init__(self, key_name: str, min_speed: float, max_speed=float('inf'), key_type='HOLD_KEY'):
        if key_type != TYPEWRITE_KEY and not isValidKey(key_name):
            raise ValueError('Invalid Key {} for key type {}'.format(key_name, key_type))
        self.key_name = key_name
        self.min_speed = min_speed
        self.max_speed = max_speed
        self.key_type = key_type
        self.down = False
        self.toggled = False


def main(key_speed_ranges: List[KeySpeedRange], dev_name: str):
    with Serial(dev_name, 9600, timeout=1) as cycle:
        # wait a few seconds to start the main loop
        while True:
            # request speed
            cycle.write(b's')

            try:
                # read the speed, decode the bytes, convert to float
                speed = float(cycle.readline().decode())
                # check for keyboard inputs to perform
                for key_speed_range in key_speed_ranges:
                    # Check if in range
                    if key_speed_range.min_speed <= speed <= key_speed_range.max_speed:

                        if key_speed_range.key_type == HOLD_KEY and not key_speed_range.down:
                            keyDown(key_speed_range.key_name)
                            key_speed_range.down = True
                        elif key_speed_range.key_type == TOGGLE_KEY and not key_speed_range.toggled:
                            press(key_speed_range.key_name)
                            key_speed_range.toggled = True
                        elif key_speed_range.key_type == TYPEWRITE_KEY:
                            typewrite(key_speed_range.key_name)
                    # Out of range, if held down then do a keyUp
                    elif key_speed_range.down:
                        if key_speed_range.key_type == TOGGLE_KEY:
                            keyDown(key_speed_range.key_name)
                        keyUp(key_speed_range.key_name)
                        key_speed_range.down = False
                    # if toggled press the key again and un-toggle
                    elif key_speed_range.toggled:
                        press(key_speed_range.key_name)
                        key_speed_range.toggled = False
            except ValueError:
                # there will likely be a few empty strings returned at first causing a ValueError
                pass
            except KeyboardInterrupt:
                # break out of main loop to complete
                break

        # clean up held down keys when loop breaks
        for key_speed_range in key_speed_ranges:
            if key_speed_range.down:
                keyUp(key_speed_range.key_name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Use speed of DeskCycle Speedo to create keyboard inputs')
    parser.add_argument('--file', '-f', dest='keyboard_config', type=str, required=True,
                        help='Path to json file with input configuration')
    parser.add_argument('--device', '-d', dest="device", type=str, help="Path to DeskCycle Speedo device file",
                        default='/dev/ttyACM0')
    args = parser.parse_args()

    with open(args.keyboard_config) as keyboard_config_file:
        keyboard_config = json.loads(keyboard_config_file.read())

    configured_keys = []
    key: dict
    for key in keyboard_config['keys']:
        try:
            configured_keys.append(conf_key := KeySpeedRange(*key.values()))
        except ValueError as e:
            print(e)
            exit(1)

    main(configured_keys, args.device)
