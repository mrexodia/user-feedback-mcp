import json
import os
import subprocess
import threading
from typing import Optional
from pydantic import BaseModel
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QTextEdit, QFrame,
    QGroupBox
)
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QTextCursor

class FeedbackResult(BaseModel):
    user_feedback: str
    logs: str

class FeedbackConfig(BaseModel):
    run_command: str
    execute_automatically: bool = False

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

        self.setWindowTitle("User Feedback")
        self.setFixedSize(600, 800)

        # Center the window
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - 600) // 2
        y = (screen.height() - 800) // 2
        self.setGeometry(x, y, 600, 800)

        self._create_ui()

        if self.config.execute_automatically:
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
            json.dump(self.config.dict(), f, indent=2)

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
        self.command_entry.setText(self.config.run_command)
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
        self.auto_check.setChecked(self.config.execute_automatically)
        self.auto_check.stateChanged.connect(self._update_config)

        save_button = QPushButton("Save Configuration")
        save_button.clicked.connect(self._save_config)

        auto_layout.addWidget(self.auto_check)
        auto_layout.addStretch()
        auto_layout.addWidget(save_button)
        layout.addWidget(auto_frame)

        # Log output
        log_group = QGroupBox("Output")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group)

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
        self.config.run_command = self.command_entry.text()
        self.config.execute_automatically = self.auto_check.isChecked()

    def _append_log(self, text: str):
        self.log_buffer.append(text)
        self.log_text.append(text)
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)

    def _run_command(self):
        if self.process:
            self.process.terminate()
            self.process = None
            self.run_button.setText("Run")
            return

        command = self.command_entry.text()
        if not command:
            self._append_log("Please enter a command to run\n")
            return

        self.log_text.clear()
        self.log_buffer = []
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

            def read_output(pipe, prefix=""):
                for line in iter(pipe.readline, ''):
                    line_with_prefix = f"{prefix}{line}"
                    self.log_signals.append_log.emit(line_with_prefix)

            threading.Thread(
                target=read_output,
                args=(self.process.stdout,),
                daemon=True
            ).start()

            threading.Thread(
                target=read_output,
                args=(self.process.stderr, "ERROR: "),
                daemon=True
            ).start()

        except Exception as e:
            self._append_log(f"Error running command: {str(e)}\n")
            self.run_button.setText("Run")

    def _submit_feedback(self):
        self.feedback_result = FeedbackResult(
            user_feedback=self.feedback_text.toPlainText().strip(),
            logs="".join(self.log_buffer)
        )
        self.close()

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
    print(f"\nFeedback received: {result.user_feedback}")
    print(f"\nLogs collected: \n{result.logs}")
