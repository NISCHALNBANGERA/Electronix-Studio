"""
sequential_gates.py - Sequential Logic Circuit Elements & Simulation Support
Includes:
- ClockNode: Toggle generator with configurable frequency (Hz), manual pulse, auto-run
- FlipFlopBase: Base class for sequential flip-flops with edge trigger detection,
                 visual state indicator (Q=0/1), active high/low color coding,
                 IEEE standard clock chevron, and inverted output bubbles.
- DFlipFlop: D Flip-Flop (CLK, D, async RST, async SET, Q, Q_bar)
- JKFlipFlop: JK Flip-Flop (CLK, J, K, async RST, async SET, Q, Q_bar)
- TFlipFlop: T Flip-Flop (CLK, T, async RST, async SET, Q, Q_bar)
- SRFlipFlop: SR Flip-Flop / Latch (S, R, CLK/EN, Q, Q_bar)
"""
import math
from PyQt5.QtWidgets import (
    QGraphicsItem, QMenu, QAction, QInputDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPainterPath

from gate import GateItem, Pin, _evenly_spaced_y, _height_for_pins, _restore_pin_labels


# ───────────────────────────────────────────────────────────────────────
# Clock Source
# ───────────────────────────────────────────────────────────────────────
class ClockNode(GateItem):
    """
    Clock Source: Configurable frequency toggle generator or manual pulse trigger.
    Outputs a standard clock signal on its output pin.
    """
    def __init__(self, label="CLK", freq_hz=1.0):
        super().__init__('CLOCK', label=label, num_inputs=0)
        self.freq_hz = max(0.1, float(freq_hz))
        self.is_running = True
        self._value = 0
        self.W = 70
        self.H = 60
        self.input_pins = []
        if self.output_pins:
            self.output_pins[0].setPos(self.W / 2 + Pin.RADIUS, 0)
            self.output_pins[0].label = "CLK"

        # Auto-toggle timer
        self._timer = QTimer()
        self._timer.timeout.connect(self._timer_tick)
        self._restart_timer()

    def _restart_timer(self):
        if self.is_running and self.freq_hz > 0:
            # Half period per toggle
            interval_ms = max(20, int(1000 / (2 * self.freq_hz)))
            self._timer.start(interval_ms)
        else:
            self._timer.stop()

    def _timer_tick(self):
        self._value = 1 - self._value
        if self.output_pins:
            self.output_pins[0].set_value(self._value)
        self.update()
        s = self.scene()
        if s and hasattr(s, 'circuit_changed'):
            s.circuit_changed.emit()

    def toggle(self):
        """Manual toggle 0 <-> 1"""
        self._value = 1 - self._value
        if self.output_pins:
            self.output_pins[0].set_value(self._value)
        self.update()
        s = self.scene()
        if s and hasattr(s, 'circuit_changed'):
            s.circuit_changed.emit()

    def pulse(self):
        """Generate a single clock pulse: 0 -> 1 -> 0"""
        self._value = 1
        if self.output_pins:
            self.output_pins[0].set_value(1)
        self.update()
        QTimer.singleShot(120, self._finish_pulse)

    def _finish_pulse(self):
        self._value = 0
        if self.output_pins:
            self.output_pins[0].set_value(0)
        self.update()
        s = self.scene()
        if s and hasattr(s, 'circuit_changed'):
            s.circuit_changed.emit()

    def set_frequency(self, freq_hz):
        self.freq_hz = max(0.1, float(freq_hz))
        self._restart_timer()
        self.update()

    def toggle_running(self):
        self.is_running = not self.is_running
        self._restart_timer()
        self.update()

    def evaluate(self):
        if self.output_pins:
            self.output_pins[0].set_value(self._value)
        return self._value

    def _get_shape_path(self):
        p = QPainterPath()
        p.addRoundedRect(0, -self.H / 2, self.W / 2, self.H, 6, 6)
        return p

    def _draw_body(self, painter):
        # Body background
        painter.setPen(QPen(QColor("#00e676" if self._value else "#37474f"), 2))
        painter.setBrush(QBrush(QColor("#0d2818" if self._value else "#1a2228")))
        painter.drawRoundedRect(QRectF(0, -self.H / 2, self.W / 2, self.H), 6, 6)

        # Draw square wave glyph ⎍
        painter.setPen(QPen(QColor("#00e676" if self._value else "#78909c"), 2))
        gx = 6
        gy = -self.H / 2 + 12
        gw = self.W / 2 - 12
        gh = 16
        wave = QPainterPath()
        wave.moveTo(gx, gy + gh)
        wave.lineTo(gx + gw * 0.25, gy + gh)
        wave.lineTo(gx + gw * 0.25, gy)
        wave.lineTo(gx + gw * 0.65, gy)
        wave.lineTo(gx + gw * 0.65, gy + gh)
        wave.lineTo(gx + gw, gy + gh)
        painter.drawPath(wave)

    def _draw_label(self, painter):
        painter.setFont(QFont("Consolas", 8, QFont.Bold))
        # Value display
        val_color = QColor("#00e676" if self._value else "#ff5252")
        painter.setPen(val_color)
        painter.drawText(QRectF(0, 2, self.W / 2, self.H / 2 - 4), Qt.AlignCenter,
                         f"{'1' if self._value else '0'}")

        # Frequency / status
        painter.setFont(QFont("Consolas", 6))
        painter.setPen(QColor("#aab4c0"))
        status = f"{self.freq_hz:.1f}Hz" if self.is_running else "PAUSED"
        painter.drawText(QRectF(0, self.H / 2 - 14, self.W / 2, 12), Qt.AlignCenter, status)

    def mouseDoubleClickEvent(self, e):
        # Double click generates pulse or toggles
        self.pulse()
        e.accept()

    def contextMenuEvent(self, e):
        menu = QMenu()
        menu.setStyleSheet("QMenu{background:#16213e;color:#e0e0e0;border:1px solid #00e676;}"
                           "QMenu::item:selected{background:#0f3460;}")
        menu.addAction(QAction("⚡ Manual Pulse (1-shot)", menu, triggered=self.pulse))
        menu.addAction(QAction("⇅ Toggle 0 / 1", menu, triggered=self.toggle))
        run_txt = "⏸ Pause Auto-Clock" if self.is_running else "▶ Start Auto-Clock"
        menu.addAction(QAction(run_txt, menu, triggered=self.toggle_running))
        menu.addAction(QAction("⏱ Set Frequency (Hz)...", menu, triggered=self._prompt_frequency))
        menu.addAction(QAction("✏ Rename Clock", menu, triggered=self.start_rename))
        menu.exec_(e.screenPos())

    def _prompt_frequency(self):
        f, ok = QInputDialog.getDouble(
            None, "Clock Frequency", "Frequency (Hz):",
            value=self.freq_hz, min=0.1, max=100.0, decimals=1
        )
        if ok:
            self.set_frequency(f)

    def to_dict(self):
        d = super().to_dict()
        d['freq_hz'] = self.freq_hz
        d['is_running'] = self.is_running
        d['value'] = self._value
        return d

    @staticmethod
    def from_dict(d):
        clk = ClockNode(label=d.get('label', 'CLK'), freq_hz=d.get('freq_hz', 1.0))
        clk.gate_id = d['gate_id']
        clk.setPos(d['x'], d['y'])
        clk.is_running = d.get('is_running', True)
        clk._value = d.get('value', 0)
        clk._restart_timer()
        return _restore_pin_labels(clk, d)


# ───────────────────────────────────────────────────────────────────────
# Sequential Flip-Flop Base Class
# ───────────────────────────────────────────────────────────────────────
class FlipFlopBase(GateItem):
    """
    Base class for all sequential flip-flops.
    Features:
    - Edge detection (Positive edge default / negative edge optional).
    - Internal state storage (`state`: 0 or 1, and `prev_clock`).
    - Visual state indicators on canvas with active high (vibrant green) / low color coding.
    - Standard dynamic clock trigger chevron `>` at CLK pin.
    - Standard bubble indicator for complementary output Q̅.
    """
    BODY_W = 110
    BODY_H = 130

    def __init__(self, gate_type, label, trigger_edge='posedge'):
        self.W = self.BODY_W
        self.H = self.BODY_H
        super().__init__(gate_type, label=label, num_inputs=0)
        self.state = 0
        self.prev_clock = 0
        self.trigger_edge = trigger_edge  # 'posedge' or 'negedge'
        self._edge_triggered_in_cycle = False
        self.clk_pin_idx = 0
        self.color_dark = QColor("#111b27")
        self.color_light = QColor("#1f6feb")
        self._build_ff_pins()

    def _build_pins(self):
        # Override to prevent default base pin building
        self.input_pins = []
        self.output_pins = []

    def _build_ff_pins(self):
        """Subclasses define their custom pin arrangement."""
        pass

    def boundingRect(self):
        m = 18
        return QRectF(-m, -self.H / 2 - m, self.W + 2 * m, self.H + 2 * m)

    def _draw_body(self, painter):
        # Main body rectangle
        painter.setPen(QPen(self.color_light, 2))
        painter.setBrush(QBrush(self.color_dark))
        painter.drawRoundedRect(QRectF(0, -self.H / 2, self.W, self.H), 8, 8)

        # Draw Clock dynamic chevron `>` at CLK pin position
        if self.clk_pin_idx < len(self.input_pins):
            clk_pin = self.input_pins[self.clk_pin_idx]
            cy = clk_pin.pos().y()
            chevron = QPainterPath()
            chevron.moveTo(0, cy - 8)
            chevron.lineTo(12, cy)
            chevron.lineTo(0, cy + 8)
            painter.setPen(QPen(QColor("#58a6ff"), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(chevron)
            if self.trigger_edge == 'negedge':
                # Draw bubble on negedge trigger
                painter.setBrush(QBrush(self.color_dark))
                painter.drawEllipse(QRectF(-8, cy - 4, 8, 8))

        # Draw Q_bar inverted bubble at output pin 1 if present
        if len(self.output_pins) > 1:
            qbar_pin = self.output_pins[1]
            qy = qbar_pin.pos().y()
            painter.setPen(QPen(self.color_light, 1.5))
            painter.setBrush(QBrush(self.color_dark))
            painter.drawEllipse(QRectF(self.W, qy - 4, 8, 8))

        # State Indicator Box (Internal State Q)
        state_w = 46
        state_h = 24
        state_rect = QRectF(self.W / 2 - state_w / 2, -12, state_w, state_h)
        if self.state:
            # Active HIGH: glowing neon green
            painter.setPen(QPen(QColor("#00e676"), 2))
            painter.setBrush(QBrush(QColor("#003b1f")))
        else:
            # Active LOW: dark slate / muted red
            painter.setPen(QPen(QColor("#546e7a"), 1.5))
            painter.setBrush(QBrush(QColor("#1a2228")))
        painter.drawRoundedRect(state_rect, 5, 5)

        # State text inside badge
        painter.setFont(QFont("Consolas", 9, QFont.Bold))
        painter.setPen(QColor("#00e676" if self.state else "#cf6679"))
        painter.drawText(state_rect, Qt.AlignCenter, f"Q={self.state}")

    def _draw_label(self, painter):
        # Component Title at top
        painter.setFont(QFont("Consolas", 9, QFont.Bold))
        painter.setPen(QColor("#ffffff"))
        painter.drawText(QRectF(0, -self.H / 2 + 6, self.W, 18), Qt.AlignCenter, self.label)

        # Draw pin label texts
        painter.setFont(QFont("Consolas", 7, QFont.Bold))
        for i, pin in enumerate(self.input_pins):
            if getattr(pin, '_editing', False):
                continue
            px, py = pin.pos().x(), pin.pos().y()
            # Indent text slightly past clock chevron if clock pin
            offset_x = 15 if i == self.clk_pin_idx else 9
            painter.setPen(QColor("#58a6ff" if i == self.clk_pin_idx else "#aab4c0"))
            painter.drawText(int(px) + offset_x, int(py) - 7, 34, 14, Qt.AlignLeft, pin.label)

        for i, pin in enumerate(self.output_pins):
            if getattr(pin, '_editing', False):
                continue
            px, py = pin.pos().x(), pin.pos().y()
            painter.setPen(QColor("#81c784"))
            lbl = pin.label or ("Q" if i == 0 else "Q_bar")
            display_lbl = "Q̅" if lbl in ("Q_bar", "Qbar", "Q̅") else lbl
            painter.drawText(int(px) - 34, int(py) - 7, 28, 14, Qt.AlignRight, display_lbl)

    def get_clk_value(self):
        if self.clk_pin_idx < len(self.input_pins):
            return self.input_pins[self.clk_pin_idx].value
        return 0

    def detect_clock_edge(self):
        """Returns True if a clock trigger edge occurred in the current cycle."""
        if getattr(self, '_edge_triggered_in_cycle', False):
            return False
        clk_val = self.get_clk_value()
        if self.trigger_edge == 'posedge':
            is_edge = (self.prev_clock == 0 and clk_val == 1)
        else:
            is_edge = (self.prev_clock == 1 and clk_val == 0)
        if is_edge:
            self._edge_triggered_in_cycle = True
        return is_edge

    def commit_clock(self):
        """Called by simulation engine at end of simulation pass to update previous clock."""
        self.prev_clock = self.get_clk_value()
        self._edge_triggered_in_cycle = False

    def reset_state(self):
        self.state = 0
        self._update_outputs()

    def set_state(self, val):
        self.state = 1 if val else 0
        self._update_outputs()

    def toggle_state(self):
        self.state = 1 - self.state
        self._update_outputs()

    def _update_outputs(self):
        if len(self.output_pins) > 0:
            self.output_pins[0].set_value(self.state)
        if len(self.output_pins) > 1:
            self.output_pins[1].set_value(1 - self.state)
        self.update()

    def contextMenuEvent(self, e):
        menu = QMenu()
        menu.setStyleSheet("QMenu{background:#16213e;color:#e0e0e0;border:1px solid #1f6feb;}"
                           "QMenu::item:selected{background:#0f3460;}")
        menu.addAction(QAction("⇅ Toggle State (Q 0↔1)", menu, triggered=self.toggle_state))
        menu.addAction(QAction("0 Reset State (Q=0)", menu, triggered=self.reset_state))
        menu.addAction(QAction("1 Preset State (Q=1)", menu, triggered=lambda: self.set_state(1)))
        edge_label = "Switch to Negative-Edge Trigger" if self.trigger_edge == 'posedge' else "Switch to Positive-Edge Trigger"
        menu.addAction(QAction(edge_label, menu, triggered=self._toggle_edge))
        menu.addAction(QAction("✏ Rename Flip-Flop", menu, triggered=self.start_rename))
        menu.exec_(e.screenPos())

    def _toggle_edge(self):
        self.trigger_edge = 'negedge' if self.trigger_edge == 'posedge' else 'posedge'
        self.update()

    def to_dict(self):
        d = super().to_dict()
        d['state'] = self.state
        d['trigger_edge'] = self.trigger_edge
        return d


# ───────────────────────────────────────────────────────────────────────
# D Flip-Flop (D, CLK, async RST, async SET -> Q, Q_bar)
# ───────────────────────────────────────────────────────────────────────
class DFlipFlop(FlipFlopBase):
    """
    D Flip-Flop with Data input (D), Clock (CLK), Asynchronous Reset (RST),
    Asynchronous Set (SET), and complementary outputs (Q, Q_bar).
    """
    def __init__(self, label="D-FF"):
        self.BODY_H = 130
        self.BODY_W = 105
        super().__init__('D_FF', label=label)

    def _build_ff_pins(self):
        # Left inputs: D, CLK, RST, SET
        # Arranged cleanly
        labels = ['D', 'CLK', 'RST', 'SET']
        ys = _evenly_spaced_y(len(labels), self.H)
        self.input_pins = [
            Pin(self, 'input', 0, QPointF(-Pin.RADIUS, ys[0]), 'D'),
            Pin(self, 'input', 1, QPointF(-Pin.RADIUS, ys[1]), 'CLK'),
            Pin(self, 'input', 2, QPointF(-Pin.RADIUS, ys[2]), 'RST'),
            Pin(self, 'input', 3, QPointF(-Pin.RADIUS, ys[3]), 'SET'),
        ]
        self.clk_pin_idx = 1

        # Right outputs: Q, Q_bar
        out_ys = _evenly_spaced_y(2, self.H)
        self.output_pins = [
            Pin(self, 'output', 0, QPointF(self.W + Pin.RADIUS, out_ys[0]), 'Q'),
            Pin(self, 'output', 1, QPointF(self.W + Pin.RADIUS, out_ys[1]), 'Q_bar'),
        ]

    def evaluate(self):
        d_val   = self.input_pins[0].value
        rst_val = self.input_pins[2].value
        set_val = self.input_pins[3].value

        # Asynchronous control takes precedence
        if rst_val == 1:
            self.state = 0
        elif set_val == 1:
            self.state = 1
        else:
            # Synchronous clock edge detection
            if self.detect_clock_edge():
                self.state = 1 if d_val else 0

        self._update_outputs()
        return self.state

    @staticmethod
    def from_dict(d):
        g = DFlipFlop(d.get('label', 'D-FF'))
        g.gate_id = d['gate_id']
        g.setPos(d['x'], d['y'])
        g.state = d.get('state', 0)
        g.trigger_edge = d.get('trigger_edge', 'posedge')
        g._update_outputs()
        return _restore_pin_labels(g, d)


# ───────────────────────────────────────────────────────────────────────
# JK Flip-Flop (J, CLK, K, async RST, async SET -> Q, Q_bar)
# ───────────────────────────────────────────────────────────────────────
class JKFlipFlop(FlipFlopBase):
    """
    JK Flip-Flop with Inputs J, CLK, K, async RST, async SET,
    Outputs Q, Q_bar.
    Behavior on posedge:
      J=0, K=0: Hold
      J=0, K=1: Reset (0)
      J=1, K=0: Set (1)
      J=1, K=1: Toggle (~Q)
    """
    def __init__(self, label="JK-FF"):
        self.BODY_H = 145
        self.BODY_W = 105
        super().__init__('JK_FF', label=label)

    def _build_ff_pins(self):
        labels = ['J', 'CLK', 'K', 'RST', 'SET']
        ys = _evenly_spaced_y(len(labels), self.H)
        self.input_pins = [
            Pin(self, 'input', 0, QPointF(-Pin.RADIUS, ys[0]), 'J'),
            Pin(self, 'input', 1, QPointF(-Pin.RADIUS, ys[1]), 'CLK'),
            Pin(self, 'input', 2, QPointF(-Pin.RADIUS, ys[2]), 'K'),
            Pin(self, 'input', 3, QPointF(-Pin.RADIUS, ys[3]), 'RST'),
            Pin(self, 'input', 4, QPointF(-Pin.RADIUS, ys[4]), 'SET'),
        ]
        self.clk_pin_idx = 1

        out_ys = _evenly_spaced_y(2, self.H)
        self.output_pins = [
            Pin(self, 'output', 0, QPointF(self.W + Pin.RADIUS, out_ys[0]), 'Q'),
            Pin(self, 'output', 1, QPointF(self.W + Pin.RADIUS, out_ys[1]), 'Q_bar'),
        ]

    def evaluate(self):
        j_val   = self.input_pins[0].value
        k_val   = self.input_pins[2].value
        rst_val = self.input_pins[3].value
        set_val = self.input_pins[4].value

        if rst_val == 1:
            self.state = 0
        elif set_val == 1:
            self.state = 1
        else:
            if self.detect_clock_edge():
                if j_val == 0 and k_val == 0:
                    pass  # hold
                elif j_val == 0 and k_val == 1:
                    self.state = 0
                elif j_val == 1 and k_val == 0:
                    self.state = 1
                elif j_val == 1 and k_val == 1:
                    self.state = 1 - self.state

        self._update_outputs()
        return self.state

    @staticmethod
    def from_dict(d):
        g = JKFlipFlop(d.get('label', 'JK-FF'))
        g.gate_id = d['gate_id']
        g.setPos(d['x'], d['y'])
        g.state = d.get('state', 0)
        g.trigger_edge = d.get('trigger_edge', 'posedge')
        g._update_outputs()
        return _restore_pin_labels(g, d)


# ───────────────────────────────────────────────────────────────────────
# T Flip-Flop (T, CLK, async RST, async SET -> Q, Q_bar)
# ───────────────────────────────────────────────────────────────────────
class TFlipFlop(FlipFlopBase):
    """
    T (Toggle) Flip-Flop with Inputs T, CLK, async RST, async SET,
    Outputs Q, Q_bar.
    Behavior on posedge:
      T=0: Hold
      T=1: Toggle (1 - Q)
    """
    def __init__(self, label="T-FF"):
        self.BODY_H = 130
        self.BODY_W = 105
        super().__init__('T_FF', label=label)

    def _build_ff_pins(self):
        labels = ['T', 'CLK', 'RST', 'SET']
        ys = _evenly_spaced_y(len(labels), self.H)
        self.input_pins = [
            Pin(self, 'input', 0, QPointF(-Pin.RADIUS, ys[0]), 'T'),
            Pin(self, 'input', 1, QPointF(-Pin.RADIUS, ys[1]), 'CLK'),
            Pin(self, 'input', 2, QPointF(-Pin.RADIUS, ys[2]), 'RST'),
            Pin(self, 'input', 3, QPointF(-Pin.RADIUS, ys[3]), 'SET'),
        ]
        self.clk_pin_idx = 1

        out_ys = _evenly_spaced_y(2, self.H)
        self.output_pins = [
            Pin(self, 'output', 0, QPointF(self.W + Pin.RADIUS, out_ys[0]), 'Q'),
            Pin(self, 'output', 1, QPointF(self.W + Pin.RADIUS, out_ys[1]), 'Q_bar'),
        ]

    def evaluate(self):
        t_val   = self.input_pins[0].value
        rst_val = self.input_pins[2].value
        set_val = self.input_pins[3].value

        if rst_val == 1:
            self.state = 0
        elif set_val == 1:
            self.state = 1
        else:
            if self.detect_clock_edge():
                if t_val == 1:
                    self.state = 1 - self.state

        self._update_outputs()
        return self.state

    @staticmethod
    def from_dict(d):
        g = TFlipFlop(d.get('label', 'T-FF'))
        g.gate_id = d['gate_id']
        g.setPos(d['x'], d['y'])
        g.state = d.get('state', 0)
        g.trigger_edge = d.get('trigger_edge', 'posedge')
        g._update_outputs()
        return _restore_pin_labels(g, d)


# ───────────────────────────────────────────────────────────────────────
# SR Flip-Flop / Latch (S, CLK, R -> Q, Q_bar)
# ───────────────────────────────────────────────────────────────────────
class SRFlipFlop(FlipFlopBase):
    """
    SR Flip-Flop / Clocked Latch with Inputs S, CLK, R, Outputs Q, Q_bar.
    Behavior on posedge / enable:
      S=0, R=0: Hold
      S=1, R=0: 1
      S=0, R=1: 0
      S=1, R=1: Invalid / Forbidden (held as 0 with visual alert)
    """
    def __init__(self, label="SR-FF"):
        self.BODY_H = 125
        self.BODY_W = 105
        super().__init__('SR_FF', label=label)

    def _build_ff_pins(self):
        labels = ['S', 'CLK', 'R']
        ys = _evenly_spaced_y(len(labels), self.H)
        self.input_pins = [
            Pin(self, 'input', 0, QPointF(-Pin.RADIUS, ys[0]), 'S'),
            Pin(self, 'input', 1, QPointF(-Pin.RADIUS, ys[1]), 'CLK'),
            Pin(self, 'input', 2, QPointF(-Pin.RADIUS, ys[2]), 'R'),
        ]
        self.clk_pin_idx = 1

        out_ys = _evenly_spaced_y(2, self.H)
        self.output_pins = [
            Pin(self, 'output', 0, QPointF(self.W + Pin.RADIUS, out_ys[0]), 'Q'),
            Pin(self, 'output', 1, QPointF(self.W + Pin.RADIUS, out_ys[1]), 'Q_bar'),
        ]

    def evaluate(self):
        s_val = self.input_pins[0].value
        r_val = self.input_pins[2].value

        if self.detect_clock_edge():
            if s_val == 0 and r_val == 0:
                pass  # hold
            elif s_val == 1 and r_val == 0:
                self.state = 1
            elif s_val == 0 and r_val == 1:
                self.state = 0
            elif s_val == 1 and r_val == 1:
                # S=1, R=1 is forbidden / invalid condition in SR flip flop
                self.state = 0

        self._update_outputs()
        return self.state

    @staticmethod
    def from_dict(d):
        g = SRFlipFlop(d.get('label', 'SR-FF'))
        g.gate_id = d['gate_id']
        g.setPos(d['x'], d['y'])
        g.state = d.get('state', 0)
        g.trigger_edge = d.get('trigger_edge', 'posedge')
        g._update_outputs()
        return _restore_pin_labels(g, d)
