#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Flasher
# Copyright (C) 2024-2025 ScooterTeam
#
# This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
# or send a letter to Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.
#
# You are free to:
# - Share — copy and redistribute the material in any medium or format
# - Adapt — remix, transform, and build upon the material
#
# Under the following terms:
# - Attribution — You must give appropriate credit, provide a link to the license, and indicate if changes were made.
# - NonCommercial — You may not use the material for commercial purposes.
# - ShareAlike — If you remix, transform, or build upon the material, you must distribute your contributions under the same license as the original.
#

import serial.tools.list_ports
import sys
import os
import platform
import webbrowser
import requests

from serial.serialutil import SerialException
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QProgressBar, QFileDialog, QCheckBox, QTextEdit, QStatusBar, QComboBox, QMessageBox
)
from PySide6.QtGui import QPalette, QIcon, QColor, QCursor
from PySide6.QtCore import Qt, QThread, Signal, QUrl, QTimer
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from bwflasher.flash_uart import DFU, FlasherException
from bwflasher.updater import check_update, get_name
from bwflasher.styles import DARK_THEME_STYLESHEET, COLOR_PALETTE
from bwflasher.version import __version__
from bwflasher.firmware_detector import detect_firmware_file, create_flasher_for_firmware, get_firmware_info
from bwflasher.base_flasher import FirmwareType

OS = platform.system()


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, "resources", relative_path)


def get_serial_ports():
    ports = serial.tools.list_ports.comports()
    if OS == "Windows":
        return [port[0] for port in ports] if ports else []
    else:
        prefix = "/dev/ttyUSB" if OS == "Linux" else "/dev/cu.usbserial"
        return [port[0] for port in ports if port[0].startswith(prefix)] if ports else []


class BaseThread(QThread):
    progress_signal = Signal(int)
    status_signal = Signal(str)
    debug_signal = Signal(str)
    exception_signal = Signal(list)

    def __init__(self, com_port, firmware_file, simulation, debug, firmware_type=None, parent=None):
        super().__init__(parent)
        self.com_port = com_port
        self.firmware_file = firmware_file
        self.simulation = simulation
        self.debug = debug
        self.firmware_type = firmware_type

    def update_progress(self, value):
        self.progress_signal.emit(value)

    def log_debug(self, message):
        self.debug_signal.emit(message)

    def show_status(self, message):
        self.status_signal.emit(message)


class FirmwareUpdateThread(BaseThread):
    def __init__(self, com_port, firmware_file, simulation, debug, firmware_type=None, parent=None):
        super().__init__(com_port, firmware_file, simulation, debug, firmware_type, parent)

    def run(self):
        try:
            # Auto-detect firmware type if not specified
            if self.firmware_type is None:
                self.firmware_type = detect_firmware_file(self.firmware_file)

            # Create appropriate flasher
            updater = create_flasher_for_firmware(
                self.firmware_file,
                tty_port=self.com_port,
                simulation=self.simulation,
                debug=self.debug,
                status_callback=self.show_status,
                log_callback=self.log_debug,
                progress_callback=self.update_progress,
            )
            updater.load_file(self.firmware_file)
            updater.run()
        except FlasherException as e:
            self.exception_signal.emit(["Flasher", str(e)])
        except SerialException:
            self.exception_signal.emit(["Serial", "The serial connection caused an error. Is your adapter connected?"])
        except Exception as e:
            self.exception_signal.emit(["Unknown", str(e)])


class TestConnectionThread(BaseThread):
    def __init__(self, com_port, firmware_file, simulation, debug, firmware_type=None, parent=None):
        super().__init__(com_port, firmware_file, simulation, debug, firmware_type, parent)

    def run(self):
        try:
            # Auto-detect firmware type if firmware file is provided
            if self.firmware_file and self.firmware_type is None:
                self.firmware_type = detect_firmware_file(self.firmware_file)

            # Create appropriate flasher or default to Brightway
            if self.firmware_file:
                updater = create_flasher_for_firmware(
                    self.firmware_file,
                    tty_port=self.com_port,
                    simulation=self.simulation,
                    debug=self.debug,
                    status_callback=self.show_status,
                    log_callback=self.log_debug,
                    progress_callback=self.update_progress,
                )
            else:
                # No firmware file - use default Brightway flasher
                updater = DFU(
                    tty_port=self.com_port,
                    simulation=self.simulation,
                    debug=self.debug,
                    status_callback=self.show_status,
                    log_callback=self.log_debug,
                    progress_callback=self.update_progress,
                )
            updater.test_connection()
        except SerialException:
            self.exception_signal.emit(["Serial", "The serial connection caused an error. Is your adapter connected?"])
        except Exception as e:
            self.exception_signal.emit(["Unknown", str(e)])


class FirmwareUpdateGUI(QWidget):
    def __init__(self):
        super().__init__()

        self.update_thread = None
        self.flasher_debug = False
        self.window_name = get_name()

        self.setWindowTitle(self.window_name)
        self.setWindowIcon(QIcon(resource_path("app.ico")))

        # Set object name for styling
        self.setObjectName("mainWindow")

        # Set the modern dark theme stylesheet
        self.setStyleSheet(DARK_THEME_STYLESHEET)
        
        self.check_update()
        self.disclaimer_messagebox()

        self.setGeometry(100, 100, 600, 500)
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        # Create banner text programmatically
        self.heading_text = self.create_banner_text()
        self.heading_label = QLabel(self.heading_text, self)
        self.heading_label.setAlignment(Qt.AlignCenter)
        self.heading_label.setObjectName("titleLabel")
        # Set monospace font for proper ASCII art alignment
        from PySide6.QtGui import QFont
        monospace_font = QFont("JetBrains Mono", 10)
        monospace_font.setStyleHint(QFont.Monospace)
        self.heading_label.setFont(monospace_font)
        layout.addWidget(self.heading_label)

        # Serial port selection
        layout_h = QHBoxLayout()
        layout_h.setSpacing(8)
        self.com_label = QLabel("Serial Port:")
        self.com_label.setMinimumWidth(80)
        layout_h.addWidget(self.com_label)
        self.com_port = QComboBox()
        self.com_port.setEditable(True)
        self.com_port.addItems(get_serial_ports())
        self.com_port.setObjectName("serialCombo")
        layout_h.addWidget(self.com_port)
        layout.addLayout(layout_h)

        # Firmware file selection
        layout_h = QHBoxLayout()
        layout_h.setSpacing(8)
        self.file_label = QLabel("Firmware File:")
        self.file_label.setMinimumWidth(80)
        layout_h.addWidget(self.file_label)
        self.file_path = QLineEdit()
        self.file_path.setObjectName("filePath")
        self.file_path.setPlaceholderText("Select firmware file...")
        self.file_path.textChanged.connect(self.on_firmware_file_changed)
        layout_h.addWidget(self.file_path, 1)
        self.browse_button = QPushButton("Browse")
        self.browse_button.setObjectName("browseButton")
        self.browse_button.clicked.connect(self.browse_file)
        layout_h.addWidget(self.browse_button)
        layout.addLayout(layout_h)

        # Firmware type label
        self.firmware_type_label = QLabel("Firmware Type: Unknown")
        self.firmware_type_label.setObjectName("firmwareTypeLabel")
        self.firmware_type_label.setStyleSheet("""
            QLabel#firmwareTypeLabel {
                background-color: #2b2b2b;
                padding: 8px 12px;
                border-radius: 4px;
                font-weight: bold;
                border: 1px solid #3a3a3a;
            }
        """)
        layout.addWidget(self.firmware_type_label)

        # Mode selection
        self.simulation_checkbox = QCheckBox("Simulation Mode")
        self.simulation_checkbox.setObjectName("simulationCheck")
        layout.addWidget(self.simulation_checkbox)

        self.debug_checkbox = QCheckBox("Debug Mode")
        self.debug_checkbox.setObjectName("debugCheck")
        layout.addWidget(self.debug_checkbox)

        # Action buttons
        layout_h = QHBoxLayout()
        layout_h.setSpacing(12)
        self.test_button = QPushButton("🔍 Test Connection")
        self.test_button.setObjectName("testButton")
        self.test_button.clicked.connect(self.test_connection)
        layout_h.addWidget(self.test_button)
        self.start_button = QPushButton("🚀 Start Update")
        self.start_button.setObjectName("startButton")
        self.start_button.clicked.connect(self.start_update)
        layout_h.addWidget(self.start_button)
        layout.addLayout(layout_h)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        layout.addWidget(self.progress_bar)

        # Log output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setObjectName("logOutput")
        layout.addWidget(self.log_output)

        self.status_bar = QStatusBar(self)
        layout.addWidget(self.status_bar)

        self.setLayout(layout)

        # Set up cursors for better visibility
        self.setup_cursors()
        
        # Set up banner animation
        self.setup_banner_animation()
        
        # Set up the media player and play chiptune
        self.setup_music()

    def create_banner_text(self):
        """Create banner text programmatically with proper character counts"""
        # Banner configuration
        title = f"Brightway Flasher v{__version__}"
        subtitle = "by ScooterTeam"
        
        # Calculate total width (using current banner as reference)
        total_width = 58  # Total characters per line
        
        # Calculate padding for center alignment
        title_padding = (total_width - 2 - len(title)) // 2  # -2 for ║ characters
        subtitle_padding = (total_width - 2 - len(subtitle)) // 2
        
        # Create lines
        top_line = "╔" + "═" * (total_width - 2) + "╗"
        title_line = "║" + " " * title_padding + title + " " * (total_width - 2 - title_padding - len(title)) + "║"
        subtitle_line = "║" + " " * subtitle_padding + subtitle + " " * (total_width - 2 - subtitle_padding - len(subtitle)) + "║"
        bottom_line = "╚" + "═" * (total_width - 2) + "╝"
        
        return f"{top_line}\n{title_line}\n{subtitle_line}\n{bottom_line}"

    def setup_cursors(self):
        """Set up proper cursors for better visibility on all devices"""
        # Set default cursor for the main window
        self.setCursor(Qt.ArrowCursor)
        
        # Set text cursor for input fields
        self.file_path.setCursor(Qt.IBeamCursor)
        self.com_port.setCursor(Qt.IBeamCursor)
        self.log_output.setCursor(Qt.IBeamCursor)
        
        # Set pointer cursor for clickable elements
        self.browse_button.setCursor(Qt.PointingHandCursor)
        self.test_button.setCursor(Qt.PointingHandCursor)
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.simulation_checkbox.setCursor(Qt.PointingHandCursor)
        self.debug_checkbox.setCursor(Qt.PointingHandCursor)

    def setup_banner_animation(self):
        """Set up Knight Rider-style banner animation"""
        # Animation state
        self.animation_position = 0
        self.animation_direction = 1  # 1 for right, -1 for left
        self.animation_speed = 100  # milliseconds between updates
        
        # Create timer for animation
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_banner_animation)
        self.animation_timer.start(self.animation_speed)
        
        # Initial animation update
        self.update_banner_animation()

    def update_banner_animation(self):
        """Update the Knight Rider-style animation"""
        # Get the base banner text
        base_text = self.create_banner_text()
        lines = base_text.split('\n')
        
        # Animation bar characters (Knight Rider style)
        bar_chars = ['█', '▓', '▒', '░', ' ']  # Solid to transparent
        
        # Calculate animation position (0 to banner width)
        banner_width = 58
        self.animation_position += self.animation_direction
        
        # Reverse direction at edges
        if self.animation_position >= banner_width - 1:
            self.animation_direction = -1
        elif self.animation_position <= 0:
            self.animation_direction = 1
        
        # Create animated banner
        animated_lines = []
        for i, line in enumerate(lines):
            if i == 1:  # Title line - add animation bar
                animated_line = self.create_animated_line(line, self.animation_position, bar_chars)
                animated_lines.append(animated_line)
            else:
                animated_lines.append(line)
        
        # Update the banner text
        self.heading_label.setText('\n'.join(animated_lines))

    def create_animated_line(self, base_line, position, bar_chars):
        """Create a line with Knight Rider-style animation bar"""
        # Convert line to list for manipulation
        line_chars = list(base_line)
        
        # Add animation bar at the current position
        if 0 <= position < len(line_chars):
            # Create gradient effect
            for i, char in enumerate(bar_chars):
                pos = position - i
                if 0 <= pos < len(line_chars) and line_chars[pos] == ' ':
                    line_chars[pos] = char
        
        return ''.join(line_chars)

    def setup_music(self):
        """Set up and play the chiptune music"""
        try:
            # Set up the media player
            self.player = QMediaPlayer()
            self.audio_output = QAudioOutput()
            self.player.setAudioOutput(self.audio_output)

            # Set the file path for the tune
            file_url = QUrl.fromLocalFile(resource_path("chiptune.mp3"))
            self.player.setSource(file_url)

            # Play the audio
            self.player.play()
        except Exception as e:
            # Silently handle music errors to avoid breaking the app
            pass

    def setup_animation(self):
        # Animation removed - kept for compatibility
        pass

    def update_animation(self):
        # Animation removed - kept for compatibility
        pass

    def browse_file(self):
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Select Firmware File",
            "",
            "BIN Files (*.bin);;All Files (*)"
        )
        if file:
            self.file_path.setText(file)
            self.update_firmware_type_label(file)

    def on_firmware_file_changed(self, file_path):
        """Called when firmware file path changes"""
        if file_path and os.path.exists(file_path):
            self.update_firmware_type_label(file_path)
        else:
            self.firmware_type_label.setText("Firmware Type: Unknown")
            self.firmware_type_label.setStyleSheet("""
                QLabel#firmwareTypeLabel {
                    background-color: #2b2b2b;
                    padding: 8px 12px;
                    border-radius: 4px;
                    font-weight: bold;
                    border: 1px solid #3a3a3a;
                    color: #999999;
                }
            """)

    def update_firmware_type_label(self, file_path):
        """Update the firmware type label based on detected firmware type"""
        try:
            fw_type, fw_info = get_firmware_info(open(file_path, 'rb').read())

            if fw_type == FirmwareType.BRIGHTWAY:
                self.firmware_type_label.setText(f"Firmware Type: Brightway (ARM Cortex-M)")
                self.firmware_type_label.setStyleSheet("""
                    QLabel#firmwareTypeLabel {
                        background-color: #1e3a1e;
                        padding: 8px 12px;
                        border-radius: 4px;
                        font-weight: bold;
                        border: 1px solid #2d5a2d;
                        color: #66ff66;
                    }
                """)
            elif fw_type == FirmwareType.LEQI:
                self.firmware_type_label.setText(f"Firmware Type: Leqi (Encrypted)")
                self.firmware_type_label.setStyleSheet("""
                    QLabel#firmwareTypeLabel {
                        background-color: #3a1e1e;
                        padding: 8px 12px;
                        border-radius: 4px;
                        font-weight: bold;
                        border: 1px solid #5a2d2d;
                        color: #ff6666;
                    }
                """)
            else:
                self.firmware_type_label.setText("Firmware Type: Unknown")
                self.firmware_type_label.setStyleSheet("""
                    QLabel#firmwareTypeLabel {
                        background-color: #2b2b2b;
                        padding: 8px 12px;
                        border-radius: 4px;
                        font-weight: bold;
                        border: 1px solid #3a3a3a;
                        color: #999999;
                    }
                """)
        except Exception as e:
            self.firmware_type_label.setText(f"Firmware Type: Error ({str(e)})")
            self.firmware_type_label.setStyleSheet("""
                QLabel#firmwareTypeLabel {
                    background-color: #3a3a1e;
                    padding: 8px 12px;
                    border-radius: 4px;
                    font-weight: bold;
                    border: 1px solid #5a5a2d;
                    color: #ffff66;
                }
            """)

    def test_connection(self):
        simulation = self.simulation_checkbox.isChecked()
        self.flasher_debug = self.debug_checkbox.isChecked()
        com_port = self.com_port.currentText()

        self.update_thread = TestConnectionThread(com_port, None, simulation, self.flasher_debug)
        self.start_thread()

    def start_update(self):
        firmware_file = self.file_path.text()
        if not firmware_file:
            self.update_status("Please select a firmware file!")
            return

        simulation = self.simulation_checkbox.isChecked()
        self.flasher_debug = self.debug_checkbox.isChecked()
        com_port = self.com_port.currentText()

        self.update_thread = FirmwareUpdateThread(com_port, firmware_file, simulation, self.flasher_debug)
        self.start_thread()

    def start_thread(self):
        self.update_thread.progress_signal.connect(self.update_progress)
        self.update_thread.debug_signal.connect(self.debug_log)
        self.update_thread.status_signal.connect(self.update_status)
        self.update_thread.exception_signal.connect(self.exception_messagebox)
        self.log_output.clear()
        self.update_thread.start()

        self.test_button.setEnabled(False)
        self.start_button.setEnabled(False)

    def update_progress(self, value):
        self.progress_bar.setValue(value)
        if value == 100:
            self.test_button.setEnabled(True)
            self.start_button.setEnabled(True)

    def update_status(self, message):
        if self.flasher_debug:
            self.status_bar.showMessage(message, 2000)
        else:
            self.log_output.append(message)

    def debug_log(self, message):
        self.log_output.append(message)

    def exception_messagebox(self, thread_signal: list):
        error_type = thread_signal[0]
        message = thread_signal[1]

        error_dialog = QMessageBox(self)
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setWindowTitle(f"{self.window_name} - {error_type} Error")
        error_dialog.setText(message)
        error_dialog.exec()
        self.test_button.setEnabled(True)
        self.start_button.setEnabled(True)

    def disclaimer_messagebox(self):
        messagebox = QMessageBox(self)
        messagebox.setIcon(QMessageBox.Warning)
        messagebox.setWindowTitle(f"{self.window_name} - Disclaimer")
        messagebox.setText("Use of this tool is entirely at your own risk, as it is provided as-is without any "
                           "guarantees or warranties. By using this tool, you agree not to use it for any commercial "
                           "purposes, including but not limited to selling, distributing, or integrating it into any "
                           "product or service intended for monetary gain.")
        messagebox.exec()

    def check_update(self):
        try:
            update_details = check_update()
        except requests.exceptions.RequestException as e:
            messagebox = QMessageBox(self)
            messagebox.setIcon(QMessageBox.Critical)
            messagebox.setWindowTitle(f"{self.window_name} - Updater Error")
            messagebox.setText(f"Failed to check the availability of program updates!\n{e}")
            messagebox.exec()
            return

        if not update_details:
            return

        new_version = update_details["tag_name"]
        url_download = update_details["html_url"]

        messagebox = QMessageBox(self)
        messagebox.setIcon(QMessageBox.Question)
        messagebox.setWindowTitle(f"{self.window_name} - Update Available")
        messagebox.setText(f"There is an BWFlasher {new_version} update available! Would you like to download it now?")
        messagebox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        x = messagebox.exec()
        if x == QMessageBox.StandardButton.Yes:
            webbrowser.open(url_download)
            sys.exit(0)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FirmwareUpdateGUI()
    window.show()
    sys.exit(app.exec())
