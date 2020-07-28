# DeskCycle KB
Create keyboard inputs based on speed of DeskCycle. Requires Arduino mod for DeskCycle to output to usb.

### Requires
- python3
- pyserial
- pyautogui
- tkinter (`pacman -S tk` or `apt install python3-tk`)

### Help
```
usage: deskcycle_kb.py [-h] [--file KEYBOARD_CONFIG] [--device DEVICE]

Use speed of DeskCycle Speedo to create keyboard inputs

optional arguments:
  -h, --help            show this help message and exit
  --file KEYBOARD_CONFIG, -f KEYBOARD_CONFIG
                        Path to json file with input configuration
  --device DEVICE, -d DEVICE
                        Path to DeskCycle Speedo device file
```

Original DeskCycle Mod by Kneave [Sauce](https://github.com/kneave/dcspeedo) [Post](https://neave.engineering/2015/04/03/arduino-speedometer-for-the-deskcycle/)
