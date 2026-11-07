"""
gate.py - All gate types.
FIX: ComplexGate base class sets W/H BEFORE any pins are built, so there is
     never a "build pins at wrong size, then rebuild" double-construction —
     that was the root cause of the clustered/overlapping pins on
     MUX/DEMUX/ENCODER/DECODER/BCD7SEG gates.
FIX: Generous, dynamic spacing so pins never crowd even with many I/O lines.
"""
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsEllipseItem,QGraphicsTextItem, QInputDialog
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPainterPath
import math


class Pin(QGraphicsEllipseItem):
    RADIUS = 5
    def __init__(self, parent_gate, pin_type, index, pos, label=""):
        r = self.RADIUS
        super().__init__(-r, -r, 2*r, 2*r, parent_gate)
        self.parent_gate = parent_gate
        self.pin_type = pin_type
        self.index = index
        self.label = label
        self.value = 0
        self.wires = []
        self._editing = False
        self._label_editor = None
        self.setPos(pos)
        self.setZValue(10)
        self._update_style()
        self.setAcceptHoverEvents(True)
        self.setToolTip(f"{label or pin_type}  (double-click to rename)")

    def _update_style(self):
        c = QColor("#4fc3f7") if self.pin_type == 'input' else QColor("#81c784")
        self.setPen(QPen(c, 2))
        self.setBrush(QBrush(QColor(c.red(), c.green(), c.blue(), 80)))

    def set_value(self, v):
        self.value = v
        c = QColor("#ffeb3b") if v else (QColor("#4fc3f7") if self.pin_type=='input' else QColor("#81c784"))
        self.setPen(QPen(c, 2))
        self.setBrush(QBrush(QColor(c.red(), c.green(), c.blue(), 80)))
        for w in self.wires:
            w.update_value(v)

    def scene_pos(self):
        return self.mapToScene(QPointF(0, 0))

    def hoverEnterEvent(self, e): self.setScale(1.4)
    def hoverLeaveEvent(self, e): self.setScale(1.0)

    def mousePressEvent(self, e):
        e.accept()  # always accept so Qt still delivers the doubleclick to us

    def mouseReleaseEvent(self, e):
        s = self.scene()
        if s and hasattr(s, 'pin_clicked'):
            s.pin_clicked(self)
        super().mouseReleaseEvent(e)

    def start_rename(self):
        self.start_label_edit()

    def start_label_edit(self):
        if getattr(self, '_editing', False):
            return
        s = self.scene()
        if s and hasattr(s, '_cancel_temp'):
            s._pending_src = None
            s._cancel_temp()
        self._editing = True
        if self.parent_gate: self.parent_gate.update()
        editor = InlinePinLabelEditor(self.label or self.pin_type, self)
        editor.setDefaultTextColor(QColor("#ffeb3b"))
        editor.setFont(QFont("Consolas", 7, QFont.Bold))
        editor.setTextInteractionFlags(Qt.TextEditorInteraction)
        editor.setZValue(60)
        gh = self.parent_gate.H if self.parent_gate else 0
        if self.pos().y() > gh/2 - 2:
            editor.setPos(-20, 8)
        elif self.pin_type == 'input':
            editor.setPos(8, -10)
        else:
            editor.setPos(-70, -10)
        self._label_editor = editor
        editor.setFocus(Qt.OtherFocusReason)
        cursor = editor.textCursor()
        cursor.select(cursor.Document)
        editor.setTextCursor(cursor)

    def _finish_label_edit(self, text):
        if not getattr(self, '_editing', False):
            return
        self._editing = False
        text = text.strip()
        if text:
            self.label = text
            self.setToolTip(f"{self.label}  (double-click to rename)")
        if getattr(self, '_label_editor', None):
            self._label_editor.setParentItem(None)
            self._label_editor = None
        if self.parent_gate: self.parent_gate.update()

    def _cancel_label_edit(self):
        self._editing = False
        if getattr(self, '_label_editor', None):
            self._label_editor.setParentItem(None)
            self._label_editor = None
        if self.parent_gate: self.parent_gate.update()

    def mouseDoubleClickEvent(self, e):
        self.start_rename()
        e.accept()


class InlineLabelEditor(QGraphicsTextItem):
    """A floating, focusable text item that lets you type a gate's label directly on canvas."""
    def __init__(self, text, gate):
        super().__init__(text, gate)
        self.gate = gate

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.gate._finish_label_edit(self.toPlainText())
            e.accept(); return
        if e.key() == Qt.Key_Escape:
            self.gate._cancel_label_edit()
            e.accept(); return
        super().keyPressEvent(e)

    def focusOutEvent(self, e):
        self.gate._finish_label_edit(self.toPlainText())
        super().focusOutEvent(e)


class InlinePinLabelEditor(QGraphicsTextItem):
    """Inline editable text box for renaming a single pin (I0, S0, A1, Y0, D, etc.)"""
    def __init__(self, text, pin):
        super().__init__(text, pin)
        self.pin = pin

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.pin._finish_label_edit(self.toPlainText())
            e.accept(); return
        if e.key() == Qt.Key_Escape:
            self.pin._cancel_label_edit()
            e.accept(); return
        super().keyPressEvent(e)

    def focusOutEvent(self, e):
        self.pin._finish_label_edit(self.toPlainText())
        super().focusOutEvent(e)

# ── spacing helper ───────────────────────────────────────────────────
MIN_PIN_GAP = 26   # minimum px between two pins on the same edge
VARIABLE_INPUT_TYPES = {'AND', 'OR', 'NAND', 'NOR', 'XOR', 'XNOR'}

CONFIGURABLE_MSI_TYPES = {
    'MUX': (['2:1', '4:1', '8:1', '16:1'], lambda g: f"{getattr(g, 'n_data', 2)}:1"),
    'DEMUX': (['1:2', '1:4', '1:8', '1:16'], lambda g: f"1:{getattr(g, 'n_out', 2)}"),
    'DECODER': (['2:4', '3:8', '4:16'], lambda g: f"{getattr(g, 'n_inputs', 2)}:{getattr(g, 'n_out', 4)}"),
    'ENCODER': (['4:2', '8:3', '16:4'], lambda g: f"{getattr(g, 'n_inputs', 4)}:{getattr(g, 'n_out', 2)}"),
    'PRIORITY_ENC': (['4:2', '8:3', '16:4'], lambda g: f"{getattr(g, 'n_inputs', 4)}:{getattr(g, 'n_out', 2)}"),
}
def _evenly_spaced_y(n, total_h):
    if n <= 0: return []
    if n == 1: return [0.0]
    step = total_h / (n + 1)
    return [step * (i + 1) - total_h / 2 for i in range(n)]

def _height_for_pins(n, min_gap=MIN_PIN_GAP, base=70):
    """Compute a body height that guarantees >= min_gap px between pins."""
    if n <= 1: return base
    needed = min_gap * (n + 1)
    return max(base, needed)

def _restore_pin_labels(gate, d):
    """Apply any user-renamed gate label / pin labels saved in a gate's JSON dict."""
    if 'label' in d and d['label']:
        gate.label = d['label']
    pin_labels = d.get('pin_labels', {})
    for i, pin in enumerate(gate.input_pins):
        key = f"in{i}"
        if key in pin_labels: pin.label = pin_labels[key]
    for i, pin in enumerate(gate.output_pins):
        key = f"out{i}"
        if key in pin_labels: pin.label = pin_labels[key]
    return gate


class GateItem(QGraphicsItem):
    W = 80; H = 60
    GATE_COLORS = {
        'AND':("#1565c0","#42a5f5"), 'OR':("#6a1b9a","#ab47bc"),
        'NOT':("#b71c1c","#ef5350"), 'NAND':("#1b5e20","#66bb6a"),
        'NOR':("#e65100","#ffa726"), 'XOR':("#880e4f","#f06292"),
        'XNOR':("#4a148c","#ce93d8"), 'BUFFER':("#004d40","#4db6ac"),
        'INPUT':("#37474f","#90a4ae"), 'OUTPUT':("#263238","#78909c"),
        'MUX':("#0d47a1","#1e88e5"), 'DEMUX':("#1a237e","#3949ab"),
        'ENCODER':("#004d40","#00897b"), 'DECODER':("#4a0000","#e57373"),
        'PRIORITY_ENC':("#003d33","#26a69a"), 'BCD7SEG':("#4a148c","#9c27b0"),
        'HALF_ADDER':("#3e2723","#a1887f"), 'FULL_ADDER':("#1a237e","#5c6bc0"),
        'CLOCK':("#004d40","#00e676"), 'D_FF':("#01579b","#00b0ff"),
        'JK_FF':("#311b92","#7c4dff"), 'T_FF':("#880e4f","#ff4081"),
        'SR_FF':("#e65100","#ff9100"),
        'RADIX_DISPLAY':("#090d16","#00e5ff"), 'BUS_CONVERTER':("#090d16","#00e5ff"),
        'NMOS':("#0d2a4a","#38bdf8"), 'PMOS':("#3b0764","#c084fc"),
        'PULLUP':("#14532d","#4ade80"), 'PULLDOWN':("#1e293b","#94a3b8"),
    }

    def __init__(self, gate_type, label="", num_inputs=2):
        super().__init__()
        self.gate_type = gate_type
        self.label = label or gate_type
        self.num_inputs = 1 if gate_type in ('NOT','BUFFER') else num_inputs
        self.gate_id = id(self)
        self.glow_active = False
        c = self.GATE_COLORS.get(gate_type, ("#263238","#607d8b"))
        self.color_dark  = QColor(c[0])
        self.color_light = QColor(c[1])
        self.setFlags(QGraphicsItem.ItemIsMovable |
                      QGraphicsItem.ItemIsSelectable |
                      QGraphicsItem.ItemSendsGeometryChanges)
        self.setZValue(1)
        self._build_pins()

    def _build_pins(self):
        self.input_pins = []
        self.output_pins = []
        for i, y in enumerate(_evenly_spaced_y(self.num_inputs, self.H)):
            self.input_pins.append(Pin(self, 'input', i, QPointF(-Pin.RADIUS, y)))
        self.output_pins.append(Pin(self, 'output', 0, QPointF(self.W + Pin.RADIUS, 0)))
    def set_input_count(self, n):
        if self.gate_type not in VARIABLE_INPUT_TYPES:
            return
        n = max(2, min(8, n))
        if n == len(self.input_pins):
            return
        self.prepareGeometryChange()
        s = self.scene()
        old_pins = list(self.input_pins)
        # Disconnect wires and remove pins being eliminated if reducing count
        if n < len(old_pins):
            for pin in old_pins[n:]:
                for w in list(pin.wires):
                    if s and hasattr(s, '_remove_wire'):
                        s._remove_wire(w)
                    else:
                        w.remove()
                pin.setParentItem(None)
                if s:
                    s.removeItem(pin)
            surviving = old_pins[:n]
        else:
            surviving = old_pins

        self.num_inputs = n
        self.H = _height_for_pins(n)
        new_ys = _evenly_spaced_y(n, self.H)

        new_input_pins = []
        for i, y in enumerate(new_ys):
            if i < len(surviving):
                p = surviving[i]
                p.index = i
                p.setPos(-Pin.RADIUS, y)
                for w in p.wires:
                    w.update_path()
                new_input_pins.append(p)
            else:
                p = Pin(self, 'input', i, QPointF(-Pin.RADIUS, y))
                new_input_pins.append(p)
        self.input_pins = new_input_pins

        if self.output_pins:
            self.output_pins[0].setPos(self.W + Pin.RADIUS, 0)
            for w in self.output_pins[0].wires:
                w.update_path()
        self.update()
    def boundingRect(self):
        m = 14
        return QRectF(-m, -self.H/2 - m, self.W + 2*m, self.H + 2*m)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        self._draw_body(painter)
        self._draw_label(painter)
        if self.isSelected():
            painter.setPen(QPen(QColor("#ffeb3b"), 2, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.boundingRect().adjusted(3, 3, -3, -3))
        if self.glow_active:
            painter.setPen(QPen(QColor(self.color_light.red(), self.color_light.green(),
                                       self.color_light.blue(), 160), 5))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(QRectF(-5, -self.H/2-5, self.W+10, self.H+10), 10, 10)

    def _draw_body(self, painter):
        painter.setPen(QPen(self.color_light, 2))
        painter.setBrush(QBrush(self.color_dark))
        painter.drawPath(self._get_shape_path())

    def _get_shape_path(self):
        p = QPainterPath(); p.addRoundedRect(0, -self.H/2, self.W, self.H, 8, 8); return p

    def _draw_label(self, painter):
        if getattr(self, '_editing', False):
            return
        painter.setFont(QFont("Consolas", 8, QFont.Bold))
        painter.setPen(QColor("#ffffff"))
        painter.drawText(QRectF(0, -self.H/2, self.W, self.H), Qt.AlignCenter, self.label)

    def evaluate(self):
        inputs = [p.value for p in self.input_pins]
        result = self._logic(inputs)
        if self.output_pins:
            self.output_pins[0].set_value(result)
        return result

    def _logic(self, inputs):
        if not inputs: return 0
        gt = self.gate_type
        if gt == 'AND':    return int(all(inputs))
        if gt == 'OR':     return int(any(inputs))
        if gt == 'NOT':    return int(not inputs[0])
        if gt == 'NAND':   return int(not all(inputs))
        if gt == 'NOR':    return int(not any(inputs))
        if gt == 'XOR':    return int(sum(inputs) % 2 == 1)
        if gt == 'XNOR':   return int(sum(inputs) % 2 == 0)
        if gt == 'BUFFER': return int(inputs[0])
        return 0

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            for pin in self.input_pins + self.output_pins:
                for w in pin.wires:
                    w.update_path()
        return super().itemChange(change, value)

    def _label_edit_rect(self):
        """Box the inline editor centers itself in. Subclasses override for non-default shapes."""
        return QRectF(0, -self.H/2, self.W, self.H)

    def start_rename(self):
        """Open the inline editable text box over the gate's label. Default rename entry point."""
        self.start_label_edit()

    def start_label_edit(self):
        if getattr(self, '_editing', False):
            return
        s = self.scene()
        if s and hasattr(s, '_cancel_temp'):
            s._pending_src = None
            s._cancel_temp()
        self._editing = True
        self.update()
        editor = InlineLabelEditor(self.label, self)
        editor.setDefaultTextColor(QColor("#ffeb3b"))
        editor.setFont(QFont("Consolas", 8, QFont.Bold))
        editor.setTextInteractionFlags(Qt.TextEditorInteraction)
        editor.setZValue(50)
        rect = self._label_edit_rect()
        br = editor.boundingRect()
        editor.setPos(rect.center().x() - br.width()/2, rect.center().y() - br.height()/2)
        self._label_editor = editor
        editor.setFocus(Qt.OtherFocusReason)
        cursor = editor.textCursor()
        cursor.select(cursor.Document)
        editor.setTextCursor(cursor)

    def _finish_label_edit(self, text):
        if not getattr(self, '_editing', False):
            return
        self._editing = False
        text = text.strip()
        if text:
            self.label = text
        if getattr(self, '_label_editor', None):
            self._label_editor.setParentItem(None)
            self._label_editor = None
        self.update()

    def _cancel_label_edit(self):
        self._editing = False
        if getattr(self, '_label_editor', None):
            self._label_editor.setParentItem(None)
            self._label_editor = None
        self.update()

    def mouseDoubleClickEvent(self, e):
        """Default: double-click renames inline. InputNode overrides this to toggle instead."""
        self.start_rename()
        e.accept()

    def to_dict(self):
        p = self.pos()
        d = {'gate_id':self.gate_id,'gate_type':self.gate_type,
             'label':self.label,'num_inputs':self.num_inputs,'x':p.x(),'y':p.y()}
        # Persist any pin labels the user has renamed away from the default.
        pin_labels = {}
        for kind, pins in (('in', self.input_pins), ('out', self.output_pins)):
            for i, pin in enumerate(pins):
                if pin.label:
                    pin_labels[f"{kind}{i}"] = pin.label
        if pin_labels:
            d['pin_labels'] = pin_labels
        return d

    @staticmethod
    def from_dict(d):
        g = create_gate(d['gate_type'], d.get('label',''))
        g.gate_id = d['gate_id']
        g.setPos(d['x'], d['y'])
        if d['gate_type'] in VARIABLE_INPUT_TYPES and d.get('num_inputs', 2) != len(g.input_pins):
            g.set_input_count(d['num_inputs'])
        pin_labels = d.get('pin_labels', {})
        for i, pin in enumerate(g.input_pins):
            key = f"in{i}"
            if key in pin_labels: pin.label = pin_labels[key]
        for i, pin in enumerate(g.output_pins):
            key = f"out{i}"
            if key in pin_labels: pin.label = pin_labels[key]
        return g


# ── Basic gates ─────────────────────────────────────────────────────
class AndGate(GateItem):
    def __init__(self): super().__init__('AND', num_inputs=2)
    def _get_shape_path(self):
        p=QPainterPath(); p.moveTo(0,-self.H/2); p.lineTo(self.W*.45,-self.H/2)
        p.arcTo(self.W*.45-self.H/2,-self.H/2,self.H,self.H,90,-180)
        p.lineTo(0,self.H/2); p.closeSubpath(); return p

class OrGate(GateItem):
    def __init__(self): super().__init__('OR', num_inputs=2)
    def _get_shape_path(self):
        p=QPainterPath(); p.moveTo(0,-self.H/2)
        p.quadTo(self.W*.35,-self.H/2,self.W,0)
        p.quadTo(self.W*.35,self.H/2,0,self.H/2)
        p.quadTo(self.W*.2,0,0,-self.H/2); return p

class NotGate(GateItem):
    def __init__(self): super().__init__('NOT')
    def _get_shape_path(self):
        p=QPainterPath(); p.moveTo(0,-self.H/2)
        p.lineTo(self.W-12,0); p.lineTo(0,self.H/2); p.closeSubpath(); return p
    def _draw_body(self, painter):
        super()._draw_body(painter); painter.drawEllipse(QRectF(self.W-12,-6,12,12))

class NandGate(GateItem):
    def __init__(self): super().__init__('NAND', num_inputs=2)
    def _get_shape_path(self):
        p=QPainterPath(); p.moveTo(0,-self.H/2); p.lineTo(self.W*.45,-self.H/2)
        p.arcTo(self.W*.45-self.H/2,-self.H/2,self.H,self.H,90,-180)
        p.lineTo(0,self.H/2); p.closeSubpath(); return p
    def _draw_body(self, painter):
        super()._draw_body(painter); painter.drawEllipse(QRectF(self.W-6,-6,12,12))

class NorGate(GateItem):
    def __init__(self): super().__init__('NOR', num_inputs=2)
    def _get_shape_path(self):
        p=QPainterPath(); p.moveTo(0,-self.H/2)
        p.quadTo(self.W*.35,-self.H/2,self.W-12,0)
        p.quadTo(self.W*.35,self.H/2,0,self.H/2)
        p.quadTo(self.W*.2,0,0,-self.H/2); return p
    def _draw_body(self, painter):
        super()._draw_body(painter); painter.drawEllipse(QRectF(self.W-12,-6,12,12))

class XorGate(GateItem):
    def __init__(self): super().__init__('XOR', num_inputs=2)
    def _get_shape_path(self):
        p=QPainterPath(); p.moveTo(8,-self.H/2)
        p.quadTo(self.W*.35,-self.H/2,self.W,0)
        p.quadTo(self.W*.35,self.H/2,8,self.H/2)
        p.quadTo(self.W*.2+8,0,8,-self.H/2); return p
    def _draw_body(self, painter):
        super()._draw_body(painter)
        ex=QPainterPath(); ex.moveTo(0,-self.H/2); ex.quadTo(self.W*.15,0,0,self.H/2)
        painter.setBrush(Qt.NoBrush); painter.drawPath(ex)

class XnorGate(GateItem):
    def __init__(self): super().__init__('XNOR', num_inputs=2)
    def _get_shape_path(self):
        p=QPainterPath(); p.moveTo(8,-self.H/2)
        p.quadTo(self.W*.35,-self.H/2,self.W-12,0)
        p.quadTo(self.W*.35,self.H/2,8,self.H/2)
        p.quadTo(self.W*.2+8,0,8,-self.H/2); return p
    def _draw_body(self, painter):
        super()._draw_body(painter)
        ex=QPainterPath(); ex.moveTo(0,-self.H/2); ex.quadTo(self.W*.15,0,0,self.H/2)
        painter.setBrush(Qt.NoBrush); painter.drawPath(ex)
        painter.setBrush(QBrush(self.color_dark)); painter.drawEllipse(QRectF(self.W-12,-6,12,12))

class BufferGate(GateItem):
    def __init__(self): super().__init__('BUFFER')
    def _get_shape_path(self):
        p=QPainterPath(); p.moveTo(0,-self.H/2)
        p.lineTo(self.W,0); p.lineTo(0,self.H/2); p.closeSubpath(); return p

class InputNode(GateItem):
    def __init__(self, label="IN"):
        super().__init__('INPUT', label=label, num_inputs=0)
        self._value = 0
        self.input_pins = []
        if self.output_pins: self.output_pins[0].setPos(self.W/2 + Pin.RADIUS, 0)
    def _label_edit_rect(self):
        return QRectF(0, -self.H/2, self.W/2, self.H/2)

    def start_rename(self):
        self.start_label_edit()
    def toggle(self):
        self._value = 1 - self._value
        if self.output_pins: self.output_pins[0].set_value(self._value)
        self.update()

    def evaluate(self):
        if self.output_pins: self.output_pins[0].set_value(self._value)
        return self._value

    def _get_shape_path(self):
        p=QPainterPath(); p.addRoundedRect(0,-self.H/2,self.W/2,self.H,6,6); return p

    def _draw_label(self, painter):
        painter.setFont(QFont("Consolas",8,QFont.Bold))
        if getattr(self, '_editing', False):
            painter.setPen(QColor("#90a4ae"))
            painter.drawText(QRectF(0,self.H/4,self.W/2,self.H/4), Qt.AlignCenter,
                             f"{'1' if self._value else '0'}")
            return
        painter.setPen(QColor("#ffeb3b") if self._value else QColor("#90a4ae"))
        painter.drawText(QRectF(0,-self.H/2,self.W/2,self.H), Qt.AlignCenter,
                         f"{self.label}\n{'1' if self._value else '0'}")
    def mouseDoubleClickEvent(self, e): self.toggle(); e.accept()

    def to_dict(self):
        d = super().to_dict(); d['value'] = self._value; return d

    @staticmethod
    def from_dict(d):
        g = InputNode(d.get('label','IN')); g.gate_id = d['gate_id']
        g.setPos(d['x'],d['y']); g._value = d.get('value',0)
        return _restore_pin_labels(g, d)

class OutputNode(GateItem):
    def __init__(self, label="OUT"):
        super().__init__('OUTPUT', label=label, num_inputs=1)
        self.output_pins = []
        if self.input_pins: self.input_pins[0].setPos(-Pin.RADIUS, 0)
    def _label_edit_rect(self):
        return QRectF(0, -self.H/2, self.W/2, self.H/2)

    def start_rename(self):
        self.start_label_edit()    

    def evaluate(self):
        return self.input_pins[0].value if self.input_pins else 0

    def _get_shape_path(self):
        p=QPainterPath(); p.addRoundedRect(0,-self.H/2,self.W/2,self.H,6,6); return p

    def _draw_label(self, painter):
        painter.setFont(QFont("Consolas",8,QFont.Bold))
        v = self.input_pins[0].value if self.input_pins else 0
        if getattr(self, '_editing', False):
            painter.setPen(QColor("#90a4ae"))
            painter.drawText(QRectF(0,self.H/4,self.W/2,self.H/4), Qt.AlignCenter,
                             f"{'1' if v else '0'}")
            return
        painter.setPen(QColor("#ffeb3b") if v else QColor("#90a4ae"))
        painter.drawText(QRectF(0,-self.H/2,self.W/2,self.H), Qt.AlignCenter,
                         f"{self.label}\n{'1' if v else '0'}")
    @staticmethod
    def from_dict(d):
        g = OutputNode(d.get('label','OUT')); g.gate_id = d['gate_id']
        g.setPos(d['x'],d['y'])
        return _restore_pin_labels(g, d)


# ── Complex gate base — fixes the pin-congestion bug ─────────────────
class ComplexGate(GateItem):
    """
    Base for MUX / DEMUX / ENCODER / DECODER / BCD7SEG.

    The old implementation called super().__init__(num_inputs=n) BEFORE
    self.W/self.H were resized, so the base GateItem._build_pins() ran once
    at the WRONG (default 80x60) size, then a second _rebuild_pins() pass
    created a second, correctly-sized set of pins — but the first set was
    never actually removed (it wasn't attached to a scene yet at __init__
    time, so the removeItem() guard silently did nothing). Both sets stayed
    as child items, which is exactly the clustered/overlapping pins you saw.

    Fix: W/H are committed BEFORE any pin is created, and pins are built
    exactly once, by the subclass, after sizing is final.
    """
    BODY_W = 100
    BODY_H = 120

    def __init__(self, gate_type, label):
        self.W = self.BODY_W
        self.H = self.BODY_H
        super().__init__(gate_type, label=label, num_inputs=0)

    def _build_pins(self):
        # Intentionally empty — subclass builds pins after sizing is final.
        self.input_pins = []
        self.output_pins = []

    def _make_input_pins(self, labels):
        ys = _evenly_spaced_y(len(labels), self.H)
        for i, (lbl, y) in enumerate(zip(labels, ys)):
            self.input_pins.append(Pin(self, 'input', i, QPointF(-Pin.RADIUS, y), lbl))

    def _make_output_pins(self, labels):
        ys = _evenly_spaced_y(len(labels), self.H)
        for i, (lbl, y) in enumerate(zip(labels, ys)):
            self.output_pins.append(Pin(self, 'output', i, QPointF(self.W + Pin.RADIUS, y), lbl))

    def _make_select_pins(self, labels):
        """Select lines along the bottom edge, evenly spaced, never overlapping data pins."""
        n = len(labels)
        y = self.H / 2 + Pin.RADIUS
        margin = self.W * 0.18
        usable = self.W - 2 * margin
        step = usable / max(n - 1, 1) if n > 1 else 0
        for i, lbl in enumerate(labels):
            x = margin if n == 1 else margin + step * i
            idx = len(self.input_pins)
            self.input_pins.append(Pin(self, 'input', idx, QPointF(x, y), lbl))

    def _reconfigure_structure(self, data_in_labels, select_labels, out_labels):
        """
        Safely reconfigures input, select, and output pins:
        - Pins whose labels/roles match are preserved and moved to new positions; their wires are retained.
        - Pins that are removed have their wires safely deleted from the scene.
        - New pins are created.
        - Wires on preserved pins have update_path() called.
        """
        self.prepareGeometryChange()
        s = self.scene()
        self.W = self.BODY_W
        self.H = self.BODY_H

        # Target input pins: data pins along left edge, then select pins along bottom edge
        target_inputs = []
        data_ys = _evenly_spaced_y(len(data_in_labels), self.H)
        for lbl, y in zip(data_in_labels, data_ys):
            target_inputs.append((lbl, QPointF(-Pin.RADIUS, y)))

        n_sel = len(select_labels) if select_labels else 0
        if n_sel > 0:
            y_sel = self.H / 2 + Pin.RADIUS
            margin = self.W * 0.18
            usable = self.W - 2 * margin
            step = usable / max(n_sel - 1, 1) if n_sel > 1 else 0
            for i, lbl in enumerate(select_labels):
                x = margin if n_sel == 1 else margin + step * i
                target_inputs.append((lbl, QPointF(x, y_sel)))

        # Target output pins along right edge
        target_outputs = []
        out_ys = _evenly_spaced_y(len(out_labels), self.H)
        for lbl, y in zip(out_labels, out_ys):
            target_outputs.append((lbl, QPointF(self.W + Pin.RADIUS, y)))

        # Match existing input pins (match by label first, then match by index among remaining)
        matched_inputs = set()
        new_input_pins = []
        for idx, (lbl, pos) in enumerate(target_inputs):
            m = None
            for p in self.input_pins:
                if p not in matched_inputs and p.label == lbl:
                    m = p
                    break
            if not m:
                for p in self.input_pins:
                    if p not in matched_inputs and p.index == idx:
                        m = p
                        break
            if m:
                matched_inputs.add(m)
                m.index = idx
                m.label = lbl
                m.setPos(pos)
                for w in m.wires:
                    w.update_path()
                new_input_pins.append(m)
            else:
                p = Pin(self, 'input', idx, pos, lbl)
                new_input_pins.append(p)

        # Disconnect and delete any un-matched old input pins
        for p in self.input_pins:
            if p not in matched_inputs:
                for w in list(p.wires):
                    if s and hasattr(s, '_remove_wire'):
                        s._remove_wire(w)
                    else:
                        w.remove()
                p.setParentItem(None)
                if s:
                    s.removeItem(p)
        self.input_pins = new_input_pins

        # Match existing output pins
        matched_outputs = set()
        new_output_pins = []
        for idx, (lbl, pos) in enumerate(target_outputs):
            m = None
            for p in self.output_pins:
                if p not in matched_outputs and p.label == lbl:
                    m = p
                    break
            if not m:
                for p in self.output_pins:
                    if p not in matched_outputs and p.index == idx:
                        m = p
                        break
            if m:
                matched_outputs.add(m)
                m.index = idx
                m.label = lbl
                m.setPos(pos)
                for w in m.wires:
                    w.update_path()
                new_output_pins.append(m)
            else:
                p = Pin(self, 'output', idx, pos, lbl)
                new_output_pins.append(p)

        for p in self.output_pins:
            if p not in matched_outputs:
                for w in list(p.wires):
                    if s and hasattr(s, '_remove_wire'):
                        s._remove_wire(w)
                    else:
                        w.remove()
                p.setParentItem(None)
                if s:
                    s.removeItem(p)
        self.output_pins = new_output_pins
        self.update()

    def boundingRect(self):
        m = 18
        return QRectF(-m, -self.H/2 - m, self.W + 2*m, self.H + 2*m + 22)

    def _draw_body(self, painter):
        painter.setPen(QPen(self.color_light, 2))
        painter.setBrush(QBrush(self.color_dark))
        painter.drawRoundedRect(QRectF(0, -self.H/2, self.W, self.H), 8, 8)

    def _draw_label(self, painter):
        painter.setFont(QFont("Consolas", 9, QFont.Bold))
        painter.setPen(QColor("#ffffff"))
        painter.drawText(QRectF(0, -self.H/2, self.W, self.H), Qt.AlignCenter, self.label)
        painter.setFont(QFont("Consolas", 6))
        painter.setPen(QColor("#aab4c0"))
        for pin in self.input_pins:
            if getattr(pin, '_editing', False): continue
            px, py = pin.pos().x(), pin.pos().y()
            if py > self.H/2 - 2:
                painter.drawText(int(px)-10, int(py)+9, 24, 12, Qt.AlignCenter, pin.label)
            else:
                painter.drawText(int(px)+9, int(py)-6, 32, 12, Qt.AlignLeft, pin.label)
        for pin in self.output_pins:
            if getattr(pin, '_editing', False): continue
            px, py = pin.pos().x(), pin.pos().y()
            painter.drawText(int(px)-38, int(py)-6, 34, 12, Qt.AlignRight, pin.label)

# ── MUX ───────────────────────────────────────────────────────────────
class MuxGate(ComplexGate):
    ALLOWED_SIZES = ["2:1", "4:1", "8:1", "16:1"]

    def __init__(self, n_data=2):
        self.n_data = n_data
        self.n_sel  = max(1, math.ceil(math.log2(max(n_data, 2))))
        self.BODY_H = _height_for_pins(n_data)
        self.BODY_W = max(95, 24 * (self.n_sel + 2))
        super().__init__('MUX', f'{n_data}:1\nMUX')
        self._make_input_pins([f'I{i}' for i in range(n_data)])
        self._make_select_pins([f'S{i}' for i in range(self.n_sel)])
        self._make_output_pins(['Y'])

    def configure_size(self, size):
        if isinstance(size, str) and ':' in size:
            n_data = int(size.split(':')[0])
        else:
            n_data = int(size)
        if n_data not in (2, 4, 8, 16):
            return
        self.n_data = n_data
        self.n_sel = max(1, math.ceil(math.log2(n_data)))
        self.BODY_H = _height_for_pins(n_data)
        self.BODY_W = max(95, 24 * (self.n_sel + 2))
        self.label = f'{n_data}:1\nMUX'
        self._reconfigure_structure(
            [f'I{i}' for i in range(n_data)],
            [f'S{i}' for i in range(self.n_sel)],
            ['Y']
        )

    def evaluate(self):
        sel = 0
        for i in range(self.n_sel):
            idx = self.n_data + i
            if idx < len(self.input_pins): sel |= (self.input_pins[idx].value << i)
        sel = min(sel, self.n_data - 1)
        result = self.input_pins[sel].value if sel < self.n_data else 0
        if self.output_pins: self.output_pins[0].set_value(result)
        return result

    def to_dict(self):
        d = super().to_dict(); d['n_data'] = self.n_data; return d
    @staticmethod
    def from_dict(d):
        g = MuxGate(d.get('n_data', 2)); g.gate_id = d['gate_id']; g.setPos(d['x'], d['y']); return _restore_pin_labels(g, d)


# ── DEMUX ─────────────────────────────────────────────────────────────
class DemuxGate(ComplexGate):
    ALLOWED_SIZES = ["1:2", "1:4", "1:8", "1:16"]

    def __init__(self, n_out=2):
        self.n_out = n_out
        self.n_sel = max(1, math.ceil(math.log2(max(n_out, 2))))
        self.BODY_H = _height_for_pins(n_out)
        self.BODY_W = max(95, 24 * (self.n_sel + 2))
        super().__init__('DEMUX', f'1:{n_out}\nDEMUX')
        self._make_input_pins(['D'])
        self._make_select_pins([f'S{i}' for i in range(self.n_sel)])
        self._make_output_pins([f'Y{i}' for i in range(n_out)])

    def configure_size(self, size):
        if isinstance(size, str) and ':' in size:
            n_out = int(size.split(':')[-1])
        else:
            n_out = int(size)
        if n_out not in (2, 4, 8, 16):
            return
        self.n_out = n_out
        self.n_sel = max(1, math.ceil(math.log2(n_out)))
        self.BODY_H = _height_for_pins(n_out)
        self.BODY_W = max(95, 24 * (self.n_sel + 2))
        self.label = f'1:{n_out}\nDEMUX'
        self._reconfigure_structure(
            ['D'],
            [f'S{i}' for i in range(self.n_sel)],
            [f'Y{i}' for i in range(n_out)]
        )

    def evaluate(self):
        d_in = self.input_pins[0].value if self.input_pins else 0
        sel = 0
        for i in range(self.n_sel):
            idx = 1 + i
            if idx < len(self.input_pins): sel |= (self.input_pins[idx].value << i)
        sel = min(sel, self.n_out - 1)
        for i, pin in enumerate(self.output_pins):
            pin.set_value(d_in if i == sel else 0)
        return self.output_pins[sel].value if self.output_pins else 0

    def to_dict(self):
        d = super().to_dict(); d['n_out'] = self.n_out; return d
    @staticmethod
    def from_dict(d):
        g = DemuxGate(d.get('n_out', 2)); g.gate_id = d['gate_id']; g.setPos(d['x'], d['y']); return _restore_pin_labels(g, d)


# ── Encoder ───────────────────────────────────────────────────────────
class EncoderGate(ComplexGate):
    ALLOWED_SIZES = ["4:2", "8:3", "16:4"]

    def __init__(self, n_inputs=4):
        self.n_inputs = n_inputs
        self.n_out = max(1, math.ceil(math.log2(max(n_inputs, 2))))
        self.BODY_H = _height_for_pins(max(n_inputs, self.n_out))
        self.BODY_W = 95
        super().__init__('ENCODER', f'{n_inputs}:{self.n_out}\nENC')
        self._make_input_pins([f'I{i}' for i in range(n_inputs)])
        self._make_output_pins([f'A{i}' for i in range(self.n_out)])

    def configure_size(self, size):
        if isinstance(size, str) and ':' in size:
            n_inputs = int(size.split(':')[0])
        else:
            n_inputs = int(size)
        if n_inputs not in (4, 8, 16):
            return
        self.n_inputs = n_inputs
        self.n_out = max(1, math.ceil(math.log2(n_inputs)))
        self.BODY_H = _height_for_pins(max(n_inputs, self.n_out))
        self.BODY_W = 95
        self.label = f'{n_inputs}:{self.n_out}\nENC'
        self._reconfigure_structure(
            [f'I{i}' for i in range(n_inputs)],
            [],
            [f'A{i}' for i in range(self.n_out)]
        )

    def evaluate(self):
        active = -1
        for i, pin in enumerate(self.input_pins):
            if pin.value: active = i
        for i, pin in enumerate(self.output_pins):
            pin.set_value((active >> i) & 1 if active >= 0 else 0)
        return max(active, 0)

    def to_dict(self):
        d = super().to_dict(); d['n_inputs'] = self.n_inputs; return d
    @staticmethod
    def from_dict(d):
        g = EncoderGate(d.get('n_inputs', 4)); g.gate_id = d['gate_id']; g.setPos(d['x'], d['y']); return _restore_pin_labels(g, d)


# ── Priority Encoder ──────────────────────────────────────────────────
class PriorityEncoderGate(ComplexGate):
    ALLOWED_SIZES = ["4:2", "8:3", "16:4"]

    def __init__(self, n_inputs=4):
        self.n_inputs = n_inputs
        self.n_out = max(1, math.ceil(math.log2(max(n_inputs, 2))))
        self.BODY_H = _height_for_pins(max(n_inputs, self.n_out + 1))
        self.BODY_W = 95
        super().__init__('PRIORITY_ENC', f'{n_inputs}:{self.n_out}\nPRI ENC')
        self._make_input_pins([f'I{i}' for i in range(n_inputs)])
        self._make_output_pins([f'A{i}' for i in range(self.n_out)] + ['V'])

    def configure_size(self, size):
        if isinstance(size, str) and ':' in size:
            n_inputs = int(size.split(':')[0])
        else:
            n_inputs = int(size)
        if n_inputs not in (4, 8, 16):
            return
        self.n_inputs = n_inputs
        self.n_out = max(1, math.ceil(math.log2(n_inputs)))
        self.BODY_H = _height_for_pins(max(n_inputs, self.n_out + 1))
        self.BODY_W = 95
        self.label = f'{n_inputs}:{self.n_out}\nPRI ENC'
        self._reconfigure_structure(
            [f'I{i}' for i in range(n_inputs)],
            [],
            [f'A{i}' for i in range(self.n_out)] + ['V']
        )

    def evaluate(self):
        active = -1
        for i, pin in enumerate(self.input_pins):
            if pin.value: active = i
        valid = 1 if active >= 0 else 0
        for i in range(self.n_out):
            v = (active >> i) & 1 if active >= 0 else 0
            if i < len(self.output_pins): self.output_pins[i].set_value(v)
        if self.n_out < len(self.output_pins):
            self.output_pins[self.n_out].set_value(valid)
        return active

    def to_dict(self):
        d = super().to_dict(); d['n_inputs'] = self.n_inputs; return d
    @staticmethod
    def from_dict(d):
        g = PriorityEncoderGate(d.get('n_inputs', 4)); g.gate_id = d['gate_id']; g.setPos(d['x'], d['y']); return _restore_pin_labels(g, d)


# ── Decoder ───────────────────────────────────────────────────────────
class DecoderGate(ComplexGate):
    ALLOWED_SIZES = ["2:4", "3:8", "4:16"]

    def __init__(self, n_inputs=2):
        self.n_inputs = n_inputs
        self.n_out = 2 ** n_inputs
        self.BODY_H = _height_for_pins(max(n_inputs, self.n_out))
        self.BODY_W = 95
        super().__init__('DECODER', f'{n_inputs}:{self.n_out}\nDEC')
        self._make_input_pins([f'A{i}' for i in range(n_inputs)])
        self._make_output_pins([f'Y{i}' for i in range(self.n_out)])

    def configure_size(self, size):
        if isinstance(size, str) and ':' in size:
            n_inputs = int(size.split(':')[0])
        else:
            n_inputs = int(size)
        if n_inputs not in (2, 3, 4):
            return
        self.n_inputs = n_inputs
        self.n_out = 2 ** n_inputs
        self.BODY_H = _height_for_pins(max(n_inputs, self.n_out))
        self.BODY_W = 95
        self.label = f'{n_inputs}:{self.n_out}\nDEC'
        self._reconfigure_structure(
            [f'A{i}' for i in range(n_inputs)],
            [],
            [f'Y{i}' for i in range(self.n_out)]
        )

    def evaluate(self):
        addr = sum(p.value << i for i, p in enumerate(self.input_pins))
        for i, pin in enumerate(self.output_pins):
            pin.set_value(1 if i == addr else 0)
        return addr

    def to_dict(self):
        d = super().to_dict(); d['n_inputs'] = self.n_inputs; return d
    @staticmethod
    def from_dict(d):
        g = DecoderGate(d.get('n_inputs', 2)); g.gate_id = d['gate_id']; g.setPos(d['x'], d['y']); return _restore_pin_labels(g, d)


# ── BCD 7-Segment ─────────────────────────────────────────────────────
class BCD7SegGate(ComplexGate):
    SEG = {0:0b1111110,1:0b0110000,2:0b1101101,3:0b1111001,
           4:0b0110011,5:0b1011011,6:0b1011111,7:0b1110000,
           8:0b1111111,9:0b1111011}

    def __init__(self):
        self.BODY_H = _height_for_pins(7)   # 7 segment outputs is the limiter
        self.BODY_W = 95
        super().__init__('BCD7SEG', 'BCD\n7-SEG')
        self._make_input_pins(['B0','B1','B2','B3'])
        self._make_output_pins(list('abcdefg'))

    def evaluate(self):
        bcd = sum(p.value << i for i, p in enumerate(self.input_pins))
        code = self.SEG.get(bcd & 0xF, 0)
        for i, pin in enumerate(self.output_pins):
            pin.set_value((code >> (6-i)) & 1)
        return code

    @staticmethod
    def from_dict(d):
        g = BCD7SegGate(); g.gate_id = d['gate_id']; g.setPos(d['x'], d['y']); return _restore_pin_labels(g, d)
# ── Half Adder ──────────────────────────────────────────────────────
class HalfAdder(ComplexGate):
    def __init__(self):
        self.BODY_H = _height_for_pins(2)
        self.BODY_W = 90
        super().__init__('HALF_ADDER', 'HALF\nADDER')
        self._make_input_pins(['A', 'B'])
        self._make_output_pins(['S', 'C'])

    def evaluate(self):
        a = self.input_pins[0].value
        b = self.input_pins[1].value
        s = int(a ^ b)
        c = int(a & b)
        self.output_pins[0].set_value(s)
        self.output_pins[1].set_value(c)
        return s

    @staticmethod
    def from_dict(d):
        g = HalfAdder(); g.gate_id = d['gate_id']; g.setPos(d['x'], d['y'])
        return _restore_pin_labels(g, d)


# ── Full Adder ──────────────────────────────────────────────────────
class FullAdder(ComplexGate):
    def __init__(self):
        self.BODY_H = _height_for_pins(3)
        self.BODY_W = 90
        super().__init__('FULL_ADDER', 'FULL\nADDER')
        self._make_input_pins(['A', 'B', 'Cin'])
        self._make_output_pins(['S', 'Cout'])

    def evaluate(self):
        a = self.input_pins[0].value
        b = self.input_pins[1].value
        cin = self.input_pins[2].value
        s = a ^ b ^ cin
        cout = (a & b) | (b & cin) | (a & cin)
        self.output_pins[0].set_value(int(s))
        self.output_pins[1].set_value(int(cout))
        return int(s)

    @staticmethod
    def from_dict(d):
        g = FullAdder(); g.gate_id = d['gate_id']; g.setPos(d['x'], d['y'])
        return _restore_pin_labels(g, d)


# ── Bus Display & Multi-Radix Converter ─────────────────────────────
class RadixDisplayBlock(GateItem):
    """
    Bus Display & Multi-Radix Converter (RadixDisplayBlock / BusConverterNode)
    Accepts parallel multi-bit binary bus lines (2 to 8 bits, e.g. from counter flip-flops),
    combines them into an integer (D = sum(Di * 2^i)),
    and renders a live, glowing digital OLED instrument readout in:
    - Decimal (Unsigned)
    - Hexadecimal
    - Octal
    - Binary (Grouped Bus View)
    - BCD (Binary-Coded Decimal, 4-bit nibbles)
    - Signed Decimal (Two's Complement)
    - All-in-One Dashboard (Dec, Hex, Oct, Bin stacked)
    """
    BODY_W = 168

    COLOR_THEMES = {
        'GREEN': {
            'name': '🟢 Neon Green',
            'accent': '#39ff14',
            'dim': '#0d3813',
            'screen_bg': '#041307',
            'glow': QColor(57, 255, 20, 60),
            'border': '#1b4d24',
        },
        'CYAN': {
            'name': '🔵 Electric Cyan',
            'accent': '#00e5ff',
            'dim': '#0a3345',
            'screen_bg': '#02141c',
            'glow': QColor(0, 229, 255, 60),
            'border': '#12485e',
        },
        'AMBER': {
            'name': '🟠 Lab Amber',
            'accent': '#ffb000',
            'dim': '#3d2800',
            'screen_bg': '#170f02',
            'glow': QColor(255, 176, 0, 60),
            'border': '#593e0b',
        },
        'RED': {
            'name': '🔴 Laser Red',
            'accent': '#ff3333',
            'dim': '#401010',
            'screen_bg': '#1a0505',
            'glow': QColor(255, 51, 51, 60),
            'border': '#591515',
        },
    }

    DISPLAY_MODES = [
        ('DEC', 'Decimal (Unsigned)'),
        ('HEX', 'Hexadecimal (0x..)'),
        ('OCT', 'Octal (0o..)'),
        ('BIN', 'Binary Bus View'),
        ('BCD', 'BCD (Binary-Coded Dec)'),
        ('SIGNED', "Signed Decimal (2's Comp)"),
        ('ALL', 'All-in-One Dashboard'),
    ]

    def __init__(self, bit_width=4, label="BUS DISPLAY", display_mode="DEC", color_theme="GREEN"):
        self.bit_width = max(2, min(16, int(bit_width)))
        self.display_mode = display_mode if display_mode in dict(self.DISPLAY_MODES) else "DEC"
        self.color_theme = color_theme if color_theme in self.COLOR_THEMES else "GREEN"
        self.bus_value = 0
        self.W = self.BODY_W
        self.H = max(110, 24 * (self.bit_width + 1))
        super().__init__('RADIX_DISPLAY', label=label or 'BUS DISPLAY', num_inputs=self.bit_width)

    def _build_pins(self):
        """Construct input pins labeled with clear bit weight markers (D0 LSB, D1, ..., Dn-1 MSB)."""
        self.input_pins = []
        self.output_pins = []
        ys = _evenly_spaced_y(self.bit_width, self.H)
        for i in range(self.bit_width):
            if i == 0:
                lbl = "D0 (LSB)"
            elif i == self.bit_width - 1:
                lbl = f"D{i} (MSB)"
            else:
                lbl = f"D{i}"
            pin = Pin(self, 'input', i, QPointF(-Pin.RADIUS, ys[i]), lbl)
            pin.setToolTip(f"D{i} [Weight: 2^{i} = {1 << i}] (double-click to rename)")
            self.input_pins.append(pin)

    def set_bit_width(self, n):
        """Safely reconfigure bus bit width between 2 and 16 bits while preserving wires."""
        n = max(2, min(16, int(n)))
        if n == self.bit_width and len(self.input_pins) == n:
            return
        self.prepareGeometryChange()
        self.bit_width = n
        self.num_inputs = n
        self.H = max(110, 24 * (n + 1))
        s = self.scene()

        ys = _evenly_spaced_y(n, self.H)
        old_pins = list(self.input_pins)
        new_input_pins = []

        for i in range(n):
            if i == 0:
                default_lbl = "D0 (LSB)"
            elif i == n - 1:
                default_lbl = f"D{i} (MSB)"
            else:
                default_lbl = f"D{i}"
            pos = QPointF(-Pin.RADIUS, ys[i])

            if i < len(old_pins):
                p = old_pins[i]
                p.index = i
                # Update label if using default naming pattern
                if not p.label or p.label.startswith('D'):
                    p.label = default_lbl
                p.setPos(pos)
                p.setToolTip(f"D{i} [Weight: 2^{i} = {1 << i}] (double-click to rename)")
                for w in p.wires:
                    w.update_path()
                new_input_pins.append(p)
            else:
                p = Pin(self, 'input', i, pos, default_lbl)
                p.setToolTip(f"D{i} [Weight: 2^{i} = {1 << i}] (double-click to rename)")
                new_input_pins.append(p)

        # Disconnect and safely remove excess pins and wires
        if len(old_pins) > n:
            for p in old_pins[n:]:
                for w in list(p.wires):
                    if s and hasattr(s, '_remove_wire'):
                        s._remove_wire(w)
                    else:
                        w.remove()
                p.setParentItem(None)
                if s:
                    s.removeItem(p)

        self.input_pins = new_input_pins
        self.evaluate()
        self.update()

    def set_input_count(self, n):
        """Alias for compatibility with canvas context menu actions."""
        self.set_bit_width(n)

    def set_display_mode(self, mode):
        if mode in dict(self.DISPLAY_MODES):
            self.display_mode = mode
            self.update()

    def set_color_theme(self, theme):
        if theme in self.COLOR_THEMES:
            self.color_theme = theme
            self.update()

    def evaluate(self):
        """Read all parallel input lines and compute the integer bus value."""
        val = 0
        for i, pin in enumerate(self.input_pins):
            bit_val = 1 if getattr(pin, 'value', 0) else 0
            val |= (bit_val << i)
        self.bus_value = val
        self.update()
        return val

    def get_formatted_value(self):
        """
        Compute formatted string readout and helper subtitle based on conversion mode:
        1. Decimal (Unsigned): 0 to 2^n - 1
        2. Hexadecimal: 0x0 .. 0xFF
        3. Octal: 0o0 .. 0o377
        4. Binary (Grouped Bus View): [ 0 1 1 0 ]
        5. BCD (Binary-Coded Decimal): 4-bit nibbles (e.g. 12 -> 0001 0010)
        6. Signed Decimal (Two's Complement): -2^(n-1) to +2^(n-1)-1
        7. All-in-One Dashboard: Dec, Hex, Oct, Bin stacked
        """
        val = self.bus_value
        mode = self.display_mode
        n = self.bit_width

        if mode == 'DEC':
            return str(val), f"Range: 0 .. {2**n - 1}"

        elif mode == 'HEX':
            hex_digits = max(1, (n + 3) // 4)
            return f"0x{val:0{hex_digits}X}", f"Hex (0x0 .. 0x{2**n - 1:X})"

        elif mode == 'OCT':
            return f"0o{val:o}", f"Octal (0o0 .. 0o{2**n - 1:o})"

        elif mode == 'BIN':
            b_str = f"{val:0{n}b}"
            groups = []
            for i in range(len(b_str), 0, -4):
                start = max(0, i - 4)
                groups.insert(0, b_str[start:i])
            grouped = " ".join(groups)
            return f"[ {grouped} ]", f"{n}-Bit Bus"

        elif mode == 'BCD':
            dec_str = str(val)
            bcd_parts = [f"{int(d):04b}" for d in dec_str]
            return " ".join(bcd_parts), f"BCD for {val}"

        elif mode == 'SIGNED':
            sign_bit = 1 << (n - 1)
            if val & sign_bit:
                signed_val = val - (1 << n)
            else:
                signed_val = val
            min_v = -(1 << (n - 1))
            max_v = (1 << (n - 1)) - 1
            sign_str = f"{signed_val:+d}" if signed_val > 0 else f"{signed_val}"
            return sign_str, f"2's Comp ({min_v} .. {max_v})"

        elif mode == 'ALL':
            hex_digits = max(1, (n + 3) // 4)
            b_str = f"{val:0{n}b}"
            lines = [
                f"DEC: {val}",
                f"HEX: 0x{val:0{hex_digits}X}",
                f"OCT: 0o{val:o}",
                f"BIN: {b_str}",
            ]
            return "\n".join(lines), "All-in-One"

        return str(val), ""

    def boundingRect(self):
        m = 16
        return QRectF(-m, -self.H/2 - 10, self.W + 2*m, self.H + 20)

    def _get_shape_path(self):
        p = QPainterPath()
        p.addRoundedRect(0, -self.H/2, self.W, self.H, 8, 8)
        return p

    def _label_edit_rect(self):
        return QRectF(12, -self.H/2 + 4, self.W - 60, 16)

    def start_rename(self):
        self.start_label_edit()

    def mouseDoubleClickEvent(self, e):
        """Cycle through multi-radix conversion modes on double-click."""
        modes = [m[0] for m in self.DISPLAY_MODES]
        if self.display_mode in modes:
            curr_idx = modes.index(self.display_mode)
            next_mode = modes[(curr_idx + 1) % len(modes)]
            self.set_display_mode(next_mode)
        e.accept()

    def paint(self, painter, option, widget=None):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        theme = self.COLOR_THEMES.get(self.color_theme, self.COLOR_THEMES['GREEN'])
        accent_col = QColor(theme['accent'])
        dim_col = QColor(theme['dim'])
        screen_bg = QColor(theme['screen_bg'])
        border_col = QColor(theme['border'])

        W = self.W
        H = self.H
        top_y = -H / 2

        # ── 1. Outer Acrylic/Metal Instrument Chassis ───────────────────
        chassis_rect = QRectF(0, top_y, W, H)
        pen_color = QColor("#58a6ff") if self.isSelected() else QColor("#30363d")
        pen_width = 2.0 if self.isSelected() else 1.2
        painter.setPen(QPen(pen_color, pen_width))
        painter.setBrush(QBrush(QColor("#0d1117")))
        painter.drawRoundedRect(chassis_rect, 7.0, 7.0)

        # Chassis corner screws
        screw_pen = QPen(QColor("#484f58"), 1)
        screw_brush = QBrush(QColor("#161b22"))
        painter.setPen(screw_pen)
        painter.setBrush(screw_brush)
        screw_offset = 6
        for sx, sy in [
            (screw_offset, top_y + screw_offset),
            (W - screw_offset, top_y + screw_offset),
            (screw_offset, top_y + H - screw_offset),
            (W - screw_offset, top_y + H - screw_offset)
        ]:
            painter.drawEllipse(QPointF(sx, sy), 2.2, 2.2)
            painter.drawLine(QPointF(sx - 1.2, sy), QPointF(sx + 1.2, sy))
            painter.drawLine(QPointF(sx, sy - 1.2), QPointF(sx, sy + 1.2))

        # ── 2. Top Header Bar (Title & Mode Badge) ───────────────────────
        painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
        painter.setPen(QColor("#8b949e"))
        title_rect = QRectF(12, top_y + 4, W - 60, 14)
        disp_title = self.label if self.label != 'RADIX_DISPLAY' else 'BUS CONVERTER'
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, disp_title)

        # Mode Badge Pill (top right)
        badge_rect = QRectF(W - 46, top_y + 4, 38, 13)
        painter.setPen(QPen(accent_col, 1))
        painter.setBrush(QBrush(QColor(accent_col.red(), accent_col.green(), accent_col.blue(), 30)))
        painter.drawRoundedRect(badge_rect, 3, 3)
        painter.setFont(QFont("Consolas", 6, QFont.Bold))
        painter.setPen(accent_col)
        painter.drawText(badge_rect, Qt.AlignCenter, self.display_mode)

        # ── 3. Pin Weight Column (Left Margin) ──────────────────────────
        painter.setFont(QFont("Consolas", 6, QFont.Bold))
        for i, pin in enumerate(self.input_pins):
            py = pin.pos().y()
            is_high = bool(getattr(pin, 'value', 0))
            lbl_rect = QRectF(4, py - 6, 32, 12)
            if is_high:
                painter.setPen(accent_col)
            else:
                painter.setPen(QColor("#6e7681"))
            painter.drawText(lbl_rect, Qt.AlignLeft | Qt.AlignVCenter, f"D{i}")

        # ── 4. Recessed OLED Screen Area ────────────────────────────────
        screen_x = 36
        screen_y = top_y + 20
        screen_w = W - screen_x - 8
        screen_h = H - 28 - (18 if self.display_mode != 'ALL' else 6)
        screen_rect = QRectF(screen_x, screen_y, screen_w, screen_h)

        # Screen background & outer glow border
        painter.setPen(QPen(border_col, 1.2))
        painter.setBrush(QBrush(screen_bg))
        painter.drawRoundedRect(screen_rect, 4.0, 4.0)

        # Subtle CRT / OLED horizontal scanlines
        painter.setPen(QPen(QColor(accent_col.red(), accent_col.green(), accent_col.blue(), 12), 1))
        scan_y = screen_y + 3
        while scan_y < screen_y + screen_h:
            painter.drawLine(QPointF(screen_x + 2, scan_y), QPointF(screen_x + screen_w - 2, scan_y))
            scan_y += 3

        # ── 5. Value Rendering Inside OLED Screen ────────────────────────
        formatted_val, sub_text = self.get_formatted_value()

        if self.display_mode == 'ALL':
            lines = formatted_val.split('\n')
            painter.setFont(QFont("Consolas", 8, QFont.Bold))
            line_h = screen_h / max(len(lines), 1)
            for idx, line in enumerate(lines):
                l_rect = QRectF(screen_x + 6, screen_y + idx * line_h, screen_w - 12, line_h)
                if line.startswith("DEC:"):
                    painter.setPen(accent_col)
                elif line.startswith("HEX:"):
                    painter.setPen(QColor("#58a6ff"))
                elif line.startswith("OCT:"):
                    painter.setPen(QColor("#e3b341"))
                else:
                    painter.setPen(QColor("#bc8cff"))
                painter.drawText(l_rect, Qt.AlignLeft | Qt.AlignVCenter, line)
        else:
            text_len = len(formatted_val)
            if text_len <= 3:
                font_size = 18
            elif text_len <= 5:
                font_size = 15
            elif text_len <= 8:
                font_size = 12
            elif text_len <= 11:
                font_size = 10
            elif text_len <= 15:
                font_size = 8.5
            elif text_len <= 20:
                font_size = 7.5
            else:
                font_size = 6.5

            val_rect = QRectF(screen_x + 2, screen_y + 2, screen_w - 4, screen_h * 0.65)
            painter.setFont(QFont("Consolas", font_size, QFont.Bold))
            painter.setPen(accent_col)
            painter.drawText(val_rect, Qt.AlignCenter, formatted_val)

            if sub_text:
                sub_rect = QRectF(screen_x + 2, screen_y + screen_h * 0.65, screen_w - 4, screen_h * 0.32)
                painter.setFont(QFont("Segoe UI", 6))
                painter.setPen(QColor("#8b949e"))
                painter.drawText(sub_rect, Qt.AlignCenter, sub_text)

        # ── 6. Live Binary Bit Bus LED Bar (Bottom of Chassis) ──────────
        if self.display_mode != 'ALL':
            bar_y = top_y + H - 16
            bar_h = 10
            total_bar_w = screen_w
            spacing = 2 if self.bit_width <= 8 else 1
            bit_w = max(4.5, min(15.0, (total_bar_w - (self.bit_width - 1) * spacing) / self.bit_width))
            actual_total_w = self.bit_width * bit_w + (self.bit_width - 1) * spacing
            start_bx = screen_x + (total_bar_w - actual_total_w) / 2

            for i in range(self.bit_width):
                bit_idx = self.bit_width - 1 - i
                bit_val = (self.bus_value >> bit_idx) & 1
                bx = start_bx + i * (bit_w + spacing)
                b_rect = QRectF(bx, bar_y, bit_w, bar_h)

                if bit_val:
                    painter.setPen(QPen(accent_col, 1))
                    painter.setBrush(QBrush(accent_col))
                    painter.drawRoundedRect(b_rect, 1.5, 1.5)
                    if bit_w >= 9:
                        painter.setPen(QColor("#000000"))
                        painter.setFont(QFont("Consolas", 6, QFont.Bold))
                        painter.drawText(b_rect, Qt.AlignCenter, "1")
                else:
                    painter.setPen(QPen(QColor("#30363d"), 1))
                    painter.setBrush(QBrush(dim_col))
                    painter.drawRoundedRect(b_rect, 1.5, 1.5)
                    if bit_w >= 9:
                        painter.setPen(QColor("#8b949e"))
                        painter.setFont(QFont("Consolas", 6))
                        painter.drawText(b_rect, Qt.AlignCenter, "0")

        painter.restore()

    def to_dict(self):
        d = super().to_dict()
        d['bit_width'] = self.bit_width
        d['display_mode'] = self.display_mode
        d['color_theme'] = self.color_theme
        return d

    @staticmethod
    def from_dict(d):
        g = RadixDisplayBlock(
            bit_width=d.get('bit_width', d.get('num_inputs', 4)),
            label=d.get('label', 'BUS DISPLAY'),
            display_mode=d.get('display_mode', 'DEC'),
            color_theme=d.get('color_theme', 'GREEN')
        )
        g.gate_id = d['gate_id']
        g.setPos(d['x'], d['y'])
        return _restore_pin_labels(g, d)


# Component Aliases
BusConverterNode = RadixDisplayBlock


# ── Factory ───────────────────────────────────────────────────────────
from sequential_gates import ClockNode, DFlipFlop, JKFlipFlop, TFlipFlop, SRFlipFlop

GATE_CLASSES = {
    'AND':AndGate,'OR':OrGate,'NOT':NotGate,'NAND':NandGate,'NOR':NorGate,
    'XOR':XorGate,'XNOR':XnorGate,'BUFFER':BufferGate,
    'INPUT':InputNode,'OUTPUT':OutputNode,
    'MUX':MuxGate,'DEMUX':DemuxGate,
    'ENCODER':EncoderGate,'PRIORITY_ENC':PriorityEncoderGate,
    'DECODER':DecoderGate,'BCD7SEG':BCD7SegGate,
    'HALF_ADDER':HalfAdder, 'FULL_ADDER':FullAdder,
    'CLOCK':ClockNode, 'D_FF':DFlipFlop, 'JK_FF':JKFlipFlop,
    'T_FF':TFlipFlop, 'SR_FF':SRFlipFlop,
    'RADIX_DISPLAY':RadixDisplayBlock, 'BUS_CONVERTER':RadixDisplayBlock,
}

# Safely import and register extended components
try:
    import transistor_gates
except ImportError:
    pass
try:
    import ic_chip
except ImportError:
    pass

def create_gate(gate_type, label="", size=None):
    if gate_type in ('RADIX_DISPLAY', 'BUS_CONVERTER'):
        width = size if isinstance(size, int) else 4
        return RadixDisplayBlock(bit_width=width, label=label or 'BUS DISPLAY')
    if gate_type.startswith('IC_') or gate_type in ('7400', '7402', '7404', '7408', '7432', '7486', '7474', '74138', '74151'):
        from ic_chip import DIPChipItem
        ic_key = gate_type[3:] if gate_type.startswith('IC_') else gate_type
        return DIPChipItem(ic_type=ic_key, label=label or f"IC_{ic_key}")
    if gate_type in ('NMOS', 'PMOS', 'PULLUP', 'PULLDOWN'):
        import transistor_gates
        cls_map = {'NMOS': 'NMOSGate', 'PMOS': 'PMOSGate', 'PULLUP': 'PullUpResistor', 'PULLDOWN': 'PullDownResistor'}
        cls = getattr(transistor_gates, cls_map[gate_type])
        return cls(label=label or gate_type)
    cls = GATE_CLASSES.get(gate_type)
    if cls is None: raise ValueError(f"Unknown gate: {gate_type}")
    if gate_type == 'INPUT':  return InputNode(label or 'IN')
    if gate_type == 'OUTPUT': return OutputNode(label or 'OUT')
    if gate_type == 'CLOCK':  return ClockNode(label or 'CLK')
    g = cls()
    if size is not None and hasattr(g, 'configure_size'):
        g.configure_size(size)
    if label:
        g.label = label
    return g
