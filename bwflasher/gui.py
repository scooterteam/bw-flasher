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
from PySide6.QtGui import QPalette, QIcon, QColor
from PySide6.QtCore import Qt, QThread, Signal, QUrl, QTimer
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from bwflasher.flash_uart import DFU, FlasherException
from bwflasher.updater import check_update, get_name
from bwflasher.styles import DARK_THEME_STYLESHEET, COLOR_PALETTE

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
        prefix = "/dev/ttyUSB" if OS == "Linux" else "/dev/tty.usb"
        return [port[0] for port in ports if port[0].startswith(prefix)] if ports else []


class BaseThread(QThread):
    progress_signal = Signal(int)
    status_signal = Signal(str)
    debug_signal = Signal(str)
    exception_signal = Signal(list)

    def __init__(self, com_port, firmware_file, simulation, debug, parent=None):
        super().__init__(parent)
        self.com_port = com_port
        self.firmware_file = firmware_file
        self.simulation = simulation
        self.debug = debug

    def update_progress(self, value):
        self.progress_signal.emit(value)

    def log_debug(self, message):
        self.debug_signal.emit(message)

    def show_status(self, message):
        self.status_signal.emit(message)


class FirmwareUpdateThread(BaseThread):
    def __init__(self, com_port, firmware_file, simulation, debug, parent=None):
        super().__init__(com_port, firmware_file, simulation, debug, parent)

    def run(self):
        try:
            updater = DFU(
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
    def __init__(self, com_port, firmware_file, simulation, debug, parent=None):
        super().__init__(com_port, firmware_file, simulation, debug, parent)

    def run(self):
        try:
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

        self.heading_text = "╔══════════════════════════════════════════════════════════════╗\n║                    Brightway Flasher v0.5.2                    ║\n║                        by ScooterTeam                          ║\n╚══════════════════════════════════════════════════════════════╝"
        self.heading_label = QLabel(self.heading_text, self)
        self.heading_label.setAlignment(Qt.AlignCenter)
        self.heading_label.setObjectName("titleLabel")
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
        layout_h.addWidget(self.file_path, 1)
        self.browse_button = QPushButton("Browse")
        self.browse_button.setObjectName("browseButton")
        self.browse_button.clicked.connect(self.browse_file)
        layout_h.addWidget(self.browse_button)
        layout.addLayout(layout_h)

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

        # Set up the media player
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        # Set the file path for the tune
        file_url = QUrl.fromLocalFile(resource_path("chiptune.mp3"))
        self.player.setSource(file_url)

        # Play the audio
        self.player.play()

        # Set static banner (no animation)
        self.heading_label.setText(self.heading_text)

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
