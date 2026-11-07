"""
main_window.py - Professional EDA Workstation Architecture
Digital Electronics Design & Learning Studio

Layout Highlights:
1. Component Insertion via Pop-down Category Buttons ([Gates ▼], [Sequential ▼], [MSI ▼], [I/O ▼], [74xx IC ▼], [Transistors ▼])
   using QToolButton with InstantPopup menus.
2. Dedicated Right-Hand Utility & Analysis Tool Strip housing AI Tutor, Waveform, Truth Table, Verilog, K-Map, etc.
3. Live Light Mode / Dark Mode Theme Switcher ([ 🌙 Dark / ☀️ Light ]) with dynamic palette, canvas, and grid refresh.
4. Clean, spacious workspace: 0 duplicate buttons, 0 cluttered static button columns, maximum canvas breathing room.
"""
import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QAction, QStatusBar, QLabel, QPushButton,
    QFileDialog, QMessageBox, QFrame, QMenu, QDockWidget,
    QComboBox, QScrollArea, QLineEdit, QCompleter,
    QShortcut, QToolButton, QSizePolicy, QApplication,
    QSplitter, QGridLayout
)
from PyQt5.QtCore import Qt, QMimeData, QTimer, QPointF, QEvent, pyqtSlot
from PyQt5.QtGui import (QFont, QColor, QPalette, QDrag, QPixmap,
                          QPainter, QPen, QBrush, QKeySequence)

from canvas import CircuitScene, CircuitView
from gate import GateItem, InputNode, OutputNode, create_gate, CONFIGURABLE_MSI_TYPES, RadixDisplayBlock
from wire import Wire
from notes import NoteItem
from simulation import SimulationEngine
from truth_table import TruthTableDialog
from waveform import WaveformDialog
from expression import ExpressionDialog
from save_load import (save_project, load_project, PROJECTS_DIR, ensure_projects_dir)
from export_image import export_scene_as_png, export_scene_as_jpeg
from kmap_solver import KMapDialog
from code_converter import CodeConverterDialog
from verilog_studio import VerilogStudioDialog
from ai_chatbot import ChatbotPanel
from project_browser import ProjectBrowserPanel
from signal_animator import SignalAnimator
from mosfet_simulator import MosfetSimulatorDialog
from ic_manual_dialog import ICDatasheetDialog

ensure_projects_dir()

# ── Global Component Catalog for Quick-Add & Dropdowns ────────────────
ALL_COMPONENTS = [
    # Basic Gates
    ("AND", "AND Gate (2-8 inputs)", "Basic Gates", "#42a5f5"),
    ("OR", "OR Gate (2-8 inputs)", "Basic Gates", "#ab47bc"),
    ("NOT", "Inverter (NOT Gate)", "Basic Gates", "#ef5350"),
    ("NAND", "NAND Gate (2-8 inputs)", "Basic Gates", "#66bb6a"),
    ("NOR", "NOR Gate (2-8 inputs)", "Basic Gates", "#ffa726"),
    ("XOR", "XOR Gate (2-8 inputs)", "Basic Gates", "#f06292"),
    ("XNOR", "XNOR Gate (2-8 inputs)", "Basic Gates", "#ce93d8"),
    ("BUFFER", "Buffer (Non-inverting)", "Basic Gates", "#4db6ac"),

    # Sequential Logic
    ("CLOCK", "Clock Generator (Square wave)", "Sequential Logic", "#00e676"),
    ("D_FF", "D Flip-Flop (Edge-triggered w/ Preset/Clear)", "Sequential Logic", "#00b0ff"),
    ("JK_FF", "JK Flip-Flop (Universal edge-triggered)", "Sequential Logic", "#7c4dff"),
    ("T_FF", "T Flip-Flop (Toggle / Divider)", "Sequential Logic", "#ff4081"),
    ("SR_FF", "Clocked SR Flip-Flop / Latch", "Sequential Logic", "#ff9100"),

    # MSI & Complex
    ("MUX", "Multiplexer (2:1, 4:1, 8:1, 16:1)", "MSI & Complex", "#1e88e5"),
    ("DEMUX", "Demultiplexer (1:2, 1:4, 1:8, 1:16)", "MSI & Complex", "#3949ab"),
    ("DECODER", "Decoder (2:4, 3:8, 4:16)", "MSI & Complex", "#e57373"),
    ("ENCODER", "Encoder (4:2, 8:3, 16:4)", "MSI & Complex", "#00897b"),
    ("PRIORITY_ENC", "Priority Encoder w/ Valid bit", "MSI & Complex", "#26a69a"),
    ("HALF_ADDER", "Half Adder (Sum & Carry)", "MSI & Complex", "#a1887f"),
    ("FULL_ADDER", "Full Adder (A, B, Cin)", "MSI & Complex", "#5c6bc0"),
    ("BCD7SEG", "BCD to 7-Segment Display Decoder", "MSI & Complex", "#9c27b0"),

    # I/O & Indicators
    ("INPUT", "Digital Input Toggle Switch (0/1)", "I/O & Displays", "#90a4ae"),
    ("OUTPUT", "Digital Probe Output / Indicator", "I/O & Displays", "#78909c"),
    ("RADIX_DISPLAY", "Bus Display & Multi-Radix Converter", "I/O & Displays", "#00e5ff"),

    # Virtual 74xx ICs
    ("IC_7400", "7400 Quad 2-Input NAND Gates (DIP-14)", "Virtual 74xx ICs", "#38bdf8"),
    ("IC_7402", "7402 Quad 2-Input NOR Gates (DIP-14)", "Virtual 74xx ICs", "#ffa726"),
    ("IC_7404", "7404 Hex Inverter (NOT) Gates (DIP-14)", "Virtual 74xx ICs", "#ef5350"),
    ("IC_7408", "7408 Quad 2-Input AND Gates (DIP-14)", "Virtual 74xx ICs", "#42a5f5"),
    ("IC_7432", "7432 Quad 2-Input OR Gates (DIP-14)", "Virtual 74xx ICs", "#ab47bc"),
    ("IC_7486", "7486 Quad 2-Input XOR Gates (DIP-14)", "Virtual 74xx ICs", "#f06292"),
    ("IC_7474", "7474 Dual D Flip-Flops w/ PRE/CLR (DIP-14)", "Virtual 74xx ICs", "#00b0ff"),
    ("IC_74138", "74138 3-to-8 Decoder / Demux (DIP-16)", "Virtual 74xx ICs", "#e57373"),
    ("IC_74151", "74151 8-to-1 Data Selector / MUX (DIP-16)", "Virtual 74xx ICs", "#1e88e5"),

    # Transistors & Analog
    ("NMOS", "NMOS Transistor Switch (N-Channel)", "Transistors & Analog", "#38bdf8"),
    ("PMOS", "PMOS Transistor Switch (P-Channel Active-Low)", "Transistors & Analog", "#c084fc"),
    ("PULLUP", "Pull-Up Resistor (VDD = 1)", "Transistors & Analog", "#4ade80"),
    ("PULLDOWN", "Pull-Down Resistor (GND = 0)", "Transistors & Analog", "#94a3b8"),
]

# Pop-down Category Definitions
DROPDOWN_CATEGORIES = [
    {
        'title': '⊞ Basic Gates',
        'color': '#42a5f5',
        'items': [
            ('AND', 'AND Gate (2-8 inputs)'),
            ('OR', 'OR Gate (2-8 inputs)'),
            ('NOT', 'Inverter (NOT Gate)'),
            ('NAND', 'NAND Gate (Universal)'),
            ('NOR', 'NOR Gate (Universal)'),
            ('XOR', 'XOR Gate (Exclusive OR)'),
            ('XNOR', 'XNOR Gate (Equivalence)'),
            ('BUFFER', 'Buffer (Non-inverting)'),
        ]
    },
    {
        'title': '⏱ Sequential Logic',
        'color': '#00e676',
        'items': [
            ('CLOCK', 'Clock Source (Pulse Generator)'),
            ('D_FF', 'D Flip-Flop (Edge-Triggered)'),
            ('JK_FF', 'JK Flip-Flop (Universal)'),
            ('T_FF', 'T Flip-Flop (Toggle Divider)'),
            ('SR_FF', 'SR Latch / Flip-Flop'),
        ]
    },
    {
        'title': '🔀 MSI & Complex',
        'color': '#1e88e5',
        'items': [
            ('MUX', 'Multiplexer (2:1, 4:1, 8:1, 16:1)'),
            ('DEMUX', 'Demultiplexer (1:2, 1:4, 1:8, 1:16)'),
            ('PRIORITY_ENC', 'Priority Encoder w/ Valid bit'),
            ('DECODER', 'Decoder (2:4, 3:8, 4:16)'),
            ('ENCODER', 'Binary Encoder (4:2, 8:3)'),
            ('HALF_ADDER', 'Half Adder (Sum & Carry)'),
            ('FULL_ADDER', 'Full Adder (A, B, Cin)'),
            ('BCD7SEG', 'BCD to 7-Segment Decoder'),
        ]
    },
    {
        'title': '🔌 I/O & Displays',
        'color': '#90a4ae',
        'items': [
            ('INPUT', 'Digital Input Toggle Switch (0/1)'),
            ('OUTPUT', 'Digital Output Probe Indicator'),
            ('RADIX_DISPLAY', 'Bus Display & Multi-Radix Converter (2-16b)'),
        ]
    },
    {
        'title': '🖲 Virtual IC 74xx',
        'color': '#f59e0b',
        'items': [
            ('IC_7400', '7400 Quad 2-In NAND (DIP-14)'),
            ('IC_7402', '7402 Quad 2-In NOR (DIP-14)'),
            ('IC_7404', '7404 Hex Inverter NOT (DIP-14)'),
            ('IC_7408', '7408 Quad 2-In AND (DIP-14)'),
            ('IC_7432', '7432 Quad 2-In OR (DIP-14)'),
            ('IC_7486', '7486 Quad 2-In XOR (DIP-14)'),
            ('IC_7474', '7474 Dual D-FF w/ PRE/CLR (DIP-14)'),
            ('IC_74138', '74138 3-to-8 Decoder (DIP-16)'),
            ('IC_74151', '74151 8-to-1 MUX Selector (DIP-16)'),
        ]
    },
    {
        'title': '🔬 Transistors',
        'color': '#38bdf8',
        'items': [
            ('NMOS', 'NMOS Transistor Switch (N-Channel)'),
            ('PMOS', 'PMOS Transistor Switch (P-Channel)'),
            ('PULLUP', 'Pull-Up Resistor (VDD = 1)'),
            ('PULLDOWN', 'Pull-Down Resistor (GND = 0)'),
        ]
    },
]

# Short display labels for compact palette buttons
SHORT_LABELS = {
    'D_FF': 'D-FF',
    'JK_FF': 'JK-FF',
    'T_FF': 'T-FF',
    'SR_FF': 'SR-FF',
    'PRIORITY_ENC': 'P-ENC',
    'HALF_ADDER': 'H-ADD',
    'FULL_ADDER': 'F-ADD',
    'BCD7SEG': '7-SEG',
    'RADIX_DISPLAY': 'RADIX',
    'IC_7400': '7400',
    'IC_7402': '7402',
    'IC_7404': '7404',
    'IC_7408': '7408',
    'IC_7432': '7432',
    'IC_7486': '7486',
    'IC_7474': '7474',
    'IC_74138': '74138',
    'IC_74151': '74151',
    'PULLUP': 'PULL-UP',
    'PULLDOWN': 'PULL-DN',
}


class DraggablePaletteButton(QPushButton):
    """Component palette button supporting both click-to-place and drag-and-drop to canvas."""
    def __init__(self, gate_type, label, tooltip="", on_click=None, parent=None):
        super().__init__(label, parent)
        self.gate_type = gate_type
        self.on_click = on_click
        self._drag_start_pos = None
        self.setToolTip(tooltip or f"{label} — Click to place at center, or drag to canvas")
        self.setFixedHeight(28)
        self.setFont(QFont("Segoe UI", 9))
        self.setCursor(Qt.PointingHandCursor)
        if on_click:
            self.clicked.connect(lambda: self.on_click(self.gate_type))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.LeftButton) and self._drag_start_pos is not None:
            if (event.pos() - self._drag_start_pos).manhattanLength() >= QApplication.startDragDistance():
                drag = QDrag(self)
                mime = QMimeData()
                mime.setText(self.gate_type)
                drag.setMimeData(mime)

                pix = QPixmap(self.size())
                pix.fill(Qt.transparent)
                painter = QPainter(pix)
                self.render(painter)
                painter.end()
                drag.setPixmap(pix)
                drag.setHotSpot(event.pos())
                drag.exec_(Qt.CopyAction)
                self._drag_start_pos = None
                return
        super().mouseMoveEvent(event)


class PaletteAccordionGroup(QWidget):
    """Collapsible category group with an expandable/collapsible button header."""
    def __init__(self, title, color_accent, items, on_click, parent=None):
        super().__init__(parent)
        self.raw_title = title
        self.color_accent = color_accent
        self.items = items
        self.on_click = on_click
        self.is_expanded = True

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(2)

        # Header Toggle Button
        self.toggle_btn = QPushButton(f"▼  {title}")
        self.toggle_btn.setFixedHeight(26)
        self.toggle_btn.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                padding-left: 6px;
                border: none;
                border-left: 3px solid {color_accent};
                background: transparent;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(88, 166, 255, 0.12);
            }}
        """)
        self.toggle_btn.clicked.connect(self.toggle)
        lay.addWidget(self.toggle_btn)

        # Content Container (2-Column Grid)
        self.content_widget = QWidget()
        grid = QGridLayout(self.content_widget)
        grid.setContentsMargins(4, 2, 4, 2)
        grid.setSpacing(4)

        total = len(items)
        for idx, (k, desc) in enumerate(items):
            row = idx // 2
            col = idx % 2
            short_lbl = SHORT_LABELS.get(k, k)
            btn = DraggablePaletteButton(k, short_lbl, tooltip=f"{k}: {desc}", on_click=self.on_click)
            if idx == total - 1 and col == 0:
                grid.addWidget(btn, row, 0, 1, 2)
            else:
                grid.addWidget(btn, row, col)

        lay.addWidget(self.content_widget)

    def toggle(self):
        self.is_expanded = not self.is_expanded
        self.content_widget.setVisible(self.is_expanded)
        arrow = "▼" if self.is_expanded else "▶"
        self.toggle_btn.setText(f"{arrow}  {self.raw_title}")

    def set_expanded(self, expanded: bool):
        self.is_expanded = expanded
        self.content_widget.setVisible(self.is_expanded)
        arrow = "▼" if self.is_expanded else "▶"
        self.toggle_btn.setText(f"{arrow}  {self.raw_title}")


# ── Main Application Window ───────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Digital Logic Simulator — EDA Studio")
        self.setMinimumSize(1200, 750)
        self._current_file = None
        self._anim_speed = 'medium'
        self._animator = None
        self.current_theme = "dark"

        self._build_ui()
        self._build_menubar()
        self._build_statusbar()
        self._connect_signals()

        # Apply default theme (Dark Mode)
        self._apply_theme("dark")

        # Install event filter on canvas viewport for live status bar coordinate tracking
        self.view.viewport().setMouseTracking(True)
        self.view.viewport().installEventFilter(self)

        # Background Simulation Loop
        self._sim_timer = QTimer()
        self._sim_timer.setInterval(120)
        self._sim_timer.timeout.connect(self._auto_simulate)
        self._sim_timer.start()

    def eventFilter(self, watched, event):
        """Track mouse move over canvas viewport to update live status bar coordinates."""
        if hasattr(self, 'view') and watched == self.view.viewport():
            if event.type() == QEvent.MouseMove:
                scene_pos = self.view.mapToScene(event.pos())
                if hasattr(self, '_coord_lbl'):
                    self._coord_lbl.setText(f"X: {int(scene_pos.x())}, Y: {int(scene_pos.y())}")
        return super().eventFilter(watched, event)

    # ── Workspace Layout Architecture ─────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 1. Main Center Workspace: Top Command Bar + Canvas View
        canvas_container = QWidget()
        cv_lay = QVBoxLayout(canvas_container)
        cv_lay.setContentsMargins(0, 0, 0, 0)
        cv_lay.setSpacing(0)

        # Expansive Circuit Canvas (Maximum Screen Space)
        self.scene = CircuitScene()
        self.view = CircuitView(self.scene)

        # Top Command & Pop-Down Component Insertion Bar
        self._top_bar = self._build_top_command_bar()
        cv_lay.addWidget(self._top_bar)
        cv_lay.addWidget(self.view, stretch=1)

        # 2. Left Component Palette (Scrollable & Collapsible Accordion)
        self._left_scroll = self._build_left_palette()

        # 3. Horizontal QSplitter (Left Palette + Central Canvas)
        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.addWidget(self._left_scroll)
        self._splitter.addWidget(canvas_container)
        self._splitter.setSizes([200, 1000])
        self._splitter.setCollapsible(0, False)
        self._splitter.setCollapsible(1, False)

        root.addWidget(self._splitter, stretch=1)

        # 4. Dedicated Right-Hand Utility & Analysis Tool Strip (Opposite to Gates)
        self._utility_strip = self._build_right_utility_strip()
        root.addWidget(self._utility_strip)

        # 5. Dedicated Dock Panels (Hidden by default, slide out when triggered from Right Strip)
        self._chatbot_dock = ChatbotPanel(self)
        self._chatbot_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, self._chatbot_dock)
        self._chatbot_dock.hide()

        self._browser_dock = ProjectBrowserPanel(self)
        self._browser_dock.open_project.connect(self._open_project_path)
        self._browser_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, self._browser_dock)
        self._browser_dock.hide()

    # ── Left Component Palette (Scrollable & Accordion Groups) ────────
    def _build_left_palette(self):
        """Construct the vertically scrollable left palette with collapsible category accordions."""
        palette_content = QWidget()
        pal_lay = QVBoxLayout(palette_content)
        pal_lay.setContentsMargins(6, 6, 6, 6)
        pal_lay.setSpacing(6)

        # Header with title and quick collapse/expand all buttons
        hdr_bar = QWidget()
        hdr_lay = QHBoxLayout(hdr_bar)
        hdr_lay.setContentsMargins(4, 2, 4, 4)
        hdr_lay.setSpacing(4)

        lbl = QLabel("COMPONENTS")
        lbl.setFont(QFont("Consolas", 8, QFont.Bold))
        lbl.setStyleSheet("color: #8b949e; letter-spacing: 1px;")
        hdr_lay.addWidget(lbl)
        hdr_lay.addStretch()

        btn_collapse_all = QPushButton("⊟")
        btn_collapse_all.setToolTip("Collapse All Categories")
        btn_collapse_all.setFixedSize(22, 22)
        btn_collapse_all.setCursor(Qt.PointingHandCursor)
        btn_collapse_all.clicked.connect(self._collapse_all_categories)
        hdr_lay.addWidget(btn_collapse_all)

        btn_expand_all = QPushButton("⊞")
        btn_expand_all.setToolTip("Expand All Categories")
        btn_expand_all.setFixedSize(22, 22)
        btn_expand_all.setCursor(Qt.PointingHandCursor)
        btn_expand_all.clicked.connect(self._expand_all_categories)
        hdr_lay.addWidget(btn_expand_all)

        pal_lay.addWidget(hdr_bar)

        # Build accordion sections for each category
        self._accordion_groups = []
        for cat in DROPDOWN_CATEGORIES:
            group = PaletteAccordionGroup(
                cat['title'], cat['color'], cat['items'], self._place_component_center
            )
            pal_lay.addWidget(group)
            self._accordion_groups.append(group)

        pal_lay.addStretch()

        # Wrap entire left palette container inside a QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(palette_content)
        scroll.setMinimumWidth(160)

        self._palette_scroll = scroll
        return scroll

    def _collapse_all_categories(self):
        for g in getattr(self, '_accordion_groups', []):
            g.set_expanded(False)

    def _expand_all_categories(self):
        for g in getattr(self, '_accordion_groups', []):
            g.set_expanded(True)

    def _toggle_left_palette(self):
        """Toggle left component palette visibility for maximum canvas space."""
        if hasattr(self, '_left_scroll'):
            is_hidden = self._left_scroll.isHidden()
            self._left_scroll.setVisible(is_hidden)
            self._status_lbl.setText("Component palette " + ("opened" if is_hidden else "hidden"))

    # ── Top Command & Pop-down Component Bar ──────────────────────────
    def _build_top_command_bar(self):
        bar = QWidget()
        bar.setFixedHeight(42)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(5)

        # File & Simulation Action Buttons
        def action_btn(text, tip, slot, primary=False):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.setFixedHeight(28)
            b.clicked.connect(slot)
            return b

        self._btn_palette = action_btn("☰", "Toggle Component Palette (Ctrl+B)", self._toggle_left_palette)
        self._btn_new = action_btn("📄 New", "New Project (Ctrl+N)", self._new_circuit)
        self._btn_open = action_btn("📂 Open", "Open Project (Ctrl+O)", self._open_project)
        self._btn_save = action_btn("💾 Save", "Save Project (Ctrl+S)", self._save_project)
        self._btn_run = action_btn("▶ Run", "Run Simulation Cycle (F5)", self._run_simulation)
        self._btn_anim = action_btn("✨ Animate", "Animate Signal Flow (F9)", self._run_animated)

        for b in (self._btn_palette, self._btn_new, self._btn_open, self._btn_save, self._btn_run, self._btn_anim):
            lay.addWidget(b)

        lay.addWidget(self._make_vsep())

        # Pop-down Category Buttons for Component Insertion
        self._category_buttons = []
        for cat in DROPDOWN_CATEGORIES:
            btn = QToolButton()
            btn.setText(f"{cat['title']} ▾")
            btn.setPopupMode(QToolButton.InstantPopup)
            btn.setFixedHeight(28)
            btn.setCursor(Qt.PointingHandCursor)

            menu = QMenu(btn)
            for item_key, item_desc in cat['items']:
                act = menu.addAction(f"●  {item_key:<12} —  {item_desc}")
                act.triggered.connect(lambda checked, k=item_key: self._place_component_center(k))

            btn.setMenu(menu)
            lay.addWidget(btn)
            self._category_buttons.append((btn, cat['color']))

        # Quick Add Search Box
        self._quick_search = QLineEdit()
        self._quick_search.setPlaceholderText("🔍 Quick Add (Ctrl+Space)...")
        self._quick_search.setFixedWidth(190)
        self._quick_search.setFixedHeight(28)

        search_entries = [f"{k} — {desc}" for k, desc, c, col in ALL_COMPONENTS]
        completer = QCompleter(search_entries, self._quick_search)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self._quick_search.setCompleter(completer)
        completer.activated.connect(self._on_quick_add_activated)
        self._quick_search.returnPressed.connect(lambda: self._on_quick_add_activated(self._quick_search.text()))
        lay.addWidget(self._quick_search)

        # Shortcut Ctrl+Space to focus quick search
        QShortcut(QKeySequence("Ctrl+Space"), self, activated=self._focus_quick_search)
        # Shortcut Ctrl+B to toggle component palette
        QShortcut(QKeySequence("Ctrl+B"), self, activated=self._toggle_left_palette)

        lay.addStretch()

        # Canvas View Controls (Zoom & Fit)
        self._btn_zin = action_btn("⊕", "Zoom In (Ctrl++)", self.view._zoom_in)
        self._btn_zout = action_btn("⊖", "Zoom Out (Ctrl+-)", self.view._zoom_out)
        self._btn_fit = action_btn("⊡ Fit", "Fit to View (Ctrl+F)", self.view.fit_circuit)

        for b in (self._btn_zin, self._btn_zout, self._btn_fit):
            lay.addWidget(b)

        lay.addWidget(self._make_vsep())

        # Live Light Mode / Dark Mode Switcher Toggle
        self._theme_btn = QPushButton("🌙 Dark")
        self._theme_btn.setFixedHeight(28)
        self._theme_btn.setToolTip("Toggle Light Mode / Dark Mode Theme")
        self._theme_btn.clicked.connect(self._toggle_theme)
        lay.addWidget(self._theme_btn)

        return bar

    def _make_vsep(self):
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFixedHeight(22)
        line.setStyleSheet("color: #30363d; margin: 0 4px;")
        return line

    def _place_component_center(self, gate_type, size=None):
        """Place the requested component neatly at the center of the active canvas viewport."""
        view_rect = self.view.viewport().rect()
        pos = self.view.mapToScene(view_rect.center())
        self.scene.add_gate(gate_type, pos=pos, size_config=size)
        self._status_lbl.setText(f"Added {gate_type} to canvas center")

    def _focus_quick_search(self):
        if hasattr(self, '_quick_search'):
            self._quick_search.setFocus()
            self._quick_search.selectAll()

    def _on_quick_add_activated(self, text):
        t = text.strip()
        if not t: return

        gt = None
        for key, desc, cat, col in ALL_COMPONENTS:
            if t == key or t == f"{key} — {desc}" or t.lower() == key.lower():
                gt = key
                break
            if key.startswith("IC_") and (t == key[3:] or t.lower() == f"74{key[3:]}".lower()):
                gt = key
                break

        if not gt:
            for key, desc, cat, col in ALL_COMPONENTS:
                if t.lower() in key.lower() or t.lower() in desc.lower():
                    gt = key
                    break

        if gt:
            self._place_component_center(gt)
            self._quick_search.clear()
            self._quick_search.clearFocus()

    # ── Dedicated Right-Hand Utility & Analysis Tool Strip ─────────────
    def _build_right_utility_strip(self):
        """Construct a dedicated vertical utility strip on the right side of the canvas."""
        strip = QWidget()
        strip.setFixedWidth(66)
        lay = QVBoxLayout(strip)
        lay.setContentsMargins(4, 6, 4, 6)
        lay.setSpacing(4)

        hdr = QLabel("TOOLS")
        hdr.setFont(QFont("Consolas", 7, QFont.Bold))
        hdr.setAlignment(Qt.AlignCenter)
        hdr.setStyleSheet("color: #8b949e; letter-spacing: 1px; padding: 2px 0;")
        lay.addWidget(hdr)

        def tool_btn(icon_text, tip, slot):
            b = QPushButton(icon_text)
            b.setToolTip(tip)
            b.setFixedHeight(40)
            b.setFont(QFont("Segoe UI", 8))
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(slot)
            lay.addWidget(b)
            return b

        self._btn_ai = tool_btn("🤖\nAI", "Toggle AI Tutor & Troubleshooting Panel (Ctrl+I)", self._toggle_chatbot)
        self._btn_wave = tool_btn("📊\nWave", "Digital Waveform Timing Diagram (F8)", self._show_waveform)
        self._btn_table = tool_btn("📋\nTable", "Truth Table Generator (F6)", self._show_truth_table)
        self._btn_verilog = tool_btn("💻\nHDL", "Verilog Studio Modal (Ctrl+H)", self._show_verilog_studio)
        self._btn_kmap = tool_btn("🗺️\nK-Map", "K-Map Visual Minimizer (Ctrl+K)", self._show_kmap)
        self._btn_conv = tool_btn("⇄\nCode", "Digital Code System Converter", self._show_converter)
        self._btn_mosfet = tool_btn("🔬\nMOS", "MOSFET Physics Studio (Ctrl+M)", self._show_mosfet_simulator)
        self._btn_ic = tool_btn("📖\n74xx", "74xx Series IC Datasheet Manual (Ctrl+D)", lambda: self._show_ic_manual("7408"))
        self._btn_notes = tool_btn("📝\nNote", "Add Reference Note to Canvas (Ctrl+Shift+N)", self._add_note)
        self._btn_proj = tool_btn("📁\nFiles", "Toggle Visual Project Browser", self._toggle_browser)

        lay.addStretch()
        return strip

    def _toggle_chatbot(self):
        """Toggle AI Chatbot dock visibility."""
        is_hidden = self._chatbot_dock.isHidden()
        self._chatbot_dock.setVisible(is_hidden)
        self._status_lbl.setText("AI Tutor panel " + ("opened" if is_hidden else "closed"))

    def _toggle_browser(self):
        """Toggle Project Browser dock visibility."""
        is_hidden = self._browser_dock.isHidden()
        if is_hidden:
            self._browser_dock.refresh()
            self._browser_dock.show()
        else:
            self._browser_dock.hide()
        self._status_lbl.setText("Project Browser " + ("opened" if is_hidden else "closed"))

    # ── Light Mode / Dark Mode Live Theme Switcher ────────────────────
    def _toggle_theme(self):
        """Toggle between Dark Mode and Light Mode."""
        new_mode = "light" if self.current_theme == "dark" else "dark"
        self._apply_theme(new_mode)
        self._status_lbl.setText(f"Switched to {new_mode.capitalize()} Mode")

    def _apply_theme(self, mode="dark"):
        self.current_theme = mode
        is_dark = (mode == "dark")

        # Update Theme Switcher Button Text
        if hasattr(self, '_theme_btn'):
            self._theme_btn.setText("🌙 Dark" if is_dark else "☀️ Light")
            self._theme_btn.setToolTip(f"Current: {mode.capitalize()} Mode. Click to switch to {'Light' if is_dark else 'Dark'} Mode.")

        # Update Scene background & grid
        if hasattr(self, 'scene') and self.scene:
            self.scene.set_theme(mode)

        # Colors definition
        bg_canvas = "#0d1117" if is_dark else "#ffffff"
        bg_header = "#161b22" if is_dark else "#ffffff"
        bg_control = "#21262d" if is_dark else "#f1f5f9"
        border_col = "#30363d" if is_dark else "#cbd5e1"
        text_primary = "#e6edf3" if is_dark else "#0f172a"
        text_muted = "#8b949e" if is_dark else "#64748b"
        accent_col = "#58a6ff" if is_dark else "#2563eb"
        hover_col = "#30363d" if is_dark else "#e2e8f0"

        # Apply application palette
        pal = QPalette()
        pal.setColor(QPalette.Window,          QColor(bg_canvas))
        pal.setColor(QPalette.WindowText,      QColor(text_primary))
        pal.setColor(QPalette.Base,            QColor(bg_header))
        pal.setColor(QPalette.Text,            QColor(text_primary))
        pal.setColor(QPalette.Button,          QColor(bg_control))
        pal.setColor(QPalette.ButtonText,      QColor(text_primary))
        pal.setColor(QPalette.Highlight,       QColor(accent_col))
        pal.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        self.setPalette(pal)

        # Apply global stylesheet
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background: {bg_canvas};
                color: {text_primary};
                font-family: 'Segoe UI', system-ui, sans-serif;
            }}
            QMenuBar {{
                background: {bg_header};
                color: {text_primary};
                border-bottom: 1px solid {border_col};
                padding: 2px 4px;
                font-size: 11px;
            }}
            QMenuBar::item {{
                padding: 4px 8px;
                border-radius: 3px;
            }}
            QMenuBar::item:selected {{
                background: {hover_col};
                color: {accent_col};
            }}
            QMenu {{
                background: {bg_header};
                color: {text_primary};
                border: 1px solid {border_col};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 18px 6px 10px;
                font-size: 11px;
            }}
            QMenu::item:selected {{
                background: {accent_col};
                color: #ffffff;
                border-radius: 3px;
            }}
            QStatusBar {{
                background: {bg_header};
                color: {text_muted};
                border-top: 1px solid {border_col};
                font-size: 11px;
                font-family: Consolas, 'Segoe UI';
            }}
            QDockWidget {{
                color: {text_primary};
                font-size: 11px;
            }}
            QDockWidget::title {{
                background: {bg_header};
                padding: 6px 8px;
                border-bottom: 1px solid {border_col};
                font-weight: bold;
            }}
            QPushButton, QToolButton {{
                background: {bg_control};
                color: {text_primary};
                border: 1px solid {border_col};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }}
            QPushButton:hover, QToolButton:hover {{
                background: {hover_col};
                border-color: {accent_col};
                color: {accent_col};
            }}
            QPushButton:pressed, QToolButton:pressed {{
                background: {accent_col};
                color: #ffffff;
            }}
            QLineEdit {{
                background: {bg_control};
                color: {text_primary};
                border: 1px solid {border_col};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border-color: {accent_col};
            }}

            /* Thin, elegant vertical scrollbar */
            QScrollBar:vertical {{
                border: none;
                background: {bg_canvas};
                width: 6px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {border_col};
                min-height: 25px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {accent_col};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}

            /* Subtle draggable splitter handle */
            QSplitter::handle:horizontal {{
                background: {bg_control};
                width: 3px;
            }}
            QSplitter::handle:horizontal:hover {{
                background: {accent_col};
            }}
        """)

        # Style Left Palette Scroll Area
        if hasattr(self, '_left_scroll'):
            self._left_scroll.setStyleSheet(f"background: {bg_header}; border-right: 1px solid {border_col};")

        # Style Top Command Bar
        if hasattr(self, '_top_bar'):
            self._top_bar.setStyleSheet(f"background: {bg_header}; border-bottom: 1px solid {border_col};")

        # Style Right Utility Strip
        if hasattr(self, '_utility_strip'):
            self._utility_strip.setStyleSheet(f"background: {bg_header}; border-left: 1px solid {border_col};")

        # Update Status Bar Badges styling
        if hasattr(self, '_coord_lbl'):
            self._coord_lbl.setStyleSheet(f"color: {text_muted}; padding: 0 8px; border-left: 1px solid {border_col};")
        if hasattr(self, '_counts_lbl'):
            self._counts_lbl.setStyleSheet(f"color: {text_muted}; padding: 0 8px; border-left: 1px solid {border_col};")

    # ── Menu Bar ──────────────────────────────────────────────────────
    def _build_menubar(self):
        mb = self.menuBar()

        # File
        fm = mb.addMenu("File")
        fm.addAction(self._act("New Project",       "Ctrl+N",         self._new_circuit))
        fm.addAction(self._act("Open Project...",   "Ctrl+O",         self._open_project))
        fm.addAction(self._act("Save Project",      "Ctrl+S",         self._save_project))
        fm.addAction(self._act("Save As...",        "Ctrl+Shift+S",   self._save_project_as))
        fm.addSeparator()
        fm.addAction(self._act("Export PNG...",     "Ctrl+E",         lambda: export_scene_as_png(self.scene, self)))
        fm.addAction(self._act("Export JPEG...",    "Ctrl+Shift+E",   lambda: export_scene_as_jpeg(self.scene, self)))
        fm.addSeparator()
        fm.addAction(self._act("Exit",              "Ctrl+Q",         self.close))

        # Edit
        em = mb.addMenu("Edit")
        em.addAction(self._act("Delete Selected",   "Del",            self.scene.delete_selected))
        em.addAction(self._act("Select All",        "Ctrl+A",         lambda: [i.setSelected(True) for i in self.scene.items()]))
        em.addAction(self._act("Clear Canvas",      None,             self._clear_circuit))
        em.addSeparator()
        em.addAction(self._act("Add Reference Note","Ctrl+Shift+N",   self._add_note))

        # Simulate
        sm = mb.addMenu("Simulate")
        sm.addAction(self._act("Run Simulation",    "F5",             self._run_simulation))
        sm.addAction(self._act("Animated Run",      "F9",             self._run_animated))
        sm.addSeparator()
        sm.addAction(self._act("Truth Table",       "F6",             self._show_truth_table))
        sm.addAction(self._act("Boolean Expression","F7",             self._show_expression))
        sm.addAction(self._act("Waveform Viewer",   "F8",             self._show_waveform))

        # Tools
        tm = mb.addMenu("Tools")
        tm.addAction(self._act("Verilog Studio",    "Ctrl+H",         self._show_verilog_studio))
        tm.addAction(self._act("K-Map Solver",      "Ctrl+K",         self._show_kmap))
        tm.addAction(self._act("Code Converter",    "Ctrl+T",         self._show_converter))
        tm.addAction(self._act("MOSFET Physics",    "Ctrl+M",         self._show_mosfet_simulator))
        tm.addAction(self._act("74xx IC Manual",    "Ctrl+D",         lambda: self._show_ic_manual("7408")))
        tm.addSeparator()
        tm.addAction(self._act("AI Assistant",      "Ctrl+I",         self._toggle_chatbot))
        tm.addAction(self._act("Project Browser",   "Ctrl+P",         self._toggle_browser))

        # View
        vm = mb.addMenu("View")
        vm.addAction(self._act("Toggle Theme (Dark/Light)", "Ctrl+U", self._toggle_theme))
        vm.addSeparator()
        vm.addAction(self._act("Zoom In",           "Ctrl++",         self.view._zoom_in))
        vm.addAction(self._act("Zoom Out",          "Ctrl+-",         self.view._zoom_out))
        vm.addAction(self._act("Reset Zoom",        "Ctrl+0",         self.view.reset_zoom))
        vm.addAction(self._act("Fit Circuit View",  "Ctrl+F",         self.view.fit_circuit))

        # Help
        mb.addMenu("Help").addAction(self._act("About & Quick Guide", None, self._show_about))

    def _act(self, label, shortcut, slot):
        a = QAction(label, self)
        if shortcut:
            a.setShortcut(shortcut)
        a.triggered.connect(slot)
        return a

    # ── Slim Status Bar ───────────────────────────────────────────────
    def _build_statusbar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)

        # Left: Main status notification
        self._status_lbl = QLabel("✓ Ready")
        self._status_lbl.setFont(QFont("Consolas", 9))
        self._status_lbl.setStyleSheet("color: #8b949e; padding-left: 4px;")
        sb.addWidget(self._status_lbl, stretch=1)

        # Right Permanent Badges
        # 1. Cursor Coordinates
        self._coord_lbl = QLabel("X: 0, Y: 0")
        self._coord_lbl.setFont(QFont("Consolas", 9))
        self._coord_lbl.setStyleSheet("color: #8b949e; padding: 0 8px; border-left: 1px solid #30363d;")
        sb.addPermanentWidget(self._coord_lbl)

        # 2. Gate & Wire Counts
        self._counts_lbl = QLabel("Gates: 0 | Wires: 0")
        self._counts_lbl.setFont(QFont("Consolas", 9))
        self._counts_lbl.setStyleSheet("color: #8b949e; padding: 0 8px; border-left: 1px solid #30363d;")
        sb.addPermanentWidget(self._counts_lbl)

        # 3. Clock Status & Frequency
        self._clock_lbl = QLabel("Clock: None")
        self._clock_lbl.setFont(QFont("Consolas", 9))
        self._clock_lbl.setStyleSheet("color: #00e676; padding: 0 8px; border-left: 1px solid #30363d;")
        sb.addPermanentWidget(self._clock_lbl)

        # 4. Simulation Engine State
        self._sim_state_lbl = QLabel("● Sim: Active")
        self._sim_state_lbl.setFont(QFont("Consolas", 9, QFont.Bold))
        self._sim_state_lbl.setStyleSheet("color: #3fb950; padding: 0 8px; border-left: 1px solid #30363d;")
        sb.addPermanentWidget(self._sim_state_lbl)

        self._update_status_right()

    def _update_status_right(self):
        g = len(self.scene.gates)
        w = len(self.scene.wires)
        self._counts_lbl.setText(f"Gates: {g} | Wires: {w}")

        clocks = [gate for gate in self.scene.gates if getattr(gate, 'gate_type', '') == 'CLOCK']
        if clocks:
            freq = getattr(clocks[0], 'freq_hz', 1.0)
            running = getattr(clocks[0], 'is_running', True)
            self._clock_lbl.setText(f"Clock: {freq:.1f}Hz" if running else "Clock: Paused")
            self._clock_lbl.setStyleSheet("color: #00e676; padding: 0 8px; border-left: 1px solid #30363d;" if running else "color: #ffa657; padding: 0 8px; border-left: 1px solid #30363d;")
        else:
            self._clock_lbl.setText("Clock: None")
            self._clock_lbl.setStyleSheet("color: #8b949e; padding: 0 8px; border-left: 1px solid #30363d;")

    # ── Signal Connections ────────────────────────────────────────────
    def _connect_signals(self):
        self.scene.status_msg.connect(self._status_lbl.setText)
        self.scene.circuit_changed.connect(self._on_changed)

    @pyqtSlot()
    def _on_changed(self):
        self._update_status_right()

    # ── Simulation Triggers ───────────────────────────────────────────
    def _auto_simulate(self):
        if self.scene.gates:
            try:
                SimulationEngine(self.scene.gates, self.scene.wires).run()
                for g in self.scene.gates:
                    g.update()
                self._update_status_right()
            except:
                pass

    def _run_simulation(self):
        try:
            SimulationEngine(self.scene.gates, self.scene.wires).run()
            for g in self.scene.gates:
                g.update()
            self._status_lbl.setText("✓ Simulation cycle complete")
            self._update_status_right()
        except Exception as e:
            self._status_lbl.setText(f"Error: {e}")

    def _run_animated(self):
        if not self.scene.gates:
            self._status_lbl.setText("Add gates first")
            return
        if self._animator:
            self._animator.stop()
        self._animator = SignalAnimator(self.scene, self.scene.gates, self.scene.wires)
        self._animator.on_finished(lambda: self._status_lbl.setText("✓ Animation complete"))
        self._animator.play(self._anim_speed)
        self._status_lbl.setText(f"▶ Animating signal flow ({self._anim_speed})...")

    def _pause_animation(self):
        if self._animator:
            self._animator.pause()
        self._status_lbl.setText("⏸ Animation paused")

    def _stop_animation(self):
        if self._animator:
            self._animator.stop()
        self._status_lbl.setText("⏹ Animation stopped")

    # ── Dialog Openers ────────────────────────────────────────────────
    def _show_truth_table(self):
        try:
            eng = SimulationEngine(self.scene.gates, self.scene.wires)
            il, ol, rows = eng.generate_truth_table()
            if not il:
                QMessageBox.information(self, "Truth Table", "Add INPUT and OUTPUT nodes first.")
                return
            TruthTableDialog(il, ol, rows, self).exec_()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _show_expression(self):
        try:
            exprs = SimulationEngine(self.scene.gates, self.scene.wires).generate_boolean_expression()
            ExpressionDialog(exprs, self).exec_()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _show_waveform(self):
        try:
            eng = SimulationEngine(self.scene.gates, self.scene.wires)
            WaveformDialog(eng, self).exec_()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _show_kmap(self):
        KMapDialog(self).exec_()

    def _show_converter(self):
        CodeConverterDialog(self).exec_()

    def _show_verilog_studio(self):
        VerilogStudioDialog(self.scene, self).exec_()

    def _show_mosfet_simulator(self):
        MosfetSimulatorDialog(parent=self).exec_()

    def _show_ic_manual(self, target_ic="7408"):
        ICDatasheetDialog(target_ic=target_ic, main_window=self, parent=self).exec_()

    # ── File Operations ───────────────────────────────────────────────
    def _new_circuit(self):
        if self.scene.gates:
            if QMessageBox.question(self, "New Project", "Clear canvas and start a new circuit?",
                                    QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
                return
        self.scene.clear_circuit()
        self._current_file = None
        self._on_changed()
        self._status_lbl.setText("✓ New project created")

    def _save_project(self):
        if self._current_file:
            self._do_save_project(self._current_file)
        else:
            self._save_project_as()

    def _save_project_as(self):
        ensure_projects_dir()
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project", PROJECTS_DIR, "Circuit Files (*.json)")
        if path:
            if not path.endswith('.json'):
                path += '.json'
            self._do_save_project(path)
            self._current_file = path
            self._on_changed()

    def _do_save_project(self, path):
        try:
            json_path, _ = save_project(
                self.scene.gates, self.scene.wires, self.scene, path, notes=self.scene.notes)
            self._status_lbl.setText(f"💾 Saved: {os.path.basename(json_path)}")
            if hasattr(self, '_browser_dock') and self._browser_dock.isVisible():
                self._browser_dock.refresh()
        except Exception as e:
            QMessageBox.warning(self, "Save Error", str(e))

    def _open_project(self):
        ensure_projects_dir()
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", PROJECTS_DIR, "Circuit Files (*.json)")
        if path:
            self._open_project_path(path)

    def _open_project_path(self, path):
        try:
            self.scene.clear_circuit()
            gates, wire_data, gate_map, notes, _ = load_project(path)
            for g in gates:
                self.scene.addItem(g)
                self.scene.gates.append(g)
            for wd in wire_data:
                sg = gate_map.get(wd['src_gate_id'])
                dg = gate_map.get(wd['dst_gate_id'])
                if sg and dg:
                    si, di = wd['src_pin_idx'], wd['dst_pin_idx']
                    if si < len(sg.output_pins) and di < len(dg.input_pins):
                        wire = Wire(sg.output_pins[si], dg.input_pins[di])
                        self.scene.addItem(wire)
                        self.scene.wires.append(wire)
            for n in notes:
                self.scene.addItem(n)
                self.scene.notes.append(n)
            self._current_file = path
            self._on_changed()
            self._status_lbl.setText(f"📂 Loaded: {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.warning(self, "Load Error", str(e))

    def _clear_circuit(self):
        if self.scene.gates:
            if QMessageBox.question(self, "Clear Canvas", "Delete all gates, wires, and notes on canvas?",
                                    QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
                return
        self.scene.clear_circuit()
        self._on_changed()
        self._status_lbl.setText("Canvas cleared")

    def _add_note(self):
        center = self.view.mapToScene(self.view.viewport().rect().center())
        self.scene.add_note(pos=center)
        self._status_lbl.setText("Added reference note to canvas")

    def _show_about(self):
        QMessageBox.about(self, "About Digital Logic Simulator",
            "<b style='font-family:Consolas;font-size:14px;color:#58a6ff'>Digital Logic Simulator — EDA Studio</b><br>"
            "<i>Professional Electronic Design Automation Workstation</i><br><br>"
            "<b>Key Features:</b><br>"
            "• <b>Pop-down Insertion:</b> Clean dropdown menus for Basic Gates, Sequential Logic, MSI, I/O, and ICs.<br>"
            "• <b>Right Utility Strip:</b> Dedicated one-click launcher for AI Tutor, Waveform, Truth Table, Verilog, K-Map, and Notes.<br>"
            "• <b>Live Theme Switcher:</b> Switch instantaneously between Dark Mode and Light Mode with dynamic canvas refresh.<br>"
            "• <b>Configurable Bus Display:</b> Parallel bus multi-radix readout (2 to 16 bits, Hex/Oct/BCD/Signed).<br>"
            "• <b>Bidirectional Verilog:</b> Synthesize schematics to HDL and import Verilog code to canvas.<br>"
            "• <b>Virtual 74xx DIP ICs:</b> Realistic pinouts, power rail verification, and complete datasheets.<br>"
            "• <b>Semiconductor Physics:</b> Interactive 2D MOSFET cross-section & electron drift animation.<br><br>"
            "<b>Controls:</b><br>"
            "• <b>Pop-down Buttons:</b> Click category ▾ to insert any component at center<br>"
            "• <b>Click Pin ➔ Pin:</b> Connect wires (Green=Out, Blue=In)<br>"
            "• <b>Double-Click INPUT:</b> Toggle 0/1; double-click Bus Display to cycle radix<br>"
            "• <b>Right-Click:</b> Inspect properties, configure size, or delete<br>"
            "• <b>Ctrl+Space:</b> Quick-add search | <b>Ctrl+U:</b> Toggle Theme<br>"
            "• <b>Mouse Wheel:</b> Zoom | <b>Middle-Click Drag:</b> Pan canvas")
