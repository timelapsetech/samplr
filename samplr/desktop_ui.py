import sys
from pathlib import Path
from datetime import time, datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFileDialog, QComboBox, QSpinBox, QTimeEdit, QMessageBox
)
from PyQt6.QtCore import Qt
from samplr.core import ImageSampler

class SamplrUI(QWidget):
    def __init__(self):
        super().__init__()
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

        # Method options
        self.nth_spin = QSpinBox()
        self.nth_spin.setMinimum(1)
        self.nth_spin.setValue(5)
        self.target_time_edit = QTimeEdit()
        self.target_time_edit.setTime(datetime.strptime("14:30", "%H:%M").time())
        self.start_time_edit = QTimeEdit()
        self.start_time_edit.setTime(datetime.strptime("09:00", "%H:%M").time())
        self.end_time_edit = QTimeEdit()
        self.end_time_edit.setTime(datetime.strptime("17:00", "%H:%M").time())

        self.method_options_layout = QVBoxLayout()
        layout.addLayout(self.method_options_layout)
        self.update_method_options()

        # Run button
        self.run_btn = QPushButton("Run Samplr")
        self.run_btn.setObjectName("run_btn")
        self.run_btn.clicked.connect(self.run_sampler)
        layout.addWidget(self.run_btn)

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

    def update_method_options(self):
        # Clear previous widgets
        while self.method_options_layout.count():
            item = self.method_options_layout.takeAt(0)
            widget = item.widget()
            if widget and widget not in [self.nth_spin, self.target_time_edit, self.start_time_edit, self.end_time_edit]:
                widget.deleteLater()
            elif widget:
                widget.setParent(None)
        method = self.method_combo.currentText()
        if method == "Every Nth Image":
            self.method_options_layout.addWidget(QLabel("Sample every Nth image:"))
            self.method_options_layout.addWidget(self.nth_spin)
        elif method == "Closest to Time Each Day":
            self.method_options_layout.addWidget(QLabel("Target Time (24h):"))
            self.method_options_layout.addWidget(self.target_time_edit)
        elif method == "Every Nth Image in Time Range":
            self.method_options_layout.addWidget(QLabel("Sample every Nth image:"))
            self.method_options_layout.addWidget(self.nth_spin)
            hbox = QHBoxLayout()
            hbox.addWidget(QLabel("Start Time (24h):"))
            hbox.addWidget(self.start_time_edit)
            hbox.addWidget(QLabel("End Time (24h):"))
            hbox.addWidget(self.end_time_edit)
            self.method_options_layout.addLayout(hbox)

    def run_sampler(self):
        src = Path(self.src_edit.text())
        dst = Path(self.dst_edit.text())
        base_name = self.base_edit.text().strip() or None
        method = self.method_combo.currentText()
        try:
            if not src.exists() or not src.is_dir():
                raise ValueError(f"Source directory does not exist: {src}")
            dst.mkdir(parents=True, exist_ok=True)
            sampler = ImageSampler(src, dst, base_name=base_name)
            if method == "Every Nth Image":
                selected = sampler.sample_every_nth(self.nth_spin.value())
            elif method == "Closest to Time Each Day":
                t = self.target_time_edit.time()
                selected = sampler.sample_closest_to_time(time(t.hour(), t.minute()))
            elif method == "Every Nth Image in Time Range":
                n = self.nth_spin.value()
                start = self.start_time_edit.time()
                end = self.end_time_edit.time()
                selected = sampler.sample_every_nth_in_time_range(n, time(start.hour(), start.minute()), time(end.hour(), end.minute()))
            else:
                selected = []
            sampler.copy_and_rename(selected)
            self.status_label.setText(f"<b>Copied {len(selected)} images to {dst}</b>")
            if len(selected) > 0:
                sample_files = list(dst.glob("*"))[:5]
                msg = "<br>Sample of output files:<br>" + "<br>".join(f.name for f in sample_files)
                self.status_label.setText(self.status_label.text() + msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.status_label.setText(f"<span style='color:red'>Error: {e}</span>")

def main():
    app = QApplication(sys.argv)
    window = SamplrUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 