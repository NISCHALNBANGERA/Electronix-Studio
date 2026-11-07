"""wire.py - Wire with signal propagation and animation support"""
from PyQt5.QtWidgets import QGraphicsPathItem
from PyQt5.QtCore import QPointF, QTimer
from PyQt5.QtGui import QPen, QColor, QPainterPath

class Wire(QGraphicsPathItem):
    def __init__(self, src_pin, dst_pin):
        super().__init__()
        self.src_pin = src_pin
        self.dst_pin = dst_pin
        self.setZValue(0)
        self.setFlag(self.ItemIsSelectable, True)
        self._value = 0
        self._animating = False
        self._update_pen()
        self.update_path()
        src_pin.wires.append(self)
        dst_pin.wires.append(self)

    def _update_pen(self):
        if self._animating:
            color = QColor("#00e5ff"); width = 4
        elif self._value:
            color = QColor("#ffeb3b"); width = 3
        else:
            color = QColor("#546e7a"); width = 2
        self.setPen(QPen(color, width))

    def update_value(self, v):
        self._value = v
        self._update_pen()
        self.dst_pin.value = v

    def set_animating(self, on):
        self._animating = on
        self._update_pen()

    def update_path(self):
        try:
            p1 = self.src_pin.scene_pos()
            p2 = self.dst_pin.scene_pos()
        except RuntimeError:
            return
        path = QPainterPath(p1)
        dx = max(abs(p2.x()-p1.x())*0.5, 40)
        path.cubicTo(QPointF(p1.x()+dx,p1.y()), QPointF(p2.x()-dx,p2.y()), p2)
        self.setPath(path)

    def remove(self):
        if self in self.src_pin.wires: self.src_pin.wires.remove(self)
        if self in self.dst_pin.wires: self.dst_pin.wires.remove(self)
        if self.scene(): self.scene().removeItem(self)

    def to_dict(self):
        return {
            'src_gate_id': self.src_pin.parent_gate.gate_id,
            'src_pin_idx': self.src_pin.index,
            'dst_gate_id': self.dst_pin.parent_gate.gate_id,
            'dst_pin_idx': self.dst_pin.index,
        }
