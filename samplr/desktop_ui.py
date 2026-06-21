import sys
from pathlib import Path
from datetime import time, datetime
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFileDialog, QComboBox, QTimeEdit, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QIcon
from samplr.core import DirectoryValidationError, ImageSampler, validate_sample_directories


def logo_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets" / "samplr_logo.png"
    return Path(__file__).resolve().parent.parent / "assets" / "samplr_logo.png"


def apply_app_icon(app: QApplication, window: QWidget) -> None:
    path = logo_path()
    if not path.is_file():
        return
    icon = QIcon(str(path))
    app.setWindowIcon(icon)
    window.setWindowIcon(icon)


class SamplerWorker(QThread):
    progress = pyqtSignal(int, int, str)
    sampling_complete = pyqtSignal(int, str)
    error = pyqtSignal(str)

    def __init__(
        self,
        src: Path,
        dst: Path,
        base_name: Optional[str],
        method: str,
        nth: int,
        target_time: Optional[time],
        start_time: Optional[time],
        end_time: Optional[time],
    ):
        super().__init__()
        self.src = src
        self.dst = dst
        self.base_name = base_name
        self.method = method
        self.nth = nth
        self.target_time = target_time
        self.start_time = start_time
        self.end_time = end_time

    def run(self):
        try:
            sampler = ImageSampler(
                self.src,
                self.dst,
                base_name=self.base_name,
                progress_callback=self.progress.emit,
            )
            if self.method == "Every Nth Image":
                selected = sampler.sample_every_nth(self.nth)
            elif self.method == "Closest to Time Each Day":
                selected = sampler.sample_closest_to_time(self.target_time)
            elif self.method == "Every Nth Image in Time Range":
                selected = sampler.sample_every_nth_in_time_range(
                    self.nth, self.start_time, self.end_time
                )
            else:
                selected = []
            sampler.copy_and_rename(selected)
            self.sampling_complete.emit(len(selected), str(self.dst))
        except Exception as exc:
            self.error.emit(str(exc))


class SamplrUI(QWidget):
    def __init__(self):
        super().__init__()
        self.worker: Optional[SamplerWorker] = None
        self.setWindowTitle("Samplr - Image Sequence Sampler")
        self.setMinimumWidth(480)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Source directory
        src_layout = QHBoxLayout()
        self.src_edit = QLineEdit()
        src_btn = QPushButton("Browse...")
        src_btn.setObjectName("src_browse_btn")
        src_btn.clicked.connect(self.pick_src)
        src_layout.addWidget(QLabel("Source Directory:"))
        src_layout.addWidget(self.src_edit)
        src_layout.addWidget(src_btn)
        layout.addLayout(src_layout)

        # Destination directory
        dst_layout = QHBoxLayout()
        self.dst_edit = QLineEdit()
        dst_btn = QPushButton("Browse...")
        dst_btn.setObjectName("dst_browse_btn")
        dst_btn.clicked.connect(self.pick_dst)
        dst_layout.addWidget(QLabel("Destination Directory:"))
        dst_layout.addWidget(self.dst_edit)
        dst_layout.addWidget(dst_btn)
        layout.addLayout(dst_layout)

        # Output base name
        base_layout = QHBoxLayout()
        self.base_edit = QLineEdit()
        base_layout.addWidget(QLabel("Output Base Name (optional):"))
        base_layout.addWidget(self.base_edit)
        layout.addLayout(base_layout)

        # Sampling method
        self.method_combo = QComboBox()
        self.method_combo.setObjectName("method_combo")
        self.method_combo.addItems([
            "Every Nth Image",
            "Closest to Time Each Day",
            "Every Nth Image in Time Range"
        ])
        self.method_combo.currentIndexChanged.connect(self.update_method_options)
        layout.addWidget(QLabel("Sampling Method:"))
        layout.addWidget(self.method_combo)

        # Method options (kept alive; visibility toggled per method)
        self.nth_label = QLabel("Sample every Nth image:")
        self.nth_edit = QLineEdit()
        self.nth_edit.setObjectName("nth_edit")
        self.nth_edit.setText("5")
        self.nth_edit.setPlaceholderText("e.g. 5, 100, 1000")

        self.target_time_label = QLabel("Target Time (24h):")
        self.target_time_edit = QTimeEdit()
        self.target_time_edit.setTime(datetime.strptime("14:30", "%H:%M").time())

        self.start_time_label = QLabel("Start Time (24h):")
        self.start_time_edit = QTimeEdit()
        self.start_time_edit.setTime(datetime.strptime("09:00", "%H:%M").time())
        self.end_time_label = QLabel("End Time (24h):")
        self.end_time_edit = QTimeEdit()
        self.end_time_edit.setTime(datetime.strptime("17:00", "%H:%M").time())

        self.method_options_layout = QVBoxLayout()
        self.method_options_layout.addWidget(self.nth_label)
        self.method_options_layout.addWidget(self.nth_edit)
        self.method_options_layout.addWidget(self.target_time_label)
        self.method_options_layout.addWidget(self.target_time_edit)
        time_range_layout = QHBoxLayout()
        time_range_layout.addWidget(self.start_time_label)
        time_range_layout.addWidget(self.start_time_edit)
        time_range_layout.addWidget(self.end_time_label)
        time_range_layout.addWidget(self.end_time_edit)
        self.method_options_layout.addLayout(time_range_layout)
        layout.addLayout(self.method_options_layout)
        self.update_method_options()

        # Run button
        self.run_btn = QPushButton("Run Samplr")
        self.run_btn.setObjectName("run_btn")
        self.run_btn.clicked.connect(self.run_sampler)
        layout.addWidget(self.run_btn)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progress_bar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Progress detail label
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("progress_label")
        self.progress_label.setWordWrap(True)
        self.progress_label.hide()
        layout.addWidget(self.progress_label)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def pick_src(self):
        dir = QFileDialog.getExistingDirectory(self, "Select Source Directory")
        if dir:
            self.src_edit.setText(dir)

    def pick_dst(self):
        dir = QFileDialog.getExistingDirectory(self, "Select Destination Directory")
        if dir:
            self.dst_edit.setText(dir)

    def update_method_options(self, _index=0):
        method = self.method_combo.currentText()
        show_nth = method in ("Every Nth Image", "Every Nth Image in Time Range")
        show_target = method == "Closest to Time Each Day"
        show_range = method == "Every Nth Image in Time Range"

        self.nth_label.setVisible(show_nth)
        self.nth_edit.setVisible(show_nth)
        self.target_time_label.setVisible(show_target)
        self.target_time_edit.setVisible(show_target)
        self.start_time_label.setVisible(show_range)
        self.start_time_edit.setVisible(show_range)
        self.end_time_label.setVisible(show_range)
        self.end_time_edit.setVisible(show_range)

    def _set_running(self, running: bool):
        self.run_btn.setEnabled(not running)
        self.run_btn.setText("Running..." if running else "Run Samplr")
        if running:
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Starting...")
            self.progress_bar.show()
            self.progress_label.setText("")
            self.progress_label.show()
            self.status_label.setText("")
        else:
            self.progress_bar.hide()
            self.progress_label.hide()

    @pyqtSlot(int, int, str)
    def _on_progress(self, current: int, total: int, message: str):
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
            self.progress_bar.setFormat(f"{current} / {total} ({int(current / total * 100)}%)")
        else:
            self.progress_bar.setRange(0, 0)
            self.progress_bar.setFormat(message)
        self.progress_label.setText(message)

    @pyqtSlot(int, str)
    def _on_finished(self, count: int, dst: str):
        self._set_running(False)
        self.status_label.setText(f"<b>Copied {count} images to {dst}</b>")
        if count > 0:
            sample_files = list(Path(dst).glob("*"))[:5]
            msg = "<br>Sample of output files:<br>" + "<br>".join(f.name for f in sample_files)
            self.status_label.setText(self.status_label.text() + msg)
        self.worker = None

    @pyqtSlot(str)
    def _on_error(self, message: str):
        self._set_running(False)
        QMessageBox.critical(self, "Error", message)
        self.status_label.setText(f"<span style='color:red'>Error: {message}</span>")
        self.worker = None

    def _parse_nth(self) -> Optional[int]:
        text = self.nth_edit.text().strip()
        if not text.isdigit():
            return None
        value = int(text)
        if value < 1:
            return None
        return value

    @pyqtSlot(bool)
    def run_sampler(self, checked=False):
        if self.worker is not None and self.worker.isRunning():
            return

        src = Path(self.src_edit.text().strip()).expanduser()
        dst = Path(self.dst_edit.text().strip()).expanduser()
        base_name = self.base_edit.text().strip() or None
        method = self.method_combo.currentText()

        try:
            validate_sample_directories(src, dst)
        except DirectoryValidationError as exc:
            QMessageBox.critical(self, "Error", str(exc))
            self.status_label.setText(f"<span style='color:red'>Error: {exc}</span>")
            return

        try:
            dst.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.critical(self, "Error", str(exc))
            self.status_label.setText(f"<span style='color:red'>Error: {exc}</span>")
            return

        target_time = None
        start_time = None
        end_time = None
        nth = 1
        if method == "Every Nth Image":
            nth = self._parse_nth()
            if nth is None:
                QMessageBox.critical(self, "Error", "Enter a whole number of 1 or greater for N.")
                self.status_label.setText(
                    "<span style='color:red'>Error: Enter a whole number of 1 or greater for N.</span>"
                )
                return
        elif method == "Closest to Time Each Day":
            t = self.target_time_edit.time()
            target_time = time(t.hour(), t.minute())
        elif method == "Every Nth Image in Time Range":
            nth = self._parse_nth()
            if nth is None:
                QMessageBox.critical(self, "Error", "Enter a whole number of 1 or greater for N.")
                self.status_label.setText(
                    "<span style='color:red'>Error: Enter a whole number of 1 or greater for N.</span>"
                )
                return
            start = self.start_time_edit.time()
            end = self.end_time_edit.time()
            start_time = time(start.hour(), start.minute())
            end_time = time(end.hour(), end.minute())

        self._set_running(True)
        self.worker = SamplerWorker(
            src, dst, base_name, method,
            nth, target_time, start_time, end_time,
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.sampling_complete.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()


def main():
    app = QApplication(sys.argv)
    window = SamplrUI()
    apply_app_icon(app, window)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
