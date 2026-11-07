"""
waveform.py - Digital waveform viewer using matplotlib
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLabel, QComboBox)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
import numpy as np


class WaveformDialog(QDialog):
    def __init__(self, simulation_engine, parent=None):
        super().__init__(parent)
        self.sim = simulation_engine
        self.setWindowTitle("Waveform Viewer")
        self.setMinimumSize(900, 550)
        self.setStyleSheet("""
            QDialog { background: #0d0d1a; color: #e0e0e0; }
            QLabel { color: #b0bec5; font-family: Consolas; }
            QPushButton { background: #0f3460; color: #4fc3f7; border: 1px solid #4fc3f7;
                          padding: 8px 18px; border-radius: 4px; font-family: Consolas; }
            QPushButton:hover { background: #4fc3f7; color: #0d0d1a; }
            QComboBox { background: #16213e; color: #e0e0e0; border: 1px solid #4fc3f7;
                        padding: 4px; font-family: Consolas; }
        """)

        self.figure = plt.Figure(figsize=(10, 6), facecolor='#0d0d1a')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background: #0d0d1a;")
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setStyleSheet("background: #16213e; color: #e0e0e0;")

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Header
        hdr = QLabel("◈  Digital Timing Waveform")
        hdr.setFont(QFont("Consolas", 13, QFont.Bold))
        hdr.setStyleSheet("color: #4fc3f7; padding: 6px 0;")
        layout.addWidget(hdr)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self._plot()

    def _plot(self):
        inputs = self.sim.get_input_nodes()
        outputs = self.sim.get_output_nodes()

        if not inputs:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, "No input nodes found.\nAdd INPUT nodes to see waveforms.",
                    ha='center', va='center', color='#90a4ae',
                    fontfamily='monospace', fontsize=12,
                    transform=ax.transAxes)
            ax.set_facecolor('#0d0d1a')
            self.canvas.draw()
            return

        n_in = len(inputs)
        n = 2 ** n_in
        time = np.arange(n + 1)

        # Build a unique key + display label for every input/output, so
        # nodes that share the same default label (e.g. two nodes both
        # named "IN") never collide and overwrite each other.
        in_keys = [f"in_{i}" for i in range(len(inputs))]
        out_keys = [f"out_{i}" for i in range(len(outputs))]

        def display_label(node, idx, total, fallback):
            base = getattr(node, "label", None) or fallback
            return f"{base} {idx + 1}" if total > 1 else base

        in_labels = [display_label(inp, i, len(inputs), "IN") for i, inp in enumerate(inputs)]
        out_labels = [display_label(out, i, len(outputs), "OUT") for i, out in enumerate(outputs)]

        # Collect waveform data, keyed by the unique key (not label)
        signal_data = {k: [] for k in in_keys + out_keys}

        for combo in range(n):
            for i, inp in enumerate(inputs):
                inp._value = (combo >> (n_in - 1 - i)) & 1
                inp.evaluate()
            self.sim.run()
            for i, inp in enumerate(inputs):
                signal_data[in_keys[i]].append(inp._value)
            for i, out in enumerate(outputs):
                signal_data[out_keys[i]].append(out.evaluate())

        all_signals = in_keys + out_keys
        signal_labels = dict(zip(in_keys, in_labels))
        signal_labels.update(dict(zip(out_keys, out_labels)))
        num_signals = len(all_signals)

        self.figure.clear()
        colors_in  = ['#4fc3f7', '#81c784', '#ffb74d', '#f48fb1', '#ce93d8']
        colors_out = ['#ffeb3b', '#ff7043', '#26c6da', '#aed581', '#ff8a65']

        for idx, sig in enumerate(all_signals):
            ax = self.figure.add_subplot(num_signals, 1, idx + 1)
            vals = signal_data[sig]
            label_text = signal_labels[sig]
            # Build step waveform
            t_steps = []
            v_steps = []
            for i, v in enumerate(vals):
                t_steps.extend([i, i + 1])
                v_steps.extend([v, v])

            is_out = sig in out_keys
            c = colors_out[idx % len(colors_out)] if is_out else colors_in[idx % len(colors_in)]

            ax.step(range(len(vals) + 1), vals + [vals[-1]],
                    where='post', color=c, linewidth=2.5)
            ax.fill_between(range(len(vals) + 1), vals + [vals[-1]],
                            step='post', alpha=0.15, color=c)

            ax.set_ylim(-0.3, 1.3)
            ax.set_yticks([0, 1])
            ax.set_yticklabels(['0', '1'], color='#b0bec5', fontfamily='monospace')
            ax.set_facecolor('#0d0d1a')
            ax.tick_params(colors='#546e7a')
            for spine in ax.spines.values():
                spine.set_edgecolor('#263238')

            prefix = "▶ " if is_out else "▷ "
            ax.set_ylabel(prefix + label_text, color=c, fontfamily='monospace',
                          fontsize=9, rotation=0, labelpad=45, va='center')
            ax.set_xticks(range(n + 1))
            if idx == num_signals - 1:
                ax.set_xlabel("Time step", color='#546e7a', fontfamily='monospace')
            else:
                ax.set_xticklabels([])

            ax.grid(axis='x', color='#263238', linestyle='--', alpha=0.5)
            ax.axhline(0.5, color='#263238', linestyle=':', alpha=0.4)

        self.figure.suptitle("Digital Timing Diagram", color='#4fc3f7',
                             fontfamily='monospace', fontsize=12, y=1.01)
        self.figure.patch.set_facecolor('#0d0d1a')
        self.figure.tight_layout()
        self.canvas.draw()
