import os
from datetime import datetime
from pathlib import Path

import pytest
from PIL import Image
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QPushButton, QComboBox, QLineEdit
from samplr.desktop_ui import SamplrUI

@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

@pytest.fixture
def window(qtbot, qapp):
    """Create and show the main window."""
    window = SamplrUI()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    return window

def test_window_title(window):
    """Test that the window title is correct."""
    assert window.windowTitle() == "Samplr - Image Sequence Sampler"

def test_source_directory_picker(window, qtbot):
    """Test that the source directory picker button exists and is clickable."""
    src_btn = window.findChild(QPushButton, "src_browse_btn")
    assert src_btn is not None
    assert src_btn.isVisible()
    qtbot.mouseClick(src_btn, Qt.MouseButton.LeftButton)

def test_destination_directory_picker(window, qtbot):
    """Test that the destination directory picker button exists and is clickable."""
    dst_btn = window.findChild(QPushButton, "dst_browse_btn")
    assert dst_btn is not None
    assert dst_btn.isVisible()
    qtbot.mouseClick(dst_btn, Qt.MouseButton.LeftButton)

def test_sampling_method_selection(window, qtbot):
    """Test that the sampling method combo box works."""
    combo = window.findChild(QComboBox, "method_combo")
    assert combo is not None
    assert combo.isVisible()
    
    # Test selecting each method
    for method in ["Every Nth Image", "Closest to Time Each Day", "Every Nth Image in Time Range"]:
        combo.setCurrentText(method)
        assert combo.currentText() == method

def test_nth_edit_accepts_large_values(window):
    """N can be any positive integer, not limited to two digits."""
    nth_edit = window.findChild(QLineEdit, "nth_edit")
    assert nth_edit is not None
    nth_edit.setText("12345")
    assert window._parse_nth() == 12345


def test_nth_edit_rejects_invalid_values(window):
    """Invalid N values are rejected."""
    nth_edit = window.findChild(QLineEdit, "nth_edit")
    nth_edit.setText("0")
    assert window._parse_nth() is None
    nth_edit.setText("abc")
    assert window._parse_nth() is None


def test_run_sampler_with_invalid_source(window, qtbot):
    """Test error handling with invalid source directory."""
    window.src_edit.setText("/nonexistent/path")
    window.dst_edit.setText("/tmp/also-nonexistent")

    run_btn = window.findChild(QPushButton, "run_btn")
    assert run_btn is not None
    assert run_btn.isVisible()
    qtbot.mouseClick(run_btn, Qt.MouseButton.LeftButton)

    qtbot.waitUntil(lambda: "Error" in window.status_label.text(), timeout=1000)
    assert "Error" in window.status_label.text()


def test_run_sampler_rejects_same_source_and_destination(window, qtbot, tmp_path):
    """Sampling must not run when source and destination are the same."""
    shared_dir = tmp_path / "photos"
    shared_dir.mkdir()
    Image.new("RGB", (10, 10)).save(shared_dir / "CO_001.jpg")

    window.src_edit.setText(str(shared_dir))
    window.dst_edit.setText(str(shared_dir))

    run_btn = window.findChild(QPushButton, "run_btn")
    qtbot.mouseClick(run_btn, Qt.MouseButton.LeftButton)

    qtbot.waitUntil(lambda: "Error" in window.status_label.text(), timeout=1000)
    assert "different directories" in window.status_label.text()
    assert len(list(shared_dir.glob("SM_*.jpg"))) == 0


def test_run_sampler_via_button_click(window, qtbot, tmp_path):
    """Run sampling through the Run button (clicked signal passes a bool)."""
    source_dir = tmp_path / "source"
    dest_dir = tmp_path / "dest"
    source_dir.mkdir()
    dest_dir.mkdir()
    for i in range(5):
        img_path = source_dir / f"CO_{i:03d}.jpg"
        Image.new("RGB", (10, 10)).save(img_path)
        timestamp = datetime(2024, 1, 1, 9 + i, 0, 0).timestamp()
        os.utime(img_path, (timestamp, timestamp))

    window.src_edit.setText(str(source_dir))
    window.dst_edit.setText(str(dest_dir))

    run_btn = window.findChild(QPushButton, "run_btn")
    qtbot.mouseClick(run_btn, Qt.MouseButton.LeftButton)

    qtbot.waitUntil(
        lambda: "Copied" in window.status_label.text() or "Error" in window.status_label.text(),
        timeout=5000,
    )
    assert "Copied" in window.status_label.text()
    assert len(list(dest_dir.glob("*.jpg"))) > 0


def test_run_sampler_closest_to_time(window, qtbot, tmp_path):
    """Run sampling with Closest to Time method (widgets must stay alive)."""
    source_dir = tmp_path / "source"
    dest_dir = tmp_path / "dest"
    source_dir.mkdir()
    dest_dir.mkdir()
    for i in range(5):
        img_path = source_dir / f"CO_{i:03d}.jpg"
        Image.new("RGB", (10, 10)).save(img_path)
        timestamp = datetime(2024, 1, 1, 9 + i, 0, 0).timestamp()
        os.utime(img_path, (timestamp, timestamp))

    window.src_edit.setText(str(source_dir))
    window.dst_edit.setText(str(dest_dir))
    window.method_combo.setCurrentText("Closest to Time Each Day")
    qtbot.wait(100)

    run_btn = window.findChild(QPushButton, "run_btn")
    qtbot.mouseClick(run_btn, Qt.MouseButton.LeftButton)

    qtbot.waitUntil(
        lambda: "Copied" in window.status_label.text() or "Error" in window.status_label.text(),
        timeout=5000,
    )
    assert "Copied" in window.status_label.text()