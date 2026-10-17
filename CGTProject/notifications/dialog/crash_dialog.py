"""Dialog displayed for fatal application errors."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QTextEdit


class CrashDialog(QDialog):
    """Modal dialog shown when the application encounters an unrecoverable error."""

    def __init__(self, error_message: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Error")
        self.setModal(True)
        self.setMinimumWidth(620)
        self.setMinimumHeight(360)
        self._build_ui(error_message)

    def _build_ui(self, error_message: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("The application encountered a fatal error and needs to close.")
        title.setWordWrap(True)

        subtitle = QLabel("Error details:")

        details = QTextEdit()
        details.setReadOnly(True)
        details.setPlainText(error_message)
        details.setLineWrapMode(QTextEdit.NoWrap)

        close_button = QPushButton("Close")
        close_button.setDefault(True)
        close_button.clicked.connect(self.accept)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(details, stretch=1)
        layout.addWidget(close_button, alignment=Qt.AlignRight)

        self.setStyleSheet(
            """
            QDialog {
                background-color: #1f2937;
                color: #f3f4f6;
                border: 1px solid #374151;
                border-radius: 10px;
            }
            QLabel {
                color: #f3f4f6;
                font-size: 13px;
            }
            QTextEdit {
                background-color: #111827;
                color: #e5e7eb;
                border: 1px solid #374151;
                border-radius: 8px;
                font-family: "DejaVu Sans Mono", "Courier New", monospace;
                font-size: 12px;
                padding: 8px;
            }
            QPushButton {
                background-color: #dc2626;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
                min-width: 100px;
                padding: 8px 14px;
            }
            QPushButton:hover {
                background-color: #b91c1c;
            }
            """
        )
