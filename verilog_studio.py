"""
verilog_studio.py - Dedicated Verilog Toolpanel / Modal Studio
Features:
- Bidirectional Verilog Conversion:
  1. Verilog Code -> Schematic (Design Synthesizer)
  2. Schematic -> Verilog Code (HDL Generator with 4 Modeling Styles: Gate-Level, Dataflow, Behavioral, Switch-Level)
- Rich Monospace Code Editor with Line Numbers and Quick Verilog Design Templates.
- Interactive Synthesis Console with colored error and status reporting.
- Clipboard copy, Load/Save .v files, and live schematic synthesis.
"""

import os
from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QComboBox, QLineEdit, QPlainTextEdit,
    QTextEdit, QFileDialog, QMessageBox, QGroupBox, QFrame,
    QApplication
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QColor, QTextCursor

from verilog_converter import VerilogParser, VerilogSynthesizer, VerilogGenerator


# ───────────────────────────────────────────────────────────────────────
# Built-in Verilog Design Templates
# ───────────────────────────────────────────────────────────────────────
TEMPLATES = {
    "D Flip-Flop with Async Reset (Sequential)": """// D Flip-Flop with Asynchronous Reset
module d_flip_flop (
    input  wire clk,
    input  wire d,
    input  wire rst,
    output reg  q,
    output wire q_bar
);
    assign q_bar = ~q;

    always @(posedge clk or posedge rst) begin
        if (rst)
            q <= 1'b0;
        else
            q <= d;
    end
endmodule
""",

    "T Flip-Flop Frequency Divider (Sequential)": """// T Flip-Flop Frequency Divider
module t_flip_flop (
    input  wire clk,
    input  wire t,
    output reg  q,
    output wire q_bar
);
    assign q_bar = ~q;

    always @(posedge clk) begin
        if (t)
            q <= ~q;
    end
endmodule
""",

    "JK Flip-Flop Circuit (Sequential)": """// JK Flip-Flop Structural Instance
module jk_circuit (
    input  wire clk,
    input  wire j,
    input  wire k,
    output wire q,
    output wire q_bar
);
    jk_ff jk1 (
        .clk(clk),
        .j(j),
        .k(k),
        .q(q),
        .q_bar(q_bar)
    );
endmodule
""",

    "Full Adder (Gate-Level Primitives)": """// Full Adder using Gate Primitives
module full_adder_structural (
    input  wire a,
    input  wire b,
    input  wire cin,
    output wire sum,
    output wire cout
);
    wire s1, c1, c2;

    xor g1 (s1, a, b);
    xor g2 (sum, s1, cin);
    and g3 (c1, a, b);
    and g4 (c2, s1, cin);
    or  g5 (cout, c1, c2);
endmodule
""",

    "Full Adder (Dataflow Assign)": """// Full Adder using Continuous Dataflow Modeling
module full_adder_dataflow (
    input  wire a,
    input  wire b,
    input  wire cin,
    output wire sum,
    output wire cout
);
    assign sum  = a ^ b ^ cin;
    assign cout = (a & b) | (b & cin) | (a & cin);
endmodule
""",

    "2-to-1 Multiplexer (Dataflow)": """// 2:1 Multiplexer with Enable
module mux2to1 (
    input  wire in0,
    input  wire in1,
    input  wire sel,
    output wire out
);
    assign out = sel ? in1 : in0;
endmodule
""",

    "4-to-1 Multiplexer (Gate-Level)": """// 4:1 Multiplexer Structural
module mux4to1_structural (
    input  wire d0,
    input  wire d1,
    input  wire d2,
    input  wire d3,
    input  wire s0,
    input  wire s1,
    output wire y
);
    wire not_s0, not_s1;
    wire m0, m1, m2, m3;

    not (not_s0, s0);
    not (not_s1, s1);

    and (m0, d0, not_s1, not_s0);
    and (m1, d1, not_s1, s0);
    and (m2, d2, s1, not_s0);
    and (m3, d3, s1, s0);

    or  (y, m0, m1, m2, m3);
endmodule
""",

    "CMOS Inverter (Switch-Level)": """// CMOS Inverter using Switch-Level Modeling
module cmos_inverter (
    input  wire in,
    output wire out
);
    supply1 vdd;
    supply0 gnd;

    pmos p1 (out, vdd, in);
    nmos n1 (out, gnd, in);
endmodule
""",
}


# ───────────────────────────────────────────────────────────────────────
# Verilog Studio Dialog
# ───────────────────────────────────────────────────────────────────────
class VerilogStudioDialog(QDialog):
    """
    Dedicated Verilog Toolpanel / Modal Dialog.
    Split view with:
    - Code Editor, Template Loader, Copy/Save/Load options
    - Modeling Style Selector (Gate-Level, Dataflow, Behavioral, Switch-Level)
    - Synthesis & HDL Generation engines
    - Status / Console output
    """

    def __init__(self, scene, parent=None):
        super().__init__(parent)
        self.scene = scene
        self.setWindowTitle("⚡ Verilog HDL Studio — Synthesis & HDL Generator")
        self.setMinimumSize(1020, 680)
        self._apply_style()
        self._build_ui()

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog { background: #0d1117; color: #e6edf3; }
            QLabel { color: #8b949e; font-family: Consolas; }
            QGroupBox { border: 1px solid #30363d; border-radius: 6px; margin-top: 12px;
                        font-family: Consolas; font-size: 10px; color: #58a6ff; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
            QPlainTextEdit, QTextEdit {
                background: #161b22; color: #c9d1d9; border: 1px solid #30363d;
                border-radius: 4px; font-family: Consolas; font-size: 12px; line-height: 1.4;
            }
            QLineEdit {
                background: #161b22; color: #58a6ff; border: 1px solid #30363d;
                border-radius: 4px; padding: 6px 10px; font-family: Consolas; font-size: 11px;
            }
            QComboBox {
                background: #161b22; color: #e6edf3; border: 1px solid #30363d;
                border-radius: 4px; padding: 6px 10px; font-family: Consolas; font-size: 11px;
            }
            QComboBox QAbstractItemView {
                background: #161b22; color: #e6edf3; selection-background-color: #1f6feb;
            }
            QPushButton {
                background: #21262d; color: #e6edf3; border: 1px solid #30363d;
                border-radius: 4px; padding: 8px 14px; font-family: Consolas; font-size: 11px;
            }
            QPushButton:hover { background: #30363d; border-color: #58a6ff; }
        """)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        # Header bar
        hdr_bar = QHBoxLayout()
        hdr_lbl = QLabel("⚡ Verilog HDL Studio")
        hdr_lbl.setFont(QFont("Consolas", 13, QFont.Bold))
        hdr_lbl.setStyleSheet("color: #58a6ff;")
        hdr_bar.addWidget(hdr_lbl)

        sub_lbl = QLabel("Bidirectional Synthesis & HDL Code Generation (Gate-Level • Dataflow • Behavioral • Switch-Level)")
        sub_lbl.setFont(QFont("Consolas", 9))
        sub_lbl.setStyleSheet("color: #8b949e;")
        hdr_bar.addWidget(sub_lbl)
        hdr_bar.addStretch()

        root.addLayout(hdr_bar)

        # Main splitter (Left: Editor, Right: Conversion & Controls)
        splitter = QSplitter(Qt.Horizontal)

        # ── Left Pane: Code Editor ────────────────────────────────────
        left_pane = QWidget()
        ll = QVBoxLayout(left_pane)
        ll.setContentsMargins(0, 0, 8, 0)
        ll.setSpacing(8)

        # Template Bar
        tmpl_bar = QHBoxLayout()
        tmpl_lbl = QLabel("Template:")
        tmpl_lbl.setFont(QFont("Consolas", 9, QFont.Bold))
        tmpl_bar.addWidget(tmpl_lbl)

        self._tmpl_combo = QComboBox()
        self._tmpl_combo.addItem("Select a design template...")
        for name in TEMPLATES:
            self._tmpl_combo.addItem(name)
        self._tmpl_combo.currentIndexChanged.connect(self._load_template)
        tmpl_bar.addWidget(self._tmpl_combo, stretch=1)
        ll.addLayout(tmpl_bar)

        # Code Editor
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText(
            "// Enter your Verilog module code here...\n"
            "module my_circuit (input clk, input d, output q);\n"
            "    always @(posedge clk) q <= d;\n"
            "endmodule"
        )
        # Default with D-FF template
        self.editor.setPlainText(TEMPLATES["D Flip-Flop with Async Reset (Sequential)"])
        ll.addWidget(self.editor, stretch=1)

        # Action Buttons under Editor
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(6)

        btn_synth = QPushButton("⚡ Generate Circuit from Verilog")
        btn_synth.setFont(QFont("Consolas", 9, QFont.Bold))
        btn_synth.setStyleSheet(
            "QPushButton{background:#1f6feb;color:#ffffff;border:1px solid #388bfd;font-weight:bold;padding:9px 14px;}"
            "QPushButton:hover{background:#388bfd;}"
        )
        btn_synth.clicked.connect(self._synthesize_to_schematic)
        btn_bar.addWidget(btn_synth)

        btn_copy = QPushButton("📋 Copy")
        btn_copy.setToolTip("Copy code to clipboard")
        btn_copy.clicked.connect(self._copy_code)
        btn_bar.addWidget(btn_copy)

        btn_save = QPushButton("💾 Save .v")
        btn_save.setToolTip("Save to .v Verilog file")
        btn_save.clicked.connect(self._save_file)
        btn_bar.addWidget(btn_save)

        btn_load = QPushButton("📂 Load .v")
        btn_load.setToolTip("Load from .v Verilog file")
        btn_load.clicked.connect(self._load_file)
        btn_bar.addWidget(btn_load)

        btn_clear = QPushButton("🗑 Clear")
        btn_clear.clicked.connect(self.editor.clear)
        btn_bar.addWidget(btn_clear)

        ll.addLayout(btn_bar)
        splitter.addWidget(left_pane)

        # ── Right Pane: Schematic -> Verilog & Console ────────────────
        right_pane = QWidget()
        rl = QVBoxLayout(right_pane)
        rl.setContentsMargins(8, 0, 0, 0)
        rl.setSpacing(10)

        # Box 1: Schematic -> Verilog Conversion Settings
        conv_grp = QGroupBox("SCHEMATIC ➔ VERILOG CONVERTER")
        cgl = QVBoxLayout(conv_grp)
        cgl.setSpacing(8)

        # Module Name input
        mod_row = QHBoxLayout()
        mod_lbl = QLabel("Module Name:")
        mod_lbl.setFixedWidth(90)
        self._mod_input = QLineEdit("circuit_top")
        mod_row.addWidget(mod_lbl)
        mod_row.addWidget(self._mod_input)
        cgl.addLayout(mod_row)

        # Modeling Style Combo
        style_row = QHBoxLayout()
        style_lbl = QLabel("Modeling Style:")
        style_lbl.setFixedWidth(90)
        self._style_combo = QComboBox()
        self._style_combo.addItem("1. Gate-Level (Primitives & Cells)", "gate_level")
        self._style_combo.addItem("2. Dataflow (assign & Boolean Logic)", "dataflow")
        self._style_combo.addItem("3. Behavioral (always @(*) & Sequential)", "behavioral")
        self._style_combo.addItem("4. Switch-Level (CMOS Transistors)", "switch_level")
        style_row.addWidget(style_lbl)
        style_row.addWidget(self._style_combo)
        cgl.addLayout(style_row)

        # Description of selected style
        self._style_desc = QLabel(
            "• Structural modeling using Verilog primitives (and, or, xor, not) and flip-flop cell instances."
        )
        self._style_desc.setWordWrap(True)
        self._style_desc.setFont(QFont("Consolas", 8))
        self._style_desc.setStyleSheet("color:#7ee787;padding:2px 0;")
        self._style_combo.currentIndexChanged.connect(self._update_style_desc)
        cgl.addWidget(self._style_desc)

        # Convert Circuit Button
        btn_to_verilog = QPushButton("⇄ Convert Circuit to Verilog")
        btn_to_verilog.setFont(QFont("Consolas", 9, QFont.Bold))
        btn_to_verilog.setStyleSheet(
            "QPushButton{background:#238636;color:#ffffff;border:1px solid #2ea043;font-weight:bold;padding:10px;}"
            "QPushButton:hover{background:#2ea043;}"
        )
        btn_to_verilog.clicked.connect(self._convert_circuit_to_verilog)
        cgl.addWidget(btn_to_verilog)

        rl.addWidget(conv_grp)

        # Box 2: Synthesis & Diagnostic Console
        console_grp = QGroupBox("SYNTHESIS & COMPILER CONSOLE")
        csl = QVBoxLayout(console_grp)
        csl.setSpacing(6)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Consolas", 9))
        self.console.setStyleSheet("background:#0d1117;color:#8b949e;border:1px solid #30363d;padding:6px;")
        csl.addWidget(self.console, stretch=1)

        clr_btn = QPushButton("Clear Console")
        clr_btn.clicked.connect(self.console.clear)
        csl.addWidget(clr_btn)

        rl.addWidget(console_grp, stretch=1)
        splitter.addWidget(right_pane)

        # Set splitter sizes 60% / 40%
        splitter.setSizes([620, 380])
        root.addWidget(splitter, stretch=1)

        # Dialog bottom close button
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        bottom_bar.addWidget(close_btn)
        root.addLayout(bottom_bar)

        self._log("⚡ Verilog HDL Studio initialized.", color="#58a6ff")
        self._log(f"Canvas state: {len(self.scene.gates)} gates, {len(self.scene.wires)} wires ready.")

    def _update_style_desc(self, idx):
        descriptions = [
            "• Structural modeling using Verilog primitives (and, or, xor, not) and flip-flop cell instances.",
            "• Concurrent dataflow modeling using continuous 'assign' statements with boolean logic operators.",
            "• Behavioral modeling using procedural 'always @(*)' combinational and 'always @(posedge clk)' sequential blocks.",
            "• Low-level CMOS transistor switch network using 'pmos', 'nmos', and 'cmos' switch primitives.",
        ]
        if 0 <= idx < len(descriptions):
            self._style_desc.setText(descriptions[idx])

    def _load_template(self, idx):
        if idx <= 0:
            return
        name = self._tmpl_combo.currentText()
        if name in TEMPLATES:
            self.editor.setPlainText(TEMPLATES[name])
            self._log(f"Loaded template: '{name}'", color="#58a6ff")

    def _log(self, text, color="#c9d1d9"):
        self.console.append(f'<span style="color:{color}; font-family:Consolas;">{text}</span>')
        self.console.moveCursor(QTextCursor.End)

    # ───────────────────────────────────────────────────────────────────
    # Action 1: Verilog Code -> Schematic (Synthesizer)
    # ───────────────────────────────────────────────────────────────────
    def _synthesize_to_schematic(self):
        code = self.editor.toPlainText().strip()
        if not code:
            self._log("❌ Error: Code editor is empty. Provide a Verilog module.", color="#f85149")
            return

        self._log("⚡ Starting Verilog synthesis...", color="#58a6ff")
        parser = VerilogParser(code)
        ok = parser.parse()

        if not ok or parser.errors:
            self._log("❌ Syntax & Synthesis Errors detected:", color="#f85149")
            for err in parser.errors:
                self._log(f"  • {err}", color="#ff7b72")
            return

        for warn in parser.warnings:
            self._log(f"⚠ Warning: {warn}", color="#d29922")

        # Synthesize onto scene
        synth = VerilogSynthesizer(self.scene, parser)
        g_cnt, w_cnt = synth.synthesize(clear_scene=True)

        self._log(f"✓ Synthesis Successful for module '{parser.module_name}'!", color="#3fb950")
        self._log(f"  • Ports: {len(parser.inputs)} inputs, {len(parser.outputs)} outputs", color="#7ee787")
        self._log(f"  • Sequential Blocks: {len(parser.sequential_blocks)} registers", color="#7ee787")
        self._log(f"  • Generated Circuit: {g_cnt} components placed, {w_cnt} nets wired.", color="#3fb950")
        self._log("Canvas auto-layout completed ✓", color="#58a6ff")

        # Fit view if parent window has view
        parent = self.parent()
        if parent and hasattr(parent, 'view'):
            parent.view.fit_circuit()

    # ───────────────────────────────────────────────────────────────────
    # Action 2: Schematic -> Verilog Code (Generator)
    # ───────────────────────────────────────────────────────────────────
    def _convert_circuit_to_verilog(self):
        if not self.scene.gates:
            self._log("❌ Error: Canvas is empty. Add gates, inputs, or flip-flops first.", color="#f85149")
            return

        style_key = self._style_combo.currentData() or "gate_level"
        mod_name = self._mod_input.text().strip() or "circuit_top"

        self._log(f"⚡ Generating Verilog code (Style: {style_key})...", color="#58a6ff")
        gen = VerilogGenerator(self.scene, module_name=mod_name)
        code = gen.generate(style=style_key)

        self.editor.setPlainText(code)
        self._log(f"✓ Circuit converted to Verilog ({len(code)} characters).", color="#3fb950")
        self._log(f"  • Inputs: {len(gen.inputs)}  |  Outputs: {len(gen.outputs)}  |  Gates/FF: {len(gen.internal_gates)}", color="#7ee787")

    # ───────────────────────────────────────────────────────────────────
    # File & Clipboard Actions
    # ───────────────────────────────────────────────────────────────────
    def _copy_code(self):
        code = self.editor.toPlainText()
        if code:
            QApplication.clipboard().setText(code)
            self._log("📋 Code copied to system clipboard ✓", color="#3fb950")
        else:
            self._log("Nothing to copy.", color="#8b949e")

    def _save_file(self):
        code = self.editor.toPlainText()
        if not code.strip():
            self._log("Editor is empty. Nothing to save.", color="#8b949e")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Verilog File", "", "Verilog HDL Files (*.v *.sv);;All Files (*)"
        )
        if path:
            if not path.endswith('.v') and not path.endswith('.sv'):
                path += '.v'
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(code)
                self._log(f"💾 Saved to {os.path.basename(path)} ✓", color="#3fb950")
            except Exception as e:
                self._log(f"❌ Save error: {e}", color="#f85149")

    def _load_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Verilog File", "", "Verilog HDL Files (*.v *.sv);;All Files (*)"
        )
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    code = f.read()
                self.editor.setPlainText(code)
                self._log(f"📂 Loaded {os.path.basename(path)} ✓", color="#3fb950")
            except Exception as e:
                self._log(f"❌ Load error: {e}", color="#f85149")
