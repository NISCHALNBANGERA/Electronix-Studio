"""
save_load.py - Advanced project save/load with automatic image preview generation
Saves BOTH .json + .jpg together as a project bundle
"""
import json, os
from datetime import datetime
from PyQt5.QtGui import QPixmap, QPainter, QColor
from PyQt5.QtCore import Qt


PROJECTS_DIR = os.path.join(os.path.dirname(__file__), "projects")


def ensure_projects_dir():
    os.makedirs(PROJECTS_DIR, exist_ok=True)


# ── Image export helper ───────────────────────────────────────────────
def export_preview_image(scene, filepath, fmt="JPEG"):
    """Render scene to image. Returns True on success."""
    bounds = scene.itemsBoundingRect().adjusted(-40, -40, 40, 40)
    w = max(int(bounds.width()), 200)
    h = max(int(bounds.height()), 200)
    px = QPixmap(w, h)
    px.fill(QColor("#0d1117"))
    painter = QPainter(px)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    scene.render(painter, source=bounds)
    painter.end()
    return px.save(filepath, fmt, quality=90)


def generate_thumbnail(scene, size=(160, 100)):
    """Generate a small QPixmap thumbnail of the circuit."""
    bounds = scene.itemsBoundingRect().adjusted(-20, -20, 20, 20)
    w = max(int(bounds.width()), 100)
    h = max(int(bounds.height()), 100)
    px = QPixmap(w, h)
    px.fill(QColor("#0d1117"))
    painter = QPainter(px)
    painter.setRenderHint(QPainter.Antialiasing)
    scene.render(painter, source=bounds)
    painter.end()
    return px.scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)


# ── Core JSON save/load ───────────────────────────────────────────────
def save_circuit(gates, wires, filepath, notes=None):
    data = {
        'version': '2.1',
        'saved_at': datetime.now().isoformat(),
        'gates': [g.to_dict() for g in gates],
        'wires': [w.to_dict() for w in wires],
        'notes': [n.to_dict() for n in (notes or [])],
    }
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


def load_circuit(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)

    from gate import InputNode, OutputNode, GateItem, GATE_CLASSES, create_gate
    from notes import NoteItem
    gates = []
    gate_map = {}

    SPECIAL = {
        'INPUT':  InputNode.from_dict,
        'OUTPUT': OutputNode.from_dict,
    }
    # Gates with custom from_dict
    CUSTOM = {}
    for gt, cls in GATE_CLASSES.items():
        if hasattr(cls, 'from_dict') and gt not in SPECIAL:
            CUSTOM[gt] = cls.from_dict

    for gd in data.get('gates', []):
        gt = gd['gate_type']
        if gt in SPECIAL:
            g = SPECIAL[gt](gd)
        elif gt in CUSTOM:
            g = CUSTOM[gt](gd)
        else:
            g = GateItem.from_dict(gd)
        gate_map[gd['gate_id']] = g
        gates.append(g)

    notes = [NoteItem.from_dict(nd) for nd in data.get('notes', [])]

    return gates, data.get('wires', []), gate_map, notes


# ── Project save (JSON + JPEG bundle) ────────────────────────────────
def save_project(gates, wires, scene, filepath, notes=None):
    """
    Save project as:
      filepath.json  — editable circuit (gates + wires + notes)
      filepath.jpg   — visual preview
    """
    base = filepath.replace('.json','')
    json_path = base + '.json'
    jpg_path  = base + '.jpg'

    save_circuit(gates, wires, json_path, notes=notes)
    export_preview_image(scene, jpg_path, fmt="JPEG")
    return json_path, jpg_path


def load_project(filepath):
    base = filepath.replace('.json','')
    json_path = base + '.json'
    jpg_path  = base + '.jpg'
    gates, wire_data, gate_map, notes = load_circuit(json_path)
    thumb = None
    if os.path.exists(jpg_path):
        px = QPixmap(jpg_path)
        thumb = px.scaled(160, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return gates, wire_data, gate_map, notes, thumb


def list_projects():
    """Return list of (name, json_path, jpg_path, mtime) for all saved projects."""
    ensure_projects_dir()
    result = []
    for fname in os.listdir(PROJECTS_DIR):
        if fname.endswith('.json'):
            base = fname[:-5]
            json_path = os.path.join(PROJECTS_DIR, fname)
            jpg_path  = os.path.join(PROJECTS_DIR, base + '.jpg')
            mtime = os.path.getmtime(json_path)
            result.append((base, json_path, jpg_path, mtime))
    result.sort(key=lambda x: -x[3])
    return result
