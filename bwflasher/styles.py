#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BW Flasher - Modern Dark Theme
# Copyright (C) 2024-2025 ScooterTeam
#

DARK_THEME_STYLESHEET = """
/* Professional 'Terminal' Theme for BWFlasher */
QWidget {
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', 'Monaco', monospace;
    font-size: 9pt;
    color: #e6e6e6;
    font-weight: 400;
}

/* Main Window */
QWidget#mainWindow {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #0d1117, stop:0.3 #161b22, stop:0.7 #21262d, stop:1 #30363d);
    border: none;
}

/* Application Title */
QLabel#titleLabel {
    font-size: 14px;
    font-weight: 600;
    color: #0ea5e9;
    padding: 12px 16px;
    background: rgba(14, 165, 233, 0.08);
    border-radius: 4px;
    margin: 8px;
    border: 1px solid rgba(14, 165, 233, 0.15);
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', 'Monaco', monospace;
    line-height: 1.2;
}

/* Specific widget styling */
QComboBox#serialCombo {
    min-width: 200px;
}

QLineEdit#filePath {
    min-width: 300px;
}

QPushButton#browseButton {
    min-width: 80px;
}

QPushButton#testButton, QPushButton#startButton {
    min-width: 140px;
    font-size: 11pt;
}

QProgressBar#progressBar {
    min-height: 30px;
    font-size: 11pt;
}

QTextEdit#logOutput {
    min-height: 200px;
    font-size: 9pt;
}

/* Input Fields */
QLineEdit, QComboBox {
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 6px 10px;
    background: #0d1117;
    color: #e6e6e6;
    font-size: 9pt;
    font-weight: 400;
    selection-background-color: #58a6ff;
}

QLineEdit:focus, QComboBox:focus {
    border: 1px solid #0ea5e9;
    background: #161b22;
}

QLineEdit::placeholder {
    color: #7d8590;
    font-style: normal;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 4px solid #0ea5e9;
    margin-right: 4px;
}

QComboBox QAbstractItemView {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 4px;
    selection-background-color: #0ea5e9;
    color: #e6e6e6;
    outline: none;
}

/* Buttons */
QPushButton {
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 8px 16px;
    background: #21262d;
    color: #e6e6e6;
    font-weight: 500;
    font-size: 9pt;
    min-width: 100px;
    min-height: 28px;
}

QPushButton:hover {
    background: #30363d;
    border: 1px solid #0ea5e9;
    color: #0ea5e9;
}

QPushButton:pressed {
    background: #0d1117;
    border: 1px solid #58a6ff;
    color: #58a6ff;
}

QPushButton:disabled {
    background: #161b22;
    color: #7d8590;
    border: 1px solid #21262d;
}

/* Progress Bar */
QProgressBar {
    border: 1px solid #30363d;
    border-radius: 2px;
    text-align: center;
    background: #0d1117;
    color: #ffffff;
    font-weight: 600;
    font-size: 9pt;
    min-height: 16px;
}

QProgressBar::chunk {
    background: #0ea5e9;
    border-radius: 1px;
    margin: 1px;
}

/* Text Edit (Log Output) */
QTextEdit {
    border: 1px solid #30363d;
    border-radius: 4px;
    background: #0d1117;
    color: #e6e6e6;
    padding: 8px;
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', 'Monaco', monospace;
    font-size: 8pt;
    font-weight: 400;
    line-height: 1.3;
}

QTextEdit:focus {
    border: 1px solid #0ea5e9;
}

/* Checkboxes */
QCheckBox {
    spacing: 8px;
    color: #e6e6e6;
    font-size: 9pt;
    font-weight: 400;
}

QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #30363d;
    border-radius: 2px;
    background: #0d1117;
}

QCheckBox::indicator:checked {
    background: #0ea5e9;
    border: 1px solid #0ea5e9;
}

QCheckBox::indicator:hover {
    border: 1px solid #0ea5e9;
    background: #161b22;
}

/* Status Bar */
QStatusBar {
    border-top: 1px solid #30363d;
    background: #0d1117;
    color: #7d8590;
    font-size: 8pt;
    font-weight: 400;
    padding: 4px;
}

/* Labels */
QLabel {
    color: #e6e6e6;
    font-size: 9pt;
    font-weight: 400;
}

/* Scrollbars */
QScrollBar:vertical {
    background: #0d1117;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #30363d;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #0ea5e9;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Tooltips */
QToolTip {
    background: #0d1117;
    border: 1px solid #1f6feb;
    border-radius: 4px;
    color: #e6e6e6;
    padding: 6px;
    font-size: 8pt;
    font-weight: 400;
}

/* Message Boxes */
QMessageBox {
    background: #0d1117;
    color: #e6e6e6;
}

QMessageBox QPushButton {
    min-width: 80px;
    min-height: 24px;
}

/* Checkbox glow when checked */
QCheckBox#simulationCheck:checked, QCheckBox#debugCheck:checked {
    color: #0ea5e9;
}
"""

# Color palette for the application
COLOR_PALETTE = {
    'primary': '#0ea5e9',       # Fresh sky blue
    'primary_dark': '#0284c7',  # Darker sky blue
    'primary_light': '#38bdf8', # Lighter sky blue
    'background': '#0d1117',    # GitHub dark
    'surface': '#161b22',       # Surface color
    'text': '#e6e6e6',          # Light grey text
    'text_secondary': '#7d8590', # Muted text
    'border': '#30363d',        # Border color
    'error': '#f85149',         # Error color
    'success': '#3fb950',       # Success color
    'warning': '#d29922',       # Warning color
    'accent': '#0ea5e9'         # Sky blue accent
} 