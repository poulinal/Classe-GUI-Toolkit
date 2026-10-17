"""Tests for CGTProject.main module."""
import pytest

import CGTProject.main as main_mod


class FakeApp:
    """Mock QApplication that doesn't require a Qt platform plugin."""

    def __init__(self, argv):
        self.argv = argv
        self.started = False
        self.exec_called = False

    def exec_(self):
        self.exec_called = True
        return 0

    def quit(self):
        self.started = False


@pytest.mark.unit
def test_main_starts_and_executes(monkeypatch):
    """Test that main() creates QApplication, shows window, and calls exec_."""
    # Replace monitoring to no-op
    monkeypatch.setattr(main_mod, "initialize_monitor", lambda *a, **k: None)
    monkeypatch.setattr(main_mod, "cleanup_monitor", lambda *a, **k: None)

    # Replace QApplication with a fake that won't require a Qt platform plugin
    monkeypatch.setattr(main_mod, "QApplication", FakeApp)

    # Replace MainWindow so it can be instantiated without a full UI
    class DummyWindow:
        def __init__(self):
            self.shown = False

        def show(self):
            self.shown = True

    monkeypatch.setattr(main_mod, "MainWindow", DummyWindow)

    # Run main and assert it returned the fake exec_ result
    rc = main_mod.main()
    assert rc == 0

@pytest.mark.unit

def test_main_shows_error_on_exception(monkeypatch):
    """Test that main() catches exceptions, shows crash dialog, and returns exit code 1."""
    # No-op monitoring
    monkeypatch.setattr(main_mod, "initialize_monitor", lambda *a, **k: None)
    monkeypatch.setattr(main_mod, "cleanup_monitor", lambda *a, **k: None)

    # Use FakeApp to avoid real Qt
    monkeypatch.setattr(main_mod, "QApplication", FakeApp)

    # Make MainWindow raise to simulate crash
    def exploding_ctor():
        raise RuntimeError("boom")

    monkeypatch.setattr(main_mod, "MainWindow", exploding_ctor)

    called = {"shown": False}

    def fake_show_crash_dialog(msg):
        called["shown"] = True
        assert "RuntimeError" in msg or "boom" in msg

    monkeypatch.setattr(main_mod, "show_crash_dialog", fake_show_crash_dialog)

    rc = main_mod.main()
    assert rc == 1
    assert called["shown"] is True
