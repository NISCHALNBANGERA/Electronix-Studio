"""
code_converter.py - Digital Code Converter with animated step visualization
Supports: Decimal, Binary, BCD, Excess-3, Gray Code, 2421, ASCII↔Binary
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QLineEdit,
    QFrame, QWidget, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import QGraphicsOpacityEffect


# ── Conversion Engine ─────────────────────────────────────────────────
class ConversionEngine:

    CODES = ["Decimal", "Binary", "BCD", "Excess-3", "Gray Code", "2421", "ASCII→Binary", "Binary→ASCII"]

    @staticmethod
    def decimal_to_binary(n: int, bits=8) -> str:
        return bin(n)[2:].zfill(bits)

    @staticmethod
    def binary_to_decimal(b: str) -> int:
        return int(b, 2)

    @staticmethod
    def decimal_to_bcd(n: int) -> str:
        return ' '.join(bin(int(d))[2:].zfill(4) for d in str(n))

    @staticmethod
    def decimal_to_excess3(n: int) -> str:
        return ' '.join(bin(int(d) + 3)[2:].zfill(4) for d in str(n))

    @staticmethod
    def decimal_to_gray(n: int, bits=8) -> str:
        gray = n ^ (n >> 1)
        return bin(gray)[2:].zfill(bits)

    @staticmethod
    def gray_to_decimal(g: str) -> int:
        n = int(g, 2)
        mask = n >> 1
        while mask:
            n ^= mask
            mask >>= 1
        return n

    @staticmethod
    def decimal_to_2421(n: int) -> str:
        """2421 BCD code (weighted: 2,4,2,1)"""
        TABLE = {
            0:'0000',1:'0001',2:'0010',3:'0011',4:'0100',
            5:'1011',6:'1100',7:'1101',8:'1110',9:'1111'
        }
        return ' '.join(TABLE.get(int(d),'????') for d in str(n))

    @staticmethod
    def ascii_to_binary(text: str) -> str:
        return ' '.join(bin(ord(c))[2:].zfill(8) for c in text)

    @staticmethod
    def binary_to_ascii(b: str) -> str:
        chunks = b.replace(' ','')
        result = ''
        for i in range(0, len(chunks), 8):
            byte = chunks[i:i+8]
            if len(byte) == 8:
                result += chr(int(byte, 2))
        return result

    @classmethod
    def convert(cls, value_str: str, from_code: str, to_code: str):
        """Main conversion dispatcher. Returns (result_str, steps_list)"""
        steps = []
        try:
            # Step 1: Parse input
            if from_code == "Decimal":
                n = int(value_str)
                steps.append(("Input", f"Decimal: {n}"))
            elif from_code == "Binary":
                n = cls.binary_to_decimal(value_str.replace(' ',''))
                steps.append(("Parse", f"Binary {value_str} → Decimal {n}"))
            elif from_code == "Gray Code":
                n = cls.gray_to_decimal(value_str.replace(' ',''))
                steps.append(("Parse", f"Gray {value_str} → Decimal {n}"))
            elif from_code == "ASCII→Binary":
                result = cls.ascii_to_binary(value_str)
                steps.append(("Input", f"Text: \"{value_str}\""))
                steps.append(("Convert", f"ASCII codes: {[ord(c) for c in value_str]}"))
                steps.append(("Output", f"Binary: {result}"))
                return result, steps
            elif from_code == "Binary→ASCII":
                result = cls.binary_to_ascii(value_str)
                steps.append(("Input", f"Binary: {value_str}"))
                steps.append(("Output", f"Text: \"{result}\""))
                return result, steps
            else:
                n = int(value_str)
                steps.append(("Input", f"{from_code}: {value_str}"))

            # Step 2: Convert to target
            if to_code == "Binary":
                result = cls.decimal_to_binary(n)
                steps.append(("Step", f"Decimal {n} ÷ 2 repeatedly"))
                steps.append(("Output", f"Binary: {result}"))
            elif to_code == "Decimal":
                result = str(n)
                steps.append(("Output", f"Decimal: {result}"))
            elif to_code == "BCD":
                result = cls.decimal_to_bcd(n)
                steps.append(("Step", f"Each digit 0-9 → 4-bit group"))
                for d in str(n):
                    steps.append(("Detail", f"  {d} → {bin(int(d))[2:].zfill(4)}"))
                steps.append(("Output", f"BCD: {result}"))
            elif to_code == "Excess-3":
                result = cls.decimal_to_excess3(n)
                steps.append(("Step", f"Each digit + 3, then BCD-encode"))
                for d in str(n):
                    steps.append(("Detail", f"  {d}+3={int(d)+3} → {bin(int(d)+3)[2:].zfill(4)}"))
                steps.append(("Output", f"Excess-3: {result}"))
            elif to_code == "Gray Code":
                result = cls.decimal_to_gray(n)
                binary = cls.decimal_to_binary(n)
                steps.append(("Step", f"Binary: {binary}"))
                steps.append(("Step", f"XOR adjacent bits: {n} XOR {n>>1} = {n ^ (n>>1)}"))
                steps.append(("Output", f"Gray Code: {result}"))
            elif to_code == "2421":
                result = cls.decimal_to_2421(n)
                steps.append(("Step", "Lookup 2421 table per digit"))
                steps.append(("Output", f"2421 Code: {result}"))
            else:
                result = str(n)
                steps.append(("Output", result))

            return result, steps

        except Exception as e:
            return f"Error: {e}", [("Error", str(e))]


# ── Step Card Widget ──────────────────────────────────────────────────
class StepCard(QFrame):
    """An animated step card in the conversion flow."""

    COLORS = {
        "Input":  ("#1565c0", "#42a5f5"),
        "Parse":  ("#4a148c", "#ce93d8"),
        "Step":   ("#1b5e20", "#66bb6a"),
        "Detail": ("#263238", "#90a4ae"),
        "Output": ("#b71c1c", "#ef9a9a"),
        "Error":  ("#b71c1c", "#ef5350"),
    }

    def __init__(self, kind, text, parent=None):
        super().__init__(parent)
        bg, fg = self.COLORS.get(kind, ("#21262d", "#e0e0e0"))
        self.setStyleSheet(f"""
            QFrame {{ background: {bg}; border-radius: 8px;
                     border: 1px solid {fg}33; margin: 2px; }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        badge = QLabel(kind)
        badge.setFixedWidth(55)
        badge.setStyleSheet(f"color:{fg}; font-family:Consolas; font-size:9px; font-weight:bold; background:transparent; border:none;")
        layout.addWidget(badge)

        lbl = QLabel(text)
        lbl.setStyleSheet(f"color:#e0e0e0; font-family:Consolas; font-size:12px; background:transparent; border:none;")
        lbl.setWordWrap(True)
        layout.addWidget(lbl, stretch=1)

        # Opacity effect for fade-in
        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        self.effect.setOpacity(0)


class CodeConverterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Digital Code Converter")
        self.setMinimumSize(680, 600)
        self._apply_style()
        self._build_ui()
        self._step_cards = []

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog { background: #0d1117; color: #e0e0e0; }
            QLabel { color: #b0bec5; font-family: Consolas; }
            QLineEdit { background: #161b22; color: #4fc3f7; border: 1px solid #4fc3f7;
                        padding: 10px; font-family: Consolas; font-size: 14px; border-radius:4px; }
            QComboBox { background: #161b22; color: #e0e0e0; border: 1px solid #30363d;
                        padding: 6px 10px; font-family: Consolas; font-size: 12px; border-radius:4px; }
            QPushButton { background: #21262d; color: #e0e0e0; border: 1px solid #30363d;
                          padding: 10px 22px; border-radius: 4px; font-family: Consolas; font-size:12px; }
            QPushButton:hover { background: #1f6feb; border-color: #58a6ff; }
        """)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(14)
        root.setContentsMargins(18, 18, 18, 18)

        # Header
        hdr = QLabel("⇄  Digital Code Converter")
        hdr.setFont(QFont("Consolas", 14, QFont.Bold))
        hdr.setStyleSheet("color: #4fc3f7;")
        root.addWidget(hdr)

        # I/O row
        io_frame = QFrame()
        io_frame.setStyleSheet("QFrame{background:#161b22;border-radius:8px;border:1px solid #30363d;}")
        io_layout = QGridLayout(io_frame)
        io_layout.setSpacing(10)
        io_layout.setContentsMargins(14, 14, 14, 14)

        io_layout.addWidget(QLabel("Input type:"), 0, 0)
        self.from_combo = QComboBox()
        self.from_combo.addItems(ConversionEngine.CODES)
        io_layout.addWidget(self.from_combo, 0, 1)

        io_layout.addWidget(QLabel("Output type:"), 0, 2)
        self.to_combo = QComboBox()
        self.to_combo.addItems(ConversionEngine.CODES)
        self.to_combo.setCurrentIndex(1)
        io_layout.addWidget(self.to_combo, 0, 3)

        io_layout.addWidget(QLabel("Input value:"), 1, 0)
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Enter value...")
        self.input_box.returnPressed.connect(self._convert)
        io_layout.addWidget(self.input_box, 1, 1, 1, 3)

        root.addWidget(io_frame)

        # Buttons
        btn_row = QHBoxLayout()
        conv_btn = QPushButton("⇄  Convert")
        conv_btn.setStyleSheet("QPushButton{background:#1b5e20;color:#a5d6a7;border:1px solid #388e3c;padding:10px 24px;border-radius:4px;font-family:Consolas;font-weight:bold;font-size:13px;}"
                               "QPushButton:hover{background:#2e7d32;}")
        conv_btn.clicked.connect(self._convert)
        btn_row.addWidget(conv_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

        # Result
        res_frame = QFrame()
        res_frame.setStyleSheet("QFrame{background:#161b22;border-radius:8px;border:1px solid #30363d;}")
        res_layout = QVBoxLayout(res_frame)
        res_layout.setContentsMargins(14, 10, 14, 10)
        lbl = QLabel("Result:")
        lbl.setStyleSheet("color:#8b949e; font-size:10px;")
        res_layout.addWidget(lbl)
        self.result_label = QLabel("—")
        self.result_label.setFont(QFont("Consolas", 18, QFont.Bold))
        self.result_label.setStyleSheet("color:#ffeb3b;")
        self.result_label.setWordWrap(True)
        res_layout.addWidget(self.result_label)
        root.addWidget(res_frame)

        # Step flow (scrollable)
        sep = QLabel("Conversion Steps:")
        sep.setStyleSheet("color:#8b949e; font-size:10px; font-family:Consolas;")
        root.addWidget(sep)

        self.steps_scroll = QScrollArea()
        self.steps_scroll.setWidgetResizable(True)
        self.steps_scroll.setStyleSheet("QScrollArea{border:1px solid #30363d;border-radius:4px;background:#0d1117;}")

        self.steps_widget = QWidget()
        self.steps_widget.setStyleSheet("background:#0d1117;")
        self.steps_layout = QVBoxLayout(self.steps_widget)
        self.steps_layout.setSpacing(4)
        self.steps_layout.setContentsMargins(6, 6, 6, 6)
        self.steps_layout.addStretch()

        self.steps_scroll.setWidget(self.steps_widget)
        root.addWidget(self.steps_scroll, stretch=1)

    def _convert(self):
        val = self.input_box.text().strip()
        if not val:
            return
        from_code = self.from_combo.currentText()
        to_code   = self.to_combo.currentText()

        result, steps = ConversionEngine.convert(val, from_code, to_code)
        self.result_label.setText(result)
        self._animate_steps(steps)

    def _animate_steps(self, steps):
        # Clear old
        for card in self._step_cards:
            card.deleteLater()
        self._step_cards = []

        stretch = self.steps_layout.takeAt(self.steps_layout.count() - 1)

        for i, (kind, text) in enumerate(steps):
            card = StepCard(kind, text)
            self.steps_layout.addWidget(card)
            self._step_cards.append(card)
            # Fade in each card with delay
            QTimer.singleShot(i * 180, lambda c=card: self._fade_in(c))

        self.steps_layout.addStretch()

    def _fade_in(self, card):
        anim = QPropertyAnimation(card.effect, b"opacity")
        anim.setDuration(350)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
        card._anim = anim  # keep reference

    def _clear(self):
        self.input_box.clear()
        self.result_label.setText("—")
        for card in self._step_cards:
            card.deleteLater()
        self._step_cards = []
