"""
notes.py - Editable reference / annotation text boxes for the circuit canvas.

Behavior:
  - Drag "NOTE" from the palette (or right-click empty canvas -> Add Note Here)
  - Double-click a note to edit its text in place
  - Click elsewhere (focus-out) to commit the edit
  - Drag to reposition, Delete key / right-click to remove
  - Notes are saved and restored together with the circuit JSON
"""
from PyQt5.QtWidgets import QGraphicsTextItem, QGraphicsItem
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QFont, QColor, QPen, QBrush, QTextCursor, QPainter

DEFAULT_NOTE_TEXT = "Reference note..."
NOTE_WIDTH = 190


class NoteItem(QGraphicsTextItem):
    """A movable, double-click-to-edit sticky-note style annotation."""

    def __init__(self, text=None, note_id=None):
        super().__init__(text if text is not None else DEFAULT_NOTE_TEXT)
        self.note_id = note_id or id(self)
        self.setFont(QFont("Consolas", 9))
        self.setDefaultTextColor(QColor("#ffe9a8"))
        self.setTextWidth(NOTE_WIDTH)
        self.document().setDocumentMargin(10)
        self.setFlags(QGraphicsItem.ItemIsMovable |
                      QGraphicsItem.ItemIsSelectable |
                      QGraphicsItem.ItemSendsGeometryChanges)
        self.setZValue(5)
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.setCursor(Qt.OpenHandCursor)
        self.setToolTip("Double-click to edit this note")

    # ── visuals ───────────────────────────────────────────────────
    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.boundingRect()
        painter.setPen(QPen(QColor("#caa84a"), 1.2))
        painter.setBrush(QBrush(QColor(40, 34, 14, 235)))
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 6, 6)
        # Left accent strip marks it as a note, distinct from gate bodies.
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#ffd54f")))
        painter.drawRoundedRect(QRectF(rect.left(), rect.top(), 4, rect.height()), 2, 2)
        if self.isSelected():
            painter.setPen(QPen(QColor("#4fc3f7"), 1.4, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect.adjusted(1, 1, -1, -1))
        super().paint(painter, option, widget)

    # ── in-place editing ─────────────────────────────────────────
    def mouseDoubleClickEvent(self, e):
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setFocus(Qt.MouseFocusReason)
        cursor = self.textCursor()
        cursor.select(QTextCursor.Document)
        self.setTextCursor(cursor)
        super().mouseDoubleClickEvent(e)

    def focusOutEvent(self, e):
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        cursor = self.textCursor()
        cursor.clearSelection()
        self.setTextCursor(cursor)
        if not self.toPlainText().strip():
            self.setPlainText(DEFAULT_NOTE_TEXT)
        super().focusOutEvent(e)

    # ── persistence ───────────────────────────────────────────────
    def to_dict(self):
        p = self.pos()
        return {'note_id': self.note_id, 'text': self.toPlainText(), 'x': p.x(), 'y': p.y()}

    @staticmethod
    def from_dict(d):
        n = NoteItem(d.get('text', DEFAULT_NOTE_TEXT), d.get('note_id'))
        n.setPos(d.get('x', 0), d.get('y', 0))
        return n
