"""Parse the definition file and build the logic network.

Used in the Logic Simulator project to analyse the syntactic and semantic
correctness of the symbols received from the scanner and then builds the
logic network.

Classes
-------
Parser - parses the definition file and builds the logic network.
"""

import uuid

from devices import Devices
from names import Names
from scanner import Scanner, Symbol


class Parser:
    """Parse the definition file and build the logic network.

    The parser deals with error handling. It analyses the syntactic and
    semantic correctness of the symbols it receives from the scanner, and
    then builds the logic network. If there are errors in the definition file,
    the parser detects this and tries to recover from it, giving helpful
    error messages.

    Parameters
    ----------
    names: instance of the names.Names() class.
    devices: instance of the devices.Devices() class.
    network: instance of the network.Network() class.
    monitors: instance of the monitors.Monitors() class.
    scanner: instance of the scanner.Scanner() class.

    Public methods
    --------------
    parse_network(self): Parses the circuit definition file.
    """

    def __init__(self, names, devices, network, monitors, scanner):
        """Initialise constants."""

        self.names = names
        self.devices = devices
        self.network = network
        self.monitors = monitors
        self.scanner = scanner
        self.symbol = None
        self.error_count = 0
        self.current_module_name = None

        # dict of module names: [[inputs],[outputs]]
        self.module_mappings = {}

        # dict of gate:count
        self.gate_counts = {}

    def generate_symbols(self):
        """Deprecated."""
        symbols = []
        current_symbol = self.scanner.get_symbol()
        while current_symbol.type != Symbol.EOF:
            symbols.append(current_symbol)
            current_symbol = self.scanner.get_symbol()
        return symbols

    def next_symbol(self):
        self.symbol = self.scanner.get_symbol()

    def accept(self, symbol_type, text: str | None = None):
        if self.symbol.type == symbol_type:
            if text is None or self.symbol.text == text:
                self.next_symbol()
                return True
        return False

    def expect(self, symbol_type, text=None):
        if self.accept(symbol_type, text):
            return True

        expected = (
            text
            if text
            else (
                "NAME"
                if symbol_type == Symbol.NAME
                else "NUMBER" if symbol_type == Symbol.NUMBER else "EOF"
            )
        )
        print(
            f"Syntax Error at line {self.symbol.line}, pos {self.symbol.pos}: Expected {expected}, got '{self.symbol.text}'"
        )
        self.error_count += 1
        return False

    def parse_network(self):
        self.next_symbol()
        self.parse_program()
        return self.error_count == 0

    def parse_program(self):
        self.parse_prog_defn()
        while self.symbol.type != Symbol.EOF:
            self.parse_prog_defn()

    def parse_prog_defn(self):
        self.expect(Symbol.KEYWORD, "module")

        if self.symbol.type == Symbol.NAME:
            self.current_module_name = self.symbol.text
            self.next_symbol()
        else:
            # error handling
            self.expect(Symbol.NAME)

        self.expect(Symbol.PUNCTUATION, ":")

        module_inputs = self.parse_port_list()
        self.expect(Symbol.PUNCTUATION, "->")
        module_outputs = self.parse_port_list()

        self.module_mappings[self.current_module_name] = [
            [module_inputs],
            [module_outputs],
        ]

        self.expect(Symbol.PUNCTUATION, ";")

        while not (self.symbol.type == Symbol.KEYWORD and self.symbol.text == "end"):
            if self.symbol.type == Symbol.EOF:
                print("Syntax Error: unexpected End of File (EOF)")
                self.error_count += 1
                break
            self.parse_statement()

        self.expect(Symbol.KEYWORD, "end")
        self.expect(Symbol.PUNCTUATION, ";")

    def parse_port_list(self):
        ports = []
        if self.symbol.type == Symbol.NAME:
            ports.append(self.parse_port())
            while self.accept(Symbol.PUNCTUATION, ","):
                ports.append(self.parse_port())

    def parse_port(self):
        self.expect(Symbol.NAME)

        if self.symbol.type == Symbol.NAME:
            port_name = f"__{self.symbol.text}__{self.current_module_name}__"
            self.next_symbol()
            return port_name
        else:
            self.expect(Symbol.NAME)

        # marked for removal pending bit slicing decision
        if self.accept(Symbol.PUNCTUATION, "["):
            self.expect(Symbol.NUMBER)
            self.expect(Symbol.PUNCTUATION, "]")

    def parse_statement(self):
        if self.symbol.type == Symbol.KEYWORD:
            if self.symbol.text in ["wire", "clock", "switch", "dtype"]:
                self.parse_declaration()
            elif self.symbol.text == "monitor":
                self.parse_monitor()
            else:
                print(
                    f"Syntax Error: unexpected keyword '{self.symbol.text}' in statement"
                )
                self.error_count += 1
                self.next_symbol()
        elif self.symbol.type == Symbol.NAME:
            if self.symbol.text == "instance":
                self.parse_instance()
            else:
                self.parse_assignment()
        else:
            print(
                f"Syntax Error: invalid statement starting with '{self.symbol.text}' at {self.scanner.line_count},{self.scanner.line_position}"
            )
            self.error_count += 1
            self.next_symbol()

    def parse_declaration(self):
        if self.accept(Symbol.KEYWORD, "wire"):
            if self.symbol.type == Symbol.NAME:
                wire_name = f"__{self.symbol.text}__{self.current_module_name}__"
                [wire_id] = self.names.lookup([wire_name])
                self.next_symbol()

                self.devices.make_device(wire_id, self.devices.AND, 1)
            else:
                self.expect(Symbol.NAME)
                return

            if self.accept(Symbol.PUNCTUATION, "["):
                self.expect(Symbol.NUMBER)
                self.expect(Symbol.PUNCTUATION, "]")
            self.expect(Symbol.PUNCTUATION, ";")

        elif self.accept(Symbol.KEYWORD, "clock"):
            if self.symbol.type == Symbol.NAME:
                clock_name = f"__{self.symbol.text}__{self.current_module_name}__"
                [clock_id] = self.names.lookup([clock_name])
                self.next_symbol()
            else:
                self.expect(Symbol.NAME)
                return

            self.expect(Symbol.PUNCTUATION, "[")

            if self.symbol.type == Symbol.NUMBER:
                period = int(self.symbol.text)
                self.next_symbol()
            else:
                self.expect(Symbol.NUMBER)
                return

            self.expect(Symbol.PUNCTUATION, "]")
            self.expect(Symbol.PUNCTUATION, ";")

            # Make clock
            self.devices.make_device(clock_id, self.devices.CLOCK, period)

        elif self.accept(Symbol.KEYWORD, "switch"):
            if self.symbol.type == Symbol.NAME:
                switch_name = f"__{self.symbol.text}__{self.current_module_name}__"
                [switch_id] = self.names.lookup([switch_name])
                self.next_symbol()
            else:
                self.expect(Symbol.NAME)
                return

            self.expect(Symbol.PUNCTUATION, "=")

            if self.symbol.type == Symbol.NUMBER and self.symbol.text in ["0", "1"]:
                # Valid, add device
                state = int(self.symbol.text)
                self.devices.make_device(switch_id, self.devices.SWITCH, state)
                self.next_symbol()
            else:
                print("Syntax Error: Expected 0 or 1 for switch state")
                self.error_count += 1

            self.expect(Symbol.PUNCTUATION, ";")

        elif self.accept(Symbol.KEYWORD, "dtype"):
            if self.symbol.type == Symbol.NAME:
                dtype_name = f"__{self.symbol.text}__{self.current_module_name}__"
                [dtype_id] = self.names.lookup([dtype_name])
                self.next_symbol()
            else:
                self.expect(Symbol.NAME)
                return

            self.expect(Symbol.PUNCTUATION, ";")
            self.devices.make_device(dtype_id, self.devices.D_TYPE)

    def parse_assignment(self):
        """Parse an assignment and connect the RHS to the LHS."""
        target_device_id, target_port_id = self.parse_lhs()

        if not (
            self.accept(Symbol.PUNCTUATION, "=")
            or self.accept(Symbol.PUNCTUATION, "<=")
        ):
            print(f"Syntax Error: Expected '=' or '<=', got {self.symbol.text}")
            self.error_count += 1

        source_device_id, source_port_id = self.parse_rhs()
        self.expect(Symbol.PUNCTUATION, ";")

        # If assigning to a standalone variable (e.g., A = ... rather than D1.DATA = ...)
        if target_port_id is None:
            # If this variable hasn't been instantiated yet, make it a buffer (1-input AND gate)
            if self.devices.get_device(target_device_id) is None:
                self.devices.make_device(target_device_id, self.devices.AND, 1)

            # Wires and buffers receive their input on port 'I1'
            [target_port_id] = self.names.lookup(["I1"])

        # Wire the calculated right-hand expression to the target on the left
        error = self.network.make_connection(
            source_device_id, source_port_id, target_device_id, target_port_id
        )
        if error != self.network.NO_ERROR:
            print(f"Semantic Error: Failed to connect. Error code: {error}")
            self.error_count += 1

    def parse_lhs(self):
        return self.parse_signal_or_port_ref()

    def parse_rhs(self):
        return self.parse_or_expr()

    def _parse_gate(self, gate_type):
        gates = {
            "OR": [self.parse_and_expr, "+", self.devices.OR],
            "AND": [self.parse_xor_expr, "*", self.devices.AND],
            "XOR": [self.parse_factor, "^", self.devices.XOR],
        }
        inputs = [gates[gate_type][0]()]
        while self.accept(Symbol.PUNCTUATION, gates[gate_type][1]):
            inputs.append(gates[gate_type][0]())

        if len(inputs) == 1:
            return inputs[0]

        # current count of gate type
        if self.gate_counts.get(gate_type) is None:
            self.gate_counts[gate_type] = 0
        self.gate_counts[gate_type] += 1

        gate_name = f"__{gate_type} {self.gate_counts[gate_type]}__{self.current_module_name}__{uuid.uuid4().hex}"
        [gate_id] = self.names.lookup([gate_name])

        if gate_type == "XOR" and len(inputs) == 2:
            # XOR gates need 2 inputs
            # -------------------------------------------------------------------------------------
            # display this error to the user in a nice format
            self.devices.make_device(gate_id, gates[gate_type][2], None)
        else:
            self.devices.make_device(gate_id, gates[gate_type][2], len(inputs))

        for i, (src_dev, src_port) in enumerate(inputs, start=1):
            [input_port_id] = self.names.lookup([f"I{i}"])
            self.network.make_connection(src_dev, src_port, gate_id, input_port_id)

        return (gate_id, None)

    def parse_or_expr(self):
        return self._parse_gate("OR")

    def parse_and_expr(self):
        return self._parse_gate("AND")

    def parse_xor_expr(self):
        return self._parse_gate("XOR")

    def parse_factor(self):
        """Parse factors, handling NOT operators and brackets natively."""
        invert = self.accept(Symbol.PUNCTUATION, "!")

        if self.accept(Symbol.PUNCTUATION, "("):
            # This recursion natively handles innermost brackets exactly like your script!
            signal = self.parse_or_expr()
            self.expect(Symbol.PUNCTUATION, ")")
        else:
            signal = self.parse_signal_or_port_ref()

        # If there's a NOT operator (!), instantiate a 1-input NAND gate as an inverter
        if invert:
            gate_name = f"__NOT__{self.current_module_name}__{uuid.uuid4().hex}"
            [gate_id] = self.names.lookup([gate_name])

            # A 1-input NAND functions as a NOT gate in this architecture
            self.devices.make_device(gate_id, self.devices.NAND, 1)
            [input_port_id] = self.names.lookup(["I1"])

            self.network.make_connection(signal[0], signal[1], gate_id, input_port_id)
            return (gate_id, None)

        return signal

    def parse_signal_or_port_ref(self):
        """Parse a reference to a device or a specific port[cite: 20]."""
        # Capture the device name
        name = f"__{self.symbol.text}__{self.current_module_name}__"
        [device_id] = self.names.lookup([name])
        self.expect(Symbol.NAME)

        port_id = None
        # Check if a specific port is referenced (e.g., DTYPE.Q)
        if self.accept(Symbol.PUNCTUATION, "."):
            valid_ports = ["CLK", "DATA", "SET", "CLEAR", "Q", "QBAR"]
            if self.symbol.type == Symbol.NAME and self.symbol.text in valid_ports:
                port_name = self.symbol.text
                [port_id] = self.names.lookup([port_name])
                self.next_symbol()
            else:
                print(f"Syntax Error: Expected valid port_name, got {self.symbol.text}")
                self.error_count += 1

        # EG thing[3], handle that logic here.

        return (device_id, port_id)

    def parse_monitor(self):
        """Parse a monitor declaration and add it to the monitors list."""
        self.expect(Symbol.KEYWORD, "monitor")

        device_id, port_id = self.parse_signal_or_port_ref()

        self.expect(Symbol.PUNCTUATION, ";")

        if device_id is not None:
            error = self.monitors.make_monitor(device_id, port_id)

            if error != self.monitors.NO_ERROR:
                print(f"Semantic Error: Failed to add monitor. Error code: {error}")
                self.error_count += 1

    def parse_instance(self):
        self.expect(Symbol.KEYWORD, "instance")

        if self.symbol.type == Symbol.NAME:
            module_name = self.symbol.text
            self.next_symbol()
        else:
            # error handling
            self.expect(Symbol.NAME)
            return

        self.expect(Symbol.PUNCTUATION, "(")

        module_inputs = self.parse_bind_list()

        self.expect(Symbol.PUNCTUATION, "->")

        module_outputs = self.parse_bind_list()

        self.expect(Symbol.PUNCTUATION, ")")
        self.expect(Symbol.PUNCTUATION, ";")

        # check form of I/O against module def
        expected_inputs, expected_outputs = self.module_mappings[module_name]
        if len(module_inputs) != len(expected_inputs):
            self.error_count += 1
        if len(module_outputs) != len(expected_outputs):
            self.error_count += 1

        # re-instantiate the module in this place

    def parse_bind_list(self):
        signals = []
        if self.symbol.type == Symbol.NAME:
            signals.append(self.parse_signal_or_port_ref())

            while self.accept(Symbol.PUNCTUATION, ","):
                signals.append(self.parse_signal_or_port_ref())
        return signals
