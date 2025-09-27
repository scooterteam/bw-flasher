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
import os, sys
import tempfile
import platform
import webbrowser
import requests
from bwpatcher.utils import patch_firmware

from serial.serialutil import SerialException
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QProgressBar, QFileDialog, QCheckBox, QTextEdit, QStatusBar, QComboBox, QMessageBox, QSlider
)
from PySide6.QtGui import QPalette, QIcon, QColor, QCursor, QFont
from PySide6.QtCore import Qt, QThread, Signal, QUrl, QTimer
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from bwflasher.flash_uart import DFU, FlasherException
from bwflasher.updater import check_update, get_name
from bwflasher.styles import DARK_THEME_STYLESHEET, COLOR_PALETTE
from bwflasher.version import __version__

OS = platform.system()


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS  # Temp-Ordner der EXE
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

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
        self.setObjectName("mainWindow")
        self.setStyleSheet(DARK_THEME_STYLESHEET)

        self.check_update()
        self.disclaimer_messagebox()

        self.setGeometry(100, 100, 600, 500)
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        # Banner
        self.heading_text = self.create_banner_text()
        self.heading_label = QLabel(self.heading_text, self)
        self.heading_label.setAlignment(Qt.AlignCenter)
        self.heading_label.setObjectName("titleLabel")
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
        layout.addSpacing(5)  # 20 Pixel vertikal

        # ------------------ Patcher ------------------

        # Scooter model selection
        layout_h = QHBoxLayout()
        layout_h.setSpacing(8)
        self.scooter_label = QLabel("Scooter Model:")
        self.scooter_label.setMinimumWidth(100)
        layout_h.addWidget(self.scooter_label)
        self.scooter_combo = QComboBox()
        self.scooter_combo.addItems(["Mi4Pro2nd", "Mi5", "Mi5Pro", "Mi5Max"])
        self.scooter_combo.setObjectName("scooterCombo")
        layout_h.addWidget(self.scooter_combo)
        layout.addLayout(layout_h)

        # SLS
        self.sls_checkbox = QCheckBox("Speed Limit Sport (SLS)")
        self.sls_checkbox.setObjectName("slsCheck")
        self.sls_checkbox.stateChanged.connect(self.toggle_sls_slider)
        layout.addWidget(self.sls_checkbox)

        layout_h = QHBoxLayout()
        self.sls_label = QLabel("SLS Speed:")
        self.sls_label.setMinimumWidth(100)
        layout_h.addWidget(self.sls_label)

        self.sls_slider = QSlider(Qt.Horizontal)
        self.sls_slider.setMinimum(10)    
        self.sls_slider.setMaximum(395)   
        self.sls_slider.setValue(250)     
        self.sls_slider.valueChanged.connect(self.update_sls_label)
        layout_h.addWidget(self.sls_slider, 1)

        self.sls_value_label = QLabel(f"{self.sls_slider.value()/10:.1f}")
        layout_h.addWidget(self.sls_value_label)
        layout.addLayout(layout_h)
        self.toggle_sls_slider()

        # SLD
        self.sld_checkbox = QCheckBox("Speed Limit Default (SLD)")
        self.sld_checkbox.setObjectName("sldCheck")
        self.sld_checkbox.stateChanged.connect(self.toggle_sld_slider)
        layout.addWidget(self.sld_checkbox)

        layout_h = QHBoxLayout()
        self.sld_label = QLabel("SLD Speed:")
        self.sld_label.setMinimumWidth(100)
        layout_h.addWidget(self.sld_label)

        self.sld_slider = QSlider(Qt.Horizontal)
        self.sld_slider.setMinimum(10)     
        self.sld_slider.setMaximum(395)    
        self.sld_slider.setValue(150)      
        self.sld_slider.valueChanged.connect(self.update_sld_label)
        layout_h.addWidget(self.sld_slider, 1)

        self.sld_value_label = QLabel(f"{self.sld_slider.value()/10:.1f}")
        layout_h.addWidget(self.sld_value_label)
        layout.addLayout(layout_h)
        self.toggle_sld_slider()

        # MSS 
        self.mss_checkbox = QCheckBox("Enable Motor Startspeed (MSS)")
        self.mss_checkbox.setObjectName("mssCheck")
        self.mss_checkbox.stateChanged.connect(self.toggle_mss_slider)
        layout.addWidget(self.mss_checkbox)

        layout_h = QHBoxLayout()
        self.mss_label = QLabel("MSS Speed:")
        self.mss_label.setMinimumWidth(100)
        layout_h.addWidget(self.mss_label)

        self.mss_slider = QSlider(Qt.Horizontal)
        self.mss_slider.setMinimum(10)     
        self.mss_slider.setMaximum(100)    
        self.mss_slider.setValue(60)      
        self.mss_slider.valueChanged.connect(self.update_mss_label)
        layout_h.addWidget(self.mss_slider, 1)

        self.mss_value_label = QLabel(f"{self.mss_slider.value()/10:.1f}")
        layout_h.addWidget(self.mss_value_label)
        layout.addLayout(layout_h)
        self.toggle_mss_slider()

        # CCE
        self.cce_checkbox = QCheckBox("Cruise Controll Enabled (CCE)")
        self.cce_checkbox.setObjectName("cce")
        layout.addWidget(self.cce_checkbox)

        # Load and Patch the Firmware
        self.load_button = QPushButton("Load Firmware")
        self.load_button.clicked.connect(self.patch)
        layout.addWidget(self.load_button)

        layout.addSpacing(10)  

        # Simulation and Debug
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

        # Cursors, animation, music
        self.setup_cursors()
        self.setup_banner_animation()
        self.setup_music()
        
    def patch(self):
        patches = []
        temp_dir = tempfile.gettempdir()
        scooter_model = self.scooter_combo.currentText()  

        model_file_map = {
            "Mi4Pro2nd": "4Pro2ndGen.bin",
            "Mi5": "5.bin",
            "Mi5Max": "5Max.bin",
            "Mi5Pro": "5Pro.bin"
        }

        if scooter_model not in model_file_map:
            print(f"Unknown model: {scooter_model}")
            return

        firmware_path = resource_path(os.path.join("Firmwares", model_file_map[scooter_model]))

        if not os.path.isfile(firmware_path):
            print(f"Firmware file not found: {firmware_path}")
            return
        
        with open(firmware_path, "rb") as f:
            input_firmware = f.read()

        if self.sls_checkbox.isChecked():
            patches.append(f"sls={self.sls_slider.value()/10.0}")
        if self.sld_checkbox.isChecked():
            patches.append(f"sld={self.sld_slider.value()/10.0}")
        if self.mss_checkbox.isChecked():
            patches.append(f"mss={self.mss_slider.value()/10.0}")
        if self.cce_checkbox.isChecked():
            patches.append(f"cce")
        
        if not patches or patches[-1] != "chk":
            patches.append("chk")

        print(f"Loading Firmware for {scooter_model}, Patches: {patches}")

        patched_firmware = patch_firmware(scooter_model, input_firmware, patches)

        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        output_path = os.path.join(temp_dir, "patched_firmware.bin")
        with open(output_path, "wb") as f:
            f.write(patched_firmware)

        print(f"Patched firmware saved to: {output_path}")

    def toggle_sls_slider(self):
        visible = self.sls_checkbox.isChecked()
        self.sls_slider.setVisible(visible)
        self.sls_value_label.setVisible(visible)
        self.sls_label.setVisible(visible)

    def update_sls_label(self):
        value = self.sls_slider.value() / 10.0
        self.sls_value_label.setText(f"{value:.1f}")

    def toggle_sld_slider(self):
        visible = self.sld_checkbox.isChecked()
        self.sld_slider.setVisible(visible)
        self.sld_value_label.setVisible(visible)
        self.sld_label.setVisible(visible)

    def update_sld_label(self):
        value = self.sld_slider.value() / 10.0
        self.sld_value_label.setText(f"{value:.1f}")

    def toggle_mss_slider(self):
        visible = self.mss_checkbox.isChecked()
        self.mss_slider.setVisible(visible)
        self.mss_value_label.setVisible(visible)
        self.mss_label.setVisible(visible)

    def update_mss_label(self):
        value = self.mss_slider.value() / 10.0
        self.mss_value_label.setText(f"{value:.1f}")

    # ------------------- Banner -------------------
    def create_banner_text(self):
        title = f"Brightway Flasher v{__version__}"
        subtitle = "by ScooterTeam"
        total_width = 58
        title_padding = (total_width - 2 - len(title)) // 2
        subtitle_padding = (total_width - 2 - len(subtitle)) // 2
        top_line = "╔" + "═" * (total_width - 2) + "╗"
        title_line = "║" + " " * title_padding + title + " " * (total_width - 2 - title_padding - len(title)) + "║"
        subtitle_line = "║" + " " * subtitle_padding + subtitle + " " * (total_width - 2 - subtitle_padding - len(subtitle)) + "║"
        bottom_line = "╚" + "═" * (total_width - 2) + "╝"
        return f"{top_line}\n{title_line}\n{subtitle_line}\n{bottom_line}"

    def setup_cursors(self):
        self.setCursor(Qt.ArrowCursor)
        self.com_port.setCursor(Qt.IBeamCursor)
        self.log_output.setCursor(Qt.IBeamCursor)
        self.test_button.setCursor(Qt.PointingHandCursor)
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.simulation_checkbox.setCursor(Qt.PointingHandCursor)
        self.debug_checkbox.setCursor(Qt.PointingHandCursor)

    def setup_banner_animation(self):
        self.animation_position = 0
        self.animation_direction = 1
        self.animation_speed = 100
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_banner_animation)
        self.animation_timer.start(self.animation_speed)
        self.update_banner_animation()

    def update_banner_animation(self):
        base_text = self.create_banner_text()
        lines = base_text.split('\n')
        bar_chars = ['█', '▓', '▒', '░', ' ']
        banner_width = 58
        self.animation_position += self.animation_direction
        if self.animation_position >= banner_width - 1:
            self.animation_direction = -1
        elif self.animation_position <= 0:
            self.animation_direction = 1
        animated_lines = []
        for i, line in enumerate(lines):
            if i == 1:
                animated_line = self.create_animated_line(line, self.animation_position, bar_chars)
                animated_lines.append(animated_line)
            else:
                animated_lines.append(line)
        self.heading_label.setText('\n'.join(animated_lines))

    def create_animated_line(self, base_line, position, bar_chars):
        line_chars = list(base_line)
        if 0 <= position < len(line_chars):
            for i, char in enumerate(bar_chars):
                pos = position - i
                if 0 <= pos < len(line_chars) and line_chars[pos] == ' ':
                    line_chars[pos] = char
        return ''.join(line_chars)

    # ------------------- Music -------------------
    def setup_music(self):
        try:
            self.player = QMediaPlayer()
            self.audio_output = QAudioOutput()
            self.player.setAudioOutput(self.audio_output)
            file_url = QUrl.fromLocalFile(resource_path("chiptune.mp3"))
            self.player.setSource(file_url)
            self.player.play()
        except Exception:
            pass

    # ------------------- Connection / Update -------------------
    def test_connection(self):
        simulation = self.simulation_checkbox.isChecked()
        self.flasher_debug = self.debug_checkbox.isChecked()
        com_port = self.com_port.currentText()
        self.update_thread = TestConnectionThread(com_port, None, simulation, self.flasher_debug)
        self.start_thread()

    def start_update(self):
        temp_dir = tempfile.gettempdir()
        firmware_file = os.path.join(temp_dir, "patched_firmware.bin")

        if not os.path.isfile(firmware_file):
            QMessageBox.critical(self, "Fehler", "Please Load a Firmware!")
            return
        
        firmware_file = os.path.join(temp_dir, "patched_firmware.bin")

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
        error_type, message = thread_signal
        error_dialog = QMessageBox(self)
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setWindowTitle(f"{self.window_name} - {error_type} Error")
        error_dialog.setText(message)
        error_dialog.exec()
        self.test_button.setEnabled(True)
        self.start_button.setEnabled(True)

    # ------------------- Disclaimer / Update -------------------
    def disclaimer_messagebox(self):
        messagebox = QMessageBox(self)
        messagebox.setIcon(QMessageBox.Warning)
        messagebox.setWindowTitle(f"{self.window_name} - Disclaimer")
        messagebox.setText(
            "Use of this tool is entirely at your own risk, as it is provided as-is without any "
            "guarantees or warranties. By using this tool, you agree not to use it for any commercial "
            "purposes, including but not limited to selling, distributing, or integrating it into any "
            "product or service intended for monetary gain."
        )
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
