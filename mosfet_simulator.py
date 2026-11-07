"""
mosfet_simulator.py - Interactive MOSFET Physics & Visual Switching Simulator.
Features:
- Live parameter sliders (V_GS, V_DS, V_TH) with instant Shockley equation calculation.
- Animated semiconductor cross-section showing inversion channel formation, pinch-off, and carrier flow.
- Matplotlib live I_D vs V_DS curve family with dynamic operating point tracker.
- CMOS Inverter visual application tab with interactive VTC (Voltage Transfer Characteristic).
"""
import math
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QRadioButton, QButtonGroup, QTabWidget, QWidget,
    QGroupBox, QFrame, QGridLayout
)
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPainterPath

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np


class SemiconductorView(QWidget):
    """
    Renders an animated 2D cross-section of the MOSFET semiconductor structure:
    - Substrate (P-type for NMOS / N-type for PMOS)
    - Source & Drain wells (N+ for NMOS / P+ for PMOS)
    - Thin Gate Oxide layer (SiO2)
    - Gate Electrode
    - Inversion Channel (forms when V_GS > V_TH)
    - Pinch-off tapering near Drain when V_DS >= V_GS - V_TH
    - Moving charge carriers (electrons / holes)
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(240)
        self.transistor_type = "NMOS"
        self.v_gs = 3.0
        self.v_ds = 2.0
        self.v_th = 1.0
        self.mode = "Saturation"
        self.i_d = 0.0

        # Animation state for carrier flow
        self.carrier_offset = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate_carriers)
        self.timer.start(40)

    def _animate_carriers(self):
        if self.i_d > 0.01:
            speed = min(8.0, 1.0 + self.i_d * 2.5)
            self.carrier_offset = (self.carrier_offset + speed) % 40.0
            self.update()

    def update_params(self, t_type, v_gs, v_ds, v_th, mode, i_d):
        self.transistor_type = t_type
        self.v_gs = v_gs
        self.v_ds = v_ds
        self.v_th = v_th
        self.mode = mode
        self.i_d = i_d
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Canvas Background
        painter.fillRect(0, 0, w, h, QBrush(QColor("#0d1117")))

        is_nmos = (self.transistor_type == "NMOS")
        sub_color = QColor("#1e293b") if is_nmos else QColor("#2a1b3d")
        well_color = QColor("#0284c7") if is_nmos else QColor("#9333ea")
        channel_color = QColor("#38bdf8") if is_nmos else QColor("#c084fc")
        carrier_color = QColor("#fef08a") if is_nmos else QColor("#f472b6")

        # Dimensions of substrate & regions
        pad_x = 40
        top_y = 70
        sub_h = h - top_y - 20
        sub_w = w - 2 * pad_x

        # 1. P-Substrate (NMOS) / N-Substrate (PMOS) Body
        painter.setPen(QPen(QColor("#475569"), 1.5))
        painter.setBrush(QBrush(sub_color))
        painter.drawRoundedRect(pad_x, top_y, sub_w, sub_h, 6, 6)

        sub_label = "P-type Silicon Substrate (Si)" if is_nmos else "N-type Silicon Substrate (Si)"
        painter.setFont(QFont("Consolas", 9, QFont.Bold))
        painter.setPen(QColor("#94a3b8"))
        painter.drawText(pad_x + 12, top_y + sub_h - 12, sub_label)

        # 2. Source Well (Left) & Drain Well (Right)
        well_w = 90
        well_h = 75

        # Source Well
        painter.setPen(QPen(well_color.lighter(130), 1.5))
        painter.setBrush(QBrush(well_color))
        painter.drawRoundedRect(pad_x + 20, top_y, well_w, well_h, 4, 4)

        # Drain Well
        drain_x = pad_x + sub_w - 20 - well_w
        painter.drawRoundedRect(drain_x, top_y, well_w, well_h, 4, 4)

        # Well Labels
        painter.setFont(QFont("Consolas", 8, QFont.Bold))
        painter.setPen(QColor("#ffffff"))
        src_tag = "Source\n(n+)" if is_nmos else "Source\n(p+)"
        drn_tag = "Drain\n(n+)" if is_nmos else "Drain\n(p+)"
        painter.drawText(pad_x + 20, top_y + 16, well_w, 36, Qt.AlignCenter, src_tag)
        painter.drawText(drain_x, top_y + 16, well_w, 36, Qt.AlignCenter, drn_tag)

        # 3. Gate Oxide Layer (SiO2)
        gate_left = pad_x + 20 + well_w - 10
        gate_right = drain_x + 10
        gate_w = gate_right - gate_left
        ox_h = 10
        ox_y = top_y - ox_h

        painter.setPen(QPen(QColor("#64748b"), 1))
        painter.setBrush(QBrush(QColor("#e2e8f0")))
        painter.drawRect(gate_left, ox_y, gate_w, ox_h)
        painter.setFont(QFont("Consolas", 6))
        painter.setPen(QColor("#0f172a"))
        painter.drawText(gate_left, ox_y, gate_w, ox_h, Qt.AlignCenter, "SiO2 Oxide")

        # 4. Metal / Polysilicon Gate Electrode
        gate_poly_h = 18
        gate_poly_y = ox_y - gate_poly_h
        painter.setPen(QPen(QColor("#f59e0b"), 1.5))
        painter.setBrush(QBrush(QColor("#b45309")))
        painter.drawRect(gate_left, gate_poly_y, gate_w, gate_poly_h)
        painter.setFont(QFont("Consolas", 8, QFont.Bold))
        painter.setPen(QColor("#ffffff"))
        painter.drawText(gate_left, gate_poly_y, gate_w, gate_poly_h, Qt.AlignCenter, "GATE (Metal)")

        # 5. Terminals & Contacts (Leads)
        painter.setPen(QPen(QColor("#cbd5e1"), 2.5))
        # Gate Terminal
        painter.drawLine(int(gate_left + gate_w/2), gate_poly_y, int(gate_left + gate_w/2), 16)
        painter.setFont(QFont("Consolas", 9, QFont.Bold))
        painter.setPen(QColor("#f59e0b"))
        painter.drawText(int(gate_left + gate_w/2 - 20), 14, f"VG={self.v_gs:.1f}V")

        # Source Terminal
        painter.setPen(QPen(QColor("#cbd5e1"), 2.5))
        painter.drawLine(int(pad_x + 20 + well_w/2), top_y, int(pad_x + 20 + well_w/2), 24)
        painter.setFont(QFont("Consolas", 9, QFont.Bold))
        painter.setPen(QColor("#38bdf8"))
        painter.drawText(int(pad_x + 20 + well_w/2 - 20), 22, "VS=0V")

        # Drain Terminal
        painter.setPen(QPen(QColor("#cbd5e1"), 2.5))
        painter.drawLine(int(drain_x + well_w/2), top_y, int(drain_x + well_w/2), 24)
        painter.setFont(QFont("Consolas", 9, QFont.Bold))
        painter.setPen(QColor("#ef4444"))
        painter.drawText(int(drain_x + well_w/2 - 20), 22, f"VD={self.v_ds:.1f}V")

        # 6. Inversion Conduction Channel & Pinch-Off
        v_ov = max(0.0, self.v_gs - self.v_th)
        if v_ov > 0.05:
            # Channel forms
            # Left thickness (at source): proportional to V_OV
            th_src = min(22.0, 5.0 + v_ov * 4.5)

            # Right thickness (at drain): proportional to V_GS - V_TH - V_DS
            v_ov_drain = max(0.0, v_ov - self.v_ds)
            th_drn = min(22.0, 5.0 + v_ov_drain * 4.5) if self.mode != "Saturation" else 0.0

            channel_path = QPainterPath()
            channel_path.moveTo(gate_left, top_y)
            channel_path.lineTo(gate_right, top_y)

            # Tapering bottom edge
            pinch_x = gate_right if self.mode != "Saturation" else (gate_left + gate_w * max(0.4, 1.0 - (self.v_ds - v_ov)*0.1))
            channel_path.lineTo(pinch_x, top_y + th_drn)
            channel_path.lineTo(gate_left, top_y + th_src)
            channel_path.closeSubpath()

            painter.setPen(QPen(channel_color.lighter(120), 1))
            painter.setBrush(QBrush(channel_color))
            painter.drawPath(channel_path)

            # Channel Label
            painter.setFont(QFont("Consolas", 7, QFont.Bold))
            painter.setPen(QColor("#0f172a"))
            chan_label = "e- Inversion Channel" if is_nmos else "Hole Inversion Channel"
            painter.drawText(gate_left, top_y + 1, gate_w, 14, Qt.AlignCenter, chan_label)

            # Pinch-off annotation if saturated
            if self.mode == "Saturation":
                painter.setPen(QPen(QColor("#ef4444"), 1.5, Qt.DashLine))
                painter.drawLine(int(pinch_x), top_y, int(pinch_x), int(top_y + 24))
                painter.setFont(QFont("Consolas", 7, QFont.Bold))
                painter.setPen(QColor("#ef4444"))
                painter.drawText(int(pinch_x - 30), int(top_y + 26), 70, 14, Qt.AlignCenter, "Pinch-Off!")

            # 7. Animated Moving Charge Carriers (Electrons / Holes)
            if self.i_d > 0.02:
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(carrier_color))
                num_dots = 12
                c_len = gate_right - gate_left
                for d_idx in range(num_dots):
                    x_dot = gate_left + ((d_idx * (c_len / num_dots) + self.carrier_offset) % c_len)
                    # Interpolate Y in the channel
                    y_dot = top_y + 6
                    painter.drawEllipse(QPointF(x_dot, y_dot), 3.0, 3.0)


class MosfetSimulatorDialog(QDialog):
    """
    Dedicated Interactive MOSFET Visual Simulation & Characteristic Playground dialog.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔬 Interactive MOSFET Physics & Visual Switching Simulator")
        self.resize(1060, 720)
        self.setMinimumSize(960, 640)
        self._apply_style()
        self._build_ui()
        self._recalculate()

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog { background: #0d1117; color: #e6edf3; }
            QLabel { color: #8b949e; font-family: Consolas; font-size: 11px; }
            QGroupBox { border: 1px solid #30363d; border-radius: 6px; margin-top: 10px; font-family: Consolas; font-weight: bold; color: #58a6ff; font-size: 11px; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
            QTabWidget::pane { border: 1px solid #30363d; background: #161b22; }
            QTabBar::tab { background: #161b22; color: #8b949e; border: 1px solid #30363d; border-bottom: none; padding: 8px 18px; font-family: Consolas; }
            QTabBar::tab:selected { background: #0d1117; color: #58a6ff; border-bottom: 2px solid #58a6ff; font-weight: bold; }
            QSlider::groove:horizontal { border: 1px solid #30363d; height: 6px; background: #21262d; border-radius: 3px; }
            QSlider::sub-page:horizontal { background: #1f6feb; border-radius: 3px; }
            QSlider::handle:horizontal { background: #58a6ff; border: 1px solid #388bfd; width: 16px; margin-top: -5px; margin-bottom: -5px; border-radius: 8px; }
            QRadioButton { color: #e6edf3; font-family: Consolas; font-weight: bold; }
            QRadioButton::indicator { width: 14px; height: 14px; }
            QPushButton { background: #21262d; color: #e6edf3; border: 1px solid #30363d; border-radius: 4px; padding: 6px 14px; font-family: Consolas; }
            QPushButton:hover { background: #1f6feb; border-color: #58a6ff; }
        """)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # Title bar
        top_bar = QHBoxLayout()
        title = QLabel("MOSFET Conduction Physics & Characteristic Curve Explorer")
        title.setFont(QFont("Consolas", 13, QFont.Bold))
        title.setStyleSheet("color: #58a6ff;")
        top_bar.addWidget(title)

        top_bar.addStretch()

        # Type Selector Radio Buttons
        self.btn_group = QButtonGroup(self)
        self.radio_nmos = QRadioButton("N-Channel (NMOS)")
        self.radio_pmos = QRadioButton("P-Channel (PMOS)")
        self.radio_nmos.setChecked(True)
        self.btn_group.addButton(self.radio_nmos)
        self.btn_group.addButton(self.radio_pmos)
        self.radio_nmos.toggled.connect(self._recalculate)
        top_bar.addWidget(self.radio_nmos)
        top_bar.addWidget(self.radio_pmos)

        root.addLayout(top_bar)

        # Main Tabs
        tabs = QTabWidget()
        tabs.addTab(self._build_physics_tab(), "  ⚡ Physical Semiconductor Model  ")
        tabs.addTab(self._build_curves_tab(),  "  📈 I_D vs V_DS Curves  ")
        tabs.addTab(self._build_cmos_tab(),    "  🔄 CMOS Inverter Application  ")
        root.addWidget(tabs, stretch=1)

    # ── Tab 1: Physics Cross-Section & Parameters ─────────────────────
    def _build_physics_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        # Visual Cross-Section
        self.semi_view = SemiconductorView(self)
        lay.addWidget(self.semi_view, stretch=1)

        # Parameter Sliders Grid
        ctrl_box = QGroupBox("Interactive Voltage Controls & Device Parameters")
        grid = QGridLayout(ctrl_box)
        grid.setSpacing(8)

        # V_GS Slider (-5V to +5V)
        grid.addWidget(QLabel("Gate-Source Voltage (V_GS):"), 0, 0)
        self.slider_vgs = QSlider(Qt.Horizontal)
        self.slider_vgs.setRange(-50, 50)
        self.slider_vgs.setValue(30)
        self.slider_vgs.valueChanged.connect(self._recalculate)
        grid.addWidget(self.slider_vgs, 0, 1)
        self.val_vgs = QLabel("3.0 V")
        self.val_vgs.setFixedWidth(55)
        self.val_vgs.setStyleSheet("color: #58a6ff; font-weight: bold;")
        grid.addWidget(self.val_vgs, 0, 2)

        # V_DS Slider (0V to 10V)
        grid.addWidget(QLabel("Drain-Source Voltage (V_DS):"), 1, 0)
        self.slider_vds = QSlider(Qt.Horizontal)
        self.slider_vds.setRange(0, 100)
        self.slider_vds.setValue(20)
        self.slider_vds.valueChanged.connect(self._recalculate)
        grid.addWidget(self.slider_vds, 1, 1)
        self.val_vds = QLabel("2.0 V")
        self.val_vds.setFixedWidth(55)
        self.val_vds.setStyleSheet("color: #ef4444; font-weight: bold;")
        grid.addWidget(self.val_vds, 1, 2)

        # V_TH Slider (0.7V to 2.5V)
        grid.addWidget(QLabel("Threshold Voltage (V_TH):"), 2, 0)
        self.slider_vth = QSlider(Qt.Horizontal)
        self.slider_vth.setRange(7, 25)
        self.slider_vth.setValue(10)
        self.slider_vth.valueChanged.connect(self._recalculate)
        grid.addWidget(self.slider_vth, 2, 1)
        self.val_vth = QLabel("1.0 V")
        self.val_vth.setFixedWidth(55)
        self.val_vth.setStyleSheet("color: #f59e0b; font-weight: bold;")
        grid.addWidget(self.val_vth, 2, 2)

        lay.addWidget(ctrl_box)

        # Readout Badges Bar
        readout_box = QGroupBox("Shockley Conduction Readouts")
        r_lay = QHBoxLayout(readout_box)
        r_lay.setContentsMargins(10, 8, 10, 8)

        # Region Badge
        self.badge_mode = QLabel("SATURATION")
        self.badge_mode.setFont(QFont("Consolas", 11, QFont.Bold))
        self.badge_mode.setStyleSheet("background: #1e3a5f; color: #38bdf8; padding: 4px 10px; border-radius: 4px;")
        r_lay.addWidget(QLabel("Operating Region:"))
        r_lay.addWidget(self.badge_mode)

        r_lay.addSpacing(20)
        r_lay.addWidget(QLabel("Drain Current (I_D):"))
        self.lbl_id = QLabel("2.00 mA")
        self.lbl_id.setFont(QFont("Consolas", 11, QFont.Bold))
        self.lbl_id.setStyleSheet("color: #4ade80;")
        r_lay.addWidget(self.lbl_id)

        r_lay.addSpacing(20)
        r_lay.addWidget(QLabel("Transconductance (g_m):"))
        self.lbl_gm = QLabel("2.00 mS")
        self.lbl_gm.setFont(QFont("Consolas", 11, QFont.Bold))
        self.lbl_gm.setStyleSheet("color: #e2e8f0;")
        r_lay.addWidget(self.lbl_gm)

        r_lay.addSpacing(20)
        r_lay.addWidget(QLabel("R_DS(on):"))
        self.lbl_rds = QLabel("1.00 kΩ")
        self.lbl_rds.setFont(QFont("Consolas", 11, QFont.Bold))
        self.lbl_rds.setStyleSheet("color: #e2e8f0;")
        r_lay.addWidget(self.lbl_rds)

        r_lay.addStretch()
        lay.addWidget(readout_box)
        return w

    # ── Tab 2: Matplotlib Curve Families ──────────────────────────────
    def _build_curves_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 4, 4, 4)

        self.fig = Figure(figsize=(8, 4.5), facecolor="#0d1117")
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#161b22")
        self.canvas = FigureCanvas(self.fig)
        lay.addWidget(self.canvas)
        return w

    # ── Tab 3: CMOS Inverter Switching ────────────────────────────────
    def _build_cmos_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        hdr = QLabel("Complementary MOS (CMOS) Inverter Switching Principle")
        hdr.setFont(QFont("Consolas", 11, QFont.Bold))
        hdr.setStyleSheet("color: #58a6ff;")
        lay.addWidget(hdr)

        info = QLabel(
            "A CMOS Inverter is formed by cascading a PMOS pull-up network to VDD (+5V) "
            "and an NMOS pull-down network to GND (0V). Because complementary gates switch "
            "oppositely, zero static current flows from VDD to GND in either stable state!"
        )
        info.setWordWrap(True)
        lay.addWidget(info)

        # Inverter slider
        inv_box = QGroupBox("Interactive Input Voltage V_IN")
        ib_lay = QHBoxLayout(inv_box)
        self.slider_vin = QSlider(Qt.Horizontal)
        self.slider_vin.setRange(0, 50)
        self.slider_vin.setValue(0)
        self.slider_vin.valueChanged.connect(self._update_cmos)
        ib_lay.addWidget(QLabel("V_IN (0V to 5V):"))
        ib_lay.addWidget(self.slider_vin, stretch=1)
        self.val_vin = QLabel("0.0 V (LOW)")
        self.val_vin.setFont(QFont("Consolas", 10, QFont.Bold))
        self.val_vin.setStyleSheet("color: #38bdf8;")
        ib_lay.addWidget(self.val_vin)
        lay.addWidget(inv_box)

        # Status cards
        status_box = QGroupBox("Transistor States & Output")
        sb_lay = QGridLayout(status_box)

        self.pmos_status = QLabel("PMOS (Pull-Up): ON (Conduction path to VDD)")
        self.pmos_status.setFont(QFont("Consolas", 10, QFont.Bold))
        self.pmos_status.setStyleSheet("color: #4ade80;")
        sb_lay.addWidget(self.pmos_status, 0, 0)

        self.nmos_status = QLabel("NMOS (Pull-Down): OFF (High impedance / Cutoff)")
        self.nmos_status.setFont(QFont("Consolas", 10, QFont.Bold))
        self.nmos_status.setStyleSheet("color: #f87171;")
        sb_lay.addWidget(self.nmos_status, 1, 0)

        self.vout_status = QLabel("V_OUT = 5.0 V  (Logic 1) ✓")
        self.vout_status.setFont(QFont("Consolas", 12, QFont.Bold))
        self.vout_status.setStyleSheet("background: #0f2d1e; color: #4ade80; padding: 8px; border-radius: 4px;")
        sb_lay.addWidget(self.vout_status, 0, 1, 2, 1)

        lay.addWidget(status_box)
        lay.addStretch()
        return w

    def _update_cmos(self):
        vin = self.slider_vin.value() / 10.0
        logic_level = "LOW (0)" if vin < 2.5 else "HIGH (1)"
        self.val_vin.setText(f"{vin:.1f} V ({logic_level})")

        # Inverter switching threshold ~2.5V
        if vin < 1.5:
            self.pmos_status.setText("PMOS (Pull-Up): ON  (conducts VDD)")
            self.pmos_status.setStyleSheet("color: #4ade80;")
            self.nmos_status.setText("NMOS (Pull-Down): OFF (Cutoff)")
            self.nmos_status.setStyleSheet("color: #94a3b8;")
            self.vout_status.setText("V_OUT = 5.0 V  (Logic 1) ✓")
            self.vout_status.setStyleSheet("background: #0f2d1e; color: #4ade80; padding: 8px; border-radius: 4px;")
        elif vin > 3.5:
            self.pmos_status.setText("PMOS (Pull-Up): OFF (Cutoff)")
            self.pmos_status.setStyleSheet("color: #94a3b8;")
            self.nmos_status.setText("NMOS (Pull-Down): ON  (conducts to GND)")
            self.nmos_status.setStyleSheet("color: #4ade80;")
            self.vout_status.setText("V_OUT = 0.0 V  (Logic 0) ✓")
            self.vout_status.setStyleSheet("background: #2a111a; color: #f87171; padding: 8px; border-radius: 4px;")
        else:
            self.pmos_status.setText("PMOS: Switching / Transition")
            self.pmos_status.setStyleSheet("color: #f59e0b;")
            self.nmos_status.setText("NMOS: Switching / Transition")
            self.nmos_status.setStyleSheet("color: #f59e0b;")
            vout = 5.0 - (vin - 1.5) * 2.5
            self.vout_status.setText(f"V_OUT = {vout:.1f} V (Transitioning)")
            self.vout_status.setStyleSheet("background: #332200; color: #fbbf24; padding: 8px; border-radius: 4px;")

    # ── Calculation Core ──────────────────────────────────────────────
    def _recalculate(self):
        self.transistor_type = "NMOS" if self.radio_nmos.isChecked() else "PMOS"
        t_type = self.transistor_type
        v_gs = self.slider_vgs.value() / 10.0
        v_ds = self.slider_vds.value() / 10.0
        v_th = self.slider_vth.value() / 10.0

        self.val_vgs.setText(f"{v_gs:.1f} V")
        self.val_vds.setText(f"{v_ds:.1f} V")
        self.val_vth.setText(f"{v_th:.1f} V")

        # Shockley conduction equations:
        # k_n = mu * C_ox * (W/L) ~ 1.0 mA/V^2
        k_factor = 1.0
        lam = 0.02  # channel length modulation

        v_ov = v_gs - v_th

        if v_ov <= 0:
            mode = "Cutoff"
            i_d = 0.0
            gm = 0.0
            rds = 999.0
            badge_bg = "#21262d"
            badge_fg = "#8b949e"
        elif v_ds < v_ov:
            mode = "Triode (Linear)"
            i_d = k_factor * (v_ov * v_ds - 0.5 * (v_ds ** 2))
            gm = k_factor * v_ds
            rds = v_ds / max(0.0001, i_d)
            badge_bg = "#234e2e"
            badge_fg = "#4ade80"
        else:
            mode = "Saturation"
            i_d = 0.5 * k_factor * (v_ov ** 2) * (1.0 + lam * v_ds)
            gm = k_factor * v_ov
            rds = v_ds / max(0.0001, i_d)
            badge_bg = "#1e3a5f"
            badge_fg = "#38bdf8"

        self.badge_mode.setText(mode.upper())
        self.badge_mode.setStyleSheet(f"background: {badge_bg}; color: {badge_fg}; padding: 4px 10px; border-radius: 4px;")
        self.lbl_id.setText(f"{i_d:.2f} mA")
        self.lbl_gm.setText(f"{gm:.2f} mS")
        self.lbl_rds.setText(f"{rds:.2f} kΩ" if rds < 100 else "> 1 MΩ")

        # Update semiconductor cross-section
        self.semi_view.update_params(t_type, v_gs, v_ds, v_th, mode, i_d)

        # Update characteristic plot
        self._plot_curves(v_th, v_ds, i_d, v_gs)

    def _plot_curves(self, v_th, curr_vds, curr_id, curr_vgs):
        self.ax.clear()
        vds_range = np.linspace(0, 10, 100)
        vgs_vals = [v_th + 0.5, v_th + 1.0, v_th + 1.5, v_th + 2.0, v_th + 2.5]
        colors = ['#64748b', '#38bdf8', '#818cf8', '#c084fc', '#f472b6']

        # Plot curves for standard V_GS levels
        for vgs, col in zip(vgs_vals, colors):
            vov = vgs - v_th
            id_curve = []
            for vds in vds_range:
                if vds < vov:
                    val = 1.0 * (vov * vds - 0.5 * (vds**2))
                else:
                    val = 0.5 * 1.0 * (vov**2) * (1.0 + 0.02 * vds)
                id_curve.append(val)
            self.ax.plot(vds_range, id_curve, label=f"V_GS={vgs:.1f}V", color=col, lw=1.5)

        # Plot boundary parabola V_DS = V_GS - V_TH
        vds_sat = np.linspace(0, 3.5, 50)
        id_sat_boundary = 0.5 * 1.0 * (vds_sat**2)
        self.ax.plot(vds_sat, id_sat_boundary, '--', color='#f59e0b', alpha=0.7, label="Saturation Boundary")

        # Plot dynamic operating point
        if curr_vgs >= v_th:
            self.ax.scatter([curr_vds], [curr_id], color='#ef4444', s=70, zorder=5, label="Q-Point")
            self.ax.annotate(f"Q ({curr_vds:.1f}V, {curr_id:.2f}mA)",
                             (curr_vds, curr_id), textcoords="offset points", xytext=(8, 8),
                             color='#ffffff', fontsize=8, fontfamily='Consolas')

        self.ax.set_title(f"MOSFET I_D vs V_DS Output Characteristic ({self.transistor_type})", color="#e2e8f0", fontsize=9, fontfamily="Consolas")
        self.ax.set_xlabel("V_DS (Volts)", color="#94a3b8", fontsize=8, fontfamily="Consolas")
        self.ax.set_ylabel("I_D (mA)", color="#94a3b8", fontsize=8, fontfamily="Consolas")
        self.ax.tick_params(colors="#94a3b8", labelsize=8)
        self.ax.grid(True, color="#30363d", linestyle=":", alpha=0.6)
        self.ax.legend(facecolor="#161b22", edgecolor="#30363d", labelcolor="#e2e8f0", fontsize=7, loc="upper left")

        self.fig.tight_layout()
        self.canvas.draw()
