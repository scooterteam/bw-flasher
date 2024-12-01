# bw-flasher
Flashing Brightway controllers using the UART.

## Terms of use
This code / tool is provided for **personal and non-commercial use only**. By using this code / tool, you agree not to use it for any commercial purposes, including but not limited to selling, distributing, or integrating it into any product or service intended for monetary gain.

## Installation
```bash
pip install -r requirements.txt
```
It's recommended to use a virtual environment like `venv` for installation.

## Usage

### CLI

```bash
usage: flash_uart.py [-h] [--simulation] [--debug] fw_file

positional arguments:
  fw_file

options:
  -h, --help    show this help message and exit
  --simulation
  --debug       Enable debug output
```

### GUI
Run the flasher GUI with this command:

```bash
python flasher.py
```

## Deployment
You can package the project as a standalone executable using the following command:

```bash
pyinstaller --name="bwflasher" -i app.ico --add-data "chiptune.mp3:." --add-data "app.ico:." --windowed --onefile flasher.py
```

## Disclaimer
This software is not affiliated with, endorsed by, or associated with any company. Use of this tool is entirely at your own risk, as it is provided as-is without any guarantees or warranties. The developers of this software assume no responsibility for any damage, malfunctions, warranty voidance, or legal consequences resulting from its use. This tool is intended solely for personal use, and users are fully responsible for ensuring compliance with local laws and regulations regarding modifications. By using this software, you acknowledge and agree to these terms.
