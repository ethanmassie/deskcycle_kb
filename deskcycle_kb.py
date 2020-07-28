from dataclasses import dataclass
from typing import List

from serial import Serial
from pyautogui import keyDown, keyUp, typewrite
import argparse
import json


@dataclass()
class KeySpeedRange:
    key_name: str
    min_speed: float
    max_speed: float = float('inf')
    hold_key: bool = True
    # track if the key is being held down so we can do a key up when out of range
    down: bool = False


def main(key_speed_ranges: List[KeySpeedRange], dev_name: str):
    with Serial(dev_name, 9600, timeout=1) as cycle:
        while True:
            # request speed
            cycle.write(b's')

            try:
                # read the speed, decode the bytes, convert to float
                speed = float(cycle.readline().decode())
                # check for keyboard inputs to perform
                for key_speed_range in key_speed_ranges:
                    if key_speed_range.min_speed <= speed <= key_speed_range.max_speed:
                        if key_speed_range.hold_key and not key_speed_range.down:
                            keyDown(key_speed_range.key_name)
                            key_speed_range.down = True
                        elif not key_speed_range.hold_key:
                            typewrite(key_speed_range.key_name)
                    elif key_speed_range.down:
                        keyUp(key_speed_range.key_name)
                        key_speed_range.down = False
            except ValueError as e:
                # there will likely be a few empty strings returned at first causing a ValueError
                pass
            except KeyboardInterrupt as e:
                # safely exit on KeyboardInterrupt
                exit(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Use speed of DeskCycle Speedo to create keyboard inputs')
    parser.add_argument('--file', '-f', dest='keyboard_config', type=str,
                        help='Path to json file with input configuration',
                        default="example_config.json")
    parser.add_argument('--device', '-d', dest="device", type=str, help="Path to DeskCycle Speedo device file",
                        default='/dev/ttyACM0')
    args = parser.parse_args()

    with open(args.keyboard_config) as keyboard_config_file:
        keyboard_config = json.loads(keyboard_config_file.read())

    configured_keys = []
    key: dict
    for key in keyboard_config['keys']:
        configured_keys.append(conf_key := KeySpeedRange(*key.values()))

    main(configured_keys, args.device)
