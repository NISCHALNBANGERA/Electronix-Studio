"""canvas.py - QGraphicsScene/View with grid, drag-drop, wire routing"""
from PyQt5.QtWidgets import (QGraphicsScene, QGraphicsView, QMenu, QAction,QInputDialog)
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import QPen, QBrush, QColor, QPainter, QTransform

from gate import GateItem, Pin, create_gate, InputNode, OutputNode, VARIABLE_INPUT_TYPES, CONFIGURABLE_MSI_TYPES, RadixDisplayBlock
from sequential_gates import ClockNode, FlipFlopBase
from wire import Wire
from notes import NoteItem
from internal_structure_dialog import InternalStructureDialog

GRID = 20

class CircuitScene(QGraphicsScene):
    status_msg      = pyqtSignal(str)
    circuit_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-2000,-2000,4000,4000)
        self.theme_mode = "dark"
        self.grid_dot_color = QColor("#1c2333")
        self.grid_line_color = QColor("#141d2b")
        self.setBackgroundBrush(QBrush(QColor("#0d1117")))
        self.gates = []; self.wires = []; self.notes = []
        self._pending_src = None; self._temp_line = None

    def set_theme(self, mode="dark"):
        """Dynamically switch canvas background and grid between dark and light themes."""
        self.theme_mode = mode
        if mode == "light":
            self.setBackgroundBrush(QBrush(QColor("#ffffff")))
            self.grid_dot_color = QColor("#cbd5e1")
            self.grid_line_color = QColor("#e2e8f0")
        else:
            self.setBackgroundBrush(QBrush(QColor("#0d1117")))
            self.grid_dot_color = QColor("#1c2333")
            self.grid_line_color = QColor("#141d2b")
        self.update()

    def add_gate(self, gate_type, pos=None, size_config=None, label=""):
        gate = create_gate(gate_type, label=label, size=size_config)
        gate.setPos(self._snap(pos or QPointF(0,0)))
        self.addItem(gate); self.gates.append(gate)
        self.circuit_changed.emit()
        self.status_msg.emit(f"Added {gate.label.replace(chr(10), ' ')}")
        return gate

    def add_note(self, text=None, pos=None):
        note = NoteItem(text)
        note.setPos(self._snap(pos or QPointF(0,0)))
        self.addItem(note); self.notes.append(note)
        self.circuit_changed.emit()
        self.status_msg.emit("Note added — double-click to edit")
        return note

    def _snap(self, pos):
        return QPointF(round(pos.x()/GRID)*GRID, round(pos.y()/GRID)*GRID)

    def pin_clicked(self, pin):
        if self._pending_src is None:
            if pin.pin_type == 'output':
                self._pending_src = pin
                self.status_msg.emit("Click an INPUT pin to complete wire")
            else:
                self.status_msg.emit("Start from an OUTPUT pin")
        else:
            src, dst = self._pending_src, pin
            self._cancel_temp()
            self._pending_src = None
            if src==dst or dst.pin_type!='input': return
            if any(w.src_pin==src and w.dst_pin==dst for w in self.wires):
                self.status_msg.emit("Wire already exists"); return
            if dst.wires:
                self.status_msg.emit("Input already connected"); return
            wire = Wire(src, dst)
            self.addItem(wire); self.wires.append(wire)
            self.circuit_changed.emit()
            self.status_msg.emit("Wire connected ✓")

    def _cancel_temp(self):
        if self._temp_line: self.removeItem(self._temp_line); self._temp_line=None

    def mouseMoveEvent(self, e):
        if self._pending_src:
            self._cancel_temp()
            sp = self._pending_src.scene_pos(); dp = e.scenePos()
            self._temp_line = self.addLine(sp.x(),sp.y(),dp.x(),dp.y(),
                                           QPen(QColor("#4fc3f7"),1,Qt.DashLine))
        super().mouseMoveEvent(e)

    def keyPressEvent(self, e):
        if e.key()==Qt.Key_Escape:
            self._pending_src=None; self._cancel_temp()
        elif e.key()==Qt.Key_Delete:
            self.delete_selected()
        super().keyPressEvent(e)

    def delete_selected(self):
        for item in self.selectedItems():
            if isinstance(item, GateItem): self._remove_gate(item)
            elif isinstance(item, Wire):   self._remove_wire(item)
            elif isinstance(item, NoteItem): self._remove_note(item)
        self.circuit_changed.emit()

    def _remove_gate(self, gate):
        for pin in gate.input_pins+gate.output_pins:
            for w in list(pin.wires): self._remove_wire(w)
        self.removeItem(gate)
        if gate in self.gates: self.gates.remove(gate)
    def _set_input_count(self, gate):
        n, ok = QInputDialog.getInt(
            None, f"Configure {gate.gate_type} Gate", "Number of inputs (2-8):",
            value=len(gate.input_pins), min=2, max=8)
        if ok:
            gate.set_input_count(n)
            self.circuit_changed.emit()
            self.status_msg.emit(f"Configured {gate.gate_type} to {n} inputs")

    def _configure_msi_size(self, gate):
        gt = gate.gate_type
        if gt not in CONFIGURABLE_MSI_TYPES:
            return
        options, current_fn = CONFIGURABLE_MSI_TYPES[gt]
        curr_val = current_fn(gate) if current_fn else options[0]
        curr_idx = options.index(curr_val) if curr_val in options else 0
        choice, ok = QInputDialog.getItem(
            None,
            f"Configure {gt}",
            f"Select {gt} configuration:",
            options,
            curr_idx,
            False
        )
        if ok and choice:
            gate.configure_size(choice)
            self.circuit_changed.emit()
            self.status_msg.emit(f"Configured {gt} to {choice}")

    def _prompt_radix_bit_width(self, gate):
        if not gate or not hasattr(gate, 'bit_width'):
            return
        view = self.views()[0] if self.views() else None
        try:
            n, ok = QInputDialog.getInt(
                view,
                "Configure Bit Width",
                f"Select Bus Bit Width (2 to 16 bits) for {gate.label}:",
                value=gate.bit_width, min=2, max=16, step=1
            )
            if ok:
                gate.set_bit_width(n)
                self.circuit_changed.emit()
                self.status_msg.emit(f"Configured {gate.label} to {n}-bit bus")
        except Exception as err:
            self.status_msg.emit(f"Error configuring bus width: {err}")
    def _open_ic_manual(self, ic_type="7408"):
        from ic_manual_dialog import ICDatasheetDialog
        main_win = self.views()[0].window() if self.views() else None
        ICDatasheetDialog(target_ic=ic_type, main_window=main_win, parent=main_win).exec_()

    def _remove_wire(self, wire):
        wire.remove()
        if wire in self.wires: self.wires.remove(wire)

    def _remove_note(self, note):
        self.removeItem(note)
        if note in self.notes: self.notes.remove(note)

    def clear_circuit(self):
        for item in self.items(): self.removeItem(item)
        self.gates.clear(); self.wires.clear(); self.notes.clear()
        self._pending_src=None; self._temp_line=None

    def contextMenuEvent(self, e):
        item = self.itemAt(e.scenePos(), QTransform())
        menu = QMenu()
        menu.setStyleSheet("QMenu{background:#16213e;color:#e0e0e0;border:1px solid #4fc3f7;}"
                           "QMenu::item:selected{background:#0f3460;}")
        if isinstance(item, Pin):
            menu.addAction(QAction("✏ Rename Pin", menu, triggered=lambda: item.start_rename()))
            menu.exec_(e.screenPos())
        elif isinstance(item, GateItem):
            menu.addAction(QAction("✏ Rename Gate", menu, triggered=lambda: item.start_rename()))
            if item.gate_type in VARIABLE_INPUT_TYPES:
                menu.addAction(QAction("⚙ Configure Inputs (2-8)...", menu, triggered=lambda: self._set_input_count(item)))
            elif item.gate_type in CONFIGURABLE_MSI_TYPES:
                menu.addAction(QAction("⚙ Configure Size / Inputs...", menu, triggered=lambda: self._configure_msi_size(item)))
            menu.addAction(QAction("🗑 Delete Gate", menu, triggered=lambda: self._remove_gate(item)))
            if isinstance(item, InputNode):
                menu.addAction(QAction("⇅ Toggle 0/1", menu, triggered=item.toggle))
            elif isinstance(item, ClockNode):
                menu.addAction(QAction("⚡ Manual Pulse (1-shot)", menu, triggered=item.pulse))
                menu.addAction(QAction("⇅ Toggle 0/1", menu, triggered=item.toggle))
                run_txt = "⏸ Pause Auto-Clock" if item.is_running else "▶ Start Auto-Clock"
                menu.addAction(QAction(run_txt, menu, triggered=item.toggle_running))
                menu.addAction(QAction("⏱ Set Frequency...", menu, triggered=item._prompt_frequency))
                menu.addSeparator()
                menu.addAction(QAction("\U0001f50d View Internal Structure...", menu,
                    triggered=lambda chk=False, g=item: InternalStructureDialog(g, self.views()[0] if self.views() else None).exec_()))
            elif isinstance(item, FlipFlopBase):
                menu.addAction(QAction("⇅ Toggle State (Q 0↔1)", menu, triggered=item.toggle_state))
                menu.addAction(QAction("0 Reset State (Q=0)", menu, triggered=item.reset_state))
                menu.addAction(QAction("1 Preset State (Q=1)", menu, triggered=lambda: item.set_state(1)))
                menu.addSeparator()
                menu.addAction(QAction("\U0001f50d View Internal Structure...", menu,
                    triggered=lambda chk=False, g=item: InternalStructureDialog(g, self.views()[0] if self.views() else None).exec_()))
            if hasattr(item, 'ic_type'):
                menu.addSeparator()
                menu.addAction(QAction("📖 Open IC Datasheet / Pinout Manual...", menu,
                    triggered=lambda chk=False, g=item: self._open_ic_manual(g.ic_type)))
            elif isinstance(item, RadixDisplayBlock) or item.gate_type in ('RADIX_DISPLAY', 'BUS_CONVERTER'):
                menu.addSeparator()
                # Multi-Radix Mode Submenu
                mode_menu = menu.addMenu("🔢 Display Mode")
                mode_menu.setStyleSheet("QMenu{background:#16213e;color:#e0e0e0;border:1px solid #4fc3f7;}"
                                        "QMenu::item:selected{background:#0f3460;}")
                for m_key, m_name in item.DISPLAY_MODES:
                    act = mode_menu.addAction(m_name)
                    act.setCheckable(True)
                    act.setChecked(item.display_mode == m_key)
                    act.triggered.connect(lambda chk, g=item, k=m_key: (g.set_display_mode(k), self.circuit_changed.emit()))

                # Bit width configuration
                menu.addAction(QAction("Configure Bit Width...", menu,
                                       triggered=lambda chk=False, g=item: self._prompt_radix_bit_width(g)))

                # Color Theme Submenu
                color_menu = menu.addMenu("🎨 Change Display Color")
                color_menu.setStyleSheet("QMenu{background:#16213e;color:#e0e0e0;border:1px solid #4fc3f7;}"
                                         "QMenu::item:selected{background:#0f3460;}")
                for c_key, c_info in item.COLOR_THEMES.items():
                    act = color_menu.addAction(c_info['name'])
                    act.setCheckable(True)
                    act.setChecked(item.color_theme == c_key)
                    act.triggered.connect(lambda chk, g=item, k=c_key: (g.set_color_theme(k), self.circuit_changed.emit()))
            menu.exec_(e.screenPos())
        elif isinstance(item, Wire):
            menu.addAction(QAction("✂ Delete Wire", menu, triggered=lambda: self._remove_wire(item)))
            menu.exec_(e.screenPos())
        elif isinstance(item, NoteItem):
            menu.addAction(QAction("🗑 Delete Note", menu, triggered=lambda: self._remove_note(item)))
            menu.exec_(e.screenPos())
        else:
            menu.addAction(QAction("📝 Add Note Here", menu,
                                   triggered=lambda: self.add_note(pos=e.scenePos())))
            menu.exec_(e.screenPos())

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        painter.setRenderHint(QPainter.Antialiasing, False)
        l,t,r,b = int(rect.left()),int(rect.top()),int(rect.right()),int(rect.bottom())
        l -= l%GRID; t -= t%GRID
        dot_col = getattr(self, 'grid_dot_color', QColor("#1c2333"))
        line_col = getattr(self, 'grid_line_color', QColor("#141d2b"))
        # Dots
        painter.setPen(QPen(dot_col, 1))
        x=l
        while x<=r:
            y=t
            while y<=b:
                painter.drawPoint(x,y); y+=GRID
            x+=GRID
        # Major lines
        painter.setPen(QPen(line_col, 1))
        x=l
        while x<=r:
            if x%(GRID*5)==0: painter.drawLine(x,t,x,b)
            x+=GRID
        y=t
        while y<=b:
            if y%(GRID*5)==0: painter.drawLine(l,y,r,y)
            y+=GRID


class CircuitView(QGraphicsView):
    ZOOM = 1.15; MIN_Z=0.1; MAX_Z=5.0

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setStyleSheet("background:#0d1117;border:none;")
        self.setAcceptDrops(True)
        self._zoom = 1.0; self._panning=False; self._pan_start=None

    def wheelEvent(self, e):
        if e.angleDelta().y()>0: self._zoom_in()
        else: self._zoom_out()

    def _zoom_in(self):
        if self._zoom<self.MAX_Z:
            self.scale(self.ZOOM,self.ZOOM); self._zoom*=self.ZOOM
    def _zoom_out(self):
        if self._zoom>self.MIN_Z:
            self.scale(1/self.ZOOM,1/self.ZOOM); self._zoom/=self.ZOOM
    def reset_zoom(self):
        self.resetTransform(); self._zoom=1.0
    def fit_circuit(self):
        if self.scene().gates:
            self.fitInView(self.scene().itemsBoundingRect().adjusted(-40,-40,40,40), Qt.KeepAspectRatio)

    def mousePressEvent(self, e):
        if e.button()==Qt.MiddleButton:
            self._panning=True; self._pan_start=e.pos(); self.setCursor(Qt.ClosedHandCursor); return
        super().mousePressEvent(e)
    def mouseMoveEvent(self, e):
        if self._panning and self._pan_start:
            d=e.pos()-self._pan_start; self._pan_start=e.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value()-d.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value()-d.y()); return
        super().mouseMoveEvent(e)
    def mouseReleaseEvent(self, e):
        if e.button()==Qt.MiddleButton:
            self._panning=False; self.setCursor(Qt.ArrowCursor); return
        super().mouseReleaseEvent(e)

    def dragEnterEvent(self, e):
        if e.mimeData().hasText(): e.acceptProposedAction()
    def dragMoveEvent(self, e):
        if e.mimeData().hasText(): e.acceptProposedAction()
    def dropEvent(self, e):
        if e.mimeData().hasText():
            text = e.mimeData().text()
            if text == "NOTE":
                self.scene().add_note(pos=self.mapToScene(e.pos()))
            elif ":" in text and not text.startswith("NOTE"):
                parts = text.split(":", 1)
                gt, sz = parts[0], parts[1]
                self.scene().add_gate(gt, self.mapToScene(e.pos()), size_config=sz)
            else:
                self.scene().add_gate(text, self.mapToScene(e.pos()))
            e.acceptProposedAction()
