import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QPushButton, QComboBox
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

def test_run_sampler_with_invalid_source(window, qtbot):
    """Test error handling with invalid source directory."""
    # Set an invalid source directory
    window.src_edit.setText("/nonexistent/path")
    
    # Click the run button
    run_btn = window.findChild(QPushButton, "run_btn")
    assert run_btn is not None
    assert run_btn.isVisible()
    qtbot.mouseClick(run_btn, Qt.MouseButton.LeftButton)
    
    # Wait for the error message
    qtbot.waitUntil(lambda: "Error" in window.status_label.text(), timeout=1000)
    assert "Error" in window.status_label.text() 