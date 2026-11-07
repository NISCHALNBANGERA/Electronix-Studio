"""
ic_chip.py - Virtual 74xx Dual In-line Package (DIP) IC Simulator.
Features realistic DIP-14 and DIP-16 packages, true pinout definitions,
power rail verification (VCC=1, GND=0), and real-time internal gate simulation.
"""
from PyQt5.QtWidgets import QGraphicsItem
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPainterPath
from gate import GateItem, Pin


# ═══════════════════════════════════════════════════════════════════════
# 74xx IC Pinout & Logic Definitions
# ═══════════════════════════════════════════════════════════════════════
# Pin numbering:
# DIP-14: Pins 1..7 down left side, 8..14 up right side (counter-clockwise).
# DIP-16: Pins 1..8 down left side, 9..16 up right side.

IC_CATALOG = {
    '7400': {
        'part': 'SN74LS00N',
        'desc': 'Quad 2-Input NAND Gates',
        'pins_count': 14,
        'vcc_pin': 14,
        'gnd_pin': 7,
        'pin_def': {
            1: ('input', '1A'), 2: ('input', '1B'), 3: ('output', '1Y'),
            4: ('input', '2A'), 5: ('input', '2B'), 6: ('output', '2Y'),
            7: ('input', 'GND'),
            8: ('output', '3Y'), 9: ('input', '3A'), 10: ('input', '3B'),
            11: ('output', '4Y'), 12: ('input', '4A'), 13: ('input', '4B'),
            14: ('input', 'VCC'),
        },
        'gates_info': '4x independent 2-input NAND gates'
    },
    '7402': {
        'part': 'SN74LS02N',
        'desc': 'Quad 2-Input NOR Gates',
        'pins_count': 14,
        'vcc_pin': 14,
        'gnd_pin': 7,
        'pin_def': {
            1: ('output', '1Y'), 2: ('input', '1A'), 3: ('input', '1B'),
            4: ('output', '2Y'), 5: ('input', '2A'), 6: ('input', '2B'),
            7: ('input', 'GND'),
            8: ('input', '3A'), 9: ('input', '3B'), 10: ('output', '3Y'),
            11: ('input', '4A'), 12: ('input', '4B'), 13: ('output', '4Y'),
            14: ('input', 'VCC'),
        },
        'gates_info': '4x independent 2-input NOR gates'
    },
    '7404': {
        'part': 'SN74LS04N',
        'desc': 'Hex Inverter (NOT)',
        'pins_count': 14,
        'vcc_pin': 14,
        'gnd_pin': 7,
        'pin_def': {
            1: ('input', '1A'), 2: ('output', '1Y'),
            3: ('input', '2A'), 4: ('output', '2Y'),
            5: ('input', '3A'), 6: ('output', '3Y'),
            7: ('input', 'GND'),
            8: ('output', '4Y'), 9: ('input', '4A'),
            10: ('output', '5Y'), 11: ('input', '5A'),
            12: ('output', '6Y'), 13: ('input', '6A'),
            14: ('input', 'VCC'),
        },
        'gates_info': '6x independent inverters'
    },
    '7408': {
        'part': 'SN74LS08N',
        'desc': 'Quad 2-Input AND Gates',
        'pins_count': 14,
        'vcc_pin': 14,
        'gnd_pin': 7,
        'pin_def': {
            1: ('input', '1A'), 2: ('input', '1B'), 3: ('output', '1Y'),
            4: ('input', '2A'), 5: ('input', '2B'), 6: ('output', '2Y'),
            7: ('input', 'GND'),
            8: ('output', '3Y'), 9: ('input', '3A'), 10: ('input', '3B'),
            11: ('output', '4Y'), 12: ('input', '4A'), 13: ('input', '4B'),
            14: ('input', 'VCC'),
        },
        'gates_info': '4x independent 2-input AND gates'
    },
    '7432': {
        'part': 'SN74LS32N',
        'desc': 'Quad 2-Input OR Gates',
        'pins_count': 14,
        'vcc_pin': 14,
        'gnd_pin': 7,
        'pin_def': {
            1: ('input', '1A'), 2: ('input', '1B'), 3: ('output', '1Y'),
            4: ('input', '2A'), 5: ('input', '2B'), 6: ('output', '2Y'),
            7: ('input', 'GND'),
            8: ('output', '3Y'), 9: ('input', '3A'), 10: ('input', '3B'),
            11: ('output', '4Y'), 12: ('input', '4A'), 13: ('input', '4B'),
            14: ('input', 'VCC'),
        },
        'gates_info': '4x independent 2-input OR gates'
    },
    '7486': {
        'part': 'SN74LS86N',
        'desc': 'Quad 2-Input XOR Gates',
        'pins_count': 14,
        'vcc_pin': 14,
        'gnd_pin': 7,
        'pin_def': {
            1: ('input', '1A'), 2: ('input', '1B'), 3: ('output', '1Y'),
            4: ('input', '2A'), 5: ('input', '2B'), 6: ('output', '2Y'),
            7: ('input', 'GND'),
            8: ('output', '3Y'), 9: ('input', '3A'), 10: ('input', '3B'),
            11: ('output', '4Y'), 12: ('input', '4A'), 13: ('input', '4B'),
            14: ('input', 'VCC'),
        },
        'gates_info': '4x independent 2-input XOR gates'
    },
    '7474': {
        'part': 'SN74LS74AN',
        'desc': 'Dual D Positive-Edge Flip-Flops w/ Preset & Clear',
        'pins_count': 14,
        'vcc_pin': 14,
        'gnd_pin': 7,
        'pin_def': {
            1: ('input', '1CLR_b'), 2: ('input', '1D'), 3: ('input', '1CLK'),
            4: ('input', '1PRE_b'), 5: ('output', '1Q'), 6: ('output', '1Q_b'),
            7: ('input', 'GND'),
            8: ('output', '2Q_b'), 9: ('output', '2Q'), 10: ('input', '2PRE_b'),
            11: ('input', '2CLK'), 12: ('input', '2D'), 13: ('input', '2CLR_b'),
            14: ('input', 'VCC'),
        },
        'gates_info': '2x D Flip-Flops with async active-low Set/Reset'
    },
    '74138': {
        'part': 'SN74LS138N',
        'desc': '3-to-8 Line Decoder / Demultiplexer',
        'pins_count': 16,
        'vcc_pin': 16,
        'gnd_pin': 8,
        'pin_def': {
            1: ('input', 'A'), 2: ('input', 'B'), 3: ('input', 'C'),
            4: ('input', 'G2A_b'), 5: ('input', 'G2B_b'), 6: ('input', 'G1'),
            7: ('output', 'Y7_b'), 8: ('input', 'GND'),
            9: ('output', 'Y6_b'), 10: ('output', 'Y5_b'), 11: ('output', 'Y4_b'),
            12: ('output', 'Y3_b'), 13: ('output', 'Y2_b'), 14: ('output', 'Y1_b'),
            15: ('output', 'Y0_b'), 16: ('input', 'VCC'),
        },
        'gates_info': '3-to-8 Decoder with 3 enable inputs (active-low outputs)'
    },
    '74151': {
        'part': 'SN74LS151N',
        'desc': '8-to-1 Line Data Selector / Multiplexer',
        'pins_count': 16,
        'vcc_pin': 16,
        'gnd_pin': 8,
        'pin_def': {
            1: ('input', 'D3'), 2: ('input', 'D2'), 3: ('input', 'D1'), 4: ('input', 'D0'),
            5: ('output', 'Y'), 6: ('output', 'W_b'), 7: ('input', 'G_b'), 8: ('input', 'GND'),
            9: ('input', 'C'), 10: ('input', 'B'), 11: ('input', 'A'),
            12: ('input', 'D4'), 13: ('input', 'D5'), 14: ('input', 'D6'), 15: ('input', 'D7'),
            16: ('input', 'VCC'),
        },
        'gates_info': '8-input data selector with complementary outputs (Y and W=Y_bar)'
    }
}


class DIPChipItem(GateItem):
    """
    Virtual Dual In-line Package (DIP) IC component for circuit canvas.
    Renders realistic DIP packaging with metallic pins, power rail verification,
    and internal TTL gate simulation.
    """
    BODY_W = 120

    def __init__(self, ic_type="7408", label=""):
        self.ic_type = ic_type if ic_type in IC_CATALOG else "7408"
        self.ic_spec = IC_CATALOG[self.ic_type]
        self.pins_count = self.ic_spec['pins_count']
        self.vcc_pin_num = self.ic_spec['vcc_pin']
        self.gnd_pin_num = self.ic_spec['gnd_pin']
        self.is_powered = False

        # Sequential state memory for flip-flop ICs like 7474
        self._ff1_q = 0
        self._ff1_prev_clk = 0
        self._ff2_q = 0
        self._ff2_prev_clk = 0

        # Physical sizing: DIP pins are standard 0.1" (2.54mm) pitch -> ~26px spacing
        pins_per_side = self.pins_count // 2
        self.BODY_H = max(190, 26 * (pins_per_side + 1))
        self.W = self.BODY_W
        self.H = self.BODY_H

        super().__init__(f'IC_{self.ic_type}', label=label or self.ic_type, num_inputs=0)
        self.setToolTip(f"{self.ic_spec['part']} — {self.ic_spec['desc']}\nRight-click -> 📖 Open IC Datasheet")

    def _build_pins(self):
        """Construct pins according to counter-clockwise DIP packaging convention."""
        self.input_pins = []
        self.output_pins = []
        self.pin_by_num = {}

        pins_per_side = self.pins_count // 2
        step = self.H / (pins_per_side + 1)

        # 1. Left side: Pins 1 to pins_per_side (top to bottom)
        for i in range(1, pins_per_side + 1):
            pin_type, pin_lbl = self.ic_spec['pin_def'][i]
            y = step * i - self.H / 2
            pos = QPointF(-Pin.RADIUS - 6, y)
            if pin_type == 'input':
                p = Pin(self, 'input', len(self.input_pins), pos, f"{i}:{pin_lbl}")
                self.input_pins.append(p)
            else:
                p = Pin(self, 'output', len(self.output_pins), pos, f"{i}:{pin_lbl}")
                self.output_pins.append(p)
            self.pin_by_num[i] = p

        # 2. Right side: Pins (pins_per_side + 1) to pins_count (bottom to top!)
        for idx, pin_num in enumerate(range(pins_per_side + 1, self.pins_count + 1)):
            # bottom-to-top position
            slot = pins_per_side - idx
            y = step * slot - self.H / 2
            pos = QPointF(self.W + Pin.RADIUS + 6, y)
            pin_type, pin_lbl = self.ic_spec['pin_def'][pin_num]
            if pin_type == 'input':
                p = Pin(self, 'input', len(self.input_pins), pos, f"{pin_num}:{pin_lbl}")
                self.input_pins.append(p)
            else:
                p = Pin(self, 'output', len(self.output_pins), pos, f"{pin_num}:{pin_lbl}")
                self.output_pins.append(p)
            self.pin_by_num[pin_num] = p

    def _get_pin_val(self, pin_num):
        p = self.pin_by_num.get(pin_num)
        return p.value if p else 0

    def _set_pin_val(self, pin_num, val):
        p = self.pin_by_num.get(pin_num)
        if p and p.pin_type == 'output':
            p.set_value(int(val))

    def evaluate(self):
        """
        Verify power rails (VCC=1, GND=0).
        If powered, run internal gate simulation based on IC type.
        """
        vcc = self._get_pin_val(self.vcc_pin_num)
        gnd = self._get_pin_val(self.gnd_pin_num)
        self.is_powered = (vcc == 1 and gnd == 0)

        if not self.is_powered:
            # Unpowered chip cannot drive outputs (all 0)
            for p in self.output_pins:
                p.set_value(0)
            return 0

        # Execute internal TTL logic based on IC type
        ic = self.ic_type
        if ic == '7400':
            # Quad 2-NAND: 1Y=!(1A & 1B), 2Y=!(2A & 2B), 3Y=!(3A & 3B), 4Y=!(4A & 4B)
            self._set_pin_val(3,  not (self._get_pin_val(1) and self._get_pin_val(2)))
            self._set_pin_val(6,  not (self._get_pin_val(4) and self._get_pin_val(5)))
            self._set_pin_val(8,  not (self._get_pin_val(9) and self._get_pin_val(10)))
            self._set_pin_val(11, not (self._get_pin_val(12) and self._get_pin_val(13)))

        elif ic == '7402':
            # Quad 2-NOR: 1Y=!(1A | 1B), 2Y=!(2A | 2B), 3Y=!(3A | 3B), 4Y=!(4A | 4B)
            self._set_pin_val(1,  not (self._get_pin_val(2) or self._get_pin_val(3)))
            self._set_pin_val(4,  not (self._get_pin_val(5) or self._get_pin_val(6)))
            self._set_pin_val(10, not (self._get_pin_val(8) or self._get_pin_val(9)))
            self._set_pin_val(13, not (self._get_pin_val(11) or self._get_pin_val(12)))

        elif ic == '7404':
            # Hex Inverter: Y = !A
            self._set_pin_val(2,  not self._get_pin_val(1))
            self._set_pin_val(4,  not self._get_pin_val(3))
            self._set_pin_val(6,  not self._get_pin_val(5))
            self._set_pin_val(8,  not self._get_pin_val(9))
            self._set_pin_val(10, not self._get_pin_val(11))
            self._set_pin_val(12, not self._get_pin_val(13))

        elif ic == '7408':
            # Quad 2-AND: Y = A & B
            self._set_pin_val(3,  self._get_pin_val(1) and self._get_pin_val(2))
            self._set_pin_val(6,  self._get_pin_val(4) and self._get_pin_val(5))
            self._set_pin_val(8,  self._get_pin_val(9) and self._get_pin_val(10))
            self._set_pin_val(11, self._get_pin_val(12) and self._get_pin_val(13))

        elif ic == '7432':
            # Quad 2-OR: Y = A | B
            self._set_pin_val(3,  self._get_pin_val(1) or self._get_pin_val(2))
            self._set_pin_val(6,  self._get_pin_val(4) or self._get_pin_val(5))
            self._set_pin_val(8,  self._get_pin_val(9) or self._get_pin_val(10))
            self._set_pin_val(11, self._get_pin_val(12) or self._get_pin_val(13))

        elif ic == '7486':
            # Quad 2-XOR: Y = A ^ B
            self._set_pin_val(3,  self._get_pin_val(1) ^ self._get_pin_val(2))
            self._set_pin_val(6,  self._get_pin_val(4) ^ self._get_pin_val(5))
            self._set_pin_val(8,  self._get_pin_val(9) ^ self._get_pin_val(10))
            self._set_pin_val(11, self._get_pin_val(12) ^ self._get_pin_val(13))

        elif ic == '7474':
            # Dual D-FF:
            # FF1: CLR(1), D(2), CLK(3), PRE(4), Q(5), Q_b(6)
            clr1 = self._get_pin_val(1); d1 = self._get_pin_val(2)
            clk1 = self._get_pin_val(3); pre1 = self._get_pin_val(4)
            if pre1 == 0 and clr1 == 1: self._ff1_q = 1
            elif pre1 == 1 and clr1 == 0: self._ff1_q = 0
            elif pre1 == 1 and clr1 == 1:
                if clk1 == 1 and self._ff1_prev_clk == 0:  # posedge
                    self._ff1_q = d1
            self._ff1_prev_clk = clk1
            self._set_pin_val(5, self._ff1_q)
            self._set_pin_val(6, 1 - self._ff1_q)

            # FF2: Q_b(8), Q(9), PRE(10), CLK(11), D(12), CLR(13)
            pre2 = self._get_pin_val(10); clk2 = self._get_pin_val(11)
            d2 = self._get_pin_val(12); clr2 = self._get_pin_val(13)
            if pre2 == 0 and clr2 == 1: self._ff2_q = 1
            elif pre2 == 1 and clr2 == 0: self._ff2_q = 0
            elif pre2 == 1 and clr2 == 1:
                if clk2 == 1 and self._ff2_prev_clk == 0:  # posedge
                    self._ff2_q = d2
            self._ff2_prev_clk = clk2
            self._set_pin_val(9, self._ff2_q)
            self._set_pin_val(8, 1 - self._ff2_q)

        elif ic == '74138':
            # 3-to-8 Decoder:
            # Inputs: A(1), B(2), C(3), G2A_b(4), G2B_b(5), G1(6)
            # Enabled when G1=1 and G2A_b=0 and G2B_b=0
            enabled = (self._get_pin_val(6) == 1 and
                       self._get_pin_val(4) == 0 and
                       self._get_pin_val(5) == 0)
            addr = (self._get_pin_val(1)) | (self._get_pin_val(2) << 1) | (self._get_pin_val(3) << 2)
            out_pin_map = [15, 14, 13, 12, 11, 10, 9, 7]  # Y0_b..Y7_b
            for i, pnum in enumerate(out_pin_map):
                self._set_pin_val(pnum, 0 if (enabled and i == addr) else 1)

        elif ic == '74151':
            # 8-to-1 MUX:
            # Inputs: D3(1), D2(2), D1(3), D0(4), G_b(7), C(9), B(10), A(11), D4(12), D5(13), D6(14), D7(15)
            # Outputs: Y(5), W_b(6)
            g_b = self._get_pin_val(7)
            sel = (self._get_pin_val(11)) | (self._get_pin_val(10) << 1) | (self._get_pin_val(9) << 2)
            data_map = [4, 3, 2, 1, 12, 13, 14, 15]  # D0..D7
            if g_b == 1:
                y = 0
            else:
                y = self._get_pin_val(data_map[sel])
            self._set_pin_val(5, y)
            self._set_pin_val(6, 1 - y)

        return 1

    def _draw_body(self, painter):
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. Metallic DIP pin legs extending out from both sides
        pins_per_side = self.pins_count // 2
        step = self.H / (pins_per_side + 1)
        leg_pen = QPen(QColor("#94a3b8"), 3)
        painter.setPen(leg_pen)
        for i in range(1, pins_per_side + 1):
            y = int(step * i - self.H / 2)
            painter.drawLine(-10, y, 0, y)            # Left pin lead
            painter.drawLine(int(self.W), y, int(self.W + 10), y)  # Right pin lead

        # 2. Realistic Dark Epoxy Plastic IC Body
        body_rect = QRectF(0, -self.H/2, self.W, self.H)
        painter.setPen(QPen(QColor("#334155"), 2))
        painter.setBrush(QBrush(QColor("#1e222b")))
        painter.drawRoundedRect(body_rect, 6, 6)

        # Subtle chip bevel highlight
        painter.setPen(QPen(QColor("#475569"), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(body_rect.adjusted(2, 2, -2, -2), 4, 4)

        # 3. Top identification notch (semi-circle cutout)
        notch = QPainterPath()
        notch.arcTo(QRectF(self.W / 2 - 12, -self.H/2 - 8, 24, 16), 180, 180)
        painter.setPen(QPen(QColor("#334155"), 1.5))
        painter.setBrush(QBrush(QColor("#0d1117")))
        painter.drawPath(notch)

        # 4. Pin 1 polarity dot (recessed circle at top-left)
        painter.setPen(QPen(QColor("#0f172a"), 1))
        painter.setBrush(QBrush(QColor("#334155")))
        painter.drawEllipse(QRectF(10, -self.H/2 + 10, 8, 8))

        # 5. Power status indicator badge
        pwr_color = QColor("#22c55e") if self.is_powered else QColor("#ef4444")
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(pwr_color))
        painter.drawEllipse(QRectF(self.W - 18, -self.H/2 + 10, 8, 8))

        # 6. Silk-screen printed text on chip top
        painter.setFont(QFont("Consolas", 9, QFont.Bold))
        painter.setPen(QColor("#f1f5f9"))
        painter.drawText(QRectF(0, -self.H/2 + 28, self.W, 16), Qt.AlignCenter, self.ic_spec['part'])

        painter.setFont(QFont("Consolas", 6))
        painter.setPen(QColor("#94a3b8"))
        painter.drawText(QRectF(0, -self.H/2 + 44, self.W, 12), Qt.AlignCenter, "TI  MALAYSIA")

        # Power rail notice if unpowered
        if not self.is_powered:
            painter.setFont(QFont("Consolas", 6, QFont.Bold))
            painter.setPen(QColor("#f87171"))
            painter.drawText(QRectF(0, self.H/2 - 24, self.W, 12), Qt.AlignCenter, "⚡ NEEDS VCC/GND")
        else:
            painter.setFont(QFont("Consolas", 6))
            painter.setPen(QColor("#4ade80"))
            painter.drawText(QRectF(0, self.H/2 - 24, self.W, 12), Qt.AlignCenter, "● POWERED OK")

        # 7. Internal pin labels on chip face
        painter.setFont(QFont("Consolas", 6))
        for pin_num, pin_item in self.pin_by_num.items():
            _, lbl = self.ic_spec['pin_def'][pin_num]
            py = int(pin_item.pos().y())
            # Color code VCC and GND
            if pin_num == self.vcc_pin_num:
                painter.setPen(QColor("#ef4444"))
            elif pin_num == self.gnd_pin_num:
                painter.setPen(QColor("#64748b"))
            elif pin_item.pin_type == 'output':
                painter.setPen(QColor("#38bdf8"))
            else:
                painter.setPen(QColor("#94a3b8"))

            if pin_num <= pins_per_side:
                # Left side
                painter.drawText(8, py - 5, 45, 10, Qt.AlignLeft, f"{pin_num}:{lbl}")
            else:
                # Right side
                painter.drawText(int(self.W - 53), py - 5, 45, 10, Qt.AlignRight, f"{lbl}:{pin_num}")

    def _draw_label(self, painter):
        # Already handled with full silk-screen in _draw_body
        pass

    def to_dict(self):
        d = super().to_dict()
        d['ic_type'] = self.ic_type
        return d

    @staticmethod
    def from_dict(d):
        ic_type = d.get('ic_type', '7408')
        g = DIPChipItem(ic_type=ic_type, label=d.get('label', ''))
        g.gate_id = d['gate_id']
        g.setPos(d['x'], d['y'])
        return g

# Auto-register all ICs into gate.GATE_CLASSES
import gate
for _ic in IC_CATALOG:
    gate.GATE_CLASSES[f"IC_{_ic}"] = DIPChipItem
    gate.GATE_CLASSES[_ic] = DIPChipItem
