"""
project_browser.py - Visual project browser panel with thumbnail previews
"""
from PyQt5.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QFrame, QFileDialog,
    QInputDialog, QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QPixmap
from datetime import datetime
import os
from save_load import list_projects, PROJECTS_DIR, ensure_projects_dir


class ProjectCard(QFrame):
    """A card widget showing project thumbnail + metadata."""
    open_requested = pyqtSignal(str)

    def __init__(self, name, json_path, jpg_path, mtime, parent=None):
        super().__init__(parent)
        self.json_path = json_path
        self.setFixedHeight(130)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QFrame { background:#161b22; border:1px solid #30363d; border-radius:8px; margin:3px; }
            QFrame:hover { border-color:#4fc3f7; background:#1c2333; }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Thumbnail
        thumb_lbl = QLabel()
        thumb_lbl.setFixedSize(140, 88)
        thumb_lbl.setStyleSheet("background:#0d1117; border-radius:4px; border:1px solid #21262d;")
        thumb_lbl.setAlignment(Qt.AlignCenter)
        if os.path.exists(jpg_path):
            px = QPixmap(jpg_path).scaled(140, 88, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            thumb_lbl.setPixmap(px)
        else:
            thumb_lbl.setText("No Preview")
            thumb_lbl.setStyleSheet(thumb_lbl.styleSheet() + "color:#484f58;font-family:Consolas;font-size:10px;")
        layout.addWidget(thumb_lbl)

        # Info
        info = QVBoxLayout()
        info.setSpacing(4)

        name_lbl = QLabel(name)
        name_lbl.setFont(QFont("Consolas", 11, QFont.Bold))
        name_lbl.setStyleSheet("color:#e6edf3; border:none; background:transparent;")
        info.addWidget(name_lbl)

        dt = datetime.fromtimestamp(mtime).strftime("%b %d %Y  %H:%M")
        date_lbl = QLabel(f"📅 {dt}")
        date_lbl.setStyleSheet("color:#8b949e; font-family:Consolas; font-size:10px; border:none; background:transparent;")
        info.addWidget(date_lbl)

        info.addStretch()

        open_btn = QPushButton("▶  Open")
        open_btn.setStyleSheet("""
            QPushButton { background:#1f6feb; color:#fff; border:none; border-radius:4px;
                          padding:6px 14px; font-family:Consolas; font-size:11px; }
            QPushButton:hover { background:#388bfd; }
        """)
        open_btn.clicked.connect(lambda: self.open_requested.emit(self.json_path))
        info.addWidget(open_btn, alignment=Qt.AlignLeft)

        layout.addLayout(info)
        layout.addStretch()

    def mouseDoubleClickEvent(self, e):
        self.open_requested.emit(self.json_path)


class ProjectBrowserPanel(QDockWidget):
    """Dockable project browser with thumbnails."""
    open_project = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("📁 Project Browser", parent)
        self.setMinimumWidth(320)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        container = QWidget()
        container.setStyleSheet("background:#0d1117;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header
        hdr = QLabel("Saved Projects")
        hdr.setFont(QFont("Consolas", 11, QFont.Bold))
        hdr.setStyleSheet("color:#4fc3f7;")
        layout.addWidget(hdr)

        # Refresh + Open buttons
        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("⟳ Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton { background:#21262d; color:#8b949e; border:1px solid #30363d;
                          border-radius:4px; padding:5px 12px; font-family:Consolas; font-size:10px; }
            QPushButton:hover { color:#4fc3f7; border-color:#4fc3f7; }
        """)
        refresh_btn.clicked.connect(self.refresh)
        btn_row.addWidget(refresh_btn)

        browse_btn = QPushButton("📂 Browse...")
        browse_btn.setStyleSheet(refresh_btn.styleSheet())
        browse_btn.clicked.connect(self._browse)
        btn_row.addWidget(browse_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Scroll area for cards
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea{border:none;background:#0d1117;}")

        self.cards_widget = QWidget()
        self.cards_widget.setStyleSheet("background:#0d1117;")
        self.cards_layout = QVBoxLayout(self.cards_widget)
        self.cards_layout.setSpacing(2)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll.setWidget(self.cards_widget)
        layout.addWidget(self.scroll)

        self.setWidget(container)

    def refresh(self):
        # Clear
        for i in reversed(range(self.cards_layout.count())):
            w = self.cards_layout.itemAt(i).widget()
            if w: w.deleteLater()

        projects = list_projects()
        if not projects:
            empty = QLabel("No saved projects yet.\nSave a circuit to see it here.")
            empty.setStyleSheet("color:#484f58; font-family:Consolas; font-size:11px; padding:20px;")
            empty.setAlignment(Qt.AlignCenter)
            self.cards_layout.addWidget(empty)
        else:
            for name, json_path, jpg_path, mtime in projects:
                card = ProjectCard(name, json_path, jpg_path, mtime)
                card.open_requested.connect(self.open_project.emit)
                self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Circuit", PROJECTS_DIR, "Circuit Files (*.json);;All Files (*)")
        if path:
            self.open_project.emit(path)
