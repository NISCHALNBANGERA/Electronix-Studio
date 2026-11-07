"""
simulation.py - Sequential & Combinational Logic Simulation Engine
Supports:
- Multi-pass relaxation loop to handle feedback loops and sequential state propagation
  without recursion errors or UI freezes.
- Clock edge detection support and post-cycle clock commitment.
- Safe boolean expression generation with cycle detection.
- Truth table and waveform support for both combinational and sequential circuits.
"""
from gate import InputNode, OutputNode
from sequential_gates import ClockNode, FlipFlopBase


class SimulationEngine:
    def __init__(self, gates, wires):
        self.gates = gates
        self.wires = wires

    def run(self, max_iterations=32):
        """
        Execute simulation pass with feedback loop relaxation and edge synchronization.
        Iterates until outputs converge or max_iterations is reached.
        """
        # Step 1: Ensure initial wire values are synchronized
        self._sync_all_wires()

        # Step 2: Determine gate evaluation order (topological with fallback)
        order = self._topological_sort()

        # Step 3: Relaxation loop — propagate signals through combinational and feedback paths
        for _ in range(max_iterations):
            changed = False
            for gate in order:
                old_outputs = [p.value for p in gate.output_pins]
                gate.evaluate()

                # Propagate output changes through connected wires immediately
                for pin in gate.output_pins:
                    for wire in pin.wires:
                        if wire.dst_pin.value != pin.value:
                            wire.update_value(pin.value)

                new_outputs = [p.value for p in gate.output_pins]
                if old_outputs != new_outputs:
                    changed = True

            if not changed:
                break

        # Step 4: Synchronize flip-flop internal clock states after the evaluation step
        for gate in self.gates:
            if hasattr(gate, 'commit_clock'):
                gate.commit_clock()

    def _sync_all_wires(self):
        for wire in self.wires:
            wire.update_value(wire.src_pin.value)

    def _topological_sort(self):
        in_degree = {id(g): 0 for g in self.gates}
        deps = {id(g): [] for g in self.gates}

        for wire in self.wires:
            sg = wire.src_pin.parent_gate
            dg = wire.dst_pin.parent_gate
            in_degree[id(dg)] = in_degree.get(id(dg), 0) + 1
            deps[id(dg)].append(sg)

        queue = [g for g in self.gates if in_degree[id(g)] == 0]
        result = []

        while queue:
            gate = queue.pop(0)
            result.append(gate)
            for other in self.gates:
                if gate in deps[id(other)]:
                    in_degree[id(other)] -= 1
                    if in_degree[id(other)] == 0:
                        queue.append(other)

        # Append any gates involved in feedback cycles that weren't popped
        visited = set(id(g) for g in result)
        for g in self.gates:
            if id(g) not in visited:
                result.append(g)

        return result

    def get_input_nodes(self):
        return [g for g in self.gates if isinstance(g, (InputNode, ClockNode))]

    def get_output_nodes(self):
        return [g for g in self.gates if isinstance(g, OutputNode)]

    def get_clock_nodes(self):
        return [g for g in self.gates if isinstance(g, ClockNode) or g.gate_type == 'CLOCK']

    def get_flip_flops(self):
        return [g for g in self.gates if isinstance(g, FlipFlopBase)]

    def generate_truth_table(self):
        inputs  = self.get_input_nodes()
        outputs = self.get_output_nodes()
        if not inputs or not outputs:
            return [], [], []

        n = len(inputs)
        rows = []
        for combo in range(2**n):
            for i, inp in enumerate(inputs):
                inp._value = (combo >> (n - 1 - i)) & 1
                inp.evaluate()
            self.run()
            rows.append([inp._value for inp in inputs] + [out.evaluate() for out in outputs])
        return [g.label for g in inputs], [g.label for g in outputs], rows

    def generate_boolean_expression(self):
        outputs = self.get_output_nodes()
        if not outputs:
            return {}

        expressions = {}
        visited_pins = set()

        def expr_for_pin(pin):
            if id(pin) in visited_pins:
                # Cycle detected: return pin's gate label or state reference
                gate = pin.parent_gate
                return f"{gate.label}_{pin.label or 'FB'}"

            visited_pins.add(id(pin))
            gate = pin.parent_gate

            if isinstance(gate, InputNode) or isinstance(gate, ClockNode):
                visited_pins.remove(id(pin))
                return gate.label

            if isinstance(gate, FlipFlopBase):
                visited_pins.remove(id(pin))
                out_name = pin.label or ("Q" if pin.index == 0 else "Q_bar")
                return f"{gate.label}.{out_name}"

            in_exprs = []
            for ip in gate.input_pins:
                driver = next((w.src_pin for w in ip.wires), None)
                in_exprs.append(expr_for_pin(driver) if driver else "0")

            visited_pins.remove(id(pin))
            gt = gate.gate_type

            if not in_exprs:
                return "0"
            if gt == 'AND':    return "(" + (" AND ".join(in_exprs)) + ")"
            if gt == 'OR':     return "(" + (" OR ".join(in_exprs)) + ")"
            if gt == 'NOT':    return f"NOT({in_exprs[0]})"
            if gt == 'NAND':   return f"NAND({', '.join(in_exprs)})"
            if gt == 'NOR':    return f"NOR({', '.join(in_exprs)})"
            if gt == 'XOR':    return "(" + (" XOR ".join(in_exprs)) + ")"
            if gt == 'XNOR':   return "(" + (" XNOR ".join(in_exprs)) + ")"
            if gt == 'BUFFER': return in_exprs[0]
            if gt == 'MUX':    return f"MUX({', '.join(in_exprs)})"
            return f"{gt}({', '.join(in_exprs)})"

        for out in outputs:
            if out.input_pins:
                driver = next((w.src_pin for w in out.input_pins[0].wires), None)
                expressions[out.label] = expr_for_pin(driver) if driver else "NC"
            else:
                expressions[out.label] = "NC"

        return expressions
