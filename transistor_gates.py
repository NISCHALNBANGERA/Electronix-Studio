"""
transistor_gates.py - Placeable MOSFET Transistor Switches (NMOS & PMOS)
Allows schematic-level CMOS circuit design (e.g. CMOS inverter, transmission gates).
"""
from PyQt5.QtWidgets import QGraphicsItem
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPainterPath
from gate import GateItem, Pin


class NMOSGate(GateItem):
    """
    N-Channel MOSFET Switch.
    Inputs:
      - Pin 0: G (Gate - control input, top or left)
      - Pin 1: S (Source - data/signal input, bottom)
    Output:
      - Pin 0: D (Drain - data/signal output, right or top)
    Conduction:
      - When G=1 (active high), switch is closed -> D = S.
      - When G=0, switch is open -> D = 0.
    """
    W = 70; H = 64

    def __init__(self, label="NMOS"):
        super().__init__('NMOS', label=label, num_inputs=2)
        self.color_dark = QColor("#0d2a4a")
        self.color_light = QColor("#38bdf8")

    def _build_pins(self):
        self.input_pins = [
            Pin(self, 'input', 0, QPointF(0, -14), "G"),       # Gate
            Pin(self, 'input', 1, QPointF(0, 14), "S"),        # Source
        ]
        self.output_pins = [
            Pin(self, 'output', 0, QPointF(self.W + Pin.RADIUS, 0), "D")  # Drain
        ]

    def evaluate(self):
        g = self.input_pins[0].value if len(self.input_pins) > 0 else 0
        s = self.input_pins[1].value if len(self.input_pins) > 1 else 0
        # NMOS conducts when Gate is HIGH
        out_val = s if g == 1 else 0
        if self.output_pins:
            self.output_pins[0].set_value(out_val)
        return out_val

    def _draw_body(self, painter):
        painter.setPen(QPen(self.color_light, 2))
        painter.setBrush(QBrush(self.color_dark))
        # Draw background container
        painter.drawRoundedRect(QRectF(0, -self.H/2, self.W, self.H), 8, 8)

        # Draw IEEE MOSFET schematic lines inside
        p = QPainterPath()
        # Gate line
        p.moveTo(10, -14); p.lineTo(26, -14)
        p.moveTo(26, -20); p.lineTo(26, 20)
        # Channel plate
        p.moveTo(32, -18); p.lineTo(32, 18)
        # Source line
        p.moveTo(32, 14); p.lineTo(10, 14)
        # Drain line
        p.moveTo(32, 0); p.lineTo(self.W - 6, 0)
        # Substrate arrow pointing IN for NMOS
        painter.strokePath(p, QPen(self.color_light, 2))

        # Arrow indicator pointing in towards channel
        arrow = QPainterPath()
        arrow.moveTo(26, 0); arrow.lineTo(32, -4); arrow.lineTo(32, 4); arrow.closeSubpath()
        painter.fillPath(arrow, QBrush(self.color_light))

    def _draw_label(self, painter):
        painter.setFont(QFont("Consolas", 7, QFont.Bold))
        painter.setPen(QColor("#ffffff"))
        painter.drawText(QRectF(0, -self.H/2 + 2, self.W, 14), Qt.AlignCenter, self.label)
        # Pin labels
        painter.setFont(QFont("Consolas", 6))
        painter.setPen(QColor("#94a3b8"))
        painter.drawText(4, -10, 12, 10, Qt.AlignLeft, "G")
        painter.drawText(4, 18, 12, 10, Qt.AlignLeft, "S")
        painter.drawText(self.W - 16, -10, 12, 10, Qt.AlignRight, "D")

    @staticmethod
    def from_dict(d):
        g = NMOSGate(d.get('label', 'NMOS'))
        g.gate_id = d['gate_id']
        g.setPos(d['x'], d['y'])
        return g


class PMOSGate(GateItem):
    """
    P-Channel MOSFET Switch.
    Inputs:
      - Pin 0: G (Gate - active-low control input, inverted circle)
      - Pin 1: S (Source - data/signal input)
    Output:
      - Pin 0: D (Drain - data/signal output)
    Conduction:
      - When G=0 (active low), switch is closed -> D = S.
      - When G=1, switch is open -> D = 0.
    """
    W = 70; H = 64

    def __init__(self, label="PMOS"):
        super().__init__('PMOS', label=label, num_inputs=2)
        self.color_dark = QColor("#3b0764")
        self.color_light = QColor("#c084fc")

    def _build_pins(self):
        self.input_pins = [
            Pin(self, 'input', 0, QPointF(0, -14), "G_bar"),   # Gate active low
            Pin(self, 'input', 1, QPointF(0, 14), "S"),        # Source
        ]
        self.output_pins = [
            Pin(self, 'output', 0, QPointF(self.W + Pin.RADIUS, 0), "D")  # Drain
        ]

    def evaluate(self):
        g = self.input_pins[0].value if len(self.input_pins) > 0 else 0
        s = self.input_pins[1].value if len(self.input_pins) > 1 else 0
        # PMOS conducts when Gate is LOW (0)
        out_val = s if g == 0 else 0
        if self.output_pins:
            self.output_pins[0].set_value(out_val)
        return out_val

    def _draw_body(self, painter):
        painter.setPen(QPen(self.color_light, 2))
        painter.setBrush(QBrush(self.color_dark))
        painter.drawRoundedRect(QRectF(0, -self.H/2, self.W, self.H), 8, 8)

        p = QPainterPath()
        # Gate line with inverting bubble
        p.moveTo(10, -14); p.lineTo(19, -14)
        p.moveTo(26, -20); p.lineTo(26, 20)
        # Channel plate
        p.moveTo(32, -18); p.lineTo(32, 18)
        # Source line
        p.moveTo(32, 14); p.lineTo(10, 14)
        # Drain line
        p.moveTo(32, 0); p.lineTo(self.W - 6, 0)
        painter.strokePath(p, QPen(self.color_light, 2))

        # Inversion bubble on Gate
        painter.setBrush(QBrush(self.color_dark))
        painter.drawEllipse(QRectF(19, -17, 6, 6))

        # Arrow indicator pointing OUT for PMOS
        arrow = QPainterPath()
        arrow.moveTo(32, 0); arrow.lineTo(26, -4); arrow.lineTo(26, 4); arrow.closeSubpath()
        painter.fillPath(arrow, QBrush(self.color_light))

    def _draw_label(self, painter):
        painter.setFont(QFont("Consolas", 7, QFont.Bold))
        painter.setPen(QColor("#ffffff"))
        painter.drawText(QRectF(0, -self.H/2 + 2, self.W, 14), Qt.AlignCenter, self.label)
        painter.setFont(QFont("Consolas", 6))
        painter.setPen(QColor("#94a3b8"))
        painter.drawText(4, -10, 12, 10, Qt.AlignLeft, "G̅")
        painter.drawText(4, 18, 12, 10, Qt.AlignLeft, "S")
        painter.drawText(self.W - 16, -10, 12, 10, Qt.AlignRight, "D")

    @staticmethod
    def from_dict(d):
        g = PMOSGate(d.get('label', 'PMOS'))
        g.gate_id = d['gate_id']
        g.setPos(d['x'], d['y'])
        return g


class PullUpResistor(GateItem):
    """Pull-up resistor providing permanent logic 1 (VDD rail reference)."""
    W = 54; H = 40
    def __init__(self, label="VDD"):
        super().__init__('PULLUP', label=label, num_inputs=0)
        self.color_dark = QColor("#14532d")
        self.color_light = QColor("#4ade80")
    def _build_pins(self):
        self.input_pins = []
        self.output_pins = [Pin(self, 'output', 0, QPointF(self.W + Pin.RADIUS, 0), "1")]
    def evaluate(self):
        if self.output_pins: self.output_pins[0].set_value(1)
        return 1
    def _draw_body(self, painter):
        painter.setPen(QPen(self.color_light, 1.5))
        painter.setBrush(QBrush(self.color_dark))
        painter.drawRoundedRect(QRectF(0, -self.H/2, self.W, self.H), 6, 6)
        painter.setFont(QFont("Consolas", 8, QFont.Bold))
        painter.setPen(QColor("#ffffff"))
        painter.drawText(QRectF(0, -self.H/2, self.W, self.H), Qt.AlignCenter, "▲ VDD\n(1)")
    @staticmethod
    def from_dict(d):
        g = PullUpResistor(d.get('label', 'VDD'))
        g.gate_id = d['gate_id']
        g.setPos(d['x'], d['y'])
        return g


class PullDownResistor(GateItem):
    """Pull-down resistor providing permanent logic 0 (GND rail reference)."""
    W = 54; H = 40
    def __init__(self, label="GND"):
        super().__init__('PULLDOWN', label=label, num_inputs=0)
        self.color_dark = QColor("#1e293b")
        self.color_light = QColor("#94a3b8")
    def _build_pins(self):
        self.input_pins = []
        self.output_pins = [Pin(self, 'output', 0, QPointF(self.W + Pin.RADIUS, 0), "0")]
    def evaluate(self):
        if self.output_pins: self.output_pins[0].set_value(0)
        return 0
    def _draw_body(self, painter):
        painter.setPen(QPen(self.color_light, 1.5))
        painter.setBrush(QBrush(self.color_dark))
        painter.drawRoundedRect(QRectF(0, -self.H/2, self.W, self.H), 6, 6)
        painter.setFont(QFont("Consolas", 8, QFont.Bold))
        painter.setPen(QColor("#ffffff"))
        painter.drawText(QRectF(0, -self.H/2, self.W, self.H), Qt.AlignCenter, "▼ GND\n(0)")
    @staticmethod
    def from_dict(d):
        g = PullDownResistor(d.get('label', 'GND'))
        g.gate_id = d['gate_id']
        g.setPos(d['x'], d['y'])
        return g

# Auto-register into gate.GATE_CLASSES
import gate
gate.GATE_CLASSES['NMOS'] = NMOSGate
gate.GATE_CLASSES['PMOS'] = PMOSGate
gate.GATE_CLASSES['PULLUP'] = PullUpResistor
gate.GATE_CLASSES['PULLDOWN'] = PullDownResistor
