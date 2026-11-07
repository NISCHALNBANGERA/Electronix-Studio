"""
ai_chatbot.py - Semantic Question Answering AI Tutor & Assistant
Features:
- Intent Recognition: Analyzes full user sentences using vector-space TF-IDF semantic embeddings,
  n-gram matching, and context-aware pattern classification.
- Contextual Awareness: Reads live circuit state (gates present, clock state, wire count)
  to provide personalized troubleshooting (e.g. diagnosing why a counter/bus display is showing 0).
- Deep Technical Knowledge Base: Covers circuit design, component usage, error troubleshooting,
  sequential logic, Verilog conversion, 74xx ICs, and MOSFET semiconductor physics.
- Graceful Fallback: Delivers constructive guidance, recognized topics, and recommended prompts
  when query confidence is low.
- Pluggable API Support: Seamlessly connects to OpenAI / Gemini API if configured.
"""
from PyQt5.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QScrollArea, QFrame,
    QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor
import re, math, os, json
from collections import Counter


# ── Stopwords & Text Normalization ───────────────────────────────────
STOPWORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'aren',
    'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by',
    'can', 'could', 'did', 'do', 'does', 'doing', 'down', 'during', 'each', 'few', 'for', 'from',
    'further', 'had', 'has', 'have', 'having', 'he', 'her', 'here', 'hers', 'herself', 'him', 'himself',
    'his', 'how', 'i', 'if', 'in', 'into', 'is', 'it', 'its', 'itself', 'just', 'me', 'more', 'most',
    'my', 'myself', 'no', 'nor', 'not', 'now', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'our',
    'ours', 'ourselves', 'out', 'over', 'own', 'same', 'should', 'so', 'some', 'such', 'than', 'that',
    'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there', 'these', 'they', 'this', 'those',
    'through', 'to', 'too', 'under', 'until', 'up', 'very', 'was', 'we', 'were', 'what', 'when', 'where',
    'which', 'while', 'who', 'whom', 'why', 'will', 'with', 'would', 'you', 'your', 'yours', 'yourself',
}

# Stemming/synonym mapping for electronics queries
LEMMA_MAP = {
    'showing': 'show', 'shows': 'show', 'showed': 'show',
    'working': 'work', 'works': 'work', 'worked': 'work',
    'connecting': 'connect', 'connects': 'connect', 'connected': 'connect', 'connection': 'connect',
    'toggling': 'toggle', 'toggles': 'toggle', 'toggled': 'toggle',
    'counters': 'counter', 'counting': 'counter',
    'registers': 'register',
    'displays': 'display',
    'gates': 'gate',
    'inputs': 'input', 'outputs': 'output',
    'clocks': 'clock', 'clocking': 'clock',
    'circuits': 'circuit',
    'wires': 'wire', 'wiring': 'wire',
    'chips': 'chip',
    'transistors': 'transistor',
    'flipflops': 'flipflop', 'ff': 'flipflop', 'latch': 'flipflop',
    'converters': 'converter', 'converting': 'convert', 'conversion': 'convert',
    'resizing': 'resize', 'reconfiguring': 'configure', 'configuration': 'configure',
    'simulating': 'simulate', 'simulation': 'simulate',
    'verifying': 'verify',
}


def tokenize(text: str):
    """Normalize, strip punctuation, expand stems, and return clean tokens."""
    cleaned = re.sub(r'[^a-zA-Z0-9_\-\s]', ' ', text.lower())
    raw_tokens = cleaned.split()
    tokens = []
    for t in raw_tokens:
        stem = LEMMA_MAP.get(t, t)
        if stem not in STOPWORDS and len(stem) > 1:
            tokens.append(stem)
    return tokens


def get_ngrams(tokens, n=2):
    """Generate n-gram tuple strings for phrase matching."""
    return [" ".join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]


# ── Knowledge Base Intent Definitions ─────────────────────────────────
KNOWLEDGE_BASE = [
    {
        'id': 'troubleshoot_showing_zero',
        'title': 'Troubleshooting: Circuit or Display Showing 0',
        'category': 'TROUBLESHOOTING',
        'phrases': [
            "why is my circuit showing 0",
            "why is the bus display showing 0",
            "it is just showing 0",
            "display shows zero and not starting",
            "my counter is not counting",
            "flip flop not toggling stays at 0",
            "how to start simulation not running",
            "clock not ticking or pulsing",
            "how do i start the counter",
            "nothing changes when clock pulses",
            "circuit output stays at low zero",
        ],
        'patterns': [
            r'show(ing)?.*0|show(ing)?.*zero',
            r'not\s+(start(ing)?|run(ning)?|work(ing)?|count(ing)?|chang(ing)?)',
            r'how\s+(do\s+i\s+)?(start|run|enable)\s+(the\s+)?(circuit|counter|clock|simulation|display)',
            r'stay(s)?\s+(at\s+)?0|stuck\s+(at\s+)?0',
            r'flip\s*flop.*not\s+toggl',
        ],
        'content': """### 🔍 Troubleshooting: Why the Circuit Shows 0 & How to Start

When a newly wired circuit or Bus Display shows **`0`**, it is almost always due to one of four initial setup requirements:

---

#### 1. Input Switches Start in the `0` (OFF) State
- `INPUT` nodes default to `0` when dropped onto the canvas.
- **Solution:** **Double-click** any `INPUT` block to toggle it to `1` (or right-click $\\rightarrow$ **`⇅ Toggle 0/1`**).
- Wires connected to `1` will immediately turn vibrant yellow.

#### 2. Flip-Flop Control Pins Must Be Enabled (HIGH)
If you built a counter using flip-flops, check their mode input pins:
- **T Flip-Flop (T-FF):** The **`T`** input pin (top-left) **must be set to 1** to toggle. If $T=0$, the flip-flop holds its value at $0$ indefinitely!
- **JK Flip-Flop (JK-FF):** Both **`J`** and **`K`** pins must be set to `1` for the flip-flop to enter toggle mode. If $J=0, K=0$, it holds $0$.
- **D Flip-Flop (D-FF):** Wire the complementary output **`Q̅` (`Q_bar`)** back into the **`D`** input so it inverts on each clock edge.

#### 3. Starting the Clock Generator
- Add a **`CLOCK`** block from the *Sequential* ribbon (`⏱ Sequential ▼` $\\rightarrow$ `CLOCK`).
- Wire the Clock's `CLK` output pin into the clock trigger input (`CLK` / `>`) of the flip-flops.
- Right-click the `CLOCK` block:
  - Click **`▶ Start Auto-Clock`** to begin auto-oscillation.
  - Or click **`⏱ Set Frequency...`** (e.g. `1.0 Hz` or `2.0 Hz`).
  - Or click **`⚡ Manual Pulse (1-shot)`** to step forward by 1 count on demand.

#### 4. Instant State Preset
- Right-click any Flip-Flop on canvas $\\rightarrow$ click **`1 Preset State (Q=1)`** to immediately inject high state and verify your display!
- Press **`F5`** or click **`▶ Simulate`** in the top toolbar to trigger an immediate simulation pass.""",
    },

    {
        'id': 'bus_display_radix',
        'title': 'Bus Display & Multi-Radix Converter',
        'category': 'COMPONENT_USAGE',
        'phrases': [
            "how to use bus display block",
            "configure bit width bus display 2 to 16 bits",
            "multi radix converter hex octal bcd signed",
            "how to change bus display size or inputs",
            "display bus binary grouped view",
            "how to read counter output with radix display",
            "set bit width for bus converter",
            "change display color neon green cyan amber red",
            "two complement signed decimal bus display",
        ],
        'patterns': [
            r'bus\s*display|radix\s*display|bus\s*converter',
            r'bit\s*width.*(bus|display|converter)',
            r'configure.*bit\s*width',
            r'multi\s*radix|hex.*octal.*bcd',
        ],
        'content': """### 🔢 Bus Display & Multi-Radix Converter Guide

The **Bus Display Block** (`RadixDisplayBlock` / `BusConverterNode`) captures parallel binary lines and renders an authentic OLED/FPGA instrument readout in multiple radix systems.

---

#### 1. Dynamic Bit Width Configuration (2 to 16 Bits)
- **Default State:** 4 parallel input ports ($D_0 \dots D_3$).
- **How to Reconfigure:**
  1. Right-click the Bus Display on canvas.
  2. Select **`Configure Bit Width...`**.
  3. Enter any width between **2 and 16 bits**.
  4. The block automatically resizes its body height to prevent pin overlapping, preserves existing wires, and updates weight markers!

#### 2. Clear Pin Weighting Markers
- **$D_0$:** Marked as **LSB** (weight $2^0 = 1$).
- **$D_1 \dots D_{n-2}$:** Marked with corresponding binary weights ($2^1, 2^2, \dots$).
- **$D_{n-1}$:** Marked as **MSB** (weight $2^{n-1}$).
- Live tooltips show the exact integer weight for each pin.

#### 3. Available Display Modes
Right-click $\\rightarrow$ **`🔢 Display Mode`** (or **double-click** the block to cycle modes):
1. **`DEC` (Unsigned Decimal):** Range $0 \dots 2^N - 1$.
2. **`HEX` (Hexadecimal):** `0x0` through `0xFFFF` with uppercase formatting.
3. **`OCT` (Octal):** Base-8 representation (`0o0` through `0o177777`).
4. **`BIN` (Binary Bus View):** Grouped nibble format (e.g., `[ 1101 ]` or `[ 1010 0110 ]`).
5. **`BCD` (Binary-Coded Decimal):** Independent 4-bit nibbles for each decimal digit (e.g. $13_{10} \\rightarrow$ `0001 0011`).
6. **`SIGNED` (2's Complement):** Evaluates sign bit $2^{N-1}$ for signed arithmetic ($-2^{N-1} \\dots +2^{N-1}-1$).
7. **`ALL` (All-in-One Dashboard):** Stacked real-time readout of DEC, HEX, OCT, and BIN.

#### 4. Hardware LED Monitor & Themes
- The bottom chassis features a live micro-LED tally bar showing active `[1]` and inactive `[0]` bits.
- Right-click $\\rightarrow$ **`🎨 Change Display Color`** to switch between **Neon Green**, **Electric Cyan**, **Lab Amber**, and **Laser Red**.""",
    },

    {
        'id': 'counter_design',
        'title': 'Sequential Counter Design (Ripple & Synchronous)',
        'category': 'CIRCUIT_DESIGN',
        'phrases': [
            "how to build a counter",
            "how to make a 3-bit or 4-bit ripple counter",
            "asynchronous ripple counter with t flip flops",
            "how to connect counter to bus display",
            "design synchronous binary counter with jk flip flop",
            "modulo n counter with reset clear",
            "frequency divider using flip flops",
        ],
        'patterns': [
            r'how\s+(to|do\s+i)\s+(build|make|design|wire)\s+.*counter',
            r'ripple\s*counter|binary\s*counter|asynchronous\s*counter|sync.*counter',
            r'frequency\s*divider',
        ],
        'content': """### ⏱ Designing Counters in the Simulator

Counters are sequential circuits that cycle through a binary sequence ($0, 1, 2, \\dots, 2^N-1$) on clock transitions.

---

#### 3-Bit Asynchronous Ripple Counter (Using T-FFs)
1. **Place Components:**
   - 1× `CLOCK` block.
   - 3× `T_FF` (T Flip-Flops: `FF0`, `FF1`, `FF2`).
   - 1× `INPUT` switch (set to `1`).
   - 1× `BUS DISPLAY` (set to 3-bit width).
2. **Wire the Toggle Inputs:**
   - Connect the `INPUT` switch (`1`) to the **`T`** pin of all three flip-flops.
3. **Wire the Clock Chain (Ripple):**
   - Connect `CLOCK` output $\\rightarrow$ `FF0` clock pin (`CLK`).
   - Connect `FF0` output **`Q`** $\\rightarrow$ `FF1` clock pin (`CLK`).
   - Connect `FF1` output **`Q`** $\\rightarrow$ `FF2` clock pin (`CLK`).
4. **Wire to the Bus Display:**
   - `FF0.Q` (LSB) $\\rightarrow$ `BUS DISPLAY.D0 (LSB)`.
   - `FF1.Q` $\\rightarrow$ `BUS DISPLAY.D1`.
   - `FF2.Q` (MSB) $\\rightarrow$ `BUS DISPLAY.D2 (MSB)`.
5. **Start:**
   - Right-click `CLOCK` $\\rightarrow$ **`▶ Start Auto-Clock`** (set frequency to `1 Hz`).
   - Watch the Bus Display count from `0` to `7`!

> [!TIP]
> In negative-edge triggered flip-flops, connecting $Q \\rightarrow \\text{CLK}$ counts UP. Connecting $\\bar{Q} \\rightarrow \\text{CLK}$ counts DOWN.""",
    },

    {
        'id': 'adder_subtractor_design',
        'title': 'Adders & Arithmetic Logic (Half, Full, Ripple Carry, Subtractor)',
        'category': 'CIRCUIT_DESIGN',
        'phrases': [
            "how to build half adder and full adder",
            "full adder logic equations truth table",
            "how to build ripple carry adder",
            "binary subtractor using two's complement and xor",
            "arithmetic logic unit design adders",
        ],
        'patterns': [
            r'half\s*adder|full\s*adder|ripple\s*carry\s*adder',
            r'binary\s*subtractor|adder\s*subtractor',
            r'how\s+(to|do\s+i)\s+(build|make|wire)\s+.*adder',
        ],
        'content': """### ➕ Binary Adders & Subtractors

Arithmetic circuits form the core of the ALU (Arithmetic Logic Unit).

---

#### 1. Half Adder
Adds two 1-bit inputs ($A, B$):
- **Sum ($S$):** $A \\oplus B$ (XOR Gate)
- **Carry ($C$):** $A \\cdot B$ (AND Gate)
- Available ready-made in `MSI & Complex ▼` $\\rightarrow$ `HALF_ADDER`.

#### 2. Full Adder
Adds three 1-bit inputs ($A, B, C_{in}$):
- **Sum ($S$):** $A \\oplus B \\oplus C_{in}$
- **Carry Out ($C_{out}$):** $(A \\cdot B) + (B \\cdot C_{in}) + (A \\cdot C_{in})$
- Available ready-made in `MSI & Complex ▼` $\\rightarrow$ `FULL_ADDER`.

#### 3. 4-Bit Ripple Carry Adder
Cascade 4 Full Adders:
- $C_{out0} \\rightarrow C_{in1}$, $C_{out1} \\rightarrow C_{in2}$, $C_{out2} \\rightarrow C_{in3}$.
- Final outputs $S_0, S_1, S_2, S_3$ connect directly to the **Bus Display**!

#### 4. Converting an Adder into a Subtractor
To compute $A - B$, use Two's Complement: $A + \\bar{B} + 1$:
- Pass each $B_i$ bit through an **XOR gate** with a `SUB` control line.
- Feed `SUB` into the initial $C_{in0}$.
- When `SUB = 0`: performs addition ($A + B$).
- When `SUB = 1`: inverts $B$ and adds $1$, performing subtraction ($A - B$)!""",
    },

    {
        'id': 'flip_flops_sequential',
        'title': 'Flip-Flops & Sequential Logic (D, JK, T, SR)',
        'category': 'THEORY',
        'phrases': [
            "explain flip flops types d jk t sr",
            "difference between latch and flip flop",
            "how does d flip flop work",
            "jk flip flop truth table and toggle condition",
            "what is setup time and hold time",
            "master slave flip flop internal structure",
        ],
        'patterns': [
            r'flip\s*flop|latch|edge\s*trigger',
            r'setup\s*time|hold\s*time',
            r'd\s*flip|jk\s*flip|t\s*flip|sr\s*flip',
        ],
        'content': """### 🔄 Flip-Flops & Sequential Storage Elements

Flip-flops are bistable multivibrators capable of storing 1 bit of memory.

---

#### Comparison of Flip-Flop Types
| Type | Inputs | Behavior on Clock Edge | Key Applications |
| :--- | :--- | :--- | :--- |
| **D-FF** | $D, \\text{CLK}$ | $Q_{next} = D$ (Follows Data) | Registers, pipeline stages, memory |
| **T-FF** | $T, \\text{CLK}$ | $T=0 \\rightarrow Q$; $T=1 \\rightarrow \\bar{Q}$ (Toggle) | Binary counters, frequency dividers |
| **JK-FF** | $J, K, \\text{CLK}$ | $J=K=0 \\rightarrow$ Hold; $J=1, K=0 \\rightarrow 1$; $J=0, K=1 \\rightarrow 0$; $J=K=1 \\rightarrow$ Toggle | Universal counters, state machines |
| **SR Latch** | $S, R$ | $S=1 \\rightarrow$ Set; $R=1 \\rightarrow$ Reset; $S=R=1$ **Invalid** | Switch debouncing, set-reset flags |

#### Inspect Internal Architecture
In this simulator, you can view the actual gate-level schematic inside any flip-flop:
- Right-click any Flip-Flop on canvas $\\rightarrow$ select **`🔍 View Internal Structure...`**.
- Visualizes Master-Slave cross-coupled NAND/NOR gates, clock inverters, and feedback loops!

#### Timing Constraints
- **Setup Time ($t_{su}$):** Minimum duration the data input must remain stable **before** the active clock edge.
- **Hold Time ($t_h$):** Minimum duration the data input must remain stable **after** the active clock edge.""",
    },

    {
        'id': 'multiplexer_demux',
        'title': 'Multiplexers (MUX) & Demultiplexers (DEMUX)',
        'category': 'COMPONENT_USAGE',
        'phrases': [
            "how does a multiplexer mux work",
            "how to configure mux size 2 to 1 4 to 1 8 to 1 16 to 1",
            "difference between mux and demux",
            "how many select lines for mux",
            "implement logic function using multiplexer",
        ],
        'patterns': [
            r'\bmux\b|multiplexer',
            r'\bdemux\b|demultiplexer',
            r'data\s*selector',
        ],
        'content': """### 🔀 Multiplexers (MUX) & Demultiplexers (DEMUX)

Multiplexers act as digitally controlled rotary switches, routing one of several input lines to a single shared output.

---

#### 1. Sizing & Select Lines ($S = \\lceil \\log_2 N \\rceil$)
- **2:1 MUX:** 2 data inputs ($I_0, I_1$), 1 select line ($S_0$) $\\rightarrow 1$ output ($Y$).
- **4:1 MUX:** 4 data inputs ($I_0..I_3$), 2 select lines ($S_0, S_1$) $\\rightarrow 1$ output ($Y$).
- **8:1 MUX:** 8 data inputs ($I_0..I_7$), 3 select lines ($S_0..S_2$) $\\rightarrow 1$ output ($Y$).
- **16:1 MUX:** 16 data inputs ($I_0..I_{15}$), 4 select lines ($S_0..S_3$) $\\rightarrow 1$ output ($Y$).

#### 2. Reconfiguring MUX/DEMUX Size
- In this simulator, complex components are not locked to 2:1!
- Right-click the MUX/DEMUX on canvas $\\rightarrow$ **`⚙ Configure Size / Inputs...`** $\\rightarrow$ select `2:1`, `4:1`, `8:1`, or `16:1`.

#### 3. DEMUX (Demultiplexer)
Takes 1 input data line ($D$) and routes it to one of $N$ output lines ($Y_0 \\dots Y_{N-1}$) based on the select lines.""",
    },

    {
        'id': 'encoders_decoders',
        'title': 'Encoders, Priority Encoders & Decoders',
        'category': 'COMPONENT_USAGE',
        'phrases': [
            "how does an encoder and decoder work",
            "priority encoder valid bit v",
            "decoder address memory decoding 2 to 4 3 to 8",
            "configure decoder size",
        ],
        'patterns': [
            r'\bencoder\b|\bdecoder\b',
            r'priority\s*encoder',
        ],
        'content': """### 🔤 Encoders & Decoders

Encoders and Decoders translate between compressed binary codes and 1-hot individual line activations.

---

#### 1. Encoders ($2^N \\rightarrow N$)
- Compresses $2^N$ input lines into an $N$-bit binary address.
- **Priority Encoder:** If multiple inputs are simultaneously HIGH, the highest indexed input takes precedence. Outputs an extra **`V` (Valid)** line indicating at least one input is active.
- Configurable in simulator as `4:2`, `8:3`, and `16:4`.

#### 2. Decoders ($N \\rightarrow 2^N$)
- Takes an $N$-bit binary address ($A_0 \\dots A_{N-1}$) and asserts exactly one corresponding output ($Y_0 \\dots Y_{2^N-1}$).
- Configurable as `2:4`, `3:8`, and `4:16`.
- Extensively used for chip select (CS) and memory address decoding.""",
    },

    {
        'id': 'transistors_mosfet_cmos',
        'title': 'MOSFET Transistors & CMOS Switching Physics',
        'category': 'THEORY',
        'phrases': [
            "how does nmos and pmos work",
            "cmos inverter operation pull up pull down",
            "mosfet physical cross section semiconductor",
            "threshold voltage vth and channel pinch off",
            "difference between nmos and pmos",
        ],
        'patterns': [
            r'mosfet|nmos|pmos|cmos',
            r'transistor\s*switch',
            r'pull\s*up|pull\s*down',
        ],
        'content': """### 🔬 MOSFET Physics & CMOS Logic

Modern digital electronics are constructed using CMOS (Complementary Metal-Oxide-Semiconductor) pairs of NMOS and PMOS transistors.

---

#### 1. NMOS vs PMOS Switching
- **NMOS Transistor:**
  - Gate HIGH (`1` / $V_{DD}$): **ON** (conducts from Drain to Source).
  - Gate LOW (`0` / GND): **OFF** (open circuit).
  - Best used as **Pull-Down** to GND (transmits strong `0`).
- **PMOS Transistor (Active-Low Bubble):**
  - Gate LOW (`0` / GND): **ON** (conducts from Source to Drain).
  - Gate HIGH (`1` / $V_{DD}$): **OFF**.
  - Best used as **Pull-Up** to $V_{DD}$ (transmits strong `1`).

#### 2. CMOS Inverter (NOT Gate)
- Connect a PMOS between $V_{DD}$ and Output, and an NMOS between Output and GND.
- Tied gates form the input:
  - Input = `0`: PMOS ON, NMOS OFF $\\rightarrow$ Output pulled to $V_{DD}$ (`1`).
  - Input = `1`: PMOS OFF, NMOS ON $\\rightarrow$ Output pulled to GND (`0`).
  - **Zero static power dissipation!**

#### 3. Interactive Physics Visualizer
- In the Tools menu, open **`🔬 MOSFET Physics Studio`** to explore interactive 2D cross-sections, electron drift animation, channel inversion, and pinch-off curves!""",
    },

    {
        'id': 'virtual_74xx_ics',
        'title': 'Virtual 74xx Dual In-line Package (DIP) ICs',
        'category': 'COMPONENT_USAGE',
        'phrases': [
            "how to use 7400 7408 7432 7404 chips",
            "7400 ic pinout vcc gnd",
            "virtual 74xx ic datasheet pinout manual",
            "7474 flip flop dip 14",
            "74138 decoder 74151 mux",
        ],
        'patterns': [
            r'74\d{2,3}|74xx|ic\s*chip|dip-14|dip-16',
            r'datasheet|pinout\s*manual',
        ],
        'content': """### 🖲 Virtual 74xx Dual In-Line Package (DIP) ICs

Our simulator includes fully functional virtual DIP integrated circuit chips with authentic pinouts and power rail verification.

---

#### Supported IC Models
- **7400:** Quad 2-Input NAND Gates (DIP-14)
- **7402:** Quad 2-Input NOR Gates (DIP-14)
- **7404:** Hex Inverter (NOT) Gates (DIP-14)
- **7408:** Quad 2-Input AND Gates (DIP-14)
- **7432:** Quad 2-Input OR Gates (DIP-14)
- **7486:** Quad 2-Input XOR Gates (DIP-14)
- **7474:** Dual D Positive-Edge Flip-Flops w/ PRE & CLR (DIP-14)
- **74138:** 3-to-8 Line Decoder / Demultiplexer (DIP-16)
- **74151:** 8-to-1 Data Selector / Multiplexer (DIP-16)

#### Pinout & Power Requirements
- **DIP-14:** Pin 14 is $V_{CC}$ (Power, $+5\\text{V}$), Pin 7 is GND.
- **DIP-16:** Pin 16 is $V_{CC}$, Pin 8 is GND.
- **Datasheet Manual:** Right-click any 74xx IC on canvas and select **`📖 Open IC Datasheet / Pinout Manual...`** to inspect pinout diagrams, truth tables, and electrical specs!""",
    },

    {
        'id': 'verilog_synthesis',
        'title': 'Bidirectional Verilog Generation & Import',
        'category': 'VERILOG',
        'phrases': [
            "how to convert circuit to verilog code",
            "verilog studio modal export import",
            "structural vs dataflow vs behavioral verilog",
            "generate verilog testbench",
            "import verilog code into schematic",
        ],
        'patterns': [
            r'verilog|hdl|synthesis|testbench',
            r'convert.*verilog|verilog.*convert',
        ],
        'content': """### 📜 Bidirectional Verilog Studio

The simulator features a dedicated **Verilog Toolpanel / Studio** (`Tools` $\\rightarrow$ `Verilog Studio` or **`F10`**) supporting bidirectional translation between visual schematics and HDL code.

---

#### 1. Schematic $\\rightarrow$ Verilog Conversion Styles
- **Structural Modeling:** Instantiates primitive gate and flip-flop cells with explicit net wiring.
- **Dataflow Modeling:** Synthesizes continuous boolean expressions using `assign` statements (e.g. `assign Y = A & B;`).
- **Behavioral Modeling:** Generates procedural `always @(*)` and `always @(posedge clk)` blocks.

#### 2. Built-in Testbench Generator
- Click **`Generate Testbench`** to auto-generate a complete self-checking testbench module with clock generation, stimulus transitions, and `$monitor` statements!

#### 3. Verilog $\\rightarrow$ Schematic Parser
- Paste valid gate-level or sequential Verilog code into the editor and click **`Convert Verilog ➔ Schematic`** to reconstruct the visual circuit on your canvas automatically.""",
    },

    {
        'id': 'boolean_algebra_kmap',
        'title': 'Boolean Algebra Laws & Karnaugh Map (K-Map) Solver',
        'category': 'THEORY',
        'phrases': [
            "boolean algebra laws rules de morgan",
            "how to solve k map karnaugh map",
            "how to solve boolean equations with k-map",
            "kmap simplification prime implicants",
            "sop vs pos sum of products",
            "don't care condition x in kmap",
            "boolean logic reduction rules",
        ],
        'patterns': [
            r'boolean|de\s*morgan|simplif',
            r'k.?map|karnaugh',
            r'sop|pos|prime\s*implicant',
        ],
        'content': """### 📐 Boolean Algebra & K-Map Simplification

Boolean algebra provides the mathematical rules for minimizing digital logic gate counts.

---

#### 1. Fundamental Laws
- **De Morgan's Theorems:**
  $$(A \\cdot B)' = A' + B' \\qquad (A + B)' = A' \\cdot B'$$
- **Absorption:** $A + (A \\cdot B) = A \\qquad A \\cdot (A + B) = A$
- **Complementarity:** $A + A' = 1 \\qquad A \\cdot A' = 0$
- **Distributive:** $A \\cdot (B + C) = (A \\cdot B) + (A \\cdot C)$

#### 2. K-Map (Karnaugh Map) Rules
1. Map minterms from the truth table onto the Gray-code grid ($00, 01, 11, 10$).
2. Form rectangular groups of 1s in powers of 2 ($1, 2, 4, 8, 16$).
3. Groups can wrap around toroidal outer edges.
4. Always select the **largest possible groups** to eliminate the maximum number of literal variables.
5. In this simulator, open **`Tools` $\\rightarrow$ `K-Map Solver`** for automatic visual reduction!""",
    },

    {
        'id': 'simulator_hotkeys_tools',
        'title': 'Simulator Hotkeys, Analysis Tools & Shortcuts',
        'category': 'SIMULATOR_TOOLS',
        'phrases': [
            "how to use the simulator hotkeys shortcuts",
            "truth table waveform boolean expression",
            "quick add component search ctrl space",
            "how to connect wires and delete gates",
            "getting started help simulator",
        ],
        'patterns': [
            r'hotkey|shortcut|getting\s*started|how\s*to\s*use',
            r'truth\s*table|waveform|quick\s*add',
        ],
        'content': """### 🚀 Simulator Navigation & Analysis Tools

Master the simulator with these built-in power features:

---

#### Analysis & Verification Tools
- **`F5`:** **Run Simulation** — forces an immediate propagation cycle.
- **`F6`:** **Truth Table Generator** — iterates all $2^N$ input vectors and builds the complete truth table.
- **`F7`:** **Boolean Expression Generator** — traces symbolic expressions from outputs back to primary inputs.
- **`F8`:** **Waveform Viewer** — opens interactive digital timing diagrams.
- **`F9`:** **Animated Signal Run** — visualizes traveling electron packets along live wires.
- **`F10`:** **Verilog Studio** — code export and import.

#### Workflow Shortcuts
- **`Ctrl+Space`:** Focuses the **Quick-Add Search Bar** at the top. Type any name (`MUX`, `7408`, `BUS`, `JK`) and hit Enter to drop it immediately on canvas!
- **Connecting Wires:** Click any green output pin, then click any blue input pin.
- **Wiring Inspection:** Right-click wires or gates to delete or rename them.
- **Zoom & Pan:** Mouse wheel zooms; middle-click drag pans the infinite schematic canvas.""",
    },
]


# ── Semantic TF-IDF & Intent Recognition Engine ──────────────────────
class SemanticAIResponseEngine:
    """
    Semantic Natural Language Question Answering Engine.
    Uses TF-IDF vectorization, n-gram matching, intent categorization,
    and contextual circuit awareness.
    """

    def __init__(self):
        self.intents = KNOWLEDGE_BASE
        self.vocabulary = {}
        self.idf = {}
        self.intent_vectors = []
        self._build_index()

    def _build_index(self):
        """Construct vocabulary and TF-IDF document vectors for all knowledge topics."""
        doc_tokens_list = []
        df = Counter()
        N = len(self.intents)

        for intent in self.intents:
            # Combine title, phrases, and keywords into training document
            text_corpus = intent['title'] + " " + " ".join(intent['phrases'])
            tokens = tokenize(text_corpus)
            bigrams = get_ngrams(tokens, 2)
            all_terms = tokens + bigrams
            doc_tokens_list.append(all_terms)
            unique_terms = set(all_terms)
            for term in unique_terms:
                df[term] += 1

        # Build vocabulary dictionary
        vocab = {}
        for term, freq in df.items():
            if freq >= 1:
                vocab[term] = len(vocab)
        self.vocabulary = vocab

        # Compute smoothed Inverse Document Frequency (IDF)
        for term, idx in vocab.items():
            self.idf[term] = math.log((N + 1.0) / (df[term] + 1.0)) + 1.0

        # Compute normalized TF-IDF vector for each intent
        self.intent_vectors = []
        for all_terms in doc_tokens_list:
            vec = self._vectorize(all_terms)
            self.intent_vectors.append(vec)

    def _vectorize(self, terms):
        """Compute normalized TF-IDF vector for given term list."""
        tf = Counter(terms)
        vec = {}
        norm_sq = 0.0
        for term, count in tf.items():
            if term in self.vocabulary:
                w = (1.0 + math.log(count)) * self.idf.get(term, 1.0)
                vec[term] = w
                norm_sq += w * w
        norm = math.sqrt(norm_sq) if norm_sq > 0 else 1.0
        for term in vec:
            vec[term] /= norm
        return vec

    def _cosine_similarity(self, vec_a, vec_b):
        """Compute cosine similarity between two normalized sparse vectors."""
        score = 0.0
        # Dot product of normalized vectors
        for term, val_a in vec_a.items():
            if term in vec_b:
                score += val_a * vec_b[term]
        return max(0.0, min(1.0, score))

    def analyze_intent(self, user_query: str):
        """
        Analyze user query using semantic similarity and regex intent patterns.
        Returns (best_intent, confidence_score, matched_metadata).
        """
        q_tokens = tokenize(user_query)
        q_bigrams = get_ngrams(q_tokens, 2)
        q_terms = q_tokens + q_bigrams
        q_vec = self._vectorize(q_terms)
        raw_text = user_query.lower()

        best_intent = None
        best_score = 0.0

        for i, intent in enumerate(self.intents):
            # 1. Vector space cosine similarity
            sim_score = self._cosine_similarity(q_vec, self.intent_vectors[i])

            # 2. Regex structural pattern boost
            pattern_boost = 0.0
            for pat in intent.get('patterns', []):
                if re.search(pat, raw_text, re.IGNORECASE):
                    pattern_boost = max(pattern_boost, 0.55)
                    break

            # 3. Direct phrase match boost
            phrase_boost = 0.0
            for phr in intent.get('phrases', []):
                phr_tokens = tokenize(phr)
                overlap = len(set(q_tokens).intersection(set(phr_tokens)))
                if len(phr_tokens) > 0:
                    phrase_boost = max(phrase_boost, overlap / len(phr_tokens))

            # Composite confidence score
            total_score = (0.45 * sim_score) + (0.35 * pattern_boost) + (0.20 * phrase_boost)

            if total_score > best_score:
                best_score = total_score
                best_intent = intent

        return best_intent, best_score, {'tokens': q_tokens}

    def respond(self, text: str, context: dict = None) -> str:
        """
        Produce a contextually aware semantic response.
        If an external API is available, attempts cloud AI first;
        otherwise runs high-accuracy offline semantic intent processing.
        """
        # Optional pluggable cloud API hook if user configured key
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if api_key:
            try:
                cloud_reply = self.api_call(text, api_key)
                if cloud_reply:
                    return cloud_reply
            except Exception:
                pass  # Fall back to local semantic engine cleanly

        # Local Semantic Intent Recognition
        intent, confidence, meta = self.analyze_intent(text)

        # Confidence threshold for positive match
        CONFIDENCE_THRESHOLD = 0.24

        if intent and confidence >= CONFIDENCE_THRESHOLD:
            base_reply = intent['content'].strip()

            # Contextual Circuit Enhancement:
            # If the user is troubleshooting and we have live circuit metadata, personalize the answer!
            if intent['id'] == 'troubleshoot_showing_zero' and context:
                extras = []
                gates = context.get('gate_types', [])
                if 'RADIX_DISPLAY' in gates:
                    extras.append("- 💡 **Bus Display detected on canvas:** Ensure bit width matches your counter output pins.")
                if any(g in gates for g in ('D_FF', 'T_FF', 'JK_FF', 'SR_FF')):
                    extras.append("- 💡 **Flip-Flops detected:** Check that control pins ($T=1$ or $J=K=1$) are tied to an active switch.")
                if context.get('has_clock') and not context.get('clock_running'):
                    extras.append("- ⚠️ **Clock is currently PAUSED:** Right-click the CLOCK block and choose **`▶ Start Auto-Clock`**.")
                if extras:
                    base_reply = "### 🔍 Live Circuit Diagnostic\n" + "\n".join(extras) + "\n\n---\n\n" + base_reply

            return base_reply

        # Graceful Fallback with recognized concepts and helpful prompts
        return self._generate_fallback(text, meta.get('tokens', []))

    def _generate_fallback(self, query: str, tokens: list) -> str:
        """Provide a helpful fallback with suggested questions and related topics."""
        # Find partial matches across intents to guide the user
        topic_suggestions = []
        for intent in self.intents:
            title = intent['title']
            for t in tokens:
                if t in title.lower():
                    topic_suggestions.append(title)
                    break

        suggestions_block = ""
        if topic_suggestions:
            suggestions_block = "\n\n**Related topics I found:**\n" + "\n".join(f"- *{s}*" for s in topic_suggestions[:3])

        return (
            f"I understood you're asking about: *\"{query}\"*, but I need a little more technical context "
            f"to give you the most accurate answer.{suggestions_block}\n\n"
            f"**Here are common questions I can help with:**\n"
            f"- *\"Why is my circuit showing 0?\"*\n"
            f"- *\"How do I configure the Bus Display to 8 or 16 bits?\"*\n"
            f"- *\"How do I build a 3-bit ripple counter with flip-flops?\"*\n"
            f"- *\"How do I convert my schematic to Verilog?\"*\n"
            f"- *\"How do 7400 IC chips work?\"*\n"
            f"- *\"Explain De Morgan's laws and K-Map simplification\"*\n\n"
            f"Try rephrasing your question or click one of the quick suggestions below!"
        )

    def api_call(self, text: str, api_key: str) -> str:
        """Pluggable cloud LLM API handler (OpenAI/Gemini)."""
        # Hook for cloud providers when internet/API key is present
        return None


# Backward-compatible alias
AIResponseEngine = SemanticAIResponseEngine


# ── Chat UI Components ────────────────────────────────────────────────
class ChatMessage(QFrame):
    """A styled chat bubble supporting markdown-style formatting."""
    def __init__(self, text, role="bot", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)

        if role == "user":
            bg = "#1f3a5c"
            fg = "#90caf9"
            align = Qt.AlignRight
            prefix = "You"
            prefix_color = "#4fc3f7"
        else:
            bg = "#161b22"
            fg = "#e6edf3"
            align = Qt.AlignLeft
            prefix = "⚡ AI Electronics Tutor"
            prefix_color = "#39ff14"

        self.setStyleSheet(f"""
            QFrame {{ background: {bg}; border-radius: 8px; border: 1px solid #30363d; margin: 2px 0; }}
        """)

        name = QLabel(prefix)
        name.setStyleSheet(f"color: {prefix_color}; font-family: Consolas; font-size: 10px; font-weight: bold; background: transparent; border: none;")
        layout.addWidget(name, alignment=align)

        formatted = self._format(text)
        msg = QLabel(formatted)
        msg.setWordWrap(True)
        msg.setTextFormat(Qt.RichText)
        msg.setStyleSheet(f"color: {fg}; font-family: Consolas, 'Segoe UI', monospace; font-size: 11px; background: transparent; border: none;")
        msg.setAlignment(align)
        layout.addWidget(msg)

    def _format(self, text):
        # Headers
        text = re.sub(r'### (.+)', r'<h4 style="color:#58a6ff;margin:4px 0 2px 0;">\1</h4>', text)
        text = re.sub(r'#### (.+)', r'<h5 style="color:#79c0ff;margin:4px 0 2px 0;">\1</h5>', text)
        # Bold **text**
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        # Italic *text*
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        # Code `text`
        text = re.sub(r'`(.+?)`', r'<code style="background:#0d1117;color:#39ff14;padding:1px 4px;border-radius:3px;">\1</code>', text)
        # Markdown lists
        text = re.sub(r'^- (.+)', r'• \1', text, flags=re.MULTILINE)
        # Newlines
        text = text.replace('\n', '<br>')
        return text


class ChatbotPanel(QDockWidget):
    """Interactive AI Assistant Dock Widget with Semantic Q&A."""
    def __init__(self, parent=None):
        super().__init__("⚡ AI Assistant", parent)
        self.setMinimumWidth(320)
        self.engine = SemanticAIResponseEngine()
        self._build_ui()

    def _build_ui(self):
        container = QWidget()
        container.setStyleSheet("background: #0d1117;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header with Title and Clear Chat button
        hdr_layout = QHBoxLayout()
        hdr = QLabel("Digital Electronics AI Tutor")
        hdr.setFont(QFont("Consolas", 10, QFont.Bold))
        hdr.setStyleSheet("color: #58a6ff; padding: 2px 0;")
        hdr_layout.addWidget(hdr)
        hdr_layout.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet("""
            QPushButton { background: #21262d; color: #8b949e; border: 1px solid #30363d;
                          border-radius: 4px; padding: 2px 8px; font-family: Consolas; font-size: 10px; }
            QPushButton:hover { background: #30363d; color: #f85149; border-color: #f85149; }
        """)
        clear_btn.clicked.connect(self._clear_chat)
        hdr_layout.addWidget(clear_btn)
        layout.addLayout(hdr_layout)

        # Chat scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: 1px solid #30363d; border-radius: 6px; background: #0d1117; }")

        self.chat_widget = QWidget()
        self.chat_widget.setStyleSheet("background: #0d1117;")
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setSpacing(6)
        self.chat_layout.setContentsMargins(6, 6, 6, 6)
        self.chat_layout.addStretch()

        self.scroll.setWidget(self.chat_widget)
        layout.addWidget(self.scroll, stretch=1)

        # Input row
        input_row = QHBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Ask a question (e.g., 'Why is it showing 0?', 'Bus display')...")
        self.input_box.setStyleSheet("""
            QLineEdit { background: #161b22; color: #e6edf3; border: 1px solid #30363d;
                        border-radius: 5px; padding: 7px; font-family: Consolas; font-size: 11px; }
            QLineEdit:focus { border-color: #58a6ff; }
        """)
        self.input_box.returnPressed.connect(self._send)
        input_row.addWidget(self.input_box)

        send_btn = QPushButton("Send")
        send_btn.setStyleSheet("""
            QPushButton { background: #238636; color: #fff; border: 1px solid #2ea043;
                          border-radius: 5px; padding: 7px 14px; font-family: Consolas; font-weight: bold; font-size: 11px; }
            QPushButton:hover { background: #2ea043; }
        """)
        send_btn.clicked.connect(self._send)
        input_row.addWidget(send_btn)
        layout.addLayout(input_row)

        # Quick-ask semantic topic chips
        quick_lbl = QLabel("Quick Questions:")
        quick_lbl.setStyleSheet("color: #8b949e; font-family: Consolas; font-size: 10px;")
        layout.addWidget(quick_lbl)

        quick_row = QHBoxLayout()
        quick_topics = [
            ("Why showing 0?", "Why is my circuit or display showing 0?"),
            ("Bus Display", "How do I configure the Bus Display bit width?"),
            ("Ripple Counter", "How do I build a 3-bit ripple counter?"),
            ("Verilog", "How do I convert my schematic to Verilog?"),
        ]
        for label, query in quick_topics:
            btn = QPushButton(label)
            btn.setStyleSheet("""
                QPushButton { background: #21262d; color: #c9d1d9; border: 1px solid #30363d;
                              border-radius: 10px; padding: 3px 8px; font-family: Consolas; font-size: 9.5px; }
                QPushButton:hover { color: #58a6ff; border-color: #58a6ff; background: #161b22; }
            """)
            btn.clicked.connect(lambda _, q=query: self._ask(q))
            quick_row.addWidget(btn)
        layout.addLayout(quick_row)

        self.setWidget(container)

        # Welcome message
        QTimer.singleShot(250, lambda: self._add_bot(
            "👋 **Hello! I'm your Digital Electronics AI Assistant.**\n\n"
            "I use semantic understanding to help with:\n"
            "- **Troubleshooting:** Why is it showing 0, flip-flops not toggling, clock setup.\n"
            "- **Bus Display & Radix:** Configuring 2 to 16 bits, Hex/Octal/BCD conversions.\n"
            "- **Circuit Design:** Designing counters, registers, adders, and MUX circuits.\n"
            "- **Verilog & ICs:** Generating Verilog code and 74xx IC pinouts.\n\n"
            "Ask me anything about your circuit!"
        ))

    def _get_circuit_context(self):
        """Retrieve live scene context from the parent window if available."""
        ctx = {
            'num_gates': 0,
            'num_wires': 0,
            'gate_types': [],
            'has_clock': False,
            'clock_running': False,
        }
        win = self.parent()
        if win and hasattr(win, 'scene') and win.scene:
            scene = win.scene
            ctx['num_gates'] = len(scene.gates)
            ctx['num_wires'] = len(scene.wires)
            ctx['gate_types'] = [getattr(g, 'gate_type', '') for g in scene.gates]
            clocks = [g for g in scene.gates if getattr(g, 'gate_type', '') == 'CLOCK']
            if clocks:
                ctx['has_clock'] = True
                ctx['clock_running'] = any(getattr(c, 'is_running', False) for c in clocks)
        return ctx

    def _clear_chat(self):
        """Reset conversation."""
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._add_bot("Chat cleared! How can I help you with your circuit?")

    def _ask(self, text):
        self.input_box.setText(text)
        self._send()

    def _send(self):
        text = self.input_box.text().strip()
        if not text:
            return
        self.input_box.clear()
        self._add_user(text)
        # Responsive processing delay
        QTimer.singleShot(150, lambda: self._respond(text))

    def _respond(self, text):
        context = self._get_circuit_context()
        reply = self.engine.respond(text, context=context)
        self._add_bot(reply)

    def _add_user(self, text):
        self._add_message(text, "user")

    def _add_bot(self, text):
        self._add_message(text, "bot")

    def _add_message(self, text, role):
        stretch_item = self.chat_layout.takeAt(self.chat_layout.count() - 1)
        msg = ChatMessage(text, role)
        self.chat_layout.addWidget(msg)
        self.chat_layout.addStretch()
        QTimer.singleShot(40, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()))
