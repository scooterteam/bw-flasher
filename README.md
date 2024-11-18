# bw-flasher
Flashing Brightway controllers using the UART.

## Installation
```bash
pip install -r requirements.txt
```

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

```bash
python flasher.py
```

## Deployment
```bash
pyinstaller --name="bwflasher" -i app.ico --add-data "chiptune.mp3:." --windowed --onefile --strip flasher.py
```
