# Digital Electronics Design & Learning Studio (EDA Studio v2.0)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/GUI-PyQt5-green.svg?logo=qt&logoColor=white)](https://riverbankcomputing.com/software/pyqt/)
[![Plotting](https://img.shields.io/badge/Engine-Matplotlib%20%7C%20NetworkX-orange.svg)](https://matplotlib.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com/)

An integrated, professional Electronic Design Automation (EDA) and educational workbench built in Python and PyQt5. Designed to bridge the gap between theoretical Boolean logic, transistor physics, physical 74xx integrated circuits, and Verilog Hardware Description Language (HDL).

---

## 🎯 Why We Developed This Project

In conventional undergraduate Computer Science and Electrical Engineering education, learning digital electronics is often abstract and fragmented across disconnected tools:

1. **The Need to Truly Visualize Digital Electronics:**  
   In textbooks and traditional breadboard labs, electrical signals and binary data (`0`s and `1`s) are **completely invisible**. Students are forced to memorize Boolean formulas, truth tables, and timing diagrams without ever seeing how signals actually travel, propagate, and settle. We developed this platform first and foremost to **bring digital electronics to life visually** — allowing learners to literally watch current flow, observe dynamic color-coded signal states across every wire, see clock pulses oscillate in real-time, and watch MOSFET switches open and close inside logic gates.
2. **Abstract Simulators as "Black Boxes":**  
   Classical software treats logic gates as opaque black-box symbols, leaving students disconnected from how circuits actually function at the silicon and CMOS transistor level.
3. **Physical Breadboarding Challenges:**  
   When moving to physical lab breadboards with 74xx IC chips, students frequently face wiring fatigue, pinout confusion, and difficult troubleshooting with zero real-time diagnostic feedback.
4. **The HDL Disconnect:**  
   Writing Verilog or VHDL is often taught as an isolated programming exercise, disconnected from visual schematics and hardware structures.
5. **Lack of Instant Guidance:**  
   When a student's circuit outputs `0` unexpectedly or fails to oscillate, there is rarely an immediate tutor available to diagnose the topology and explain why.

### Our Vision: Complete Visual Learning
We developed **Digital Electronics Design & Learning Studio** as an all-in-one Project-Based Learning (PBL) workbench that unifies visualization with the complete 4-tier abstraction hierarchy of digital systems into a single intuitive GUI:

```
┌────────────────────────────────────────────────────────┐
│                   Level 4: Verilog HDL                 │
│         (Synthesizable Code & Bi-directional Netlist)   │
├────────────────────────────────────────────────────────┤
│              Level 3: Physical 74xx IC Chips           │
│        (DIP-14/16 Pinouts & Reference Datasheets)      │
├────────────────────────────────────────────────────────┤
│               Level 2: Logic Gates & Flip-Flops        │
│       (Combinational & Sequential Schematic Canvas)    │
├────────────────────────────────────────────────────────┤
│             Level 1: Transistors & MOSFET Switches     │
│             (CMOS Pull-Up / Pull-Down Networks)        │
└────────────────────────────────────────────────────────┘
```
Coupled with an **integrated AI Electronics Tutor**, automated **Karnaugh Map (K-Map) Solver**, **Signal Pulse Animator**, and **Timing Waveform Plotter**, this platform empowers students to explore, design, simulate, and understand digital electronics comprehensively.

---

## ✨ Key Features

### 1. ⚡ Expansive Interactive Circuit Canvas
* Drag-and-drop component palette with real-time grid snapping, zooming, panning, and auto-fit.
* Smart bezier-curved orthogonal wiring with live signal state coloring (High `1` = Vivid Green/Cyan, Low `0` = Slate Gray).
* Configurable multi-input gates (2 to 8 inputs).

### 2. 🔬 Complete Component Library
* **Basic Logic Gates:** AND, OR, NOT, NAND, NOR, XOR, XNOR, BUFFER.
* **Sequential Logic:** Clock Generator (adjustable frequency), D Flip-Flop, JK Flip-Flop, T Flip-Flop, SR Latch.
* **MSI & Arithmetic:** 2:1 & 4:1 Multiplexers (MUX), Demultiplexers (DEMUX), 3:8 Decoders, Encoders, Priority Encoders, Half Adders, Full Adders, BCD to 7-Segment Decoders.
* **I/O & Visualization:** Interactive Input Toggles, Output Probes, Hex/Decimal Radix Displays, Canvas Notes/Annotations.

### 3. 🔍 Transistor & CMOS Level Inspection
* Peek inside logic gates to view their internal CMOS switch topology (Pull-Up PMOS network + Pull-Down NMOS network).
* Dedicated MOSFET simulator dialog to construct CMOS logic from scratch.

### 4. 📦 Virtual 74xx TTL IC Family & Interactive Datasheet
* Authentic Dual In-line Package (DIP-14 and DIP-16) IC components:
  * **7400** (Quad 2-Input NAND)
  * **7402** (Quad 2-Input NOR)
  * **7404** (Hex Inverter)
  * **7408** (Quad 2-Input AND)
  * **7432** (Quad 2-Input OR)
  * **7486** (Quad 2-Input XOR)
  * **7474** (Dual D Flip-Flop with Preset/Clear)
  * **74138** (3-to-8 Line Decoder/Demux)
  * **74151** (8-to-1 Data Selector/Multiplexer)
* Built-in **IC Manual & Reference Dialog** featuring authentic pin diagrams, truth tables, and a 1-click **Instantiate Test Circuit** button.

### 5. 🤖 Context-Aware AI Electronics Tutor
* Built directly into the auxiliary dock.
* Inspects live circuit topology (gate count, wire states, clock status) to answer diagnostic questions like *"Why is my circuit outputting 0?"* or *"Explain how a JK flip-flop toggles"*.

### 6. 🧮 Automated Karnaugh Map (K-Map) Solver
* Automatic Boolean minimization using tabular Quine-McCluskey / K-Map algorithms.
* Generates minimized Sum of Products (SOP) and Product of Sums (POS) expressions.

### 7. ⏱️ Waveform Timing Viewer & Signal Pulse Animator
* Multi-channel digital timing diagrams plotted via Matplotlib.
* Live animated electrical pulses propagating through wires during active simulation.

### 8. 📝 Verilog Studio & Bi-directional Converter
* **Schematic $\rightarrow$ Verilog:** Converts visual canvas schematics into clean, synthesizable Verilog-2001 HDL code.
* **Verilog $\rightarrow$ Schematic:** Parses gate-level and structural Verilog code and automatically constructs the circuit schematic on canvas.

---

## 📂 Project Structure

```
python-pbl/
├── main.py                         # Application entry point & splash screen
├── main_window.py                  # Main EDA workbench window, menus, & docks
├── canvas.py                       # QGraphicsScene & QGraphicsView canvas engine
├── gate.py                         # Logic gate items, nodes, and rendering logic
├── wire.py                         # Orthogonal smart wire connections
├── simulation.py                   # Circuit simulation & state propagation engine
├── sequential_gates.py             # Flip-flops, registers, latches, & clock logic
├── transistor_gates.py             # MOSFET & CMOS transistor switch logic
├── mosfet_simulator.py             # Transistor-level circuit simulator dialog
├── ic_chip.py                      # Virtual 74xx series DIP IC chip definitions
├── ic_manual_dialog.py             # Interactive 74xx datasheet & pinout viewer
├── internal_structure_dialog.py    # Transistor-level gate internals dialog
├── kmap_solver.py                  # Automated K-Map minimization & visual solver
├── truth_table.py                  # Combinational truth table generator
├── waveform.py                     # Matplotlib-based digital timing waveform viewer
├── signal_animator.py              # Visual current/signal flow animation on wires
├── verilog_converter.py            # AST Verilog parser & schematic generator
├── verilog_studio.py               # Integrated Verilog HDL editor & synthesis studio
├── code_converter.py               # Code translation workbench
├── ai_chatbot.py                   # Embedded AI electronics diagnostic assistant
├── project_browser.py              # Saved project file explorer panel
├── notes.py                        # Schematic notes & visual annotations
├── save_load.py                    # JSON project serialization & deserialization
├── export_image.py                 # High-resolution PNG/JPEG schematic exporter
├── app_icon.ico                    # Multi-resolution application icon
├── requirements.txt                # Python package dependencies
├── build_desktop_app.bat           # 1-click script to build standalone Windows .exe
└── run_live_app.bat                # 1-click script for live development mode
```

---

## 🛠️ Prerequisites & Installation

### Requirements
* **Operating System:** Windows 10/11, macOS, or Linux
* **Python Version:** Python 3.8 or higher (Python 3.10+ recommended)

### Step 1: Clone the Repository
Open your terminal (or Command Prompt / PowerShell) and run:
```bash
git clone https://github.com/NISCHALNBANGERA/DIGITAL---ELECTRONICS.git
cd DIGITAL---ELECTRONICS
```

### Step 2: Create a Virtual Environment (Recommended)
Creating an isolated environment keeps your system Python clean:

* **On Windows (PowerShell / Command Prompt):**
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\activate
  ```

* **On macOS / Linux:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

### Step 3: Install Required Dependencies
Install the required packages using `pip`:
```bash
pip install -r requirements.txt
```

The core libraries installed are:
* `PyQt5` — GUI framework and graphics canvas
* `matplotlib` — Digital timing waveform plots
* `numpy` — Array computation for waveforms and analysis
* `Pillow` — Icon and image rendering pipeline
* `networkx` — Graph traversal and circuit netlist routing

---

## 🚀 How to Run and Use

### Quick Launch
To start the application, run:
```bash
python main.py
```
*(Windows users can also double-click `run_live_app.bat` to launch without opening a command terminal).*

---

### Basic Usage Guide

1. **Placing Components:**
   * Select components from the **Left Component Library** (Basic Gates, Sequential, MSI, Transistors, 74xx ICs) and click on the canvas to place them.
   * Or press **`Ctrl + Space`** to open Quick-Search and type any component name (e.g., `NAND`, `7404`, `JK_FF`).

2. **Wiring Components:**
   * Hover over any output pin (small circular terminal) until it highlights.
   * Click and drag a wire to any input pin. The wire will automatically calculate clean orthogonal routing.

3. **Interacting with Inputs:**
   * Click on an **INPUT** switch node on the canvas to toggle its state between `0` (Low) and `1` (High).
   * Notice output probes and connected gates update in real-time.

4. **Using the Analysis Tools:**
   * **Truth Table:** Click `Tools` $\rightarrow$ `Truth Table` to generate the complete boolean evaluation.
   * **K-Map Solver:** Click `Tools` $\rightarrow$ `K-Map Solver` to view the minimized expression.
   * **Timing Waveform:** Click `Tools` $\rightarrow$ `Waveform Viewer` to observe pulse transitions.
   * **74xx IC Manual:** Click `Tools` $\rightarrow$ `IC Reference Manual` to inspect chip pinouts or click **Instantiate Test Circuit** to generate sample circuits.
   * **Verilog Studio:** Click `Tools` $\rightarrow$ `Verilog Studio` to export your schematic to Verilog code or synthesize Verilog into a schematic.

5. **Asking the AI Tutor:**
   * Open the right dock panel and select **AI Tutor**.
   * Ask any concept or troubleshooting question (e.g., *"Why is my circuit showing 0?"* or *"Explain De Morgan's Theorem"*).

---

## 📦 Deploying as a Standalone Laptop Application (`.exe`)

You can compile this project into a standalone Windows `.exe` application that runs on any laptop without needing Python installed:

1. Double-click the provided **`build_desktop_app.bat`** file in the project folder.
2. The script will automatically:
   * Install `PyInstaller` if not present.
   * Bundle your Python code, PyQt5 runtimes, icons, and assets into `dist\DigitalElectronicsStudio\`.
   * Automatically place a **"Digital Electronics Studio"** shortcut with custom icon on your Windows Desktop.

---

## 👤 Author & Developer

Developed with ❤️ as a Project-Based Learning (PBL) initiative by:

* **Nischal N Bangera**

---

## 📜 License

This project is developed for educational and academic purposes. Feel free to use, modify, and extend it for learning and teaching digital electronics.
