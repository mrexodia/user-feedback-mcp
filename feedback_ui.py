import os
import sys
import json
import argparse
import subprocess
import threading
from typing import Optional, TypedDict

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QTextEdit, QGroupBox
)
from PySide6.QtCore import Qt, Signal, QObject, QTimer, QSettings
from PySide6.QtGui import QTextCursor, QIcon, QKeyEvent, QFont, QFontDatabase, QPalette, QColor

def set_dark_title_bar(widget: QWidget, dark_title_bar: bool) -> None:
    # Ensure we're on Windows
    if sys.platform != "win32":
        return

    from ctypes import windll, c_uint32, byref

    # Get Windows build number
    build_number = sys.getwindowsversion().build
    if build_number < 17763:  # Windows 10 1809 minimum
        return

    # Check if the widget's property already matches the setting
    dark_prop = widget.property("DarkTitleBar")
    if dark_prop is not None and dark_prop == dark_title_bar:
        return

    # Set the property (True if dark_title_bar != 0, False otherwise)
    widget.setProperty("DarkTitleBar", dark_title_bar)

    # Load dwmapi.dll and call DwmSetWindowAttribute
    dwmapi = windll.dwmapi
    hwnd = widget.winId()  # Get the window handle
    attribute = 20 if build_number >= 18985 else 19  # Use newer attribute for newer builds
    c_dark_title_bar = c_uint32(dark_title_bar)  # Convert to C-compatible uint32
    dwmapi.DwmSetWindowAttribute(hwnd, attribute, byref(c_dark_title_bar), 4)

    # HACK: Create a 1x1 pixel frameless window to force redraw
    temp_widget = QWidget(None, Qt.FramelessWindowHint)
    temp_widget.resize(1, 1)
    temp_widget.move(widget.pos())
    temp_widget.show()
    temp_widget.deleteLater()  # Safe deletion in Qt event loop

def get_dark_mode_palette(app: QApplication):
    darkPalette = app.palette()
    darkPalette.setColor(QPalette.Window, QColor(53, 53, 53))
    darkPalette.setColor(QPalette.WindowText, Qt.white)
    darkPalette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(127, 127, 127))
    darkPalette.setColor(QPalette.Base, QColor(42, 42, 42))
    darkPalette.setColor(QPalette.AlternateBase, QColor(66, 66, 66))
    darkPalette.setColor(QPalette.ToolTipBase, QColor(53, 53, 53))
    darkPalette.setColor(QPalette.ToolTipText, Qt.white)
    darkPalette.setColor(QPalette.Text, Qt.white)
    darkPalette.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))
    darkPalette.setColor(QPalette.Dark, QColor(35, 35, 35))
    darkPalette.setColor(QPalette.Shadow, QColor(20, 20, 20))
    darkPalette.setColor(QPalette.Button, QColor(53, 53, 53))
    darkPalette.setColor(QPalette.ButtonText, Qt.white)
    darkPalette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127, 127, 127))
    darkPalette.setColor(QPalette.BrightText, Qt.red)
    darkPalette.setColor(QPalette.Link, QColor(42, 130, 218))
    darkPalette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    darkPalette.setColor(QPalette.Disabled, QPalette.Highlight, QColor(80, 80, 80))
    darkPalette.setColor(QPalette.HighlightedText, Qt.white)
    darkPalette.setColor(QPalette.Disabled, QPalette.HighlightedText, QColor(127, 127, 127))
    return darkPalette

class FeedbackTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Return and event.modifiers() == Qt.ControlModifier:
            # Find the parent FeedbackUI instance and call submit
            parent = self.parent()
            while parent and not isinstance(parent, FeedbackUI):
                parent = parent.parent()
            if parent:
                parent._submit_feedback()
        else:
            super().keyPressEvent(event)

class FeedbackResult(TypedDict):
    logs: str
    user_feedback: str

class FeedbackConfig(TypedDict):
    run_command: str
    execute_automatically: bool = False

class LogSignals(QObject):
    append_log = Signal(str)

class FeedbackUI(QMainWindow):
    def __init__(self, project_directory: str, prompt: str):
        super().__init__()
        self.project_directory = project_directory
        self.prompt = prompt
        self.config_path = os.path.join(project_directory, ".user-feedback.json")
        self.config = self._load_config()

        self.process: Optional[subprocess.Popen] = None
        self.log_buffer = []
        self.feedback_result = None
        self.log_signals = LogSignals()
        self.log_signals.append_log.connect(self._append_log)

        self.setWindowTitle("User Feedback")
        self.setWindowIcon(QIcon("icons/feedback.png"))

        self._create_ui()

        # Restore window geometry
        settings = QSettings("UserFeedback", "MainWindow")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            # Default size and center on screen
            self.resize(800, 600)
            screen = QApplication.primaryScreen().geometry()
            x = (screen.width() - 800) // 2
            y = (screen.height() - 600) // 2
            self.move(x, y)

        # Restore window state
        state = settings.value("windowState")
        if state:
            self.restoreState(state)

        set_dark_title_bar(self, True)

        if self.config.get("execute_automatically", False):
            self._run_command()

    def _load_config(self) -> FeedbackConfig:
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r") as f:
                    return FeedbackConfig(**json.load(f))
        except Exception:
            pass
        return FeedbackConfig(run_command="", execute_automatically=False)

    def _save_config(self):
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)

    def _create_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Command section
        command_group = QGroupBox("Command")
        command_layout = QVBoxLayout(command_group)

        # Command input row
        command_input_layout = QHBoxLayout()
        command_label = QLabel("Command:")
        self.command_entry = QLineEdit()
        self.command_entry.setText(self.config["run_command"])
        self.command_entry.returnPressed.connect(self._run_command)
        self.command_entry.textChanged.connect(self._update_config)
        self.run_button = QPushButton("&Run")
        self.run_button.clicked.connect(self._run_command)

        command_input_layout.addWidget(command_label)
        command_input_layout.addWidget(self.command_entry)
        command_input_layout.addWidget(self.run_button)
        command_layout.addLayout(command_input_layout)

        # Auto-execute and save config row
        auto_layout = QHBoxLayout()
        self.auto_check = QCheckBox("Execute automatically")
        self.auto_check.setChecked(self.config.get("execute_automatically", False))
        self.auto_check.stateChanged.connect(self._update_config)

        save_button = QPushButton("&Save Configuration")
        save_button.clicked.connect(self._save_config)

        auto_layout.addWidget(self.auto_check)
        auto_layout.addStretch()
        auto_layout.addWidget(save_button)
        command_layout.addLayout(auto_layout)

        layout.addWidget(command_group)

        # Feedback section with fixed size
        feedback_group = QGroupBox("Feedback")
        feedback_layout = QVBoxLayout(feedback_group)
        feedback_group.setFixedHeight(150)

        prompt_label = QLabel(self.prompt)
        self.feedback_text = FeedbackTextEdit()
        self.feedback_text.setMinimumHeight(60)
        submit_button = QPushButton("Submit &Feedback (Ctrl+Enter)")
        submit_button.clicked.connect(self._submit_feedback)

        feedback_layout.addWidget(prompt_label)
        feedback_layout.addWidget(self.feedback_text)
        feedback_layout.addWidget(submit_button)

        # Console section (takes remaining space)
        console_group = QGroupBox("Console")
        console_layout = QVBoxLayout(console_group)
        console_group.setMinimumHeight(200)

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        font = QFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        font.setPointSize(9)
        self.log_text.setFont(font)
        console_layout.addWidget(self.log_text)

        # Clear button
        button_layout = QHBoxLayout()
        self.clear_button = QPushButton("&Clear")
        self.clear_button.clicked.connect(self.clear_logs)
        button_layout.addStretch()
        button_layout.addWidget(self.clear_button)
        console_layout.addLayout(button_layout)

        # Add widgets in reverse order (feedback at bottom)
        layout.addWidget(console_group, stretch=1)  # Takes all remaining space
        layout.addWidget(feedback_group)  # Fixed size, no stretch

    def _update_config(self):
        self.config = {
            "run_command": self.command_entry.text(),
            "execute_automatically": self.auto_check.isChecked()
        }

    def _append_log(self, text: str):
        self.log_buffer.append(text)
        self.log_text.append(text.rstrip())
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)

    def _check_process_status(self):
        if self.process and self.process.poll() is not None:
            # Process has terminated
            exit_code = self.process.poll()
            self._append_log(f"\nProcess exited with code {exit_code}\n")
            self.run_button.setText("&Run")
            self.process = None
            self.activateWindow()
            self.feedback_text.setFocus()

    def _run_command(self):
        if self.process:
            self.process.terminate()
            self.process = None
            self.run_button.setText("&Run")
            return

        # Clear the log buffer but keep UI logs visible
        self.log_buffer = []

        command = self.command_entry.text()
        if not command:
            self._append_log("Please enter a command to run\n")
            return

        self._append_log(f"$ {command}\n")
        self.run_button.setText("Sto&p")

        try:
            self.process = subprocess.Popen(
                command,
                shell=True,
                cwd=self.project_directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            def read_output(pipe):
                for line in iter(pipe.readline, ""):
                    self.log_signals.append_log.emit(line)

            threading.Thread(
                target=read_output,
                args=(self.process.stdout,),
                daemon=True
            ).start()

            threading.Thread(
                target=read_output,
                args=(self.process.stderr,),
                daemon=True
            ).start()

            # Start process status checking
            self.status_timer = QTimer()
            self.status_timer.timeout.connect(self._check_process_status)
            self.status_timer.start(100)  # Check every 100ms

        except Exception as e:
            self._append_log(f"Error running command: {str(e)}\n")
            self.run_button.setText("&Run")

    def _submit_feedback(self):
        self.feedback_result = FeedbackResult(
            logs="".join(self.log_buffer),
            user_feedback=self.feedback_text.toPlainText().strip(),
        )
        self.close()

    def clear_logs(self):
        self.log_text.clear()

    def closeEvent(self, event):
        # Save window geometry and state
        settings = QSettings("UserFeedback", "MainWindow")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())

        if self.process:
            self.process.terminate()
        super().closeEvent(event)

    def run(self) -> FeedbackResult:
        self.show()
        QApplication.instance().exec()

        if self.process:
            self.process.terminate()

        if not self.feedback_result:
            return FeedbackResult(logs="".join(self.log_buffer), user_feedback="")

        return self.feedback_result

def feedback_ui(project_directory: str, prompt: str) -> FeedbackResult:
    app = QApplication.instance() or QApplication()
    app.setPalette(get_dark_mode_palette(app))
    app.setStyle("Fusion")
    ui = FeedbackUI(project_directory, prompt)
    return ui.run()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the feedback UI")
    parser.add_argument("--prompt", default="Give your feedback", help="The prompt to show to the user")
    args = parser.parse_args()

    result = feedback_ui(os.getcwd(), args.prompt)
    print(f"\nFeedback received:\n{result['user_feedback']}")
    print(f"\nLogs collected: \n{result['logs']}")
