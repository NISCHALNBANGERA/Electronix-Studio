"""
signal_animator.py - Live signal flow animation engine
Animates signal propagation through wires and gates step-by-step
"""

from PyQt5.QtWidgets import QGraphicsTextItem, QGraphicsEllipseItem, QGraphicsItem
from PyQt5.QtCore import (QTimer, QPropertyAnimation, QSequentialAnimationGroup,
                           QParallelAnimationGroup, QEasingCurve, Qt, QPointF, QRectF)
from PyQt5.QtGui import (QFont, QColor, QPen, QBrush, QRadialGradient,
                          QPainter, QPainterPath)
from PyQt5.QtWidgets import QGraphicsPathItem
import math


# ── Floating result popup ─────────────────────────────────────────────
class ResultPopup(QGraphicsTextItem):
    """Floating animated label showing gate output value."""

    

    def __init__(self, value, pos, scene, hold_ms=600):
        super().__init__()
        v = int(value)
        label  = "1  HIGH" if v else "0  LOW"
        color  = "#00e676" if v else "#ff5252"
        self.setHtml(
            f'<div style="font-family:Consolas;font-size:13px;font-weight:bold;'
            f'color:{color};background:rgba(0,0,0,180);padding:4px 8px;'
            f'border-radius:6px;border:1px solid {color};">{label}</div>'
        )
        self.setPos(pos)
        self.setZValue(50)
        scene.addItem(self)

        from PyQt5.QtWidgets import QGraphicsOpacityEffect
        self._effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self._effect)

        fade_at = max(0.05, min(0.95, 1.0 - (300 / max(hold_ms, 300))))
        self._anim = QPropertyAnimation(self._effect, b"opacity")
        self._anim.setDuration(hold_ms)
        self._anim.setKeyValueAt(0,   1.0)
        self._anim.setKeyValueAt(fade_at, 1.0)
        self._anim.setKeyValueAt(1.0, 0.0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.finished.connect(lambda: scene.removeItem(self))

        self._steps = 0
        self._move_timer = QTimer()
        self._move_timer.setInterval(25)
        self._move_timer.timeout.connect(self._float_up)
        self._move_timer.start()
        self._anim.start()

    def _float_up(self):
        self._steps += 1
        self.moveBy(0, -0.6)
        if self._steps > 90:
            self._move_timer.stop()


# ── Pulse dot traveling along wire ───────────────────────────────────
class WirePulse(QGraphicsEllipseItem):
    """A glowing dot that travels along a wire path."""

    def __init__(self, wire, value, scene, on_done=None):
        r = 7
        super().__init__(-r, -r, 2*r, 2*r)
        self._wire  = wire
        self._value = value
        self._scene = scene
        self._on_done = on_done
        self._t = 0.0
        self._path = wire.path()

        color = QColor("#00e676") 
        self.setPen(QPen(color, 2))
        self.setBrush(QBrush(color))
        self.setZValue(20)
        scene.addItem(self)

        # Animate position along path
        self._timer = QTimer()
        self._timer.setInterval(16)   # ~60 fps
        self._timer.timeout.connect(self._step)
        self._timer.start()

    def _step(self):
        self._t += 0.045
        if self._t >= 1.0:
            self._timer.stop()
            self._scene.removeItem(self)
            if self._on_done:
                self._on_done()
            return
        length = self._path.length()
        pt = self._path.pointAtPercent(self._t)
        self.setPos(pt)


# ── Gate glow effect ─────────────────────────────────────────────────
class GateGlowEffect:
    """Temporarily highlights a gate body."""

    def __init__(self, gate, scene, on_done=None, duration=400):
        self._gate = gate
        self._on_done = on_done
        gate.glow_active = True
        gate.update()
        # duration may arrive as a float (e.g. speed * 0.6); QTimer.singleShot
        # requires an int millisecond value, so cast defensively here.
        QTimer.singleShot(int(duration), self._stop)

    def _stop(self):
        self._gate.glow_active = False
        self._gate.update()
        if self._on_done:
            self._on_done()


# ── Main animation orchestrator ───────────────────────────────────────
class SignalAnimator:
    """
    Orchestrates step-by-step signal propagation animation.

    Usage:
        animator = SignalAnimator(scene, gates, wires)
        animator.play(speed='medium')
    """

    SPEEDS = {'slow': 700, 'medium': 350, 'fast': 120}

    def __init__(self, scene, gates, wires):
        self.scene  = scene
        self.gates  = gates
        self.wires  = wires
        self._steps = []
        self._idx   = 0
        self._timer = QTimer()
        self._timer.timeout.connect(self._next_step)
        self._playing = False
        self._speed   = 350
        self._callbacks = []

    # ── public API ────────────────────────────────────────────────
    def play(self, speed='medium'):
        self._speed = self.SPEEDS.get(speed, 350)
        self._steps = self._build_steps()
        self._idx   = 0
        self._last_gate_idx = max(
            (i for i, (kind, _) in enumerate(self._steps) if kind == 'gate'),
            default=-1
        )
        self._playing = True
        self._timer.start(self._speed)
    def pause(self):
        self._timer.stop()
        self._playing = False

    def stop(self):
        self._timer.stop()
        self._playing = False
        self._idx = 0

    def set_speed(self, speed_str):
        self._speed = self.SPEEDS.get(speed_str, 350)
        if self._playing:
            self._timer.setInterval(self._speed)

    def on_finished(self, cb):
        self._callbacks.append(cb)

    # ── step builder ──────────────────────────────────────────────
    def _build_steps(self):
        """
        Returns ordered list of (type, object) tuples:
          ('gate', gate_item)
          ('wire', wire_item)
        """
        from gate import InputNode
        from simulation import SimulationEngine

        eng = SimulationEngine(self.gates, self.wires)
        order = eng._topological_sort()

        steps = []
        for gate in order:
            steps.append(('gate', gate))
            for pin in gate.output_pins:
                for wire in pin.wires:
                    steps.append(('wire', wire))
        return steps

    # ── step execution ────────────────────────────────────────────
    def _next_step(self):
        if self._idx >= len(self._steps):
            self._timer.stop()
            self._playing = False
            for cb in self._callbacks:
                cb()
            return

        kind, obj = self._steps[self._idx]
        is_final_gate = (kind == 'gate') and (self._idx == self._last_gate_idx)
        self._idx += 1

        if kind == 'gate':
            self._animate_gate(obj, is_final=is_final_gate)
        elif kind == 'wire':
            self._animate_wire(obj)

    def _animate_gate(self, gate, is_final=False):
        """Evaluate gate and show glow + result popup."""
        result = gate.evaluate()

        def show_popup():
            p = gate.pos()
            popup_pos = QPointF(p.x() + gate.W/2 - 20, p.y() - gate.H/2 - 36)
            ResultPopup(result, popup_pos, self.scene, hold_ms=2000 if is_final else 600)

        GateGlowEffect(gate, self.scene, on_done=show_popup, duration=int(self._speed * 0.6))

    def _animate_wire(self, wire):
        """Send a pulse dot along the wire — only animate wires actually carrying a signal (1)."""
        try:
            value = wire.src_pin.value
            wire.update_value(value)
            if value:
                WirePulse(wire, value, self.scene)
        except Exception:
            pass
