"""
internal_structure_dialog.py - Interactive Gate-Level Architecture Explorer
for all Sequential Logic elements.

Shows the internal gate-level composition (which gates are inside and how
they are wired/cross-coupled) in a rich, dark-themed, three-tab modal dialog:

  Tab 1 — Visual Schematic: IEEE-symbol gates, curved/orthogonal wires,
           cross-coupled feedback loops highlighted in accent colours.
  Tab 2 — BOM / Netlist:    Gate IDs, types, connections, roles in a table.
  Tab 3 — Theory:           Characteristic equations, excitation /
                             state-transition tables, pedagogical explanations.

Supported components:
  SR Latch / Flip-Flop, D Flip-Flop (Master-Slave), JK Flip-Flop,
  T Flip-Flop, Clock Source (Ring Oscillator / Astable Multivibrator).

The dialog is fully read-only and standalone — it never touches the main
canvas simulation or scene graph.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
    QTextEdit, QFrame, QGraphicsScene, QGraphicsView,
    QGraphicsItem, QGraphicsRectItem, QGraphicsEllipseItem,
    QGraphicsTextItem, QGraphicsPathItem, QGraphicsLineItem,
    QPushButton, QSizePolicy, QAbstractItemView
)
from PyQt5.QtCore import Qt, QRectF, QPointF, QSize
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath,
    QPolygonF, QLinearGradient
)
import math


# ═══════════════════════════════════════════════════════════════════════
# Colour palette (matches IDE dark theme)
# ═══════════════════════════════════════════════════════════════════════
BG_DARK    = "#0d1117"
BG_MID     = "#161b22"
BG_PANEL   = "#1c2333"
ACCENT     = "#58a6ff"
GREEN      = "#3fb950"
RED        = "#f85149"
PINK       = "#f06292"
CYAN       = "#00e5ff"
ORANGE     = "#ffa657"
WHITE      = "#e6edf3"
MUTED      = "#8b949e"
BORDER     = "#30363d"
GATE_BODY  = "#1c2333"
GATE_EDGE  = "#58a6ff"
WIRE_NORM  = "#546e7a"
WIRE_FB    = "#f06292"     # feedback loop highlight


# ═══════════════════════════════════════════════════════════════════════
# Topology data for every sequential component
# ═══════════════════════════════════════════════════════════════════════

def _sr_data():
    """SR Latch / Clocked SR Flip-Flop internal topology."""
    title = "Clocked SR Flip-Flop  (Gated SR Latch)"
    subtitle = "Cross-Coupled NOR + Input AND Gating"

    gates = [
        ("U1_AND", "AND2",  "S, CLK",         "net_S",   "Input AND – gates S through CLK"),
        ("U2_AND", "AND2",  "R, CLK",         "net_R",   "Input AND – gates R through CLK"),
        ("U3_NOR", "NOR2",  "net_R, Q_bar_i", "Q",       "Upper cross-coupled latch element"),
        ("U4_NOR", "NOR2",  "net_S, Q_i",     "Q_bar",   "Lower cross-coupled latch element"),
    ]

    # Nodes: (id, label, x, y, w, h, gate_type, colour)
    nodes = [
        ("S",      "S",      20,  60,  0, 0, "PORT_IN",  ACCENT),
        ("R",      "R",      20, 220,  0, 0, "PORT_IN",  ACCENT),
        ("CLK",    "CLK",    20, 140,  0, 0, "PORT_IN",  ACCENT),
        ("U1",     "AND",   140,  80, 70, 44, "AND",      GATE_EDGE),
        ("U2",     "AND",   140, 200, 70, 44, "AND",      GATE_EDGE),
        ("U3",     "NOR",   300, 80,  70, 44, "NOR",      GATE_EDGE),
        ("U4",     "NOR",   300, 200, 70, 44, "NOR",      GATE_EDGE),
        ("Q",      "Q",     440, 90,  0, 0, "PORT_OUT", GREEN),
        ("Qb",     "Q_bar", 440, 210, 0, 0, "PORT_OUT", RED),
    ]

    # Wires: (src_id, dst_id, is_feedback)
    wires = [
        ("S",   "U1", False),
        ("CLK", "U1", False),
        ("R",   "U2", False),
        ("CLK", "U2", False),
        ("U1",  "U3", False),
        ("U2",  "U4", False),
        ("U3",  "Q",  False),
        ("U4",  "Qb", False),
        # Feedback: Q -> U4 input, Q_bar -> U3 input
        ("U3",  "U4", True),
        ("U4",  "U3", True),
    ]

    equation = "Q_next  =  S + R_bar . Q        (constraint: S . R = 0)"
    equation_latex = "Q_{next} = S + \\overline{R} \\cdot Q"

    truth_table_hdr = ["S", "R", "CLK", "Q_next", "Action"]
    truth_table = [
        ["0", "0", "1",  "Q",    "Hold / No Change"],
        ["0", "1", "1",  "0",    "Reset"],
        ["1", "0", "1",  "1",    "Set"],
        ["1", "1", "1",  "X",    "FORBIDDEN (Invalid / Race)"],
        ["X", "X", "0",  "Q",    "Latched (CLK disabled)"],
    ]

    theory = (
        "<h3 style='color:#58a6ff;'>SR Flip-Flop — Bi-Stable Latch Architecture</h3>"
        "<p>The SR (Set-Reset) Flip-Flop is the fundamental memory element in "
        "digital electronics. Its core is a <b>cross-coupled NOR gate pair</b> "
        "(U3 and U4) that forms a bistable multivibrator — a circuit with exactly "
        "two stable equilibrium states.</p>"

        "<h4 style='color:#ffa657;'>Cross-Coupled Feedback Loop</h4>"
        "<p>The output Q of NOR gate U3 is fed back to an input of NOR gate U4, "
        "and conversely the output Q&#772; of U4 feeds back into U3. This "
        "<span style='color:#f06292;'>positive feedback loop</span> is what gives "
        "the latch its <em>memory</em>: once the circuit settles into a state, it "
        "holds that state indefinitely (as long as power is maintained and neither "
        "S nor R is asserted).</p>"

        "<h4 style='color:#ffa657;'>Clock Gating</h4>"
        "<p>In the <b>clocked</b> (gated) SR Flip-Flop, two AND gates (U1, U2) "
        "are placed before the NOR latch. They allow the S and R signals to reach "
        "the latch core <em>only</em> when CLK = 1. When CLK = 0, both AND gate "
        "outputs are 0 regardless of S and R, holding the latch in its current state.</p>"

        "<h4 style='color:#f85149;'>Forbidden State — S = R = 1</h4>"
        "<p>When both S and R are asserted simultaneously while the clock is active, "
        "both NOR gates are forced to output 0, violating the complementary "
        "relationship Q ≠ Q&#772;. When the inputs are later released, the final "
        "state is <b>indeterminate</b> (depends on gate propagation delays), creating "
        "a <b>race condition</b>. This is why the S=R=1 input combination is "
        "designated as <b>forbidden</b> in the SR Flip-Flop.</p>"

        "<h4 style='color:#3fb950;'>Characteristic Equation</h4>"
        "<p style='font-family:Consolas; font-size:14px; color:#e6edf3;'>"
        "Q<sub>next</sub> = S + R&#772; &middot; Q &nbsp;&nbsp; "
        "(with constraint S &middot; R = 0)</p>"
    )

    return title, subtitle, gates, nodes, wires, equation, truth_table_hdr, truth_table, theory


def _dff_data():
    """D Flip-Flop (Positive-Edge-Triggered, 6-NAND) internal topology."""
    title = "Edge-Triggered D Flip-Flop  (Master-Slave)"
    subtitle = "6-NAND Positive-Edge-Triggered Design"

    gates = [
        ("INV1",    "NOT",   "D",                    "D_bar",    "Inverter — generates D complement"),
        ("INV2",    "NOT",   "CLK",                  "CLK_bar",  "Clock inverter for master enable"),
        ("U1_NAND", "NAND2", "D, CLK",               "net_1",    "Master latch input gate (D path)"),
        ("U2_NAND", "NAND2", "D_bar, CLK",           "net_2",    "Master latch input gate (D_bar path)"),
        ("U3_NAND", "NAND2", "net_1, net_4",         "net_3",    "Master latch cross-coupled gate A"),
        ("U4_NAND", "NAND2", "net_2, net_3",         "net_4",    "Master latch cross-coupled gate B"),
        ("U5_NAND", "NAND2", "net_3, CLK_bar",       "net_5",    "Slave latch input gate (Q path)"),
        ("U6_NAND", "NAND2", "net_4, CLK_bar",       "net_6",    "Slave latch input gate (Q_bar path)"),
        ("U7_NAND", "NAND2", "net_5, Q_bar_i",       "Q",        "Slave latch cross-coupled gate A"),
        ("U8_NAND", "NAND2", "net_6, Q_i",           "Q_bar",    "Slave latch cross-coupled gate B"),
    ]

    nodes = [
        ("D",    "D",     20,  70,  0, 0, "PORT_IN",  ACCENT),
        ("CLK",  "CLK",   20, 190,  0, 0, "PORT_IN",  ACCENT),
        ("INV1", "NOT",  100,  70, 50, 34, "NOT",      GATE_EDGE),
        ("INV2", "NOT",  100, 190, 50, 34, "NOT",      GATE_EDGE),
        ("U1",   "NAND", 200,  50, 65, 40, "NAND",     GATE_EDGE),
        ("U2",   "NAND", 200, 120, 65, 40, "NAND",     GATE_EDGE),
        ("U3",   "NAND", 310,  50, 65, 40, "NAND",     ORANGE),
        ("U4",   "NAND", 310, 120, 65, 40, "NAND",     ORANGE),
        ("U5",   "NAND", 200, 210, 65, 40, "NAND",     GATE_EDGE),
        ("U6",   "NAND", 200, 280, 65, 40, "NAND",     GATE_EDGE),
        ("U7",   "NAND", 310, 210, 65, 40, "NAND",     CYAN),
        ("U8",   "NAND", 310, 280, 65, 40, "NAND",     CYAN),
        ("Q",    "Q",    440, 220, 0, 0, "PORT_OUT", GREEN),
        ("Qb",   "Q_bar",440, 290, 0, 0, "PORT_OUT", RED),
    ]

    wires = [
        ("D",    "INV1", False),
        ("D",    "U1",   False),
        ("INV1", "U2",   False),
        ("CLK",  "INV2", False),
        ("CLK",  "U1",   False),
        ("CLK",  "U2",   False),
        ("U1",   "U3",   False),
        ("U2",   "U4",   False),
        ("U3",   "U4",   True),   # Master cross-couple
        ("U4",   "U3",   True),
        ("U3",   "U5",   False),
        ("U4",   "U6",   False),
        ("INV2", "U5",   False),
        ("INV2", "U6",   False),
        ("U5",   "U7",   False),
        ("U6",   "U8",   False),
        ("U7",   "U8",   True),   # Slave cross-couple
        ("U8",   "U7",   True),
        ("U7",   "Q",    False),
        ("U8",   "Qb",   False),
    ]

    equation = "Q_next = D   (captured on positive clock edge)"

    truth_table_hdr = ["CLK Edge", "D", "Q_next", "Action"]
    truth_table = [
        ["Rising ↑",  "0", "0",   "Data latched LOW"],
        ["Rising ↑",  "1", "1",   "Data latched HIGH"],
        ["Falling ↓", "X", "Q",   "No change (holds previous Q)"],
        ["No Edge",   "X", "Q",   "No change (holds previous Q)"],
    ]

    theory = (
        "<h3 style='color:#58a6ff;'>Edge-Triggered D Flip-Flop — Master-Slave Architecture</h3>"
        "<p>The D (Data) Flip-Flop is the most widely used sequential element in "
        "synchronous digital design. This implementation uses the classic "
        "<b>6-NAND gate positive-edge-triggered</b> topology.</p>"

        "<h4 style='color:#ffa657;'>Two-Stage Master-Slave Structure</h4>"
        "<p>The circuit consists of two SR-type NAND latches cascaded in series:</p>"
        "<ul>"
        "<li><span style='color:#ffa657;'><b>Master Latch</b></span> (U3-U4): "
        "Transparent when CLK = 1, latches when CLK goes LOW.</li>"
        "<li><span style='color:#00e5ff;'><b>Slave Latch</b></span> (U7-U8): "
        "Transparent when CLK = 0, latches when CLK goes HIGH.</li>"
        "</ul>"
        "<p>This complementary clocking ensures that data propagates through the "
        "master while CLK is HIGH, and is then captured by the slave on the "
        "<b>falling edge</b> of CLK — making the overall structure sensitive only "
        "to the <b>rising edge</b> of the external clock.</p>"

        "<h4 style='color:#f06292;'>Cross-Coupled Feedback Pairs</h4>"
        "<p>Each latch contains a cross-coupled NAND pair forming a bistable "
        "element. In the master (U3↔U4), the feedback loop holds the inverted "
        "data value. In the slave (U7↔U8), the feedback loop holds the "
        "final Q and Q&#772; outputs.</p>"

        "<h4 style='color:#3fb950;'>Setup & Hold Time</h4>"
        "<p>For correct operation, the D input must be stable for a minimum "
        "<b>setup time</b> before the rising clock edge and a minimum "
        "<b>hold time</b> after it. Violating these constraints causes "
        "<b>metastability</b> — the latch enters an unstable equilibrium "
        "point between 0 and 1.</p>"

        "<h4 style='color:#3fb950;'>Characteristic Equation</h4>"
        "<p style='font-family:Consolas; font-size:14px; color:#e6edf3;'>"
        "Q<sub>next</sub> = D &nbsp;&nbsp; (on positive clock edge)</p>"
    )

    return title, subtitle, gates, nodes, wires, equation, truth_table_hdr, truth_table, theory


def _jkff_data():
    """JK Flip-Flop internal topology."""
    title = "JK Flip-Flop  (Edge-Triggered)"
    subtitle = "3-Input NAND Steering + Cross-Coupled Bistable"

    gates = [
        ("U1_NAND3", "NAND3", "J, CLK, Q_bar_fb",   "net_S",  "Steering gate — feeds Set path"),
        ("U2_NAND3", "NAND3", "K, CLK, Q_fb",        "net_R",  "Steering gate — feeds Reset path"),
        ("U3_NAND",  "NAND2", "net_S, Q_bar_i",      "Q",      "Upper cross-coupled memory (Q)"),
        ("U4_NAND",  "NAND2", "net_R, Q_i",          "Q_bar",  "Lower cross-coupled memory (Q_bar)"),
    ]

    nodes = [
        ("J",    "J",     20,  50,  0, 0, "PORT_IN",  ACCENT),
        ("K",    "K",     20, 230,  0, 0, "PORT_IN",  ACCENT),
        ("CLK",  "CLK",   20, 140,  0, 0, "PORT_IN",  ACCENT),
        ("U1",   "NAND3",150,  70, 75, 48, "NAND",     GATE_EDGE),
        ("U2",   "NAND3",150, 210, 75, 48, "NAND",     GATE_EDGE),
        ("U3",   "NAND", 310,  70, 70, 44, "NAND",     CYAN),
        ("U4",   "NAND", 310, 210, 70, 44, "NAND",     CYAN),
        ("Q",    "Q",    440,  80,  0, 0, "PORT_OUT", GREEN),
        ("Qb",   "Q_bar",440, 220,  0, 0, "PORT_OUT", RED),
    ]

    wires = [
        ("J",   "U1",  False),
        ("CLK", "U1",  False),
        ("K",   "U2",  False),
        ("CLK", "U2",  False),
        ("U1",  "U3",  False),
        ("U2",  "U4",  False),
        ("U3",  "Q",   False),
        ("U4",  "Qb",  False),
        ("U3",  "U4",  True),   # Cross-couple
        ("U4",  "U3",  True),
        # Output-to-steering feedback
        ("U4",  "U1",  True),   # Q_bar -> U1 (J steering)
        ("U3",  "U2",  True),   # Q -> U2 (K steering)
    ]

    equation = "Q_next  =  J . Q_bar  +  K_bar . Q"

    truth_table_hdr = ["J", "K", "CLK Edge", "Q_next", "Action"]
    truth_table = [
        ["0", "0", "Rising ↑", "Q",      "Hold / No Change"],
        ["0", "1", "Rising ↑", "0",      "Reset"],
        ["1", "0", "Rising ↑", "1",      "Set"],
        ["1", "1", "Rising ↑", "Q_bar",  "Toggle (complement)"],
    ]

    theory = (
        "<h3 style='color:#58a6ff;'>JK Flip-Flop — Universal Sequential Element</h3>"
        "<p>The JK Flip-Flop is called the <b>universal flip-flop</b> because it "
        "can emulate all other flip-flop types (SR, D, T) through appropriate "
        "input connections.</p>"

        "<h4 style='color:#ffa657;'>Steering Logic with Output Feedback</h4>"
        "<p>The key innovation of the JK design is the <b>3-input NAND steering "
        "gates</b> (U1 and U2) that feed into a cross-coupled NAND bistable "
        "(U3-U4). Each steering gate receives:</p>"
        "<ul>"
        "<li>U1 (Set path):  J, CLK, and <span style='color:#f06292;'>"
        "Q&#772; (feedback)</span></li>"
        "<li>U2 (Reset path): K, CLK, and <span style='color:#f06292;'>"
        "Q (feedback)</span></li>"
        "</ul>"

        "<h4 style='color:#f06292;'>How Feedback Eliminates the Forbidden State</h4>"
        "<p>When J = K = 1 and a clock edge arrives:</p>"
        "<ul>"
        "<li>If Q = 0: Q&#772; = 1, so U1 fires (Set path active) → Q becomes 1</li>"
        "<li>If Q = 1: Q = 1 feeds U2 (Reset path active) → Q becomes 0</li>"
        "</ul>"
        "<p>The <span style='color:#f06292;'>output-to-input feedback</span> "
        "guarantees that <em>only one</em> steering gate can ever be active at a "
        "time, converting the SR Flip-Flop's forbidden state (S=R=1) into a "
        "well-defined <b>toggle</b> operation.</p>"

        "<h4 style='color:#3fb950;'>Characteristic Equation</h4>"
        "<p style='font-family:Consolas; font-size:14px; color:#e6edf3;'>"
        "Q<sub>next</sub> = J &middot; Q&#772; + K&#772; &middot; Q</p>"
    )

    return title, subtitle, gates, nodes, wires, equation, truth_table_hdr, truth_table, theory


def _tff_data():
    """T Flip-Flop internal topology."""
    title = "T (Toggle) Flip-Flop"
    subtitle = "D Flip-Flop + XOR Feedback (or JK with J=K=T)"

    gates = [
        ("U1_XOR",  "XOR2",  "T, Q_fb",         "D_int",  "XOR generates D = T XOR Q"),
        ("U2_NAND", "NAND2", "D_int, CLK",       "net_1",  "Master input gate A"),
        ("U3_NAND", "NAND2", "D_int_bar, CLK",   "net_2",  "Master input gate B"),
        ("INV1",    "NOT",   "D_int",            "D_int_bar", "Inverter for D complement"),
        ("U4_NAND", "NAND2", "net_1, net_6",     "net_5",  "Slave cross-coupled gate A (Q)"),
        ("U5_NAND", "NAND2", "net_2, net_5",     "net_6",  "Slave cross-coupled gate B (Q_bar)"),
    ]

    nodes = [
        ("T",    "T",     20,  80,  0, 0, "PORT_IN",  ACCENT),
        ("CLK",  "CLK",   20, 200,  0, 0, "PORT_IN",  ACCENT),
        ("XOR",  "XOR",  130,  80, 70, 44, "XOR",      ORANGE),
        ("INV1", "NOT",  240, 130, 50, 34, "NOT",      GATE_EDGE),
        ("U2",   "NAND", 240,  60, 65, 40, "NAND",     GATE_EDGE),
        ("U3",   "NAND", 240, 190, 65, 40, "NAND",     GATE_EDGE),
        ("U4",   "NAND", 360,  80, 65, 40, "NAND",     CYAN),
        ("U5",   "NAND", 360, 200, 65, 40, "NAND",     CYAN),
        ("Q",    "Q",    480,  90,  0, 0, "PORT_OUT", GREEN),
        ("Qb",   "Q_bar",480, 210,  0, 0, "PORT_OUT", RED),
    ]

    wires = [
        ("T",   "XOR",  False),
        ("XOR", "U2",   False),
        ("XOR", "INV1", False),
        ("INV1","U3",   False),
        ("CLK", "U2",   False),
        ("CLK", "U3",   False),
        ("U2",  "U4",   False),
        ("U3",  "U5",   False),
        ("U4",  "U5",   True),     # Cross-couple
        ("U5",  "U4",   True),
        ("U4",  "Q",    False),
        ("U5",  "Qb",   False),
        # Q -> XOR feedback
        ("U4",  "XOR",  True),
    ]

    equation = "Q_next  =  T  XOR  Q"

    truth_table_hdr = ["T", "CLK Edge", "Q_next", "Action"]
    truth_table = [
        ["0", "Rising ↑", "Q",     "Hold / No Change"],
        ["1", "Rising ↑", "Q_bar", "Toggle (complement)"],
    ]

    theory = (
        "<h3 style='color:#58a6ff;'>T (Toggle) Flip-Flop — Frequency Divider</h3>"
        "<p>The T Flip-Flop is primarily used in <b>binary counters</b> and "
        "<b>frequency dividers</b>. When T = 1, the output toggles on every "
        "active clock edge, dividing the clock frequency by 2.</p>"

        "<h4 style='color:#ffa657;'>Internal Architecture — XOR + D-FF</h4>"
        "<p>The most common implementation feeds the <b>XOR of T and Q</b> back "
        "to the D input of a standard D Flip-Flop:</p>"
        "<ul>"
        "<li>When T = 0: D = 0 XOR Q = Q → output holds.</li>"
        "<li>When T = 1: D = 1 XOR Q = Q&#772; → output toggles.</li>"
        "</ul>"
        "<p>Alternatively, a T-FF can be built from a "
        "<b>JK Flip-Flop with J = K = T</b>.</p>"

        "<h4 style='color:#f06292;'>Feedback Loop</h4>"
        "<p>The output Q is fed back through the "
        "<span style='color:#f06292;'>XOR gate</span> to the D-FF input. This "
        "creates a controlled oscillation: each clock edge inverts the stored "
        "state when T is high, enabling binary counting.</p>"

        "<h4 style='color:#3fb950;'>Characteristic Equation</h4>"
        "<p style='font-family:Consolas; font-size:14px; color:#e6edf3;'>"
        "Q<sub>next</sub> = T &oplus; Q &nbsp;&nbsp; "
        "(equivalently: Q<sub>next</sub> = T &middot; Q&#772; + T&#772; &middot; Q)</p>"
    )

    return title, subtitle, gates, nodes, wires, equation, truth_table_hdr, truth_table, theory


def _clock_data():
    """Clock Generator internal topology."""
    title = "Clock Generator  (Astable Multivibrator)"
    subtitle = "Ring Oscillator — Odd Inverter Chain with RC Feedback"

    gates = [
        ("INV1", "NOT",  "net_3 (feedback)",  "net_1",   "Inverter stage 1 — first inversion"),
        ("INV2", "NOT",  "net_1",             "net_2",   "Inverter stage 2 — second inversion"),
        ("INV3", "NOT",  "net_2",             "net_3",   "Inverter stage 3 — third inversion → feedback"),
        ("BUF",  "BUF",  "net_3",             "CLK_OUT", "Output buffer — drives external load"),
    ]

    nodes = [
        ("INV1", "NOT",  60,  100, 55, 34, "NOT",     ORANGE),
        ("INV2", "NOT",  180, 100, 55, 34, "NOT",     ORANGE),
        ("INV3", "NOT",  300, 100, 55, 34, "NOT",     ORANGE),
        ("BUF",  "BUF",  300, 200, 55, 34, "BUF",     GREEN),
        ("OUT",  "CLK",  430, 200,  0, 0,  "PORT_OUT", GREEN),
    ]

    wires = [
        ("INV1", "INV2", False),
        ("INV2", "INV3", False),
        ("INV3", "BUF",  False),
        ("BUF",  "OUT",  False),
        # Ring feedback
        ("INV3", "INV1", True),
    ]

    equation = "f = 1 / (2 . N . t_pd)   where N = number of stages, t_pd = propagation delay"

    truth_table_hdr = ["Time", "INV1 Out", "INV2 Out", "INV3 Out", "CLK"]
    truth_table = [
        ["t0",          "0", "1", "0", "0"],
        ["t0 + t_pd",   "1", "0", "1", "1"],
        ["t0 + 2*t_pd", "0", "1", "0", "0"],
        ["t0 + 3*t_pd", "1", "0", "1", "1"],
    ]

    theory = (
        "<h3 style='color:#58a6ff;'>Clock Generator — Ring Oscillator</h3>"
        "<p>A clock generator produces a periodic square wave signal that "
        "synchronises all sequential elements in a digital system.</p>"

        "<h4 style='color:#ffa657;'>Ring Oscillator Principle</h4>"
        "<p>The simplest on-chip clock generator is a <b>ring oscillator</b>: "
        "an <b>odd number of inverters</b> connected in a loop. Because the "
        "chain has an odd number of inversions, the output is always the "
        "<em>complement</em> of the input, so no stable DC operating point "
        "exists — the circuit <b>must oscillate</b>.</p>"
        "<p>With 3 inverters, each having propagation delay t<sub>pd</sub>, "
        "the signal must traverse all 3 stages <em>twice</em> (once for "
        "rising, once for falling) to complete one full cycle:</p>"
        "<p style='font-family:Consolas; font-size:14px; color:#e6edf3;'>"
        "T<sub>period</sub> = 2 &middot; N &middot; t<sub>pd</sub><br>"
        "f = 1 / (2 &middot; 3 &middot; t<sub>pd</sub>)</p>"

        "<h4 style='color:#f06292;'>Feedback Loop</h4>"
        "<p>The <span style='color:#f06292;'>output of the last inverter "
        "feeds back to the input of the first</span>, closing the ring. "
        "This is inherently unstable — there is no quiescent state — "
        "which is exactly what produces self-sustaining oscillation.</p>"

        "<h4 style='color:#00e5ff;'>Output Buffering</h4>"
        "<p>A buffer (non-inverting driver) at the output isolates the "
        "oscillator ring from external loading, preventing capacitive "
        "loads from distorting the oscillation frequency.</p>"

        "<h4 style='color:#3fb950;'>Practical Considerations</h4>"
        "<p>Real clock generators add <b>frequency control</b> via "
        "voltage-controlled delay elements (VCO), PLL feedback, or "
        "crystal stabilisation. In simulation, the frequency is "
        "set by a configurable timer period.</p>"
    )

    return title, subtitle, gates, nodes, wires, equation, truth_table_hdr, truth_table, theory


# ═══════════════════════════════════════════════════════════════════════
# Mini gate drawing helpers for the schematic view
# ═══════════════════════════════════════════════════════════════════════

class _GateSymbol(QGraphicsItem):
    """Draws a standard IEEE logic gate symbol on the schematic mini-canvas."""

    def __init__(self, gate_type, label, x, y, w, h, colour=GATE_EDGE):
        super().__init__()
        self.gate_type = gate_type
        self.label = label
        self.gw = w
        self.gh = h
        self.colour = QColor(colour)
        self.setPos(x, y)

    def boundingRect(self):
        return QRectF(-4, -4, self.gw + 8, self.gh + 8)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(self.colour, 1.8)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(GATE_BODY)))

        gt = self.gate_type
        w, h = self.gw, self.gh

        if gt == "AND":
            p = QPainterPath()
            p.moveTo(0, 0); p.lineTo(w * 0.45, 0)
            p.arcTo(w * 0.45 - h / 2, 0, h, h, 90, -180)
            p.lineTo(0, h); p.closeSubpath()
            painter.drawPath(p)

        elif gt == "NAND":
            p = QPainterPath()
            p.moveTo(0, 0); p.lineTo(w * 0.4, 0)
            p.arcTo(w * 0.4 - h / 2, 0, h, h, 90, -180)
            p.lineTo(0, h); p.closeSubpath()
            painter.drawPath(p)
            painter.drawEllipse(QRectF(w - 8, h / 2 - 4, 8, 8))

        elif gt == "OR":
            p = QPainterPath()
            p.moveTo(0, 0)
            p.quadTo(w * 0.35, 0, w, h / 2)
            p.quadTo(w * 0.35, h, 0, h)
            p.quadTo(w * 0.18, h / 2, 0, 0)
            painter.drawPath(p)

        elif gt == "NOR":
            p = QPainterPath()
            p.moveTo(0, 0)
            p.quadTo(w * 0.35, 0, w - 8, h / 2)
            p.quadTo(w * 0.35, h, 0, h)
            p.quadTo(w * 0.18, h / 2, 0, 0)
            painter.drawPath(p)
            painter.drawEllipse(QRectF(w - 8, h / 2 - 4, 8, 8))

        elif gt == "XOR":
            p = QPainterPath()
            p.moveTo(8, 0)
            p.quadTo(w * 0.35, 0, w, h / 2)
            p.quadTo(w * 0.35, h, 8, h)
            p.quadTo(w * 0.18 + 8, h / 2, 8, 0)
            painter.drawPath(p)
            ex = QPainterPath()
            ex.moveTo(0, 0); ex.quadTo(w * 0.14, h / 2, 0, h)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(ex)

        elif gt == "NOT":
            p = QPainterPath()
            p.moveTo(0, 0); p.lineTo(w - 10, h / 2)
            p.lineTo(0, h); p.closeSubpath()
            painter.drawPath(p)
            painter.drawEllipse(QRectF(w - 10, h / 2 - 4, 8, 8))

        elif gt == "BUF":
            p = QPainterPath()
            p.moveTo(0, 0); p.lineTo(w, h / 2)
            p.lineTo(0, h); p.closeSubpath()
            painter.drawPath(p)

        else:
            # Fallback rectangle
            painter.drawRoundedRect(QRectF(0, 0, w, h), 4, 4)

        # Label inside
        painter.setFont(QFont("Consolas", 7, QFont.Bold))
        painter.setPen(QColor(WHITE))
        painter.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, self.label)


class _PortMarker(QGraphicsItem):
    """Draws an input or output port circle with a label."""

    def __init__(self, label, x, y, colour=ACCENT, is_output=False):
        super().__init__()
        self.label = label
        self.colour = QColor(colour)
        self.is_output = is_output
        self.setPos(x, y)

    def boundingRect(self):
        return QRectF(-40, -12, 80, 24)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        r = 7
        painter.setPen(QPen(self.colour, 2))
        painter.setBrush(QBrush(QColor(BG_DARK)))
        painter.drawEllipse(QRectF(-r, -r, 2 * r, 2 * r))

        painter.setFont(QFont("Consolas", 8, QFont.Bold))
        painter.setPen(self.colour)
        if self.is_output:
            painter.drawText(QRectF(12, -8, 50, 16), Qt.AlignLeft | Qt.AlignVCenter, self.label)
        else:
            painter.drawText(QRectF(-55, -8, 50, 16), Qt.AlignRight | Qt.AlignVCenter, self.label)


class _WirePath(QGraphicsPathItem):
    """Draws a curved wire between two nodes, with optional feedback highlighting."""

    def __init__(self, x1, y1, x2, y2, is_feedback=False):
        super().__init__()
        colour = WIRE_FB if is_feedback else WIRE_NORM
        width = 2.2 if is_feedback else 1.5
        self.setPen(QPen(QColor(colour), width))
        self.setZValue(-1 if not is_feedback else 1)

        path = QPainterPath(QPointF(x1, y1))
        dx = abs(x2 - x1) * 0.4
        # For feedback wires going backwards, route with wider curves
        if is_feedback and x2 <= x1:
            mid_y = max(y1, y2) + 50
            path.cubicTo(QPointF(x1 + 30, mid_y),
                         QPointF(x2 - 30, mid_y),
                         QPointF(x2, y2))
        else:
            path.cubicTo(QPointF(x1 + dx, y1),
                         QPointF(x2 - dx, y2),
                         QPointF(x2, y2))
        self.setPath(path)


def _build_schematic_scene(nodes, wires_data):
    """
    Build a QGraphicsScene containing the gate-level schematic
    from node/wire topology data.
    Returns the scene.
    """
    scene = QGraphicsScene()
    scene.setBackgroundBrush(QBrush(QColor(BG_DARK)))

    # Place nodes and remember their centre positions for wiring
    centres = {}
    for nd in nodes:
        nid, label, x, y, w, h, gtype, colour = nd
        if gtype == "PORT_IN":
            item = _PortMarker(label, x, y, colour, is_output=False)
            scene.addItem(item)
            centres[nid] = (x + 7, y)
        elif gtype == "PORT_OUT":
            item = _PortMarker(label, x, y, colour, is_output=True)
            scene.addItem(item)
            centres[nid] = (x - 7, y)
        else:
            item = _GateSymbol(gtype, label, x, y, w, h, colour)
            scene.addItem(item)
            # Centre-left for input, centre-right for output
            centres[nid] = (x + w / 2, y + h / 2)

    # Draw wires
    for src_id, dst_id, is_fb in wires_data:
        if src_id not in centres or dst_id not in centres:
            continue
        sx, sy = centres[src_id]
        dx, dy = centres[dst_id]

        # Determine connection points on gate edges
        src_nd = next((n for n in nodes if n[0] == src_id), None)
        dst_nd = next((n for n in nodes if n[0] == dst_id), None)
        if src_nd:
            if src_nd[6] not in ("PORT_IN", "PORT_OUT") and src_nd[4] > 0:
                sx = src_nd[2] + src_nd[4]  # right edge
                sy = src_nd[3] + src_nd[5] / 2
            elif src_nd[6] == "PORT_IN":
                sx = src_nd[2] + 7
        if dst_nd:
            if dst_nd[6] not in ("PORT_IN", "PORT_OUT") and dst_nd[4] > 0:
                dx = dst_nd[2]              # left edge
                dy = dst_nd[3] + dst_nd[5] / 2
            elif dst_nd[6] == "PORT_OUT":
                dx = dst_nd[2] - 7

        wire = _WirePath(sx, sy, dx, dy, is_fb)
        scene.addItem(wire)

    # Feedback legend
    legend_y = scene.itemsBoundingRect().bottom() + 20
    legend_x = scene.itemsBoundingRect().left() + 10

    fb_line = QGraphicsPathItem()
    p = QPainterPath(QPointF(legend_x, legend_y + 6))
    p.lineTo(QPointF(legend_x + 30, legend_y + 6))
    fb_line.setPath(p)
    fb_line.setPen(QPen(QColor(WIRE_FB), 2.5))
    scene.addItem(fb_line)

    fb_text = QGraphicsTextItem("= Cross-coupled feedback path")
    fb_text.setPos(legend_x + 34, legend_y - 4)
    fb_text.setDefaultTextColor(QColor(WIRE_FB))
    fb_text.setFont(QFont("Consolas", 8))
    scene.addItem(fb_text)

    norm_line = QGraphicsPathItem()
    p2 = QPainterPath(QPointF(legend_x + 260, legend_y + 6))
    p2.lineTo(QPointF(legend_x + 290, legend_y + 6))
    norm_line.setPath(p2)
    norm_line.setPen(QPen(QColor(WIRE_NORM), 1.5))
    scene.addItem(norm_line)

    norm_text = QGraphicsTextItem("= Signal / data path")
    norm_text.setPos(legend_x + 294, legend_y - 4)
    norm_text.setDefaultTextColor(QColor(MUTED))
    norm_text.setFont(QFont("Consolas", 8))
    scene.addItem(norm_text)

    return scene


# ═══════════════════════════════════════════════════════════════════════
# Main Dialog
# ═══════════════════════════════════════════════════════════════════════

class InternalStructureDialog(QDialog):
    """
    Interactive modal showing the internal gate-level architecture of a
    sequential component with three tabs:
      1. Visual Schematic (QGraphicsView)
      2. BOM / Netlist Table
      3. Theory & State Transition
    """

    def __init__(self, gate_item, parent=None):
        super().__init__(parent)
        self.gate_item = gate_item
        self._load_topology()
        self.setWindowTitle(f"Internal Structure — {self._title}")
        self.setMinimumSize(920, 640)
        self.resize(1020, 700)
        self._apply_style()
        self._build_ui()

    # ── choose data based on gate type ────────────────────────────
    def _load_topology(self):
        from sequential_gates import (
            ClockNode, DFlipFlop, JKFlipFlop, TFlipFlop, SRFlipFlop
        )
        gt = self.gate_item
        if isinstance(gt, DFlipFlop) or getattr(gt, 'gate_type', '') == 'D_FF':
            data = _dff_data()
        elif isinstance(gt, JKFlipFlop) or getattr(gt, 'gate_type', '') == 'JK_FF':
            data = _jkff_data()
        elif isinstance(gt, TFlipFlop) or getattr(gt, 'gate_type', '') == 'T_FF':
            data = _tff_data()
        elif isinstance(gt, SRFlipFlop) or getattr(gt, 'gate_type', '') == 'SR_FF':
            data = _sr_data()
        elif isinstance(gt, ClockNode) or getattr(gt, 'gate_type', '') == 'CLOCK':
            data = _clock_data()
        else:
            data = _sr_data()  # fallback

        (self._title, self._subtitle, self._gates, self._nodes,
         self._wires, self._equation, self._tt_hdr, self._tt_rows,
         self._theory) = data

    # ── stylesheet ────────────────────────────────────────────────
    def _apply_style(self):
        self.setStyleSheet(f"""
            QDialog {{ background: {BG_DARK}; color: {WHITE}; }}
            QLabel  {{ color: {MUTED}; font-family: Consolas; }}
            QTabWidget::pane {{ border: 1px solid {BORDER}; background: {BG_MID}; }}
            QTabBar::tab {{
                background: {BG_MID}; color: {MUTED}; border: 1px solid {BORDER};
                border-bottom: none; padding: 8px 18px;
                font-family: Consolas; font-size: 11px;
            }}
            QTabBar::tab:selected {{
                background: {BG_DARK}; color: {ACCENT};
                border-bottom: 2px solid {ACCENT};
            }}
            QTabBar::tab:hover {{ color: {WHITE}; }}
            QTableWidget {{
                background: {BG_DARK}; color: {WHITE}; gridline-color: {BORDER};
                border: 1px solid {BORDER}; font-family: Consolas; font-size: 11px;
            }}
            QTableWidget::item {{ padding: 4px 8px; }}
            QTableWidget::item:selected {{ background: #1f6feb; }}
            QHeaderView::section {{
                background: {BG_MID}; color: {ACCENT}; border: 1px solid {BORDER};
                padding: 5px 8px; font-family: Consolas; font-size: 11px;
                font-weight: bold;
            }}
            QTextEdit {{
                background: {BG_DARK}; color: {WHITE}; border: 1px solid {BORDER};
                font-family: Consolas; font-size: 12px; padding: 8px;
            }}
            QPushButton {{
                background: #21262d; color: {WHITE}; border: 1px solid {BORDER};
                border-radius: 4px; padding: 7px 16px;
                font-family: Consolas; font-size: 11px;
            }}
            QPushButton:hover {{ background: #30363d; border-color: {ACCENT}; }}
        """)

    # ── build the entire UI ───────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        # ── Header ────────────────────────────────────────────────
        hdr = QHBoxLayout()

        # Component badge
        badge = QLabel(self.gate_item.gate_type)
        badge.setFixedSize(56, 56)
        badge.setAlignment(Qt.AlignCenter)
        badge.setFont(QFont("Consolas", 9, QFont.Bold))
        badge.setStyleSheet(
            f"background:{BG_PANEL}; color:{ACCENT}; border:2px solid {ACCENT};"
            f"border-radius:8px;"
        )
        hdr.addWidget(badge)

        # Title block
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        t1 = QLabel(self._title)
        t1.setFont(QFont("Consolas", 14, QFont.Bold))
        t1.setStyleSheet(f"color:{ACCENT};")
        title_col.addWidget(t1)

        t2 = QLabel(self._subtitle)
        t2.setFont(QFont("Consolas", 10))
        t2.setStyleSheet(f"color:{MUTED};")
        title_col.addWidget(t2)
        hdr.addLayout(title_col, stretch=1)

        # Live state badge (read-only snapshot)
        state_val = getattr(self.gate_item, 'state', getattr(self.gate_item, '_value', 0))
        state_txt = f"Q = {state_val}" if hasattr(self.gate_item, 'state') else f"CLK = {state_val}"
        state_color = GREEN if state_val else RED
        state_lbl = QLabel(state_txt)
        state_lbl.setFixedHeight(36)
        state_lbl.setAlignment(Qt.AlignCenter)
        state_lbl.setFont(QFont("Consolas", 12, QFont.Bold))
        state_lbl.setStyleSheet(
            f"color:{state_color}; background:{BG_PANEL};"
            f"border:2px solid {state_color}; border-radius:6px;"
            f"padding: 0 14px;"
        )
        hdr.addWidget(state_lbl)

        root.addLayout(hdr)

        # ── Separator ─────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background:{BORDER}; max-height:1px;")
        root.addWidget(sep)

        # ── Tab Widget ────────────────────────────────────────────
        tabs = QTabWidget()
        tabs.addTab(self._build_schematic_tab(), "  Schematic  ")
        tabs.addTab(self._build_bom_tab(),       "  BOM / Netlist  ")
        tabs.addTab(self._build_theory_tab(),    "  Theory & Equations  ")
        root.addWidget(tabs, stretch=1)

        # ── Bottom bar ────────────────────────────────────────────
        bottom = QHBoxLayout()

        eq_lbl = QLabel(f"Characteristic Equation:   {self._equation}")
        eq_lbl.setFont(QFont("Consolas", 10))
        eq_lbl.setStyleSheet(f"color:{GREEN}; padding:2px;")
        bottom.addWidget(eq_lbl, stretch=1)

        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(90)
        close_btn.clicked.connect(self.accept)
        bottom.addWidget(close_btn)

        root.addLayout(bottom)

    # ── Tab 1: Visual Schematic ───────────────────────────────────
    def _build_schematic_tab(self):
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(6, 6, 6, 6)

        gfx_scene = _build_schematic_scene(self._nodes, self._wires)
        view = QGraphicsView(gfx_scene)
        view.setRenderHint(QPainter.Antialiasing)
        view.setStyleSheet(f"background:{BG_DARK}; border:1px solid {BORDER};")
        view.setDragMode(QGraphicsView.ScrollHandDrag)
        view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        # Fit to contents
        bounds = gfx_scene.itemsBoundingRect().adjusted(-30, -30, 30, 30)
        view.fitInView(bounds, Qt.KeepAspectRatio)

        lay.addWidget(view, stretch=1)

        # Zoom buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        zoom_in_btn = QPushButton("Zoom +")
        zoom_in_btn.clicked.connect(lambda: view.scale(1.25, 1.25))
        btn_row.addWidget(zoom_in_btn)

        zoom_out_btn = QPushButton("Zoom -")
        zoom_out_btn.clicked.connect(lambda: view.scale(0.8, 0.8))
        btn_row.addWidget(zoom_out_btn)

        fit_btn = QPushButton("Fit View")
        fit_btn.clicked.connect(lambda: view.fitInView(
            gfx_scene.itemsBoundingRect().adjusted(-30, -30, 30, 30),
            Qt.KeepAspectRatio
        ))
        btn_row.addWidget(fit_btn)

        lay.addLayout(btn_row)
        return widget

    # ── Tab 2: BOM / Netlist Table ────────────────────────────────
    def _build_bom_tab(self):
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        hdr = QLabel("Gate Bill of Materials & Internal Netlist")
        hdr.setFont(QFont("Consolas", 11, QFont.Bold))
        hdr.setStyleSheet(f"color:{ACCENT}; padding:4px 0;")
        lay.addWidget(hdr)

        cols = ["Gate ID", "Type", "Inputs", "Output Net", "Role / Function"]
        tbl = QTableWidget(len(self._gates), len(cols))
        tbl.setHorizontalHeaderLabels(cols)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)

        for r, gate in enumerate(self._gates):
            gid, gtype, inputs, output, role = gate
            items = [gid, gtype, inputs, output, role]
            for c, val in enumerate(items):
                item = QTableWidgetItem(val)
                # Colour-code the type column
                if c == 1:
                    item.setForeground(QColor(ORANGE))
                elif c == 0:
                    item.setForeground(QColor(ACCENT))
                elif c == 4:
                    item.setForeground(QColor(MUTED))
                tbl.setItem(r, c, item)

        lay.addWidget(tbl, stretch=1)

        # Summary
        summary = QLabel(
            f"Total gates: {len(self._gates)}   |   "
            f"Feedback loops: {sum(1 for w in self._wires if w[2])}"
        )
        summary.setFont(QFont("Consolas", 9))
        summary.setStyleSheet(f"color:{MUTED}; padding:4px;")
        lay.addWidget(summary)

        return widget

    # ── Tab 3: Theory & State Transition ──────────────────────────
    def _build_theory_tab(self):
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(10)

        # State transition / Excitation table
        tt_hdr_lbl = QLabel("Excitation / State Transition Table")
        tt_hdr_lbl.setFont(QFont("Consolas", 11, QFont.Bold))
        tt_hdr_lbl.setStyleSheet(f"color:{ACCENT}; padding:4px 0;")
        lay.addWidget(tt_hdr_lbl)

        tbl = QTableWidget(len(self._tt_rows), len(self._tt_hdr))
        tbl.setHorizontalHeaderLabels(self._tt_hdr)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        for r, row in enumerate(self._tt_rows):
            for c, val in enumerate(row):
                item = QTableWidgetItem(val)
                # Colour code the Action column and special values
                if c == len(row) - 1:
                    if "FORBIDDEN" in val.upper() or "INVALID" in val.upper():
                        item.setForeground(QColor(RED))
                    elif "Toggle" in val or "Set" in val:
                        item.setForeground(QColor(GREEN))
                    elif "Reset" in val:
                        item.setForeground(QColor(ORANGE))
                    else:
                        item.setForeground(QColor(MUTED))
                elif val in ("X",):
                    item.setForeground(QColor(RED))
                elif val in ("0",):
                    item.setForeground(QColor(MUTED))
                elif val in ("1",):
                    item.setForeground(QColor(GREEN))
                tbl.setItem(r, c, item)

        tbl.setMaximumHeight(180)
        lay.addWidget(tbl)

        # Theory rich text
        theory_edit = QTextEdit()
        theory_edit.setReadOnly(True)
        theory_edit.setHtml(self._theory)
        theory_edit.setFont(QFont("Consolas", 11))
        lay.addWidget(theory_edit, stretch=1)

        return widget
