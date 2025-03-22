import json
import os
import subprocess
import threading
from datetime import datetime
from typing import Optional, TypedDict
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QTextEdit, QFrame,
    QGroupBox, QDialog
)
from PySide6.QtCore import Qt, Signal, QObject, QTimer
from PySide6.QtGui import QTextCursor, QIcon

class FeedbackResult(TypedDict):
    user_feedback: str
    logs: str

class FeedbackConfig(TypedDict):
    run_command: str
    execute_automatically: bool = False

class ConsoleDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Console")
        self.setModal(False)
        self.resize(600, 400)
        self.setWindowIcon(QIcon("icons/terminal.png"))

        layout = QVBoxLayout(self)

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        # Clear button
        button_layout = QHBoxLayout()
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_logs)
        button_layout.addStretch()
        button_layout.addWidget(self.clear_button)
        layout.addLayout(button_layout)

    def append_log(self, text: str):
        self.log_text.append(text.rstrip())
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)

    def clear_logs(self):
        self.log_text.clear()

    def closeEvent(self, event):
        event.ignore()
        self.hide()

class LogSignals(QObject):
    append_log = Signal(str)

class FeedbackUI(QMainWindow):
    def __init__(self, project_directory: str, prompt: str):
        super().__init__()
        self.project_directory = project_directory
        self.prompt = prompt
        self.config_path = os.path.join(project_directory, '.user-feedback.json')
        self.config = self._load_config()

        self.process: Optional[subprocess.Popen] = None
        self.log_buffer = []
        self.feedback_result = None
        self.log_signals = LogSignals()
        self.log_signals.append_log.connect(self._append_log)

        # Create console dialog
        self.console = ConsoleDialog(self)

        self.setWindowTitle("User Feedback")
        self.setFixedSize(600, 500)  # Reduced height since logs moved to console
        self.setWindowIcon(QIcon("icons/feedback.png"))

        # Center the window
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - 600) // 2
        y = (screen.height() - 500) // 2
        self.setGeometry(x, y, 600, 500)

        self._create_ui()

        if self.config.get("execute_automatically", False):
            self._run_command()

    def _load_config(self) -> FeedbackConfig:
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return FeedbackConfig(**json.load(f))
        except Exception:
            pass
        return FeedbackConfig(run_command="", execute_automatically=False)

    def _save_config(self):
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
        print("Config saved!")

    def _create_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Command frame
        command_frame = QFrame()
        command_layout = QHBoxLayout(command_frame)
        command_layout.setContentsMargins(5, 5, 5, 5)

        command_label = QLabel("Command:")
        self.command_entry = QLineEdit()
        self.command_entry.setText(self.config["run_command"])
        self.command_entry.returnPressed.connect(self._run_command)
        self.command_entry.textChanged.connect(self._update_config)
        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self._run_command)

        command_layout.addWidget(command_label)
        command_layout.addWidget(self.command_entry)
        command_layout.addWidget(self.run_button)
        layout.addWidget(command_frame)

        # Auto-execute frame
        auto_frame = QFrame()
        auto_layout = QHBoxLayout(auto_frame)
        auto_layout.setContentsMargins(5, 0, 5, 5)

        self.auto_check = QCheckBox("Execute automatically")
        self.auto_check.setChecked(self.config.get("execute_automatically", False))
        self.auto_check.stateChanged.connect(self._update_config)

        save_button = QPushButton("Save Configuration")
        save_button.clicked.connect(self._save_config)

        auto_layout.addWidget(self.auto_check)
        auto_layout.addStretch()
        auto_layout.addWidget(save_button)
        layout.addWidget(auto_frame)

        # Feedback section
        feedback_group = QGroupBox("Feedback")
        feedback_layout = QVBoxLayout(feedback_group)

        prompt_label = QLabel(self.prompt)
        self.feedback_text = QTextEdit()
        submit_button = QPushButton("Submit Feedback")
        submit_button.clicked.connect(self._submit_feedback)

        feedback_layout.addWidget(prompt_label)
        feedback_layout.addWidget(self.feedback_text)
        feedback_layout.addWidget(submit_button)
        layout.addWidget(feedback_group)

    def _update_config(self):
        self.config = {
            "run_command": self.command_entry.text(),
            "execute_automatically": self.auto_check.isChecked()
        }

    def _append_log(self, text: str):
        self.log_buffer.append(text)
        self.console.append_log(text)

    def _check_process_status(self):
        if self.process and self.process.poll() is not None:
            # Process has terminated
            self.run_button.setText("Run")
            self.process = None
            self.activateWindow()
            self.feedback_text.setFocus()

    def _run_command(self):
        if self.process:
            self.process.terminate()
            self.process = None
            self.run_button.setText("Run")
            return

        command = self.command_entry.text()
        if not command:
            self.console.append_log("Please enter a command to run\n")
            return

        if not self.console.isVisible():
            self.console.show()

        self.console.append_log(f"$ {command}\n")
        self.run_button.setText("Stop")

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
                for line in iter(pipe.readline, ''):
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
            self.console.append_log(f"Error running command: {str(e)}\n")
            self.run_button.setText("&Run")

    def _submit_feedback(self):
        self.feedback_result = FeedbackResult(
            user_feedback=self.feedback_text.toPlainText().strip(),
            logs="".join(self.log_buffer)
        )
        self.close()

    def closeEvent(self, event):
        if self.console:
            self.console.close()
        super().closeEvent(event)

    def run(self) -> FeedbackResult:
        self.show()
        QApplication.instance().exec()

        if self.process:
            self.process.terminate()

        if not self.feedback_result:
            return FeedbackResult(user_feedback="", logs="".join(self.log_buffer))

        return self.feedback_result

def feedback_ui(project_directory: str, prompt: str) -> FeedbackResult:
    app = QApplication.instance() or QApplication([])
    ui = FeedbackUI(project_directory, prompt)
    return ui.run()

if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Run the feedback UI")
    parser.add_argument("--prompt", default="Give your feedback", help="The prompt to show to the user")
    args = parser.parse_args()

    result = feedback_ui(os.getcwd(), args.prompt)
    print(f"\nFeedback received: {result['user_feedback']}")
    print(f"\nLogs collected: \n{result['logs']}")
