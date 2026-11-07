"""
ic_manual_dialog.py - Interactive 74xx Series IC Datasheet & Pinout Manual.
Features:
- IC lookup with instant search filter.
- High-res interactive pinout diagram with pin role explanations.
- Internal gate architecture and pin-to-gate connection diagram.
- TTL Function and Truth Tables.
- One-click sample test circuit generator on canvas.
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QTabWidget, QWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit,
    QPushButton, QFrame, QGraphicsScene, QGraphicsView,
    QGraphicsRectItem, QGraphicsTextItem, QGraphicsPathItem,
    QSplitter, QMessageBox
)
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QFont, QColor, QPen, QBrush, QPainter, QPainterPath

from ic_chip import IC_CATALOG


IC_DETAILS = {
    '7400': {
        'truth_table': {
            'headers': ['1A', '1B', '1Y (Output)'],
            'rows': [
                ['0', '0', '1'],
                ['0', '1', '1'],
                ['1', '0', '1'],
                ['1', '1', '0'],
            ]
        },
        'pins_desc': {
            1: "1A — Gate 1, Input A",
            2: "1B — Gate 1, Input B",
            3: "1Y — Gate 1, Output (NAND of 1A & 1B)",
            4: "2A — Gate 2, Input A",
            5: "2B — Gate 2, Input B",
            6: "2Y — Gate 2, Output (NAND of 2A & 2B)",
            7: "GND — Ground Reference (0V)",
            8: "3Y — Gate 3, Output",
            9: "3A — Gate 3, Input A",
            10: "3B — Gate 3, Input B",
            11: "4Y — Gate 4, Output",
            12: "4A — Gate 4, Input A",
            13: "4B — Gate 4, Input B",
            14: "VCC — Supply Voltage (+5V)",
        },
        'theory': (
            "<h3>SN74LS00 Quad 2-Input NAND Gates</h3>"
            "<p>The 7400 is the quintessential TTL integrated circuit containing <b>four independent 2-input NAND gates</b>. "
            "Because the NAND function is <b>functionally complete (universal)</b>, any boolean logic function "
            "(AND, OR, NOT, XOR, Flip-Flops) can be constructed exclusively using 7400 ICs.</p>"
            "<h4>Key Specifications:</h4>"
            "<ul>"
            "<li><b>Operating Voltage:</b> 4.75V to 5.25V (Nominal 5.0V)</li>"
            "<li><b>Propagation Delay:</b> ~9 ns typical (LS series)</li>"
            "<li><b>Fan-out:</b> 10 LS-TTL loads</li>"
            "</ul>"
        )
    },
    '7402': {
        'truth_table': {
            'headers': ['1A', '1B', '1Y (Output)'],
            'rows': [
                ['0', '0', '1'],
                ['0', '1', '0'],
                ['1', '0', '0'],
                ['1', '1', '0'],
            ]
        },
        'pins_desc': {
            1: "1Y — Gate 1, Output",
            2: "1A — Gate 1, Input A",
            3: "1B — Gate 1, Input B",
            4: "2Y — Gate 2, Output",
            5: "2A — Gate 2, Input A",
            6: "2B — Gate 2, Input B",
            7: "GND — Ground (0V)",
            8: "3A — Gate 3, Input A",
            9: "3B — Gate 3, Input B",
            10: "3Y — Gate 3, Output",
            11: "4A — Gate 4, Input A",
            12: "4B — Gate 4, Input B",
            13: "4Y — Gate 4, Output",
            14: "VCC — Supply (+5V)",
        },
        'theory': (
            "<h3>SN74LS02 Quad 2-Input NOR Gates</h3>"
            "<p>Contains <b>four independent 2-input NOR gates</b>. Like NAND, the NOR gate is a "
            "<b>universal gate</b>. Note that the 7402 pinout differs from the 7400/7408: output pins are on pins 1, 4, 10, 13.</p>"
        )
    },
    '7404': {
        'truth_table': {
            'headers': ['A (Input)', 'Y (Output)'],
            'rows': [
                ['0', '1'],
                ['1', '0'],
            ]
        },
        'pins_desc': {
            1: "1A — Inverter 1 Input", 2: "1Y — Inverter 1 Output",
            3: "2A — Inverter 2 Input", 4: "2Y — Inverter 2 Output",
            5: "3A — Inverter 3 Input", 6: "3Y — Inverter 3 Output",
            7: "GND — Ground (0V)",
            8: "4Y — Inverter 4 Output", 9: "4A — Inverter 4 Input",
            10: "5Y — Inverter 5 Output", 11: "5A — Inverter 5 Input",
            12: "6Y — Inverter 6 Output", 13: "6A — Inverter 6 Input",
            14: "VCC — Supply (+5V)",
        },
        'theory': (
            "<h3>SN74LS04 Hex Inverter Gates</h3>"
            "<p>Contains <b>six independent NOT gates</b>. Inverts digital logic signals with high speed and low power consumption.</p>"
        )
    },
    '7408': {
        'truth_table': {
            'headers': ['1A', '1B', '1Y (Output)'],
            'rows': [
                ['0', '0', '0'],
                ['0', '1', '0'],
                ['1', '0', '0'],
                ['1', '1', '1'],
            ]
        },
        'pins_desc': {
            1: "1A — Gate 1, Input A", 2: "1B — Gate 1, Input B", 3: "1Y — Gate 1, Output (AND)",
            4: "2A — Gate 2, Input A", 5: "2B — Gate 2, Input B", 6: "2Y — Gate 2, Output (AND)",
            7: "GND — Ground Reference",
            8: "3Y — Gate 3, Output", 9: "3A — Gate 3, Input A", 10: "3B — Gate 3, Input B",
            11: "4Y — Gate 4, Output", 12: "4A — Gate 4, Input A", 13: "4B — Gate 4, Input B",
            14: "VCC — Supply Voltage (+5V)",
        },
        'theory': (
            "<h3>SN74LS08 Quad 2-Input AND Gates</h3>"
            "<p>Contains <b>four independent 2-input positive-AND gates</b>. Performs boolean conjunction Y = A · B.</p>"
        )
    },
    '7432': {
        'truth_table': {
            'headers': ['1A', '1B', '1Y (Output)'],
            'rows': [
                ['0', '0', '0'],
                ['0', '1', '1'],
                ['1', '0', '1'],
                ['1', '1', '1'],
            ]
        },
        'pins_desc': {
            1: "1A — Gate 1, Input A", 2: "1B — Gate 1, Input B", 3: "1Y — Gate 1, Output (OR)",
            4: "2A — Gate 2, Input A", 5: "2B — Gate 2, Input B", 6: "2Y — Gate 2, Output (OR)",
            7: "GND — Ground (0V)",
            8: "3Y — Gate 3, Output", 9: "3A — Gate 3, Input A", 10: "3B — Gate 3, Input B",
            11: "4Y — Gate 4, Output", 12: "4A — Gate 4, Input A", 13: "4B — Gate 4, Input B",
            14: "VCC — Supply (+5V)",
        },
        'theory': "<h3>SN74LS32 Quad 2-Input OR Gates</h3><p>Performs boolean disjunction Y = A + B across 4 gates.</p>"
    },
    '7486': {
        'truth_table': {
            'headers': ['1A', '1B', '1Y (Output)'],
            'rows': [
                ['0', '0', '0'],
                ['0', '1', '1'],
                ['1', '0', '1'],
                ['1', '1', '0'],
            ]
        },
        'pins_desc': {
            1: "1A — Gate 1, Input A", 2: "1B — Gate 1, Input B", 3: "1Y — Gate 1, Output (XOR)",
            4: "2A — Gate 2, Input A", 5: "2B — Gate 2, Input B", 6: "2Y — Gate 2, Output (XOR)",
            7: "GND — Ground (0V)",
            8: "3Y — Gate 3, Output", 9: "3A — Gate 3, Input A", 10: "3B — Gate 3, Input B",
            11: "4Y — Gate 4, Output", 12: "4A — Gate 4, Input A", 13: "4B — Gate 4, Input B",
            14: "VCC — Supply (+5V)",
        },
        'theory': "<h3>SN74LS86 Quad 2-Input Exclusive-OR (XOR) Gates</h3><p>Computes modulo-2 addition and parity generation.</p>"
    },
    '7474': {
        'truth_table': {
            'headers': ['PRE_b', 'CLR_b', 'CLK', 'D', 'Q', 'Q_bar'],
            'rows': [
                ['0', '1', 'X', 'X', '1', '0'],
                ['1', '0', 'X', 'X', '0', '1'],
                ['0', '0', 'X', 'X', '1*', '1* (Unstable)'],
                ['1', '1', '↑', '1', '1', '0'],
                ['1', '1', '↑', '0', '0', '1'],
                ['1', '1', '0', 'X', 'Q0', 'Q0_bar'],
            ]
        },
        'pins_desc': {
            1: "1CLR_b — FF 1 Active-Low Clear (Async Reset)",
            2: "1D — FF 1 Data Input",
            3: "1CLK — FF 1 Positive-Edge Clock",
            4: "1PRE_b — FF 1 Active-Low Preset (Async Set)",
            5: "1Q — FF 1 True Output",
            6: "1Q_b — FF 1 Inverted Output",
            7: "GND — Ground Reference",
            8: "2Q_b — FF 2 Inverted Output",
            9: "2Q — FF 2 True Output",
            10: "2PRE_b — FF 2 Active-Low Preset",
            11: "2CLK — FF 2 Clock",
            12: "2D — FF 2 Data Input",
            13: "2CLR_b — FF 2 Active-Low Clear",
            14: "VCC — Supply (+5V)",
        },
        'theory': (
            "<h3>SN74LS74A Dual D Positive-Edge Flip-Flops</h3>"
            "<p>Individual D flip-flops with independent data, clock, preset, and clear inputs.</p>"
        )
    },
    '74138': {
        'truth_table': {
            'headers': ['G1', 'G2A_b', 'G2B_b', 'C', 'B', 'A', 'Active Output (Low)'],
            'rows': [
                ['0', 'X', 'X', 'X', 'X', 'X', 'None (All High)'],
                ['X', '1', 'X', 'X', 'X', 'X', 'None (All High)'],
                ['X', 'X', '1', 'X', 'X', 'X', 'None (All High)'],
                ['1', '0', '0', '0', '0', '0', 'Y0_b = 0'],
                ['1', '0', '0', '0', '0', '1', 'Y1_b = 0'],
                ['1', '0', '0', '0', '1', '0', 'Y2_b = 0'],
                ['1', '0', '0', '0', '1', '1', 'Y3_b = 0'],
                ['1', '0', '0', '1', '0', '0', 'Y4_b = 0'],
                ['1', '0', '0', '1', '0', '1', 'Y5_b = 0'],
                ['1', '0', '0', '1', '1', '0', 'Y6_b = 0'],
                ['1', '0', '0', '1', '1', '1', 'Y7_b = 0'],
            ]
        },
        'pins_desc': {
            1: "A — Address bit 0 (LSB)", 2: "B — Address bit 1", 3: "C — Address bit 2 (MSB)",
            4: "G2A_b — Active-Low Enable A", 5: "G2B_b — Active-Low Enable B", 6: "G1 — Active-High Enable",
            7: "Y7_b — Output 7 (Active Low)", 8: "GND — Ground",
            9: "Y6_b — Output 6", 10: "Y5_b — Output 5", 11: "Y4_b — Output 4",
            12: "Y3_b — Output 3", 13: "Y2_b — Output 2", 14: "Y1_b — Output 1",
            15: "Y0_b — Output 0", 16: "VCC — Supply (+5V)",
        },
        'theory': "<h3>SN74LS138 3-to-8 Decoder / Demultiplexer</h3><p>Designed for memory address decoding and routing.</p>"
    },
    '74151': {
        'truth_table': {
            'headers': ['G_b', 'C', 'B', 'A', 'Y', 'W_b (Y_bar)'],
            'rows': [
                ['1', 'X', 'X', 'X', '0', '1 (Strobe disabled)'],
                ['0', '0', '0', '0', 'D0', 'D0_bar'],
                ['0', '0', '0', '1', 'D1', 'D1_bar'],
                ['0', '0', '1', '0', 'D2', 'D2_bar'],
                ['0', '0', '1', '1', 'D3', 'D3_bar'],
                ['0', '1', '0', '0', 'D4', 'D4_bar'],
                ['0', '1', '0', '1', 'D5', 'D5_bar'],
                ['0', '1', '1', '0', 'D6', 'D6_bar'],
                ['0', '1', '1', '1', 'D7', 'D7_bar'],
            ]
        },
        'pins_desc': {
            1: "D3 — Data Input 3", 2: "D2 — Data Input 2", 3: "D1 — Data Input 1", 4: "D0 — Data Input 0",
            5: "Y — True Output", 6: "W_b — Inverted Output", 7: "G_b — Strobe / Enable (Active Low)",
            8: "GND — Ground",
            9: "C — Select bit 2 (MSB)", 10: "B — Select bit 1", 11: "A — Select bit 0 (LSB)",
            12: "D4 — Data Input 4", 13: "D5 — Data Input 5", 14: "D6 — Data Input 6", 15: "D7 — Data Input 7",
            16: "VCC — Supply (+5V)",
        },
        'theory': "<h3>SN74LS151 8-Line to 1-Line Data Selector</h3><p>Multiplexes 1 of 8 data sources with complementary outputs.</p>"
    }
}


class ICDatasheetDialog(QDialog):
    """
    Dedicated Interactive 74xx IC Datasheet & Manual Explorer modal.
    """
    def __init__(self, target_ic="7408", main_window=None, parent=None):
        super().__init__(parent)
        self.target_ic = target_ic if target_ic in IC_CATALOG else "7408"
        self.main_window = main_window
        self.setWindowTitle("📖 74xx TTL IC Datasheet Manual & Pinout Explorer")
        self.resize(980, 680)
        self.setMinimumSize(880, 580)
        self._apply_style()
        self._build_ui()
        self._select_ic(self.target_ic)

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog { background: #0d1117; color: #e6edf3; }
            QLabel { color: #8b949e; font-family: Consolas; }
            QLineEdit { background: #161b22; color: #e6edf3; border: 1px solid #30363d; border-radius: 4px; padding: 6px; font-family: Consolas; }
            QListWidget { background: #161b22; color: #e6edf3; border: 1px solid #30363d; border-radius: 4px; font-family: Consolas; }
            QListWidget::item { padding: 6px 10px; border-bottom: 1px solid #21262d; }
            QListWidget::item:selected { background: #1f6feb; color: #ffffff; }
            QTabWidget::pane { border: 1px solid #30363d; background: #161b22; }
            QTabBar::tab { background: #161b22; color: #8b949e; border: 1px solid #30363d; border-bottom: none; padding: 8px 16px; font-family: Consolas; }
            QTabBar::tab:selected { background: #0d1117; color: #58a6ff; border-bottom: 2px solid #58a6ff; font-weight: bold; }
            QTableWidget { background: #0d1117; color: #e6edf3; border: 1px solid #30363d; gridline-color: #30363d; font-family: Consolas; font-size: 11px; }
            QHeaderView::section { background: #161b22; color: #58a6ff; font-weight: bold; padding: 4px; border: 1px solid #30363d; }
            QTextEdit { background: #0d1117; color: #e6edf3; border: 1px solid #30363d; font-family: Consolas; font-size: 12px; }
            QPushButton { background: #21262d; color: #e6edf3; border: 1px solid #30363d; border-radius: 4px; padding: 6px 14px; font-family: Consolas; }
            QPushButton:hover { background: #1f6feb; border-color: #58a6ff; }
        """)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        # Header bar
        top_bar = QHBoxLayout()
        icon_lbl = QLabel("📖")
        icon_lbl.setFont(QFont("Segoe UI", 16))
        top_bar.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        t1 = QLabel("TTL 74xx Integrated Circuit Family Reference Manual")
        t1.setFont(QFont("Consolas", 12, QFont.Bold))
        t1.setStyleSheet("color: #58a6ff;")
        t2 = QLabel("Official Texas Instruments Dual In-line Package (DIP) Pinouts, Logic Diagrams & Truth Tables")
        t2.setFont(QFont("Consolas", 8))
        title_col.addWidget(t1); title_col.addWidget(t2)
        top_bar.addLayout(title_col, stretch=1)

        # Quick Testbench generator button
        testbench_btn = QPushButton("⚡ Instantiate Test Circuit on Canvas")
        testbench_btn.setStyleSheet("background: #238636; color: white; font-weight: bold; padding: 6px 14px;")
        testbench_btn.clicked.connect(self._instantiate_test_circuit)
        top_bar.addWidget(testbench_btn)
        root.addLayout(top_bar)

        splitter = QSplitter(Qt.Horizontal)

        # Left Column: IC Search & Selection
        left_panel = QWidget()
        left_lay = QVBoxLayout(left_panel)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(6)

        search_hdr = QLabel("FILTER ICs:")
        search_hdr.setFont(QFont("Consolas", 8, QFont.Bold))
        left_lay.addWidget(search_hdr)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search (e.g. 7408, NAND, MUX)...")
        self.search_box.textChanged.connect(self._filter_ics)
        left_lay.addWidget(self.search_box)

        self.ic_list = QListWidget()
        self.ic_list.currentRowChanged.connect(self._on_ic_selected)
        left_lay.addWidget(self.ic_list)
        left_panel.setFixedWidth(240)
        splitter.addWidget(left_panel)

        # Right Column: Detail Tabs
        right_panel = QWidget()
        right_lay = QVBoxLayout(right_panel)
        right_lay.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_pinout_tab(), "  📌 Interactive Pinout  ")
        self.tabs.addTab(self._build_truth_table_tab(), "  📋 Truth / Function Table  ")
        self.tabs.addTab(self._build_theory_tab(), "  🔬 Description & Specs  ")
        right_lay.addWidget(self.tabs)
        splitter.addWidget(right_panel)

        root.addWidget(splitter, stretch=1)

        # Close button bottom
        bottom = QHBoxLayout()
        self.pin_info_lbl = QLabel("Hover or click pins to inspect function.")
        self.pin_info_lbl.setFont(QFont("Consolas", 9, QFont.Bold))
        self.pin_info_lbl.setStyleSheet("color: #ffa657;")
        bottom.addWidget(self.pin_info_lbl, stretch=1)

        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(80)
        close_btn.clicked.connect(self.accept)
        bottom.addWidget(close_btn)
        root.addLayout(bottom)

        self._populate_list()

    def _populate_list(self):
        self.ic_list.clear()
        for ic_key, data in IC_CATALOG.items():
            item = QListWidgetItem(f"{data['part']} ({ic_key})\n{data['desc']}")
            item.setData(Qt.UserRole, ic_key)
            self.ic_list.addItem(item)

    def _filter_ics(self, query):
        q = query.strip().lower()
        for i in range(self.ic_list.count()):
            item = self.ic_list.item(i)
            txt = item.text().lower()
            item.setHidden(q not in txt if q else False)

    def _on_ic_selected(self, row):
        if row < 0: return
        item = self.ic_list.item(row)
        if item:
            ic_key = item.data(Qt.UserRole)
            self._select_ic(ic_key)

    def _select_ic(self, ic_key):
        self.current_ic = ic_key
        # Sync list selection
        for i in range(self.ic_list.count()):
            if self.ic_list.item(i).data(Qt.UserRole) == ic_key:
                self.ic_list.setCurrentRow(i)
                break
        self._refresh_pinout_diagram()
        self._refresh_truth_table()
        self._refresh_theory()

    # ── Tab 1: Interactive Pinout View ────────────────────────────────
    def _build_pinout_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)

        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QBrush(QColor("#0d1117")))
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setStyleSheet("background: #0d1117; border: 1px solid #30363d;")
        lay.addWidget(self.view, stretch=1)
        return w

    def _refresh_pinout_diagram(self):
        self.scene.clear()
        spec = IC_CATALOG[self.current_ic]
        pins_count = spec['pins_count']
        pins_per_side = pins_count // 2

        # Draw DIP chip package
        cw = 170
        ch = max(240, 32 * (pins_per_side + 1))
        x0 = 100
        y0 = 30

        # Body
        chip_rect = QRectF(x0, y0, cw, ch)
        body = self.scene.addRect(chip_rect, QPen(QColor("#475569"), 2), QBrush(QColor("#1e222b")))

        # Notch
        p = QPainterPath()
        p.arcTo(QRectF(x0 + cw/2 - 16, y0 - 10, 32, 20), 180, 180)
        self.scene.addPath(p, QPen(QColor("#475569"), 1.5), QBrush(QColor("#0d1117")))

        # Pin 1 indicator dot
        self.scene.addEllipse(QRectF(x0 + 14, y0 + 16, 10, 10), QPen(QColor("#0f172a")), QBrush(QColor("#334155")))

        # Laser silk label
        t1 = self.scene.addText(spec['part'], QFont("Consolas", 11, QFont.Bold))
        t1.setDefaultTextColor(QColor("#ffffff"))
        t1.setPos(x0 + cw/2 - t1.boundingRect().width()/2, y0 + 36)

        t2 = self.scene.addText(f"DIP-{pins_count}", QFont("Consolas", 8))
        t2.setDefaultTextColor(QColor("#94a3b8"))
        t2.setPos(x0 + cw/2 - t2.boundingRect().width()/2, y0 + 56)

        # Draw pins on both sides
        step = ch / (pins_per_side + 1)
        details = IC_DETAILS.get(self.current_ic, {})
        pins_desc = details.get('pins_desc', {})

        # Left Pins: 1 to pins_per_side (top to bottom)
        for i in range(1, pins_per_side + 1):
            ptype, plbl = spec['pin_def'][i]
            y = y0 + step * i

            # Metal pin lead
            self.scene.addLine(x0 - 24, y, x0, y, QPen(QColor("#94a3b8"), 4))

            # Number circle
            clr = QColor("#ef4444") if i == spec['vcc_pin'] else (QColor("#64748b") if i == spec['gnd_pin'] else QColor("#38bdf8"))
            dot = self.scene.addEllipse(QRectF(x0 - 46, y - 10, 20, 20), QPen(clr, 1.5), QBrush(QColor("#161b22")))
            txt = self.scene.addText(str(i), QFont("Consolas", 7, QFont.Bold))
            txt.setDefaultTextColor(clr)
            txt.setPos(x0 - 44 + (4 if i < 10 else 0), y - 10)

            # Pin label inside chip
            lbl_item = self.scene.addText(plbl, QFont("Consolas", 8, QFont.Bold))
            lbl_item.setDefaultTextColor(QColor("#e2e8f0"))
            lbl_item.setPos(x0 + 8, y - 11)

            # Interactive hover detection
            desc = pins_desc.get(i, f"Pin {i}: {plbl}")
            dot.setToolTip(desc)

        # Right Pins: pins_per_side + 1 to pins_count (bottom to top!)
        for idx, pin_num in enumerate(range(pins_per_side + 1, pins_count + 1)):
            ptype, plbl = spec['pin_def'][pin_num]
            slot = pins_per_side - idx
            y = y0 + step * slot

            # Metal pin lead
            self.scene.addLine(x0 + cw, y, x0 + cw + 24, y, QPen(QColor("#94a3b8"), 4))

            # Number circle
            clr = QColor("#ef4444") if pin_num == spec['vcc_pin'] else (QColor("#64748b") if pin_num == spec['gnd_pin'] else QColor("#38bdf8"))
            dot = self.scene.addEllipse(QRectF(x0 + cw + 26, y - 10, 20, 20), QPen(clr, 1.5), QBrush(QColor("#161b22")))
            txt = self.scene.addText(str(pin_num), QFont("Consolas", 7, QFont.Bold))
            txt.setDefaultTextColor(clr)
            txt.setPos(x0 + cw + 28 + (4 if pin_num < 10 else 0), y - 10)

            # Pin label inside chip
            lbl_item = self.scene.addText(plbl, QFont("Consolas", 8, QFont.Bold))
            lbl_item.setDefaultTextColor(QColor("#e2e8f0"))
            lbl_item.setPos(x0 + cw - lbl_item.boundingRect().width() - 8, y - 11)

            desc = pins_desc.get(pin_num, f"Pin {pin_num}: {plbl}")
            dot.setToolTip(desc)

        self.view.setSceneRect(self.scene.itemsBoundingRect().adjusted(-40, -30, 40, 30))

    # ── Tab 2: Truth Table ────────────────────────────────────────────
    def _build_truth_table_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.tt_table = QTableWidget()
        self.tt_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.tt_table)
        return w

    def _refresh_truth_table(self):
        details = IC_DETAILS.get(self.current_ic, {})
        tt_info = details.get('truth_table', {})
        headers = tt_info.get('headers', ['Input', 'Output'])
        rows = tt_info.get('rows', [])

        self.tt_table.clear()
        self.tt_table.setColumnCount(len(headers))
        self.tt_table.setRowCount(len(rows))
        self.tt_table.setHorizontalHeaderLabels(headers)

        for r_idx, row in enumerate(rows):
            for c_idx, val in enumerate(row):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                if val == '1': item.setForeground(QColor("#4ade80"))
                elif val == '0': item.setForeground(QColor("#94a3b8"))
                elif 'X' in val: item.setForeground(QColor("#f87171"))
                elif '↑' in val: item.setForeground(QColor("#38bdf8"))
                self.tt_table.setItem(r_idx, c_idx, item)

    # ── Tab 3: Description & Theory ───────────────────────────────────
    def _build_theory_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.theory_box = QTextEdit()
        self.theory_box.setReadOnly(True)
        lay.addWidget(self.theory_box)
        return w

    def _refresh_theory(self):
        details = IC_DETAILS.get(self.current_ic, {})
        th = details.get('theory', f"<h3>{IC_CATALOG[self.current_ic]['desc']}</h3>")
        self.theory_box.setHtml(th)

    # ── Testbench Generator ───────────────────────────────────────────
    def _instantiate_test_circuit(self):
        if not self.main_window or not hasattr(self.main_window, 'scene'):
            QMessageBox.warning(self, "No Canvas", "Main canvas is not active.")
            return

        scene = self.main_window.scene
        # Add the IC to the center of view
        from ic_chip import DIPChipItem
        from wire import Wire

        # Place at scene position
        chip = scene.add_gate(f"IC_{self.current_ic}", pos=QPointF(100, 100))

        # Add Power rails: VCC=1 (Pullup/Switch) and GND=0 (Pulldown/Switch)
        vcc_in = scene.add_gate("INPUT", pos=QPointF(280, -20), label="VCC")
        vcc_in._value = 1
        vcc_in.update()

        gnd_in = scene.add_gate("INPUT", pos=QPointF(-80, 200), label="GND")
        gnd_in._value = 0
        gnd_in.update()

        # Connect VCC and GND wires
        vcc_pin = chip.pin_by_num.get(chip.vcc_pin_num)
        gnd_pin = chip.pin_by_num.get(chip.gnd_pin_num)

        if vcc_pin and vcc_in.output_pins:
            w_vcc = Wire(vcc_in.output_pins[0], vcc_pin)
            scene.addItem(w_vcc); scene.wires.append(w_vcc)

        if gnd_pin and gnd_in.output_pins:
            w_gnd = Wire(gnd_in.output_pins[0], gnd_pin)
            scene.addItem(w_gnd); scene.wires.append(w_gnd)

        # Add 2 test inputs on left
        in1 = scene.add_gate("INPUT", pos=QPointF(-80, 40), label="A")
        in2 = scene.add_gate("INPUT", pos=QPointF(-80, 100), label="B")

        # Connect in1 & in2 to Gate 1 (pins 1 & 2 for standard gates)
        p1 = chip.pin_by_num.get(1)
        p2 = chip.pin_by_num.get(2)
        if p1 and p1.pin_type == 'input' and in1.output_pins:
            w1 = Wire(in1.output_pins[0], p1)
            scene.addItem(w1); scene.wires.append(w1)
        if p2 and p2.pin_type == 'input' and in2.output_pins:
            w2 = Wire(in2.output_pins[0], p2)
            scene.addItem(w2); scene.wires.append(w2)

        # Add an output probe on Gate 1 output (pin 3 for standard gates or pin 1 for 7402)
        out_pin_num = 1 if self.current_ic == '7402' else (5 if self.current_ic in ('7474', '74151') else 3)
        p_out = chip.pin_by_num.get(out_pin_num)
        out_probe = scene.add_gate("OUTPUT", pos=QPointF(280, 80), label="Y")
        if p_out and p_out.pin_type == 'output' and out_probe.input_pins:
            w_out = Wire(p_out, out_probe.input_pins[0])
            scene.addItem(w_out); scene.wires.append(w_out)

        scene.circuit_changed.emit()
        QMessageBox.information(
            self, "Testbench Created",
            f"⚡ Successfully instantiated {chip.label} on canvas with VCC, GND, test inputs, and probe!\n\n"
            "Double-click input switches A / B on canvas to test truth table behavior."
        )
        self.accept()
