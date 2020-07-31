# DeskCycle KB
Create keyboard inputs based on speed of DeskCycle. Requires Arduino mod for DeskCycle to output to usb.

### Requires
- python3
- pyserial
- pyautogui
- marshmallow_dataclass
- marshmallow_enum
- tkinter (`pacman -S tk` or `apt install python3-tk`)

### Getting Started
Install dependencies

`pip install -r requirements.txt`

(Linux Only) Install tkinter with your package manager

`pacman -S tk`

`apt install python3-tk`

Run the example config to verify everything works.

`./deskcycle_kb.py -f example_config.json`

#### Write A Custom Config
By default the script will look in `~/.config/deskcycle_kb/` for config files. 
You can also provide full paths to config files.

Config files must be written in JSON format. See example_config.json for a usable example.
```json
{
    "keys": [
        {
            "key_name": "String Representation of key to press",
            "min_speed": "Float minimum speed for trigger speed range",
            "max_speed": "Float maximum speed for trigger speed range. Default infinity",
            "key_type":  "String either HOLD_KEY, TOGGLE_KEY, or TYPEWRITE_KEY. Default HOLD_KEY"
        }
    ]
}
```

### Help
```
usage: deskcycle_kb [-h] --file KEYBOARD_CONFIG [--device DEVICE]

Use speed of DeskCycle Speedo to create keyboard inputs

optional arguments:
  -h, --help            show this help message and exit
  --file KEYBOARD_CONFIG, -f KEYBOARD_CONFIG
                        Path to json file with input configuration or name of file in ~/.config/deskcycle_kb
  --device DEVICE, -d DEVICE
                        Path to DeskCycle Speedo device file default=/dev/ttyACM0
```

Original DeskCycle Mod by Kneave 

[Source Code](https://github.com/kneave/dcspeedo) 

[Blog Post](https://neave.engineering/2015/04/03/arduino-speedometer-for-the-deskcycle/)
