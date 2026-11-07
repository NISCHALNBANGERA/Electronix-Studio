"""
verilog_converter.py - Bidirectional Verilog Conversion Engine
1. Verilog Code -> Schematic (Design Synthesizer):
   - Parses Verilog-2001/1995 module headers, ports (input, output, wire, reg).
   - Gate primitives: and, nand, or, nor, xor, xnor, not, buf.
   - Continuous assignments: assign out = expr (supports &, |, ^, ~, ternary ?, ()).
   - Sequential blocks: always @(posedge clk) begin q <= d; end with async rst/set.
   - Module instantiations: d_ff, jk_ff, t_ff, sr_ff, mux, adders.
   - Auto-layout: Inputs on left, logic/FF in center columns, Outputs on right, neatly wired.
   - Syntax error reporting with line numbers and clear diagnostics.

2. Schematic -> Verilog Code (HDL Generator):
   - Graph traversal: discovers ports, gates, flip-flops, and wire nets.
   - Supports 4 Modeling Styles:
     * Gate-Level Modeling (primitives and structural modules)
     * Dataflow Modeling (assign boolean expressions)
     * Behavioral Modeling (always @(*) and always @(posedge clk))
     * Switch-Level Modeling (CMOS pmos/nmos transistor switch networks)
"""

import re
from datetime import datetime
from PyQt5.QtCore import QPointF
from gate import create_gate, InputNode, OutputNode, GateItem
from sequential_gates import ClockNode, FlipFlopBase, DFlipFlop, JKFlipFlop, TFlipFlop, SRFlipFlop
from wire import Wire


# ───────────────────────────────────────────────────────────────────────
# Helper & Identifier Sanitizer
# ───────────────────────────────────────────────────────────────────────
def sanitize_ident(name, fallback="net"):
    """Convert an arbitrary label or pin string into a valid Verilog identifier."""
    if not name:
        return fallback
    clean = re.sub(r'[^a-zA-Z0-9_]', '_', str(name).strip())
    clean = re.sub(r'_+', '_', clean).strip('_')
    if not clean or clean[0].isdigit():
        clean = f"sig_{clean}"
    # Avoid Verilog keywords
    KEYWORDS = {'module', 'endmodule', 'input', 'output', 'wire', 'reg', 'assign',
                'always', 'posedge', 'negedge', 'begin', 'end', 'if', 'else',
                'case', 'endcase', 'and', 'nand', 'or', 'nor', 'xor', 'xnor', 'not', 'buf'}
    if clean.lower() in KEYWORDS:
        clean = f"{clean}_net"
    return clean.lower()


# ───────────────────────────────────────────────────────────────────────
# Expression AST for Continuous Assignments
# ───────────────────────────────────────────────────────────────────────
class ExprNode:
    pass

class VarNode(ExprNode):
    def __init__(self, name): self.name = name
    def __repr__(self): return f"Var({self.name})"

class ConstNode(ExprNode):
    def __init__(self, val): self.val = int(val)
    def __repr__(self): return f"Const({self.val})"

class UnaryOpNode(ExprNode):
    def __init__(self, op, operand): self.op = op; self.operand = operand
    def __repr__(self): return f"Unary({self.op}, {self.operand})"

class BinaryOpNode(ExprNode):
    def __init__(self, op, left, right): self.op = op; self.left = left; self.right = right
    def __repr__(self): return f"Binary({self.op}, {self.left}, {self.right})"

class TernaryOpNode(ExprNode):
    def __init__(self, cond, true_expr, false_expr):
        self.cond = cond; self.true_expr = true_expr; self.false_expr = false_expr
    def __repr__(self): return f"Ternary({self.cond} ? {self.true_expr} : {self.false_expr})"


# ───────────────────────────────────────────────────────────────────────
# Verilog Parser
# ───────────────────────────────────────────────────────────────────────
class VerilogParser:
    """Parses structural, dataflow, and sequential Verilog code into an intermediate AST."""

    PRIMITIVES = {'and', 'nand', 'or', 'nor', 'xor', 'xnor', 'not', 'buf'}

    def __init__(self, code: str):
        self.raw_code = code
        self.module_name = "digital_circuit"
        self.inputs = []       # list of input port names
        self.outputs = []      # list of output port names
        self.wires = set()     # internal wire names
        self.regs = set()      # reg names
        self.instances = []    # list of dicts: {'type': ..., 'name': ..., 'ports': [...], 'named_ports': {...}}
        self.assigns = []      # list of (lhs_var, expr_ast)
        self.sequential_blocks = []  # list of sequential block info dicts
        self.errors = []
        self.warnings = []

    def parse(self) -> bool:
        """Parse the input Verilog code. Returns True on success, False if syntax errors occur."""
        try:
            clean = self._strip_comments(self.raw_code)
            if not clean.strip():
                self.errors.append("Empty code input. Please provide a Verilog module.")
                return False

            tokens = self._tokenize(clean)
            if not tokens:
                self.errors.append("No valid tokens found.")
                return False

            self._parse_module(tokens)
            return len(self.errors) == 0
        except Exception as e:
            self.errors.append(f"Parser error: {str(e)}")
            return False

    def _strip_comments(self, code: str) -> str:
        # Remove /* ... */ comments
        code = re.sub(r'/\*.*?\*/', ' ', code, flags=re.DOTALL)
        # Remove // ... comments
        lines = []
        for line in code.splitlines():
            line = re.sub(r'//.*$', '', line)
            lines.append(line)
        return "\n".join(lines)

    def _tokenize(self, text: str):
        token_spec = [
            ('NUMBER',   r"\b\d+'[bBoOdDhH][0-9a-fA-F_xXzZ]+\b|\b\d+\b"),
            ('KEYWORD',  r'\b(module|endmodule|input|output|inout|wire|reg|assign|always|posedge|negedge|begin|end|if|else|case|endcase)\b'),
            ('PRIM',     r'\b(and|nand|or|nor|xor|xnor|not|buf)\b'),
            ('IDENT',    r'[a-zA-Z_][a-zA-Z0-9_]*'),
            ('OP2',      r'<=|==|!=|&&|\|\||~&|~\||~\^|\^~'),
            ('OP1',      r'[&|^~?:=;(),.@\[\]{}]'),
            ('WS',       r'\s+'),
        ]
        tok_regex = '|'.join(f'(?P<{pair[0]}>{pair[1]})' for pair in token_spec)
        tokens = []
        line_num = 1
        line_start = 0
        for mo in re.finditer(tok_regex, text):
            kind = mo.lastgroup
            val = mo.group()
            if kind == 'WS':
                newlines = val.count('\n')
                if newlines:
                    line_num += newlines
                    line_start = mo.end()
                continue
            col = mo.start() - line_start + 1
            tokens.append((kind, val, line_num, col))
        return tokens

    def _parse_module(self, tokens):
        i = 0
        n = len(tokens)

        # 1. Find 'module'
        while i < n and not (tokens[i][0] == 'KEYWORD' and tokens[i][1] == 'module'):
            i += 1
        if i >= n:
            self.errors.append("Syntax Error: Missing 'module' declaration.")
            return

        i += 1  # past 'module'
        if i < n and tokens[i][0] == 'IDENT':
            self.module_name = tokens[i][1]
            i += 1
        else:
            self.errors.append("Syntax Error: Missing module name after 'module'.")
            return

        # Check for port list `( ... )`
        if i < n and tokens[i][1] == '(':
            i += 1
            # Collect port tokens inside module header parentheses
            depth = 1
            port_tokens = []
            while i < n and depth > 0:
                if tokens[i][1] == '(':
                    depth += 1
                elif tokens[i][1] == ')':
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
                port_tokens.append(tokens[i])
                i += 1

            self._parse_port_list(port_tokens)

        # Skip semicolon after module header
        if i < n and tokens[i][1] == ';':
            i += 1

        # Parse module body items until 'endmodule'
        body_tokens = []
        while i < n and not (tokens[i][0] == 'KEYWORD' and tokens[i][1] == 'endmodule'):
            body_tokens.append(tokens[i])
            i += 1

        self._parse_module_body(body_tokens)

    def _parse_port_list(self, tokens):
        """Parse ANSI style port declarations inside module(input a, output b, ...)."""
        chunks = []
        current = []
        for tok in tokens:
            if tok[1] == ',':
                if current:
                    chunks.append(current)
                    current = []
            else:
                current.append(tok)
        if current:
            chunks.append(current)

        for chunk in chunks:
            direction = None
            ident = None
            j = 0
            while j < len(chunk):
                val = chunk[j][1]
                if val in ('input', 'output', 'inout'):
                    direction = val
                elif val in ('reg', 'wire'):
                    pass
                elif val == '[':
                    # skip bus width [N:0]
                    while j < len(chunk) and chunk[j][1] != ']':
                        j += 1
                elif chunk[j][0] == 'IDENT':
                    ident = val
                j += 1

            if ident:
                if direction == 'input':
                    if ident not in self.inputs:
                        self.inputs.append(ident)
                elif direction in ('output', 'inout'):
                    if ident not in self.outputs:
                        self.outputs.append(ident)

    def _parse_module_body(self, tokens):
        """Parse declarations, gate primitives, assigns, always blocks, and module instances."""
        idx = 0
        n = len(tokens)

        while idx < n:
            tok = tokens[idx]
            val = tok[1]

            # 1. Non-ANSI Port declarations / wires / regs
            if val in ('input', 'output', 'inout', 'wire', 'reg'):
                idx = self._parse_declaration(tokens, idx)
                continue

            # 2. Gate primitive: and g1(out, in1, in2);
            if val in self.PRIMITIVES:
                idx = self._parse_primitive_instance(tokens, idx)
                continue

            # 3. Continuous assign: assign y = a & b;
            if val == 'assign':
                idx = self._parse_assign(tokens, idx)
                continue

            # 4. Always block: always @(...) begin ... end
            if val == 'always':
                idx = self._parse_always_block(tokens, idx)
                continue

            # 5. User module instantiation (e.g. d_ff d1 (.clk(clk), .d(d), .q(q)); or positional)
            if tok[0] == 'IDENT' and idx + 1 < n and (tokens[idx + 1][0] == 'IDENT' or tokens[idx + 1][1] == '('):
                idx = self._parse_module_instance(tokens, idx)
                continue

            # Skip stray semicolons or unparsed tokens
            idx += 1

    def _parse_declaration(self, tokens, idx):
        kind = tokens[idx][1]
        idx += 1
        # Skip [msb:lsb]
        if idx < len(tokens) and tokens[idx][1] == '[':
            while idx < len(tokens) and tokens[idx][1] != ']':
                idx += 1
            if idx < len(tokens) and tokens[idx][1] == ']':
                idx += 1

        # Collect identifiers separated by comma until ';'
        while idx < len(tokens) and tokens[idx][1] != ';':
            if tokens[idx][0] == 'IDENT':
                name = tokens[idx][1]
                if kind == 'input' and name not in self.inputs:
                    self.inputs.append(name)
                elif kind == 'output' and name not in self.outputs:
                    self.outputs.append(name)
                elif kind == 'wire':
                    self.wires.add(name)
                elif kind == 'reg':
                    self.regs.add(name)
            idx += 1
        return idx + 1 if idx < len(tokens) else idx

    def _parse_primitive_instance(self, tokens, idx):
        prim_type = tokens[idx][1]
        idx += 1
        inst_name = ""
        if idx < len(tokens) and tokens[idx][0] == 'IDENT' and tokens[idx][1] != '(':
            inst_name = tokens[idx][1]
            idx += 1
        if idx >= len(tokens) or tokens[idx][1] != '(':
            self.errors.append(f"Syntax Error: Expected '(' after gate '{prim_type}'.")
            return idx

        idx += 1  # past '('
        ports = []
        while idx < len(tokens) and tokens[idx][1] != ')':
            if tokens[idx][0] in ('IDENT', 'NUMBER'):
                ports.append(tokens[idx][1])
            idx += 1
        if idx < len(tokens) and tokens[idx][1] == ')':
            idx += 1
        if idx < len(tokens) and tokens[idx][1] == ';':
            idx += 1

        if prim_type in ('not', 'buf') and len(ports) < 2:
            self.errors.append(f"Gate '{prim_type}' requires 1 output and 1 input port.")
        elif prim_type not in ('not', 'buf') and len(ports) < 3:
            self.errors.append(f"Gate '{prim_type}' requires 1 output and at least 2 input ports.")
        else:
            self.instances.append({
                'type': prim_type.upper(),
                'name': inst_name or f"{prim_type}_{len(self.instances)+1}",
                'out': ports[0],
                'inputs': ports[1:],
            })
        return idx

    def _parse_assign(self, tokens, idx):
        idx += 1  # past 'assign'
        if idx >= len(tokens) or tokens[idx][0] != 'IDENT':
            self.errors.append("Syntax Error: Missing LHS identifier in assign statement.")
            return idx
        lhs = tokens[idx][1]
        idx += 1

        if idx >= len(tokens) or tokens[idx][1] != '=':
            self.errors.append(f"Syntax Error: Expected '=' in assign for '{lhs}'.")
            return idx
        idx += 1

        expr_tokens = []
        while idx < len(tokens) and tokens[idx][1] != ';':
            expr_tokens.append(tokens[idx])
            idx += 1
        if idx < len(tokens) and tokens[idx][1] == ';':
            idx += 1

        try:
            expr_ast = self._parse_expression(expr_tokens)
            self.assigns.append((lhs, expr_ast))
        except Exception as e:
            self.errors.append(f"Error parsing assign for '{lhs}': {e}")
        return idx

    def _parse_expression(self, tokens):
        """Recursive-descent expression parser with operator precedence."""
        pos = 0

        def parse_ternary():
            nonlocal pos
            node = parse_or()
            if pos < len(tokens) and tokens[pos][1] == '?':
                pos += 1
                true_node = parse_ternary()
                if pos < len(tokens) and tokens[pos][1] == ':':
                    pos += 1
                false_node = parse_ternary()
                return TernaryOpNode(node, true_node, false_node)
            return node

        def parse_or():
            nonlocal pos
            node = parse_xor()
            while pos < len(tokens) and tokens[pos][1] in ('|', '||', '~|'):
                op = tokens[pos][1]
                pos += 1
                right = parse_xor()
                node = BinaryOpNode(op, node, right)
            return node

        def parse_xor():
            nonlocal pos
            node = parse_and()
            while pos < len(tokens) and tokens[pos][1] in ('^', '~^', '^~'):
                op = tokens[pos][1]
                pos += 1
                right = parse_and()
                node = BinaryOpNode(op, node, right)
            return node

        def parse_and():
            nonlocal pos
            node = parse_unary()
            while pos < len(tokens) and tokens[pos][1] in ('&', '&&', '~&'):
                op = tokens[pos][1]
                pos += 1
                right = parse_unary()
                node = BinaryOpNode(op, node, right)
            return node

        def parse_unary():
            nonlocal pos
            if pos < len(tokens) and tokens[pos][1] in ('~', '!'):
                op = tokens[pos][1]
                pos += 1
                operand = parse_unary()
                return UnaryOpNode(op, operand)
            return parse_primary()

        def parse_primary():
            nonlocal pos
            if pos >= len(tokens):
                raise ValueError("Unexpected end of expression")
            tok = tokens[pos]
            if tok[1] == '(':
                pos += 1
                sub = parse_ternary()
                if pos < len(tokens) and tokens[pos][1] == ')':
                    pos += 1
                return sub
            elif tok[0] == 'IDENT':
                pos += 1
                return VarNode(tok[1])
            elif tok[0] == 'NUMBER':
                pos += 1
                # parse binary 1'b0 / 1'b1 or int
                val = 0
                if "'b" in tok[1] or "'B" in tok[1]:
                    val = 1 if tok[1].endswith('1') else 0
                else:
                    try: val = int(tok[1])
                    except: val = 0
                return ConstNode(val)
            else:
                pos += 1
                return VarNode(tok[1])

        return parse_ternary()

    def _parse_always_block(self, tokens, idx):
        """Parse sequential always @(posedge clk ...) begin ... end blocks."""
        idx += 1  # past 'always'
        clk_name = None
        edge = "posedge"
        rst_name = None
        rst_edge = "posedge"

        # Check sensitivity list @(...)
        if idx < len(tokens) and tokens[idx][1] == '@':
            idx += 1
            if idx < len(tokens) and tokens[idx][1] == '(':
                idx += 1
                sens_tokens = []
                while idx < len(tokens) and tokens[idx][1] != ')':
                    sens_tokens.append(tokens[idx])
                    idx += 1
                if idx < len(tokens) and tokens[idx][1] == ')':
                    idx += 1

                # Parse sensitivity tokens
                k = 0
                while k < len(sens_tokens):
                    st = sens_tokens[k][1]
                    if st in ('posedge', 'negedge'):
                        current_edge = st
                        k += 1
                        if k < len(sens_tokens) and sens_tokens[k][0] == 'IDENT':
                            ident = sens_tokens[k][1]
                            if 'rst' in ident.lower() or 'reset' in ident.lower():
                                rst_name = ident
                                rst_edge = current_edge
                            elif 'clk' in ident.lower() or 'clock' in ident.lower():
                                clk_name = ident
                                edge = current_edge
                            elif clk_name is None:
                                clk_name = ident
                                edge = current_edge
                            elif rst_name is None:
                                rst_name = ident
                                rst_edge = current_edge
                    k += 1

        if not clk_name:
            clk_name = "clk"

        # Collect block tokens until end of statement / end of begin...end
        block_tokens = []
        depth = 0
        while idx < len(tokens):
            t = tokens[idx][1]
            if t == 'begin':
                depth += 1
            elif t == 'end':
                depth -= 1
                if depth <= 0:
                    idx += 1
                    break
            elif t == ';' and depth == 0:
                block_tokens.append(tokens[idx])
                idx += 1
                break
            block_tokens.append(tokens[idx])
            idx += 1

        # Analyze assignments in block: e.g. q <= d; or if (rst) q <= 0; else q <= d;
        q_target = None
        d_source = None
        is_toggle = False
        k = 0
        while k < len(block_tokens):
            if block_tokens[k][1] == '<=':
                lhs = block_tokens[k - 1][1] if k > 0 else "q"
                rhs_toks = []
                m = k + 1
                while m < len(block_tokens) and block_tokens[m][1] not in (';', 'else'):
                    rhs_toks.append(block_tokens[m][1])
                    m += 1
                rhs = "".join(rhs_toks)
                if rhs in ('0', "1'b0", "0'b0"):
                    # Reset branch
                    pass
                else:
                    q_target = lhs
                    if '~' in rhs or '!' in rhs:
                        is_toggle = True
                        d_source = rhs.replace('~', '').replace('!', '').strip()
                    else:
                        d_source = rhs.strip()
            k += 1

        if q_target:
            self.sequential_blocks.append({
                'q': q_target,
                'clk': clk_name,
                'edge': edge,
                'rst': rst_name,
                'rst_edge': rst_edge,
                'd': d_source or "d",
                'is_toggle': is_toggle,
            })
        return idx

    def _parse_module_instance(self, tokens, idx):
        mod_type = tokens[idx][1]
        idx += 1
        inst_name = ""
        if idx < len(tokens) and tokens[idx][0] == 'IDENT':
            inst_name = tokens[idx][1]
            idx += 1
        if idx >= len(tokens) or tokens[idx][1] != '(':
            return idx

        idx += 1  # past '('
        port_tokens = []
        depth = 1
        while idx < len(tokens) and depth > 0:
            if tokens[idx][1] == '(':
                depth += 1
            elif tokens[idx][1] == ')':
                depth -= 1
                if depth == 0:
                    idx += 1
                    break
            port_tokens.append(tokens[idx])
            idx += 1

        if idx < len(tokens) and tokens[idx][1] == ';':
            idx += 1

        # Parse port connections (named .port(net) or positional)
        named_ports = {}
        positional_ports = []
        k = 0
        while k < len(port_tokens):
            if port_tokens[k][1] == '.':
                k += 1
                if k < len(port_tokens):
                    port_name = port_tokens[k][1]
                    k += 1
                    if k < len(port_tokens) and port_tokens[k][1] == '(':
                        k += 1
                        if k < len(port_tokens) and port_tokens[k][0] in ('IDENT', 'NUMBER'):
                            net_name = port_tokens[k][1]
                            named_ports[port_name] = net_name
                            k += 1
            elif port_tokens[k][0] in ('IDENT', 'NUMBER') and port_tokens[k-1][1] != '.':
                positional_ports.append(port_tokens[k][1])
            k += 1

        self.instances.append({
            'type': mod_type.upper(),
            'name': inst_name or f"{mod_type}_{len(self.instances)+1}",
            'named_ports': named_ports,
            'ports': positional_ports,
        })
        return idx


# ───────────────────────────────────────────────────────────────────────
# Verilog Synthesizer (Builds Schematic on Canvas)
# ───────────────────────────────────────────────────────────────────────
class VerilogSynthesizer:
    """Takes parsed Verilog AST and places components & wires on CircuitScene with auto-layout."""

    def __init__(self, scene, parser: VerilogParser):
        self.scene = scene
        self.parser = parser
        self.net_drivers = {}   # net_name -> Pin (output)
        self.net_sinks = {}     # net_name -> list of Pin (inputs)
        self.created_gates = []
        self.created_wires = []

    def synthesize(self, clear_scene=True):
        """Constructs circuit components and routes wires cleanly."""
        if clear_scene:
            self.scene.clear_circuit()

        # Step 1: Create Input and Clock nodes (Left Column: x = -380)
        self._build_inputs()

        # Step 2: Create Output nodes (Right Column: x = +380)
        self._build_outputs()

        # Step 3: Create Sequential Elements (Flip-Flops)
        self._build_sequential_blocks()

        # Step 4: Create Gate Instances
        self._build_primitive_instances()

        # Step 5: Synthesize Assign Statements (Gate Trees)
        self._build_assign_statements()

        # Step 6: Connect all wire nets between driver output pins and sink input pins
        self._route_all_nets()

        # Step 7: Auto-layout nodes neatly by column & row
        self._auto_layout()

        self.scene.circuit_changed.emit()
        return len(self.created_gates), len(self.created_wires)

    def _register_driver(self, net_name, pin):
        clean = sanitize_ident(net_name)
        self.net_drivers[clean] = pin

    def _register_sink(self, net_name, pin):
        clean = sanitize_ident(net_name)
        if clean not in self.net_sinks:
            self.net_sinks[clean] = []
        self.net_sinks[clean].append(pin)

    def _build_inputs(self):
        for inp_name in self.parser.inputs:
            is_clk = 'clk' in inp_name.lower() or 'clock' in inp_name.lower()
            gate_type = 'CLOCK' if is_clk else 'INPUT'
            gate = create_gate(gate_type, label=inp_name.upper())
            self.scene.addItem(gate)
            self.scene.gates.append(gate)
            self.created_gates.append(gate)
            if gate.output_pins:
                self._register_driver(inp_name, gate.output_pins[0])

    def _build_outputs(self):
        for out_name in self.parser.outputs:
            gate = create_gate('OUTPUT', label=out_name.upper())
            self.scene.addItem(gate)
            self.scene.gates.append(gate)
            self.created_gates.append(gate)
            if gate.input_pins:
                self._register_sink(out_name, gate.input_pins[0])

    def _build_sequential_blocks(self):
        for block in self.parser.sequential_blocks:
            q_name   = block['q']
            clk_name = block['clk']
            d_name   = block['d']
            rst_name = block.get('rst')
            is_toggle = block.get('is_toggle', False)

            gate_type = 'T_FF' if is_toggle else 'D_FF'
            ff = create_gate(gate_type, label=f"{gate_type}_{q_name.upper()}")
            self.scene.addItem(ff)
            self.scene.gates.append(ff)
            self.created_gates.append(ff)

            # Register FF outputs
            if len(ff.output_pins) > 0:
                self._register_driver(q_name, ff.output_pins[0])
            if len(ff.output_pins) > 1:
                self._register_driver(f"{q_name}_bar", ff.output_pins[1])
                self._register_driver(f"{q_name}_b", ff.output_pins[1])

            # Register FF inputs
            # For D-FF: input 0 is D, input 1 is CLK, input 2 is RST
            # For T-FF: input 0 is T, input 1 is CLK, input 2 is RST
            if len(ff.input_pins) > 0:
                self._register_sink(d_name, ff.input_pins[0])
            if len(ff.input_pins) > 1:
                self._register_sink(clk_name, ff.input_pins[1])
            if rst_name and len(ff.input_pins) > 2:
                self._register_sink(rst_name, ff.input_pins[2])

    def _build_primitive_instances(self):
        for inst in self.parser.instances:
            itype = inst['type']
            name = inst.get('name', '')

            # Flip-Flop instantiation (d_ff, jk_ff, t_ff, sr_ff)
            if itype in ('D_FF', 'JK_FF', 'T_FF', 'SR_FF'):
                ff = create_gate(itype, label=name or itype)
                self.scene.addItem(ff)
                self.scene.gates.append(ff)
                self.created_gates.append(ff)
                named = inst.get('named_ports', {})
                ports = inst.get('ports', [])
                if named:
                    # Named port connections
                    for p_name, net in named.items():
                        p_clean = p_name.lower()
                        if p_clean in ('q', 'out'):
                            self._register_driver(net, ff.output_pins[0])
                        elif p_clean in ('q_bar', 'qbar', 'qb', 'qn'):
                            if len(ff.output_pins) > 1:
                                self._register_driver(net, ff.output_pins[1])
                        else:
                            # Match input pin by label
                            for ip in ff.input_pins:
                                if ip.label.lower() == p_clean:
                                    self._register_sink(net, ip)
                elif ports:
                    # Positional: (clk, d, q, q_bar) or (j, clk, k, q, q_bar)
                    for idx, net in enumerate(ports):
                        if idx < len(ff.input_pins):
                            self._register_sink(net, ff.input_pins[idx])
                continue

            # Standard gate primitives: AND, OR, NOT, NAND, NOR, XOR, XNOR, BUFFER
            if itype in ('AND', 'OR', 'NOT', 'NAND', 'NOR', 'XOR', 'XNOR', 'BUF', 'BUFFER'):
                actual_type = 'BUFFER' if itype == 'BUF' else itype
                out_net = inst.get('out', '')
                in_nets = inst.get('inputs', [])
                num_in = max(2, len(in_nets)) if actual_type not in ('NOT', 'BUFFER') else 1
                gate = create_gate(actual_type, label=name)
                if hasattr(gate, 'set_input_count') and num_in != len(gate.input_pins):
                    gate.set_input_count(num_in)

                self.scene.addItem(gate)
                self.scene.gates.append(gate)
                self.created_gates.append(gate)

                if out_net and gate.output_pins:
                    self._register_driver(out_net, gate.output_pins[0])

                for pin_idx, in_net in enumerate(in_nets):
                    if pin_idx < len(gate.input_pins):
                        self._register_sink(in_net, gate.input_pins[pin_idx])

    def _build_assign_statements(self):
        for lhs, expr_ast in self.parser.assigns:
            driver_pin = self._synthesize_expr_node(expr_ast)
            if driver_pin:
                self._register_driver(lhs, driver_pin)

    def _synthesize_expr_node(self, node: ExprNode):
        """Recursively builds gates for boolean expression AST and returns driver Pin."""
        if isinstance(node, VarNode):
            # Existing net driver will be wired during net routing
            clean = sanitize_ident(node.name)
            # If driver already exists, return it; otherwise create a dummy/proxy wire connection
            return self.net_drivers.get(clean)

        if isinstance(node, ConstNode):
            # Build constant InputNode (0 or 1)
            inp = create_gate('INPUT', label=str(node.val))
            inp._value = node.val
            self.scene.addItem(inp)
            self.scene.gates.append(inp)
            self.created_gates.append(inp)
            return inp.output_pins[0]

        if isinstance(node, UnaryOpNode):
            # Inverter / NOT gate
            sub_pin = self._synthesize_expr_node(node.operand)
            not_gate = create_gate('NOT')
            self.scene.addItem(not_gate)
            self.scene.gates.append(not_gate)
            self.created_gates.append(not_gate)
            if sub_pin:
                w = Wire(sub_pin, not_gate.input_pins[0])
                self.scene.addItem(w)
                self.scene.wires.append(w)
                self.created_wires.append(w)
            elif isinstance(node.operand, VarNode):
                self._register_sink(node.operand.name, not_gate.input_pins[0])
            return not_gate.output_pins[0]

        if isinstance(node, BinaryOpNode):
            op = node.op
            op_map = {
                '&': 'AND', '&&': 'AND',
                '|': 'OR',  '||': 'OR',
                '^': 'XOR',
                '~&': 'NAND',
                '~|': 'NOR',
                '~^': 'XNOR', '^~': 'XNOR',
            }
            gate_type = op_map.get(op, 'AND')
            gate = create_gate(gate_type)
            self.scene.addItem(gate)
            self.scene.gates.append(gate)
            self.created_gates.append(gate)

            left_pin = self._synthesize_expr_node(node.left)
            right_pin = self._synthesize_expr_node(node.right)

            if left_pin:
                w = Wire(left_pin, gate.input_pins[0])
                self.scene.addItem(w); self.scene.wires.append(w); self.created_wires.append(w)
            elif isinstance(node.left, VarNode):
                self._register_sink(node.left.name, gate.input_pins[0])

            if right_pin:
                w = Wire(right_pin, gate.input_pins[1])
                self.scene.addItem(w); self.scene.wires.append(w); self.created_wires.append(w)
            elif isinstance(node.right, VarNode):
                self._register_sink(node.right.name, gate.input_pins[1])

            return gate.output_pins[0]

        if isinstance(node, TernaryOpNode):
            # 2:1 Multiplexer
            mux = create_gate('MUX')
            self.scene.addItem(mux)
            self.scene.gates.append(mux)
            self.created_gates.append(mux)

            # MUX inputs: I0 (false), I1 (true), S0 (cond)
            # In MuxGate: input_pins[0] is I0, input_pins[1] is I1, input_pins[2] is S0
            cond_pin = self._synthesize_expr_node(node.cond)
            true_pin = self._synthesize_expr_node(node.true_expr)
            false_pin = self._synthesize_expr_node(node.false_expr)

            if false_pin:
                w = Wire(false_pin, mux.input_pins[0])
                self.scene.addItem(w); self.scene.wires.append(w); self.created_wires.append(w)
            elif isinstance(node.false_expr, VarNode):
                self._register_sink(node.false_expr.name, mux.input_pins[0])

            if true_pin:
                w = Wire(true_pin, mux.input_pins[1])
                self.scene.addItem(w); self.scene.wires.append(w); self.created_wires.append(w)
            elif isinstance(node.true_expr, VarNode):
                self._register_sink(node.true_expr.name, mux.input_pins[1])

            if cond_pin and len(mux.input_pins) > 2:
                w = Wire(cond_pin, mux.input_pins[2])
                self.scene.addItem(w); self.scene.wires.append(w); self.created_wires.append(w)
            elif isinstance(node.cond, VarNode) and len(mux.input_pins) > 2:
                self._register_sink(node.cond.name, mux.input_pins[2])

            return mux.output_pins[0]

        return None

    def _route_all_nets(self):
        """Connect all registered sink input pins to their corresponding driver output pins."""
        for net_name, sinks in self.net_sinks.items():
            driver = self.net_drivers.get(net_name)
            if driver:
                for sink in sinks:
                    # Check if already wired
                    if not any(w.src_pin == driver and w.dst_pin == sink for w in self.scene.wires):
                        w = Wire(driver, sink)
                        self.scene.addItem(w)
                        self.scene.wires.append(w)
                        self.created_wires.append(w)

    def _auto_layout(self):
        """
        Organize canvas layout neatly:
        - Inputs & Clocks on Left Column (x = -360)
        - Logic Gates & Flip-Flops in Center Columns (x = -120 to +160)
        - Outputs on Right Column (x = +400)
        """
        inputs = [g for g in self.scene.gates if isinstance(g, (InputNode, ClockNode))]
        outputs = [g for g in self.scene.gates if isinstance(g, OutputNode)]
        middle = [g for g in self.scene.gates if g not in inputs and g not in outputs]

        # Layout Inputs (Left)
        dy = 85
        total_in_h = len(inputs) * dy
        y_start = -total_in_h / 2 + 40
        for i, g in enumerate(inputs):
            g.setPos(-360, y_start + i * dy)

        # Layout Outputs (Right)
        total_out_h = len(outputs) * dy
        y_start_out = -total_out_h / 2 + 40
        for i, g in enumerate(outputs):
            g.setPos(400, y_start_out + i * dy)

        # Layout Middle components (gates & flip-flops)
        # Arrange in 1-3 columns based on component count
        if middle:
            cols = 2 if len(middle) > 4 else 1
            col_x = [-140, 130] if cols == 2 else [0]
            per_col = (len(middle) + cols - 1) // cols
            m_dy = 110
            for idx, g in enumerate(middle):
                c = idx // per_col
                r = idx % per_col
                c = min(c, len(col_x) - 1)
                total_col_h = min(per_col, len(middle) - c * per_col) * m_dy
                y_c_start = -total_col_h / 2 + 40
                g.setPos(col_x[c], y_c_start + r * m_dy)

        # Update all wire curves
        for w in self.scene.wires:
            w.update_path()


# ───────────────────────────────────────────────────────────────────────
# Verilog Generator (Schematic -> Verilog Code)
# ───────────────────────────────────────────────────────────────────────
class VerilogGenerator:
    """
    Traverses canvas circuit graph and generates clean, formatted Verilog-2001 HDL code.
    Supports 4 modeling styles:
    - 'gate_level': Primitives and structural module instantiations
    - 'dataflow': Continuous assignments with boolean operators
    - 'behavioral': always @(*) procedural combinational blocks & always @(posedge clk) sequential blocks
    - 'switch_level': CMOS pmos/nmos transistor switch networks
    """

    def __init__(self, scene, module_name="circuit_top"):
        self.scene = scene
        self.module_name = sanitize_ident(module_name, "circuit_top")
        self.gates = list(scene.gates)
        self.wires = list(scene.wires)
        self._analyze_graph()

    def _analyze_graph(self):
        """Analyze circuit graph and assign unique, clean net names to every wire connection."""
        self.inputs = [g for g in self.gates if isinstance(g, (InputNode, ClockNode))]
        self.outputs = [g for g in self.gates if isinstance(g, OutputNode)]
        self.internal_gates = [g for g in self.gates if g not in self.inputs and g not in self.outputs]

        # Map each output pin to a clean net name
        self.pin_to_net = {}
        self.declared_wires = set()
        net_counter = 1

        # Port net names
        for inp in self.inputs:
            name = sanitize_ident(inp.label, f"in_{net_counter}")
            if inp.output_pins:
                self.pin_to_net[id(inp.output_pins[0])] = name

        for out in self.outputs:
            name = sanitize_ident(out.label, f"out_{net_counter}")
            if out.input_pins:
                # Driver net connected to this output
                pass

        # Internal gates and flip-flops
        for g in self.internal_gates:
            base_label = sanitize_ident(g.label, g.gate_type.lower())
            for idx, opin in enumerate(g.output_pins):
                pin_lbl = sanitize_ident(opin.label, "q" if idx == 0 else "q_bar")
                # Check if this output connects directly to an OutputNode
                driven_out_nodes = [w.dst_pin.parent_gate for w in opin.wires if isinstance(w.dst_pin.parent_gate, OutputNode)]
                if driven_out_nodes:
                    net_name = sanitize_ident(driven_out_nodes[0].label, f"out_{net_counter}")
                else:
                    net_name = f"net_{base_label}_{pin_lbl}_{net_counter}"
                    net_counter += 1
                self.pin_to_net[id(opin)] = net_name
                self.declared_wires.add(net_name)

    def _get_net_for_input_pin(self, pin):
        """Returns the driving net name for an input pin (or '1'b0' if unconnected)."""
        if pin.wires:
            src = pin.wires[0].src_pin
            return self.pin_to_net.get(id(src), "1'b0")
        return "1'b0"

    def generate(self, style="gate_level") -> str:
        """Main generator dispatcher. Returns complete formatted Verilog code."""
        style = style.lower().strip()
        if style in ('dataflow', 'data_flow'):
            return self._gen_dataflow()
        elif style in ('behavioral', 'behavior'):
            return self._gen_behavioral()
        elif style in ('switch_level', 'switch', 'transistor'):
            return self._gen_switch_level()
        else:
            return self._gen_gate_level()

    def _header(self, style_desc: str) -> list:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            f"// ============================================================================",
            f"// Verilog HDL: {self.module_name}",
            f"// Modeling Style: {style_desc}",
            f"// Generated by: Digital Logic Simulator & EDA Studio",
            f"// Timestamp: {now}",
            f"// ============================================================================",
            f"`timescale 1ns / 1ps",
            "",
            f"module {self.module_name} (",
        ]

        port_decls = []
        for inp in self.inputs:
            name = sanitize_ident(inp.label, "clk" if isinstance(inp, ClockNode) else "in")
            port_decls.append(f"    input  wire {name}")
        for out in self.outputs:
            name = sanitize_ident(out.label, "out")
            port_decls.append(f"    output wire {name}")

        lines.append(",\n".join(port_decls) if port_decls else "    // No ports connected")
        lines.append(");")
        lines.append("")

        # Internal wires
        in_names = {sanitize_ident(inp.label) for inp in self.inputs}
        out_names = {sanitize_ident(out.label) for out in self.outputs}
        internal_wires = sorted(list(self.declared_wires - in_names - out_names))
        if internal_wires:
            lines.append("    // Internal Nets")
            lines.append(f"    wire {', '.join(internal_wires)};")
            lines.append("")

        return lines

    # ───────────────────────────────────────────────────────────────────
    # Style 1: Gate-Level Modeling
    # ───────────────────────────────────────────────────────────────────
    def _gen_gate_level(self) -> str:
        lines = self._header("Gate-Level (Structural Primitives)")
        lines.append("    // ----------------------------------------------------")
        lines.append("    // Gate Primitives & Submodule Instantiations")
        lines.append("    // ----------------------------------------------------")

        gate_counts = {}
        ff_included = False

        for g in self.internal_gates:
            gt = g.gate_type
            inst_num = gate_counts.get(gt, 0) + 1
            gate_counts[gt] = inst_num
            inst_name = sanitize_ident(g.label) or f"{gt.lower()}_{inst_num}"

            # Primitives: AND, OR, NOT, NAND, NOR, XOR, XNOR, BUF
            if gt in ('AND', 'OR', 'NOT', 'NAND', 'NOR', 'XOR', 'XNOR', 'BUFFER'):
                prim_map = {
                    'AND': 'and', 'OR': 'or', 'NOT': 'not', 'NAND': 'nand',
                    'NOR': 'nor', 'XOR': 'xor', 'XNOR': 'xnor', 'BUFFER': 'buf'
                }
                prim = prim_map.get(gt, 'and')
                out_net = self.pin_to_net.get(id(g.output_pins[0]), "nc")
                in_nets = [self._get_net_for_input_pin(p) for p in g.input_pins]
                lines.append(f"    {prim:<6} {inst_name:<10} ({out_net}, {', '.join(in_nets)});")

            elif isinstance(g, DFlipFlop):
                ff_included = True
                q_net    = self.pin_to_net.get(id(g.output_pins[0]), "nc")
                qbar_net = self.pin_to_net.get(id(g.output_pins[1]), "nc") if len(g.output_pins) > 1 else "nc"
                d_net    = self._get_net_for_input_pin(g.input_pins[0])
                clk_net  = self._get_net_for_input_pin(g.input_pins[1])
                rst_net  = self._get_net_for_input_pin(g.input_pins[2])
                lines.append(f"    d_ff_cell {inst_name} (")
                lines.append(f"        .clk( {clk_net} ),")
                lines.append(f"        .d( {d_net} ),")
                lines.append(f"        .rst( {rst_net} ),")
                lines.append(f"        .q( {q_net} ),")
                lines.append(f"        .q_bar( {qbar_net} )")
                lines.append(f"    );")

            elif isinstance(g, JKFlipFlop):
                ff_included = True
                q_net    = self.pin_to_net.get(id(g.output_pins[0]), "nc")
                qbar_net = self.pin_to_net.get(id(g.output_pins[1]), "nc") if len(g.output_pins) > 1 else "nc"
                j_net    = self._get_net_for_input_pin(g.input_pins[0])
                clk_net  = self._get_net_for_input_pin(g.input_pins[1])
                k_net    = self._get_net_for_input_pin(g.input_pins[2])
                lines.append(f"    jk_ff_cell {inst_name} (")
                lines.append(f"        .clk( {clk_net} ),")
                lines.append(f"        .j( {j_net} ),")
                lines.append(f"        .k( {k_net} ),")
                lines.append(f"        .q( {q_net} ),")
                lines.append(f"        .q_bar( {qbar_net} )")
                lines.append(f"    );")

            elif isinstance(g, TFlipFlop):
                ff_included = True
                q_net    = self.pin_to_net.get(id(g.output_pins[0]), "nc")
                qbar_net = self.pin_to_net.get(id(g.output_pins[1]), "nc") if len(g.output_pins) > 1 else "nc"
                t_net    = self._get_net_for_input_pin(g.input_pins[0])
                clk_net  = self._get_net_for_input_pin(g.input_pins[1])
                lines.append(f"    t_ff_cell {inst_name} (")
                lines.append(f"        .clk( {clk_net} ),")
                lines.append(f"        .t( {t_net} ),")
                lines.append(f"        .q( {q_net} ),")
                lines.append(f"        .q_bar( {qbar_net} )")
                lines.append(f"    );")

            elif isinstance(g, SRFlipFlop):
                ff_included = True
                q_net    = self.pin_to_net.get(id(g.output_pins[0]), "nc")
                qbar_net = self.pin_to_net.get(id(g.output_pins[1]), "nc") if len(g.output_pins) > 1 else "nc"
                s_net    = self._get_net_for_input_pin(g.input_pins[0])
                clk_net  = self._get_net_for_input_pin(g.input_pins[1])
                r_net    = self._get_net_for_input_pin(g.input_pins[2])
                lines.append(f"    sr_ff_cell {inst_name} (")
                lines.append(f"        .clk( {clk_net} ),")
                lines.append(f"        .s( {s_net} ),")
                lines.append(f"        .r( {r_net} ),")
                lines.append(f"        .q( {q_net} ),")
                lines.append(f"        .q_bar( {qbar_net} )")
                lines.append(f"    );")

            elif gt == 'MUX':
                out_net = self.pin_to_net.get(id(g.output_pins[0]), "nc")
                n_data = getattr(g, 'n_data', 2)
                if n_data == 2:
                    i0 = self._get_net_for_input_pin(g.input_pins[0])
                    i1 = self._get_net_for_input_pin(g.input_pins[1])
                    s0 = self._get_net_for_input_pin(g.input_pins[2]) if len(g.input_pins) > 2 else "1'b0"
                    lines.append(f"    // 2:1 Multiplexer")
                    lines.append(f"    wire {inst_name}_not_s, {inst_name}_a0, {inst_name}_a1;")
                    lines.append(f"    not  ({inst_name}_not_s, {s0});")
                    lines.append(f"    and  ({inst_name}_a0, {i0}, {inst_name}_not_s);")
                    lines.append(f"    and  ({inst_name}_a1, {i1}, {s0});")
                    lines.append(f"    or   ({out_net}, {inst_name}_a0, {inst_name}_a1);")
                else:
                    n_sel = getattr(g, 'n_sel', 1)
                    sel_nets = [self._get_net_for_input_pin(g.input_pins[n_data + i]) if (n_data + i) < len(g.input_pins) else "1'b0" for i in range(n_sel)]
                    data_nets = [self._get_net_for_input_pin(g.input_pins[i]) for i in range(n_data)]
                    lines.append(f"    // {n_data}:1 Multiplexer")
                    sel_comb = "{" + ", ".join(reversed(sel_nets)) + "}"
                    ternary = data_nets[0]
                    for s_idx in range(1, n_data):
                        ternary = f"({sel_comb} == {s_idx}) ? {data_nets[s_idx]} : ({ternary})"
                    lines.append(f"    assign {out_net} = {ternary};")

        lines.append("")
        lines.append("endmodule")

        # Provide self-contained structural flip-flop modules if instantiated
        if ff_included:
            lines.extend(self._ff_module_definitions())

        return "\n".join(lines)

    # ───────────────────────────────────────────────────────────────────
    # Style 2: Dataflow Modeling (Assign Statements)
    # ───────────────────────────────────────────────────────────────────
    def _gen_dataflow(self) -> str:
        lines = self._header("Dataflow Modeling (Continuous Assignments)")
        lines.append("    // ----------------------------------------------------")
        lines.append("    // Continuous Assignments (Boolean Logic Expressions)")
        lines.append("    // ----------------------------------------------------")

        for g in self.internal_gates:
            gt = g.gate_type
            if gt in ('AND', 'OR', 'NOT', 'NAND', 'NOR', 'XOR', 'XNOR', 'BUFFER'):
                out_net = self.pin_to_net.get(id(g.output_pins[0]), "nc")
                in_nets = [self._get_net_for_input_pin(p) for p in g.input_pins]

                if gt == 'AND':    expr = " & ".join(in_nets)
                elif gt == 'OR':   expr = " | ".join(in_nets)
                elif gt == 'NOT':  expr = f"~{in_nets[0]}"
                elif gt == 'NAND': expr = f"~({' & '.join(in_nets)})"
                elif gt == 'NOR':  expr = f"~({' | '.join(in_nets)})"
                elif gt == 'XOR':  expr = " ^ ".join(in_nets)
                elif gt == 'XNOR': expr = f"~({' ^ '.join(in_nets)})"
                elif gt == 'BUFFER': expr = in_nets[0]
                else: expr = "1'b0"

                lines.append(f"    assign {out_net} = {expr};")

            elif gt == 'MUX':
                out_net = self.pin_to_net.get(id(g.output_pins[0]), "nc")
                n_data = getattr(g, 'n_data', 2)
                if n_data == 2:
                    i0 = self._get_net_for_input_pin(g.input_pins[0])
                    i1 = self._get_net_for_input_pin(g.input_pins[1])
                    s0 = self._get_net_for_input_pin(g.input_pins[2]) if len(g.input_pins) > 2 else "1'b0"
                    lines.append(f"    assign {out_net} = ({s0}) ? ({i1}) : ({i0});")
                else:
                    n_sel = getattr(g, 'n_sel', 1)
                    sel_nets = [self._get_net_for_input_pin(g.input_pins[n_data + i]) if (n_data + i) < len(g.input_pins) else "1'b0" for i in range(n_sel)]
                    data_nets = [self._get_net_for_input_pin(g.input_pins[i]) for i in range(n_data)]
                    sel_comb = "{" + ", ".join(reversed(sel_nets)) + "}"
                    ternary = data_nets[0]
                    for s_idx in range(1, n_data):
                        ternary = f"({sel_comb} == {s_idx}) ? ({data_nets[s_idx]}) : ({ternary})"
                    lines.append(f"    assign {out_net} = {ternary};")

            elif isinstance(g, FlipFlopBase):
                # Sequential component in dataflow module instantiated as standard cell
                q_net    = self.pin_to_net.get(id(g.output_pins[0]), "nc")
                qbar_net = self.pin_to_net.get(id(g.output_pins[1]), "nc") if len(g.output_pins) > 1 else "nc"
                clk_net  = self._get_net_for_input_pin(g.input_pins[g.clk_pin_idx])
                d_net    = self._get_net_for_input_pin(g.input_pins[0])
                lines.append(f"    // Sequential register {g.label}")
                lines.append(f"    d_ff_cell {sanitize_ident(g.label)} (.clk({clk_net}), .d({d_net}), .rst(1'b0), .q({q_net}), .q_bar({qbar_net}));")

        lines.append("")
        lines.append("endmodule")
        if any(isinstance(g, FlipFlopBase) for g in self.internal_gates):
            lines.extend(self._ff_module_definitions())
        return "\n".join(lines)

    # ───────────────────────────────────────────────────────────────────
    # Style 3: Behavioral Modeling (always @(*) and always @(posedge clk))
    # ───────────────────────────────────────────────────────────────────
    def _gen_behavioral(self) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            f"// ============================================================================",
            f"// Verilog HDL: {self.module_name}",
            f"// Modeling Style: Behavioral Modeling (Procedural Blocks)",
            f"// Generated by: Digital Logic Simulator & EDA Studio",
            f"// Timestamp: {now}",
            f"// ============================================================================",
            f"`timescale 1ns / 1ps",
            "",
            f"module {self.module_name} (",
        ]

        port_decls = []
        for inp in self.inputs:
            name = sanitize_ident(inp.label, "in")
            port_decls.append(f"    input  wire {name}")
        for out in self.outputs:
            name = sanitize_ident(out.label, "out")
            port_decls.append(f"    output reg  {name}")

        lines.append(",\n".join(port_decls) if port_decls else "    // No ports connected")
        lines.append(");")
        lines.append("")

        # Internal regs
        in_names = {sanitize_ident(inp.label) for inp in self.inputs}
        out_names = {sanitize_ident(out.label) for out in self.outputs}
        internal_regs = sorted(list(self.declared_wires - in_names - out_names))
        if internal_regs:
            lines.append("    // Internal Registers")
            lines.append(f"    reg {', '.join(internal_regs)};")
            lines.append("")

        # Combinational procedural block
        comb_gates = [g for g in self.internal_gates if not isinstance(g, FlipFlopBase)]
        if comb_gates:
            lines.append("    // ----------------------------------------------------")
            lines.append("    // Combinational Logic Block")
            lines.append("    // ----------------------------------------------------")
            lines.append("    always @(*) begin")
            for g in comb_gates:
                gt = g.gate_type
                out_net = self.pin_to_net.get(id(g.output_pins[0]), "nc")
                in_nets = [self._get_net_for_input_pin(p) for p in g.input_pins]

                if gt == 'AND':    expr = " & ".join(in_nets)
                elif gt == 'OR':   expr = " | ".join(in_nets)
                elif gt == 'NOT':  expr = f"~{in_nets[0]}"
                elif gt == 'NAND': expr = f"~({' & '.join(in_nets)})"
                elif gt == 'NOR':  expr = f"~({' | '.join(in_nets)})"
                elif gt == 'XOR':  expr = " ^ ".join(in_nets)
                elif gt == 'XNOR': expr = f"~({' ^ '.join(in_nets)})"
                elif gt == 'BUFFER': expr = in_nets[0]
                elif gt == 'MUX':
                    n_data = getattr(g, 'n_data', 2)
                    if n_data == 2:
                        s0 = self._get_net_for_input_pin(g.input_pins[2]) if len(g.input_pins) > 2 else "1'b0"
                        expr = f"({s0}) ? ({in_nets[1]}) : ({in_nets[0]})"
                    else:
                        n_sel = getattr(g, 'n_sel', 1)
                        sel_nets = [self._get_net_for_input_pin(g.input_pins[n_data + i]) if (n_data + i) < len(g.input_pins) else "1'b0" for i in range(n_sel)]
                        sel_comb = "{" + ", ".join(reversed(sel_nets)) + "}"
                        expr = in_nets[0]
                        for s_idx in range(1, n_data):
                            expr = f"({sel_comb} == {s_idx}) ? ({in_nets[s_idx]}) : ({expr})"
                else: expr = "1'b0"

                lines.append(f"        {out_net} = {expr};")
            lines.append("    end")
            lines.append("")

        # Sequential procedural blocks
        seq_gates = [g for g in self.internal_gates if isinstance(g, FlipFlopBase)]
        for ff in seq_gates:
            clk_net = self._get_net_for_input_pin(ff.input_pins[ff.clk_pin_idx])
            q_net   = self.pin_to_net.get(id(ff.output_pins[0]), "nc")
            qbar_net = self.pin_to_net.get(id(ff.output_pins[1]), "nc") if len(ff.output_pins) > 1 else None

            edge_kw = "posedge" if ff.trigger_edge == 'posedge' else "negedge"

            if isinstance(ff, DFlipFlop):
                d_net   = self._get_net_for_input_pin(ff.input_pins[0])
                rst_net = self._get_net_for_input_pin(ff.input_pins[2])
                lines.append(f"    // D Flip-Flop: {ff.label}")
                lines.append(f"    always @({edge_kw} {clk_net} or posedge {rst_net}) begin")
                lines.append(f"        if ({rst_net}) begin")
                lines.append(f"            {q_net} <= 1'b0;")
                if qbar_net: lines.append(f"            {qbar_net} <= 1'b1;")
                lines.append(f"        end else begin")
                lines.append(f"            {q_net} <= {d_net};")
                if qbar_net: lines.append(f"            {qbar_net} <= ~({d_net});")
                lines.append(f"        end")
                lines.append(f"    end")
                lines.append("")

            elif isinstance(ff, JKFlipFlop):
                j_net = self._get_net_for_input_pin(ff.input_pins[0])
                k_net = self._get_net_for_input_pin(ff.input_pins[2])
                lines.append(f"    // JK Flip-Flop: {ff.label}")
                lines.append(f"    always @({edge_kw} {clk_net}) begin")
                lines.append(f"        case ({{ {j_net}, {k_net} }})")
                lines.append(f"            2'b00: {q_net} <= {q_net};")
                lines.append(f"            2'b01: {q_net} <= 1'b0;")
                lines.append(f"            2'b10: {q_net} <= 1'b1;")
                lines.append(f"            2'b11: {q_net} <= ~{q_net};")
                lines.append(f"        endcase")
                if qbar_net: lines.append(f"        {qbar_net} <= ~{q_net};")
                lines.append(f"    end")
                lines.append("")

            elif isinstance(ff, TFlipFlop):
                t_net = self._get_net_for_input_pin(ff.input_pins[0])
                lines.append(f"    // T Flip-Flop: {ff.label}")
                lines.append(f"    always @({edge_kw} {clk_net}) begin")
                lines.append(f"        if ({t_net}) begin")
                lines.append(f"            {q_net} <= ~{q_net};")
                if qbar_net: lines.append(f"            {qbar_net} <= {q_net};")
                lines.append(f"        end")
                lines.append(f"    end")
                lines.append("")

        lines.append("endmodule")
        return "\n".join(lines)

    # ───────────────────────────────────────────────────────────────────
    # Style 4: Switch-Level Modeling (CMOS Transistors)
    # ───────────────────────────────────────────────────────────────────
    def _gen_switch_level(self) -> str:
        lines = self._header("Switch-Level Modeling (CMOS Transistors)")
        lines.append("    // ----------------------------------------------------")
        lines.append("    // Power Rails")
        lines.append("    // ----------------------------------------------------")
        lines.append("    supply1 vdd;  // Logic 1 power rail")
        lines.append("    supply0 gnd;  // Logic 0 ground rail")
        lines.append("")

        inst_count = 1
        for g in self.internal_gates:
            gt = g.gate_type
            inst_label = sanitize_ident(g.label) or f"gate_{inst_count}"
            inst_count += 1

            if gt == 'NOT':
                out = self.pin_to_net.get(id(g.output_pins[0]), "nc")
                inp = self._get_net_for_input_pin(g.input_pins[0])
                lines.append(f"    // CMOS Inverter: {inst_label}")
                lines.append(f"    pmos p_{inst_label} ({out}, vdd, {inp});")
                lines.append(f"    nmos n_{inst_label} ({out}, gnd, {inp});")
                lines.append("")

            elif gt == 'NAND':
                out = self.pin_to_net.get(id(g.output_pins[0]), "nc")
                a = self._get_net_for_input_pin(g.input_pins[0])
                b = self._get_net_for_input_pin(g.input_pins[1])
                mid = f"mid_{inst_label}"
                lines.append(f"    // CMOS 2-input NAND: {inst_label}")
                lines.append(f"    wire {mid};")
                lines.append(f"    pmos p1_{inst_label} ({out}, vdd, {a});")
                lines.append(f"    pmos p2_{inst_label} ({out}, vdd, {b});")
                lines.append(f"    nmos n1_{inst_label} ({out}, {mid}, {a});")
                lines.append(f"    nmos n2_{inst_label} ({mid}, gnd, {b});")
                lines.append("")

            elif gt == 'NOR':
                out = self.pin_to_net.get(id(g.output_pins[0]), "nc")
                a = self._get_net_for_input_pin(g.input_pins[0])
                b = self._get_net_for_input_pin(g.input_pins[1])
                mid = f"mid_{inst_label}"
                lines.append(f"    // CMOS 2-input NOR: {inst_label}")
                lines.append(f"    wire {mid};")
                lines.append(f"    pmos p1_{inst_label} ({mid}, vdd, {a});")
                lines.append(f"    pmos p2_{inst_label} ({out}, {mid}, {b});")
                lines.append(f"    nmos n1_{inst_label} ({out}, gnd, {a});")
                lines.append(f"    nmos n2_{inst_label} ({out}, gnd, {b});")
                lines.append("")

            elif gt == 'AND':
                out = self.pin_to_net.get(id(g.output_pins[0]), "nc")
                a = self._get_net_for_input_pin(g.input_pins[0])
                b = self._get_net_for_input_pin(g.input_pins[1])
                nand_out = f"nand_out_{inst_label}"
                mid = f"mid_{inst_label}"
                lines.append(f"    // CMOS AND (NAND + Inverter): {inst_label}")
                lines.append(f"    wire {nand_out}, {mid};")
                lines.append(f"    pmos p1_{inst_label} ({nand_out}, vdd, {a});")
                lines.append(f"    pmos p2_{inst_label} ({nand_out}, vdd, {b});")
                lines.append(f"    nmos n1_{inst_label} ({nand_out}, {mid}, {a});")
                lines.append(f"    nmos n2_{inst_label} ({mid}, gnd, {b});")
                lines.append(f"    pmos p_inv_{inst_label} ({out}, vdd, {nand_out});")
                lines.append(f"    nmos n_inv_{inst_label} ({out}, gnd, {nand_out});")
                lines.append("")

            elif gt == 'OR':
                out = self.pin_to_net.get(id(g.output_pins[0]), "nc")
                a = self._get_net_for_input_pin(g.input_pins[0])
                b = self._get_net_for_input_pin(g.input_pins[1])
                nor_out = f"nor_out_{inst_label}"
                mid = f"mid_{inst_label}"
                lines.append(f"    // CMOS OR (NOR + Inverter): {inst_label}")
                lines.append(f"    wire {nor_out}, {mid};")
                lines.append(f"    pmos p1_{inst_label} ({mid}, vdd, {a});")
                lines.append(f"    pmos p2_{inst_label} ({nor_out}, {mid}, {b});")
                lines.append(f"    nmos n1_{inst_label} ({nor_out}, gnd, {a});")
                lines.append(f"    nmos n2_{inst_label} ({nor_out}, gnd, {b});")
                lines.append(f"    pmos p_inv_{inst_label} ({out}, vdd, {nor_out});")
                lines.append(f"    nmos n_inv_{inst_label} ({out}, gnd, {nor_out});")
                lines.append("")

            elif gt == 'XOR':
                out = self.pin_to_net.get(id(g.output_pins[0]), "nc")
                a = self._get_net_for_input_pin(g.input_pins[0])
                b = self._get_net_for_input_pin(g.input_pins[1])
                lines.append(f"    // CMOS Transmission-Gate XOR: {inst_label}")
                lines.append(f"    wire not_a_{inst_label}, not_b_{inst_label};")
                lines.append(f"    pmos p_ia_{inst_label} (not_a_{inst_label}, vdd, {a});")
                lines.append(f"    nmos n_ia_{inst_label} (not_a_{inst_label}, gnd, {a});")
                lines.append(f"    pmos p_ib_{inst_label} (not_b_{inst_label}, vdd, {b});")
                lines.append(f"    nmos n_ib_{inst_label} (not_b_{inst_label}, gnd, {b});")
                lines.append(f"    cmos c1_{inst_label} ({out}, {b}, not_a_{inst_label}, {a});")
                lines.append(f"    cmos c2_{inst_label} ({out}, not_b_{inst_label}, {a}, not_a_{inst_label});")
                lines.append("")

            elif isinstance(g, FlipFlopBase):
                # Switch-level structural instantiation
                q_net    = self.pin_to_net.get(id(g.output_pins[0]), "nc")
                qbar_net = self.pin_to_net.get(id(g.output_pins[1]), "nc") if len(g.output_pins) > 1 else "nc"
                clk_net  = self._get_net_for_input_pin(g.input_pins[g.clk_pin_idx])
                d_net    = self._get_net_for_input_pin(g.input_pins[0])
                lines.append(f"    // D Flip-Flop Transmission Gate Cell")
                lines.append(f"    d_ff_cell {inst_label} (.clk({clk_net}), .d({d_net}), .rst(1'b0), .q({q_net}), .q_bar({qbar_net}));")
                lines.append("")

        lines.append("endmodule")
        if any(isinstance(g, FlipFlopBase) for g in self.internal_gates):
            lines.extend(self._ff_module_definitions())
        return "\n".join(lines)

    def _ff_module_definitions(self) -> list:
        return [
            "",
            "// ============================================================================",
            "// Standard Flip-Flop Behavioral Cell Models (for Simulation & Synthesis)",
            "// ============================================================================",
            "module d_ff_cell (",
            "    input  wire clk,",
            "    input  wire d,",
            "    input  wire rst,",
            "    output reg  q,",
            "    output wire q_bar",
            ");",
            "    assign q_bar = ~q;",
            "    always @(posedge clk or posedge rst) begin",
            "        if (rst)",
            "            q <= 1'b0;",
            "        else",
            "            q <= d;",
            "    end",
            "endmodule",
            "",
            "module jk_ff_cell (",
            "    input  wire clk,",
            "    input  wire j,",
            "    input  wire k,",
            "    output reg  q,",
            "    output wire q_bar",
            ");",
            "    assign q_bar = ~q;",
            "    always @(posedge clk) begin",
            "        case ({j, k})",
            "            2'b00: q <= q;",
            "            2'b01: q <= 1'b0;",
            "            2'b10: q <= 1'b1;",
            "            2'b11: q <= ~q;",
            "        endcase",
            "    end",
            "endmodule",
            "",
            "module t_ff_cell (",
            "    input  wire clk,",
            "    input  wire t,",
            "    output reg  q,",
            "    output wire q_bar",
            ");",
            "    assign q_bar = ~q;",
            "    always @(posedge clk) begin",
            "        if (t)",
            "            q <= ~q;",
            "    end",
            "endmodule",
            "",
            "module sr_ff_cell (",
            "    input  wire clk,",
            "    input  wire s,",
            "    input  wire r,",
            "    output reg  q,",
            "    output wire q_bar",
            ");",
            "    assign q_bar = ~q;",
            "    always @(posedge clk) begin",
            "        if (s && !r)      q <= 1'b1;",
            "        else if (!s && r) q <= 1'b0;",
            "    end",
            "endmodule",
        ]
