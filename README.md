# bw-flasher
Flashing Brightway and Leqi scooter controllers using UART.

![Screenshot](resources/screenshot_v0.5.3.png)

## 🔓 Our Principles

**You own what you buy.** If you purchased a device, you have the right to understand how it works, repair it, and modify it. Vendors should not lock you out of hardware you own.

**Knowledge should be free.** Reverse engineering findings belong in the public domain. Hoarding this information only empowers those selling black-market tools while honest users stay in the dark.

**Transparency over obscurity.** Weak encryption and absent authentication are security flaws, not secrets to protect. Documenting them pushes manufacturers toward better security.

**Personal responsibility matters.** We provide tools for research and education. What you do with them—and the consequences—are yours. Know your local laws. Prioritize safety.

**No commercial exploitation.** This work is shared freely for the community, not for building products that profit from bypassing safety features.

**This is not an invitation to break laws or endanger people. This is an assertion that understanding technology is a fundamental right.**



## Further Documentation



- [Our Principles](PRINCIPLES.md) - Learn about the core values guiding this project.

- [Legal Disclaimer](LEGAL_DISCLAIMER.md) - Important information regarding legal responsibilities and risks.

- [Contributing Guidelines](CONTRIBUTING.md) - How to contribute to the project.



## ⚠️ IMPORTANT SAFETY WARNING



**Modifying device firmware can be dangerous and illegal.**

- May void your warranty
- May violate local laws and regulations
- Creates serious safety risks by bypassing manufacturer safety features
- Modified devices may be illegal to operate
- You assume ALL liability for injuries, accidents, and legal consequences

**Use at your own risk. This software is for educational and research purposes only.**

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

The flasher supports both **Brightway** and **Leqi** firmware types, with automatic detection!

### CLI

The command-line interface automatically detects the firmware type (Brightway or Leqi).

```bash
# Using Poetry
poetry run bwflasher [--simulation] [--debug] [--port PORT] <FIRMWARE_FILE>

# Using pip
python -m bwflasher [--simulation] [--debug] [--port PORT] <FIRMWARE_FILE>
```
The `<FIRMWARE_FILE>` argument should be the path to your `.bin` file.

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
