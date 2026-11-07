"""
kmap_solver.py - Interactive Karnaugh Map Solver
Supports 2, 3, and 4-variable KMaps with grouping, minimization,
literal-term breakdown, and named group-size reporting (Single/Pair/Quad/Octet).
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QFrame, QTextEdit,
    QWidget, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
import itertools


# ── Gray code orderings ──────────────────────────────────────────────
GRAY2 = [0, 1]
GRAY4 = [0, 1, 3, 2]          # 00 01 11 10

KMAP_CONFIG = {
    2: {'rows': 1, 'cols': 2, 'rvars': [],    'cvars': ['A','B'],    'rgray': [0], 'cgray': GRAY2[:2]},
    3: {'rows': 2, 'cols': 2, 'rvars': ['A'], 'cvars': ['B','C'],    'rgray': GRAY2[:2], 'cgray': GRAY2[:2]},
    4: {'rows': 4, 'cols': 4, 'rvars': ['A','B'], 'cvars': ['C','D'], 'rgray': GRAY4, 'cgray': GRAY4},
}

GROUP_COLORS = [
    "#1565c0", "#6a1b9a", "#b71c1c", "#1b5e20",
    "#e65100", "#880e4f", "#004d40", "#37474f",
]

# Standard K-Map group-size naming (digital electronics textbook terms)
GROUP_TYPE_NAMES = {
    1:  "Single",
    2:  "Pair",
    4:  "Quad",
    8:  "Octet",
    16: "Hexad (all-1s)",
}

def group_type_name(size):
    return GROUP_TYPE_NAMES.get(size, f"{size}-cell group")


def minterm_to_term(idx, n_vars, var_names):
    """Full uncombined literal term for a single minterm, e.g. m5 (n=4) -> A'B C D'."""
    bits = bin(idx)[2:].zfill(n_vars)
    parts = []
    for i, b in enumerate(bits):
        v = var_names[i]
        parts.append(v if b == '1' else v + "'")
    return "".join(parts)


class KMapCell(QPushButton):
    """Single clickable KMap cell."""
    def __init__(self, row, col, parent=None):
        super().__init__("0", parent)
        self.row = row
        self.col = col
        self.value = 0
        self.group_color = None
        self.setFixedSize(62, 52)
        self.setFont(QFont("Consolas", 16, QFont.Bold))
        self._refresh()
        self.clicked.connect(self._toggle)

    def _toggle(self):
        self.value = 1 - self.value
        self.group_color = None
        self._refresh()

    def set_group_color(self, color):
        self.group_color = color
        self._refresh()

    def _refresh(self):
        if self.value == 1:
            bg = self.group_color or "#1b5e20"
            fg = "#a5d6a7"
        else:
            bg = "#1a1a2e"
            fg = "#546e7a"
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg}; color: {fg};
                border: 1px solid #2d3561; border-radius: 4px;
                font-family: Consolas; font-size: 16px; font-weight: bold;
            }}
            QPushButton:hover {{
                border: 2px solid #4fc3f7;
                background: {'#2e7d32' if self.value else '#16213e'};
            }}
        """)
        self.setText("1" if self.value else "0")


class KMapSolverEngine:
    """Quine-McCluskey-style KMap minimization via maximal-group covering."""

    def __init__(self, n_vars, values):
        self.n_vars = n_vars
        self.values = values  # dict: minterm_index -> 0/1
        self.minterms = [i for i, v in values.items() if v == 1]

    def solve(self):
        """Returns (expression_str, groups_list) where groups_list is a list of frozensets."""
        if not self.minterms:
            return "0", []
        if len(self.minterms) == 2 ** self.n_vars:
            return "1", [frozenset(range(2 ** self.n_vars))]

        groups, covered = self._find_groups()
        expr = self._build_expression(groups)
        return expr, groups

    def _find_groups(self):
        n = self.n_vars
        minterms = set(self.minterms)
        all_groups = []
        for size in [2**k for k in range(n, -1, -1)]:
            for combo in itertools.combinations(range(2**n), size):
                combo_set = set(combo)
                if not combo_set.issubset(minterms):
                    continue
                if not self._is_valid_group(combo_set, n):
                    continue
                all_groups.append(frozenset(combo_set))

        covered = set()
        chosen = []
        all_groups.sort(key=lambda g: -len(g))
        for g in all_groups:
            if g - covered:
                chosen.append(g)
                covered |= g
            if covered >= minterms:
                break
        return chosen, covered

    def _is_valid_group(self, cells, n):
        size = len(cells)
        if size == 0 or (size & (size - 1)) != 0:
            return False
        if size == 1:
            return True
        cells = list(cells)
        xors = set()
        base = cells[0]
        for c in cells[1:]:
            xors.add(base ^ c)
        combined = 0
        for x in xors:
            combined |= x
        bits = bin(combined).count('1')
        return bits <= n and len(cells) == size

    def _build_expression(self, groups):
        n = self.n_vars
        var_names = ['A', 'B', 'C', 'D'][:n]
        terms = []
        for group in groups:
            cells = list(group)
            if not cells:
                continue
            constant_mask = (2**n - 1)
            for i in range(len(cells) - 1):
                constant_mask &= ~(cells[i] ^ cells[i+1])
            term_parts = []
            sample = cells[0]
            for bit_pos in range(n - 1, -1, -1):
                bit_idx = n - 1 - bit_pos
                if constant_mask & (1 << bit_pos):
                    var = var_names[bit_idx]
                    term_parts.append(var if (sample & (1 << bit_pos)) else var + "'")
            terms.append("".join(term_parts) if term_parts else "1")
        return " + ".join(terms) if terms else "0"


class KMapDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("K-Map Solver")
        self.setMinimumSize(740, 640)
        self.n_vars = 4
        self.cells = {}
        self._apply_style()
        self._build_ui()
        self._build_kmap()

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog { background: #0d1117; color: #e0e0e0; }
            QLabel { color: #b0bec5; font-family: Consolas; }
            QComboBox { background: #161b22; color: #e0e0e0; border: 1px solid #4fc3f7;
                        padding: 4px 8px; font-family: Consolas; border-radius: 4px; }
            QComboBox::drop-down { border: none; }
            QTextEdit { background: #161b22; color: #4fc3f7; border: 1px solid #2d3561;
                        font-family: Consolas; font-size: 13px; padding: 8px; border-radius:4px; }
            QPushButton { background: #21262d; color: #e0e0e0; border: 1px solid #30363d;
                          padding: 8px 18px; border-radius: 4px; font-family: Consolas; }
            QPushButton:hover { background: #1f6feb; border-color: #58a6ff; }
            QFrame { border: none; }
        """)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 16)

        hdr = QLabel("◈  Karnaugh Map Solver")
        hdr.setFont(QFont("Consolas", 14, QFont.Bold))
        hdr.setStyleSheet("color: #4fc3f7;")
        root.addWidget(hdr)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("Variables:"))
        self.var_combo = QComboBox()
        for n in [2, 3, 4]:
            self.var_combo.addItem(f"{n} variables  ({'  '.join(['A','B','C','D'][:n])})", n)
        self.var_combo.setCurrentIndex(2)
        self.var_combo.currentIndexChanged.connect(self._on_var_change)
        ctrl.addWidget(self.var_combo)
        ctrl.addStretch()

        solve_btn = QPushButton("▶  Solve")
        solve_btn.setStyleSheet("QPushButton{background:#1b5e20;color:#a5d6a7;border:1px solid #388e3c;padding:8px 20px;border-radius:4px;font-family:Consolas;font-weight:bold;}"
                                "QPushButton:hover{background:#2e7d32;}")
        solve_btn.clicked.connect(self._solve)
        ctrl.addWidget(solve_btn)

        clear_btn = QPushButton("✕  Clear")
        clear_btn.setStyleSheet("QPushButton{background:#b71c1c;color:#ffcdd2;border:1px solid #c62828;padding:8px 16px;border-radius:4px;font-family:Consolas;}"
                                "QPushButton:hover{background:#c62828;}")
        clear_btn.clicked.connect(self._clear)
        ctrl.addWidget(clear_btn)

        root.addLayout(ctrl)

        self.kmap_frame = QFrame()
        self.kmap_layout = QVBoxLayout(self.kmap_frame)
        self.kmap_layout.setAlignment(Qt.AlignCenter)
        root.addWidget(self.kmap_frame, stretch=1)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background:#30363d; height:1px;")
        root.addWidget(sep)

        res_lbl = QLabel("Solution:")
        res_lbl.setStyleSheet("color:#8b949e; font-family:Consolas; font-size:11px;")
        root.addWidget(res_lbl)

        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setMinimumHeight(150)
        self.result_box.setPlaceholderText("Click cells to set 1s, then click Solve...")
        root.addWidget(self.result_box)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn, alignment=Qt.AlignRight)

    def _on_var_change(self):
        self.n_vars = self.var_combo.currentData()
        self._build_kmap()

    def _build_kmap(self):
        for i in reversed(range(self.kmap_layout.count())):
            w = self.kmap_layout.itemAt(i).widget()
            if w: w.deleteLater()
        self.cells = {}

        cfg = KMAP_CONFIG[self.n_vars]
        rows, cols = cfg['rows'], cfg['cols']
        rvars, cvars = cfg['rvars'], cfg['cvars']
        rgray, cgray = cfg['rgray'], cfg['cgray']

        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(3)

        corner = QLabel("")
        corner.setFixedSize(62, 28)
        if rvars:
            corner.setText("/".join(rvars) + "\\" + "/".join(cvars))
            corner.setFont(QFont("Consolas", 8))
            corner.setStyleSheet("color:#546e7a;")
        grid.addWidget(corner, 0, 0)

        for c in range(cols):
            bits = bin(cgray[c])[2:].zfill(len(cvars))
            lbl = QLabel(bits)
            lbl.setFixedSize(62, 28)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFont(QFont("Consolas", 10, QFont.Bold))
            lbl.setStyleSheet("color:#4fc3f7;")
            grid.addWidget(lbl, 0, c + 1)

        for r in range(rows):
            if rvars:
                bits = bin(rgray[r])[2:].zfill(len(rvars))
                lbl = QLabel(bits)
                lbl.setFixedSize(62, 52)
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setFont(QFont("Consolas", 10, QFont.Bold))
                lbl.setStyleSheet("color:#ab47bc;")
                grid.addWidget(lbl, r + 1, 0)

            for c in range(cols):
                row_bits = bin(rgray[r])[2:].zfill(len(rvars)) if rvars else ''
                col_bits = bin(cgray[c])[2:].zfill(len(cvars))
                minterm = int(row_bits + col_bits, 2)
                cell = KMapCell(r, c)
                self.cells[(r, c)] = (cell, minterm)
                grid.addWidget(cell, r + 1, c + 1)

        self.kmap_layout.addWidget(container)
        self.result_box.clear()

    def _solve(self):
        values = {}
        for (r, c), (cell, minterm) in self.cells.items():
            values[minterm] = cell.value

        var_names = ['A', 'B', 'C', 'D'][:self.n_vars]
        engine = KMapSolverEngine(self.n_vars, values)
        expr, groups = engine.solve()

        # Reset then recolor cells by group
        for (r, c), (cell, minterm) in self.cells.items():
            cell.group_color = None
            cell._refresh()
        for gi, group in enumerate(groups):
            color = GROUP_COLORS[gi % len(GROUP_COLORS)]
            for (r, c), (cell, minterm) in self.cells.items():
                if minterm in group:
                    cell.set_group_color(color)

        # ── Build rich-text result ──────────────────────────────────
        active_minterms = sorted(values.keys()) if False else sorted(
            [mt for mt in values if values[mt] == 1])

        # Literal term per active cell (replaces raw minterm number list)
        term_lines = []
        for mt in active_minterms:
            term = minterm_to_term(mt, self.n_vars, var_names)
            term_lines.append(f"<span style='color:#90caf9'>m{mt}</span> = "
                              f"<span style='color:#a5d6a7'>{term}</span>")

        # Group breakdown using textbook size names, colored to match the grid
        group_lines = []
        for gi, group in enumerate(groups):
            color = GROUP_COLORS[gi % len(GROUP_COLORS)]
            type_name = group_type_name(len(group))
            members = ", ".join(f"m{m}" for m in sorted(group))
            group_lines.append(
                f"<span style='color:{color};font-weight:bold;'>● {type_name}</span>"
                f" <span style='color:#8b949e'>({len(group)} cell{'s' if len(group)!=1 else ''}: {members})</span>"
            )

        html = f"""
        <div style='font-family:Consolas; font-size:13px; line-height:1.6;'>
          <div style='color:#ffeb3b; font-size:16px; font-weight:bold;'>
            Minimized Expression:&nbsp; {expr}
          </div>
          <br>
          <div style='color:#58a6ff; font-weight:bold;'>Active Cells (literal terms):</div>
          {'<br>'.join(term_lines) if term_lines else '<span style="color:#546e7a">none</span>'}
          <br><br>
          <div style='color:#58a6ff; font-weight:bold;'>Groups Used:</div>
          {'<br>'.join(group_lines) if group_lines else '<span style="color:#546e7a">none</span>'}
        </div>
        """
        self.result_box.setHtml(html)

    def _clear(self):
        for (r, c), (cell, minterm) in self.cells.items():
            cell.value = 0
            cell.group_color = None
            cell._refresh()
        self.result_box.clear()