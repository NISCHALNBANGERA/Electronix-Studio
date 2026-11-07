"""
expression.py - Boolean expression dialog
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QTextEdit,
                              QLabel, QPushButton, QHBoxLayout, QFrame)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt


class ExpressionDialog(QDialog):
    def __init__(self, expressions, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Boolean Expressions")
        self.setMinimumSize(550, 380)
        self.setStyleSheet("""
            QDialog { background: #1a1a2e; color: #e0e0e0; }
            QLabel { color: #b0bec5; font-family: Consolas; }
            QTextEdit { background: #0d0d1a; color: #4fc3f7; border: 1px solid #2d3561;
                        font-family: Consolas; font-size: 13px; padding: 10px; }
            QPushButton { background: #0f3460; color: #4fc3f7; border: 1px solid #4fc3f7;
                          padding: 8px 20px; border-radius: 4px; font-family: Consolas; }
            QPushButton:hover { background: #4fc3f7; color: #0d0d1a; }
            QFrame { border: 1px solid #2d3561; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("∑  Boolean Expression Generator")
        title.setFont(QFont("Consolas", 13, QFont.Bold))
        title.setStyleSheet("color: #4fc3f7; padding: 8px 0;")
        layout.addWidget(title)

        if not expressions:
            info = QLabel("No outputs found. Add INPUT and OUTPUT nodes to the circuit.")
            info.setStyleSheet("color: #ef5350; padding: 10px;")
            layout.addWidget(info)
        else:
            for out_label, expr in expressions.items():
                frame = QFrame()
                frame_layout = QVBoxLayout(frame)
                frame_layout.setSpacing(4)

                lbl = QLabel(f"Output:  {out_label}")
                lbl.setStyleSheet("color: #ffeb3b; font-weight: bold; font-size: 12px;")
                frame_layout.addWidget(lbl)

                text = QTextEdit()
                text.setPlainText(expr if expr else "Not connected")
                text.setReadOnly(True)
                text.setMaximumHeight(90)
                frame_layout.addWidget(text)

                # Also show the SOP form hint
                note = QLabel("* Parentheses show operator precedence")
                note.setStyleSheet("color: #546e7a; font-size: 10px;")
                frame_layout.addWidget(note)

                layout.addWidget(frame)

        layout.addStretch()
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
