"""
truth_table.py - Truth table dialog window
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QTableWidget,
                              QTableWidgetItem, QLabel, QPushButton,
                              QHeaderView, QHBoxLayout)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont


class TruthTableDialog(QDialog):
    def __init__(self, in_labels, out_labels, rows, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Truth Table")
        self.setMinimumSize(600, 400)
        self.setStyleSheet("""
            QDialog { background: #1a1a2e; color: #e0e0e0; }
            QLabel { color: #b0bec5; font-family: Consolas; }
            QTableWidget { background: #16213e; gridline-color: #2d3561;
                           color: #e0e0e0; font-family: Consolas; font-size: 13px;
                           selection-background-color: #0f3460; border: none; }
            QHeaderView::section { background: #0f3460; color: #4fc3f7;
                                   padding: 6px; border: 1px solid #2d3561;
                                   font-weight: bold; font-family: Consolas; }
            QPushButton { background: #0f3460; color: #4fc3f7; border: 1px solid #4fc3f7;
                          padding: 8px 20px; border-radius: 4px; font-family: Consolas; }
            QPushButton:hover { background: #4fc3f7; color: #0d0d1a; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Title
        title = QLabel("⊕  Truth Table Generator")
        title.setFont(QFont("Consolas", 14, QFont.Bold))
        title.setStyleSheet("color: #4fc3f7; padding: 8px 0;")
        layout.addWidget(title)

        info = QLabel(f"Inputs: {', '.join(in_labels)}   |   Outputs: {', '.join(out_labels)}")
        layout.addWidget(info)

        # Table
        all_cols = in_labels + out_labels
        self.table = QTableWidget(len(rows), len(all_cols))
        self.table.setHorizontalHeaderLabels(all_cols)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(self.table.styleSheet() +
            "QTableWidget { alternate-background-color: #1e2a4a; }")

        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                if c >= len(in_labels):
                    # Output columns
                    fg = QColor("#ffeb3b") if val else QColor("#ef5350")
                    item.setForeground(fg)
                    item.setFont(QFont("Consolas", 12, QFont.Bold))
                else:
                    item.setForeground(QColor("#81c784") if val else QColor("#90a4ae"))
                self.table.setItem(r, c, item)

        layout.addWidget(self.table)

        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
