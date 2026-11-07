"""undo_commands.py - PyQt5 QUndoCommand classes for digital logic circuit simulator"""
from PyQt5.QtWidgets import QUndoCommand
from PyQt5.QtCore import QPointF
from gate import GateItem
from wire import Wire
from notes import NoteItem


class AddGateCommand(QUndoCommand):
    """Command to add a gate to the scene, undoable by removing it and disconnecting wires."""
    def __init__(self, scene, gate, description="Add Gate"):
        super().__init__(description)
        self.scene = scene
        self.gate = gate
        self._connected_wires = []

    def redo(self):
        if self.gate not in self.scene.items():
            self.scene.addItem(self.gate)
        if self.gate not in self.scene.gates:
            self.scene.gates.append(self.gate)
        # Restore any wires that were connected before undo
        for w in self._connected_wires:
            if w not in self.scene.items():
                self.scene.addItem(w)
            if w not in self.scene.wires:
                self.scene.wires.append(w)
            if w not in w.src_pin.wires:
                w.src_pin.wires.append(w)
            if w not in w.dst_pin.wires:
                w.dst_pin.wires.append(w)
            w.update_path()
        self._connected_wires.clear()
        self.scene.circuit_changed.emit()

    def undo(self):
        self._connected_wires = []
        for pin in self.gate.input_pins + self.gate.output_pins:
            for w in list(pin.wires):
                if w not in self._connected_wires:
                    self._connected_wires.append(w)
                w.remove()
                if w in self.scene.wires:
                    self.scene.wires.remove(w)
        if self.gate in self.scene.items():
            self.scene.removeItem(self.gate)
        if self.gate in self.scene.gates:
            self.scene.gates.remove(self.gate)
        self.scene.circuit_changed.emit()


class DeleteItemsCommand(QUndoCommand):
    """Command to delete multiple selected gates, wires, and notes with full restoration on undo."""
    def __init__(self, scene, items, description="Delete Selection"):
        super().__init__(description)
        self.scene = scene
        self.gates = [i for i in items if isinstance(i, GateItem)]
        self.notes = [i for i in items if isinstance(i, NoteItem)]
        wires_set = set(i for i in items if isinstance(i, Wire))
        for g in self.gates:
            for p in g.input_pins + g.output_pins:
                for w in p.wires:
                    wires_set.add(w)
        self.wires = list(wires_set)

    def redo(self):
        for w in self.wires:
            w.remove()
            if w in self.scene.wires:
                self.scene.wires.remove(w)
        for g in self.gates:
            if g in self.scene.items():
                self.scene.removeItem(g)
            if g in self.scene.gates:
                self.scene.gates.remove(g)
        for n in self.notes:
            if n in self.scene.items():
                self.scene.removeItem(n)
            if n in self.scene.notes:
                self.scene.notes.remove(n)
        self.scene.circuit_changed.emit()

    def undo(self):
        for g in self.gates:
            if g not in self.scene.items():
                self.scene.addItem(g)
            if g not in self.scene.gates:
                self.scene.gates.append(g)
        for n in self.notes:
            if n not in self.scene.items():
                self.scene.addItem(n)
            if n not in self.scene.notes:
                self.scene.notes.append(n)
        for w in self.wires:
            if w not in self.scene.items():
                self.scene.addItem(w)
            if w not in self.scene.wires:
                self.scene.wires.append(w)
            if w not in w.src_pin.wires:
                w.src_pin.wires.append(w)
            if w not in w.dst_pin.wires:
                w.dst_pin.wires.append(w)
            w.update_path()
        self.scene.circuit_changed.emit()


class MoveItemsCommand(QUndoCommand):
    """Command tracking movement of one or more items (gates or notes), updating wire paths on both undo and redo."""
    def __init__(self, scene, move_records, description="Move Items"):
        super().__init__(description)
        self.scene = scene
        self.move_records = list(move_records)  # [(item, old_pos, new_pos)]

    def redo(self):
        for item, old_p, new_p in self.move_records:
            item.setPos(new_p)
            if hasattr(item, 'input_pins'):
                for p in item.input_pins + item.output_pins:
                    for w in p.wires:
                        w.update_path()
        self.scene.circuit_changed.emit()

    def undo(self):
        for item, old_p, new_p in self.move_records:
            item.setPos(old_p)
            if hasattr(item, 'input_pins'):
                for p in item.input_pins + item.output_pins:
                    for w in p.wires:
                        w.update_path()
        self.scene.circuit_changed.emit()


class AddWireCommand(QUndoCommand):
    """Command to connect a wire between source and destination pins."""
    def __init__(self, scene, src_pin, dst_pin, description="Add Wire"):
        super().__init__(description)
        self.scene = scene
        self.src_pin = src_pin
        self.dst_pin = dst_pin
        self.wire = None

    def redo(self):
        if self.wire is None:
            self.wire = Wire(self.src_pin, self.dst_pin)
        else:
            if self.wire not in self.src_pin.wires:
                self.src_pin.wires.append(self.wire)
            if self.wire not in self.dst_pin.wires:
                self.dst_pin.wires.append(self.wire)
        if self.wire not in self.scene.items():
            self.scene.addItem(self.wire)
        if self.wire not in self.scene.wires:
            self.scene.wires.append(self.wire)
        self.wire.update_path()
        self.scene.circuit_changed.emit()

    def undo(self):
        if self.wire:
            self.wire.remove()
            if self.wire in self.scene.wires:
                self.scene.wires.remove(self.wire)
        self.scene.circuit_changed.emit()


class DeleteWireCommand(QUndoCommand):
    """Command to delete a single wire."""
    def __init__(self, scene, wire, description="Delete Wire"):
        super().__init__(description)
        self.scene = scene
        self.wire = wire
        self.src_pin = wire.src_pin
        self.dst_pin = wire.dst_pin

    def redo(self):
        self.wire.remove()
        if self.wire in self.scene.wires:
            self.scene.wires.remove(self.wire)
        self.scene.circuit_changed.emit()

    def undo(self):
        if self.wire not in self.src_pin.wires:
            self.src_pin.wires.append(self.wire)
        if self.wire not in self.dst_pin.wires:
            self.dst_pin.wires.append(self.wire)
        if self.wire not in self.scene.items():
            self.scene.addItem(self.wire)
        if self.wire not in self.scene.wires:
            self.scene.wires.append(self.wire)
        self.wire.update_path()
        self.scene.circuit_changed.emit()


class ConfigureGateCommand(QUndoCommand):
    """Undo/redo for gate configuration changes (inputs, MSI size, bus bit width)."""
    def __init__(self, scene, gate, config_type, old_val, new_val, description="Configure Gate"):
        super().__init__(description)
        self.scene = scene
        self.gate = gate
        self.config_type = config_type  # 'inputs', 'msi_size', 'bit_width'
        self.old_val = old_val
        self.new_val = new_val
        self._saved_wires = []
        for pin in self.gate.input_pins + self.gate.output_pins:
            for w in pin.wires:
                self._saved_wires.append((w, w.src_pin, w.dst_pin))

    def redo(self):
        self._apply(self.new_val)
        self.scene.circuit_changed.emit()

    def undo(self):
        self._apply(self.old_val)
        for w, sp, dp in self._saved_wires:
            if sp.parent_gate in self.scene.gates and dp.parent_gate in self.scene.gates:
                if sp in sp.parent_gate.output_pins and dp in dp.parent_gate.input_pins:
                    if w not in self.scene.items():
                        self.scene.addItem(w)
                    if w not in self.scene.wires:
                        self.scene.wires.append(w)
                    if w not in sp.wires:
                        sp.wires.append(w)
                    if w not in dp.wires:
                        dp.wires.append(w)
                    w.update_path()
        self.scene.circuit_changed.emit()

    def _apply(self, val):
        if self.config_type == 'inputs' and hasattr(self.gate, 'set_input_count'):
            self.gate.set_input_count(val)
        elif self.config_type == 'msi_size' and hasattr(self.gate, 'configure_size'):
            self.gate.configure_size(val)
        elif self.config_type == 'bit_width' and hasattr(self.gate, 'set_bit_width'):
            self.gate.set_bit_width(val)


class AddItemsCommand(QUndoCommand):
    """Command to add a collection of gates, wires, and notes (used for Paste and Duplicate)."""
    def __init__(self, scene, gates, wires, notes, description="Add Items"):
        super().__init__(description)
        self.scene = scene
        self.gates = list(gates)
        self.wires = list(wires)
        self.notes = list(notes)

    def redo(self):
        for g in self.gates:
            if g not in self.scene.items(): self.scene.addItem(g)
            if g not in self.scene.gates: self.scene.gates.append(g)
        for n in self.notes:
            if n not in self.scene.items(): self.scene.addItem(n)
            if n not in self.scene.notes: self.scene.notes.append(n)
        for w in self.wires:
            if w not in self.scene.items(): self.scene.addItem(w)
            if w not in self.scene.wires: self.scene.wires.append(w)
            if w not in w.src_pin.wires: w.src_pin.wires.append(w)
            if w not in w.dst_pin.wires: w.dst_pin.wires.append(w)
            w.update_path()
        self.scene.circuit_changed.emit()

    def undo(self):
        for w in self.wires:
            w.remove()
            if w in self.scene.wires: self.scene.wires.remove(w)
        for g in self.gates:
            if g in self.scene.items(): self.scene.removeItem(g)
            if g in self.scene.gates: self.scene.gates.remove(g)
        for n in self.notes:
            if n in self.scene.items(): self.scene.removeItem(n)
            if n in self.scene.notes: self.scene.notes.remove(n)
        self.scene.circuit_changed.emit()


class AddNoteCommand(QUndoCommand):
    """Command to add a text note to the scene."""
    def __init__(self, scene, note, description="Add Note"):
        super().__init__(description)
        self.scene = scene
        self.note = note

    def redo(self):
        if self.note not in self.scene.items():
            self.scene.addItem(self.note)
        if self.note not in self.scene.notes:
            self.scene.notes.append(self.note)
        self.scene.circuit_changed.emit()

    def undo(self):
        if self.note in self.scene.items():
            self.scene.removeItem(self.note)
        if self.note in self.scene.notes:
            self.scene.notes.remove(self.note)
        self.scene.circuit_changed.emit()
