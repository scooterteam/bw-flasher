#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Flasher
# Copyright (C) 2024 ScooterTeam
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

import sys
import os
import platform
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QProgressBar, QFileDialog, QCheckBox, QTextEdit, QStatusBar, QSpacerItem, QSizePolicy, QComboBox
)
from PySide6.QtGui import QPixmap, QPalette
from PySide6.QtCore import Qt, QThread, Signal, QUrl, QTimer
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from flash_uart import DFU

OS = platform.system()


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class FirmwareUpdateThread(QThread):
    progress_signal = Signal(int)
    status_signal = Signal(str)
    debug_signal = Signal(str)

    def __init__(self, com_port, firmware_file, simulation, debug, parent=None):
        super().__init__(parent)
        self.com_port = com_port
        self.firmware_file = firmware_file
        self.simulation = simulation
        self.debug = debug

    def run(self):
        def update_progress(value):
            self.progress_signal.emit(value)

        def log_debug(message):
            self.debug_signal.emit(message)

        def show_status(message):
            self.status_signal.emit(message)

        updater = DFU(
            tty_port=self.com_port,
            simulation=self.simulation,
            debug=self.debug,
            status_callback=show_status,
            log_callback=log_debug,
            progress_callback=update_progress
        )
        updater.load_file(self.firmware_file)
        updater.run()


class FirmwareUpdateGUI(QWidget):
    def __init__(self):
        super().__init__()

        self.update_thread = None

        self.setWindowTitle("BwFlasher")
        self.setGeometry(100, 100, 400, 300)

        self.setStyleSheet("QWidget { font-family: 'Courier New', monospace; font-size: 12pt; }")

        layout = QVBoxLayout()

        color = self.palette().color(QPalette.Highlight)
        self.heading_text = ".-=* Brightway Flasher by ScooterTeam *=-."
        self.heading_label = QLabel(self.heading_text, self)
        self.heading_label.setAlignment(Qt.AlignCenter)
        #self.heading_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.heading_label.setStyleSheet(f"font-size: 24px; color: {color.name()};")
        layout.addWidget(self.heading_label)

        layout_h = QHBoxLayout()
        self.dev_label = QLabel("Set device:")
        layout_h.addWidget(self.dev_label)
        self.dev_box = QComboBox()
        self.dev_box.addItem("4Pro2nd")
        layout_h.addWidget(self.dev_box)
        layout.addLayout(layout_h)

        layout_h = QHBoxLayout()
        self.com_label = QLabel("Set Serial Port:")
        layout_h.addWidget(self.com_label)
        self.com_port = QLineEdit(
            "COM1" if OS == 'Windows' else "/dev/ttyUSB0"
        )
        layout_h.addWidget(self.com_port)
        layout.addLayout(layout_h)

        layout_h = QHBoxLayout()
        self.file_label = QLabel("Select Firmware File:")
        layout_h.addWidget(self.file_label)
        self.file_path = QLineEdit()
        layout_h.addWidget(self.file_path)
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_file)
        layout_h.addWidget(self.browse_button)
        layout.addLayout(layout_h)

        self.simulation_checkbox = QCheckBox("Simulation Mode")
        layout.addWidget(self.simulation_checkbox)

        self.debug_checkbox = QCheckBox("Debug Mode")
        layout.addWidget(self.debug_checkbox)

        self.start_button = QPushButton("Start Update")
        self.start_button.clicked.connect(self.start_update)
        layout.addWidget(self.start_button)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
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

        # Set up animation
        self.animation_index = 0
        self.animation_dir = 1
        self.animation_frames = []
        self.setup_animation()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(50)  # Adjust to control speed of the animation

    def setup_animation(self):
        for i in range(len(self.heading_text)):
            self.animation_frames += [
                self.heading_text[:i] +
                self.heading_text[i].upper() +
                self.heading_text[i+1:]
            ]

    def update_animation(self):
        # Cycle through the animation frames and update the label
        self.heading_label.setText(self.animation_frames[self.animation_index])
        if self.animation_index == len(self.animation_frames) - 1:
            self.animation_dir = -1
        elif self.animation_index == 0:
            self.animation_dir = 1
        self.animation_index = self.animation_index + self.animation_dir

    def browse_file(self):
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Select Firmware File",
            "",
            "All Files (*);;BIN Files (*.bin)"
        )
        if file:
            self.file_path.setText(file)

    def start_update(self):
        firmware_file = self.file_path.text()
        if not firmware_file:
            self.update_status("Please select a firmware file!")
            return

        simulation = self.simulation_checkbox.isChecked()
        debug = self.debug_checkbox.isChecked()
        com_port = self.com_port.text()

        self.update_thread = FirmwareUpdateThread(com_port, firmware_file, simulation, debug)
        self.update_thread.progress_signal.connect(self.update_progress)
        self.update_thread.debug_signal.connect(self.debug_log)
        self.update_thread.status_signal.connect(self.update_status)
        self.update_thread.start()

        self.start_button.setEnabled(False)

    def update_progress(self, value):
        self.progress_bar.setValue(value)
        if value == 100:
            self.start_button.setEnabled(True)

    def update_status(self, message):
        if self.update_thread.debug:
            self.status_bar.showMessage(message, 2000)
        else:
            self.log_output.append(message)

    def debug_log(self, message):
        self.log_output.append(message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FirmwareUpdateGUI()
    window.show()
    sys.exit(app.exec())
