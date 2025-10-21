# bw-flasher
Flashing Brightway controllers using the UART.

![Screenshot](resources/screenshot_v0.5.3.png)

## Terms of use
This code / tool is provided for **personal and non-commercial use only**. By using this code / tool, you agree not to use it for any commercial purposes, including but not limited to selling, distributing, or integrating it into any product or service intended for monetary gain.

## Installation

### Using Poetry (Recommended)
```bash
poetry install
```

### Using pip
```bash
pip install -r requirements.txt
```
It's recommended to use a virtual environment like `venv` for installation.

## Usage

The flasher now supports both **Brightway** and **Leqi** firmware types, with automatic detection!

### CLI

#### Brightway Firmware
```bash
# Using Poetry
poetry run python -m bwflasher [--simulation] [--debug] [--port PORT] fw_file.bin

# Using pip
python -m bwflasher [--simulation] [--debug] [--port PORT] fw_file.bin
```

#### Leqi Firmware
Leqi firmware is supported through the GUI with automatic detection. For command-line operations, use the standalone `leqi_fw_tool.py` script in the project root.

### GUI
Run the flasher GUI with this command:

```bash
# Using Poetry
poetry run python -m bwflasher.gui

# Using pip
python -m bwflasher.gui
```

The GUI will automatically detect firmware type (Brightway or Leqi) when you select a file and display it with a color-coded label.

## Testing

Run the test suite with pytest:

```bash
# Using Poetry
poetry run pytest tests/ -v

# Using pip
pytest tests/ -v
```

The test suite includes:
- Firmware type detection tests
- Cryptographic function tests (CRC, bit reversal, encryption)
- Base flasher functionality tests
- Simulation mode tests

## Deployment
You can package the project as a standalone executable using the following command:

```bash
pyinstaller --name="bwflasher" -i resources/app.ico --add-data "resources/*:resources" --windowed --onefile bwflasher/gui.py
```

## Disclaimer
This software is not affiliated with, endorsed by, or associated with any company. Use of this tool is entirely at your own risk, as it is provided as-is without any guarantees or warranties. The developers of this software assume no responsibility for any damage, malfunctions, warranty voidance, or legal consequences resulting from its use. This tool is intended solely for personal use, and users are fully responsible for ensuring compliance with local laws and regulations regarding modifications. By using this software, you acknowledge and agree to these terms.
