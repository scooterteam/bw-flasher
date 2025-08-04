# bw-flasher
Flashing Brightway controllers using the UART.

![Screenshot](https://private-user-images.githubusercontent.com/46298681/474185694-ffc180a2-89f7-4be1-9422-ded7a89522ec.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NTQzMzk5NzcsIm5iZiI6MTc1NDMzOTY3NywicGF0aCI6Ii80NjI5ODY4MS80NzQxODU2OTQtZmZjMTgwYTItODlmNy00YmUxLTk0MjItZGVkN2E4OTUyMmVjLnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTA4MDQlMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwODA0VDIwMzQzN1omWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPWRkMzcwODk2YTdiOGViNjRkM2FhYTlkNzMzMjExYmRjNDJjYzA5M2JiOWQ4MTIwNWMyODRkMGU2ZTAzNTYyYjImWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.yRFkauhLflnWzAM-oJXzHVuIDp37ln6h65072Dbgwmk)

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
usage: python -m bwflasher [-h] [--simulation] [--debug] [--port PORT] fw_file

positional arguments:
  fw_file

options:
  -h, --help    show this help message and exit
  --simulation
  --debug       Enable debug output
  --port PORT   Serial port (default: COM1)
```

### GUI
Run the flasher GUI with this command:

```bash
python -m bwflasher.gui
```

## Deployment
You can package the project as a standalone executable using the following command:

```bash
pyinstaller --name="bwflasher" -i resources/app.ico --add-data "resources/*:resources" --windowed --onefile bwflasher/gui.py
```

## Disclaimer
This software is not affiliated with, endorsed by, or associated with any company. Use of this tool is entirely at your own risk, as it is provided as-is without any guarantees or warranties. The developers of this software assume no responsibility for any damage, malfunctions, warranty voidance, or legal consequences resulting from its use. This tool is intended solely for personal use, and users are fully responsible for ensuring compliance with local laws and regulations regarding modifications. By using this software, you acknowledge and agree to these terms.
