"""Crash dialog display helpers."""

from PyQt5.QtWidgets import QApplication

from .crash_dialog import CrashDialog


def show_crash_dialog(error_message: str) -> None:
    """Display a modal crash dialog as the final user-facing step before exit."""
    app = QApplication.instance()
    created_app = False

    if app is None:
        # If startup fails before QApplication is created, make a temporary one.
        app = QApplication([])
        created_app = True

    dialog = CrashDialog(error_message=error_message)
    dialog.exec_()

    if created_app:
        app.quit()
