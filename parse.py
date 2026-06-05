"""Parse the definition file and build the logic network.

Used in the Logic Simulator project to analyse the syntactic and semantic
correctness of the symbols received from the scanner and then builds the
logic network.

Classes
-------
Parser - parses the definition file and builds the logic network.
"""

import uuid

from scanner import Symbol


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
        self.errors = []

        self.map_error_code = {
            self.network.INPUT_TO_INPUT: "Both ports are inputs.",
            self.network.OUTPUT_TO_OUTPUT: "Both ports are outputs.",
            self.network.INPUT_CONNECTED: "Input already connected.",
            self.network.PORT_ABSENT: "Second port not valid.",
            self.network.DEVICE_ABSENT: "One or both devices not found.",
            self.monitors.NOT_OUTPUT: "Cannot monitor input.",
            self.monitors.MONITOR_PRESENT: "Monitor already present.",
        }

        self.current_module_name = None

        # dict of { module_name : [ [inputs],[outputs] ] }
        self.module_mappings = {}

        # dict of gate:count
        self.gate_counts = {}

    def _error_location(self):
        return f"at line {self.scanner.line_count} pos {self.scanner.line_position}: "

    def _get_syntax_error(self):
        return f"Syntax Error {self._error_location()}"

    def _get_semantic_error(self):
        return f"Semantic Error {self._error_location()}"

    def next_symbol(self):
        """Get the next symbol from scanner."""
        symbol, state = self.scanner.get_symbol()
        if not state:
            error_message = f"Syntax Error at {self.symbol.line}, pos {self.symbol.pos}: Invalid character '{symbol.text}' ascii:{ord(symbol.text)}, processing terminated."
            self.errors.append(error_message)
            self.error_count += 1
            raise SyntaxError(error_message)

        self.symbol = symbol

    def accept(self, symbol_type, text: str | None = None):
        """Return True and proceed to next symbol if the symbol type and text are correct, else False."""
        if self.symbol.type == symbol_type:
            if text is None or self.symbol.text == text:
                self.next_symbol()
                return True
        return False

    def expect(self, symbol_type, text=None):
        """Returns True and proceeds to next symbol if the symbol type and text are correct,
        else handles the error and return False."""
        if self.accept(symbol_type, text):
            return True

        expected = (
            f"'{text}'"
            if text
            else (
                "NAME"
                if symbol_type == Symbol.NAME
                else "NUMBER" if symbol_type == Symbol.NUMBER else "EOF"
            )
        )

        error_message = f"Syntax Error at line {self.symbol.line}, pos {self.symbol.pos}: Expected {expected}, got '{self.symbol.text}'"
        self.errors.append(error_message)
        self.error_count += 1

        while self.symbol.text != ";":
            if self.symbol.type == Symbol.EOF:
                return False
            self.next_symbol()
        self.next_symbol()

        return False

    def parse_network(self):
        """Parse the circuit definition file."""
        # get first symbol
        self.next_symbol()
        # parse first module
        self.parse_prog_defn()
        # if anymore modules, parse
        while self.symbol.type != Symbol.EOF:
            self.parse_prog_defn()
        # no errors, returns True
        return self.error_count == 0

    def _handle_module_header_error(self):
        """Handle module header errors."""
        # if module fails, jump to end of module
        error_message = ". Error in module header, skipped whole module."
        self.errors[-1] += error_message

        while self.symbol.text != "end":
            if self.symbol.type == Symbol.EOF:
                return
            self.next_symbol()
        self.next_symbol()
        self.next_symbol()

    def parse_prog_defn(self):
        # Should start with module
        if not self.expect(Symbol.KEYWORD, "module"):
            self._handle_module_header_error()
            return

        # Then module name
        if self.symbol.type == Symbol.NAME:
            self.current_module_name = self.symbol.text
            self.next_symbol()
        else:
            self.expect(Symbol.NAME)
            self._handle_module_header_error()
            return

        # Then inputs -> outputs
        if not self.expect(Symbol.PUNCTUATION, ":"):
            self._handle_module_header_error()
            return

        module_inputs, state = self.parse_port_list()
        if not state:
            self._handle_module_header_error()
            return

        if not self.expect(Symbol.PUNCTUATION, "->"):
            self._handle_module_header_error()
            return

        module_outputs, state = self.parse_port_list()
        if not state:
            self._handle_module_header_error()
            return

        # Save module inputs/outputs to dict for instancing later
        # TODO: come back to this
        self.module_mappings[self.current_module_name] = [
            module_inputs,
            module_outputs,
        ]

        # End of module header
        if not self.expect(Symbol.PUNCTUATION, ";"):
            self._handle_module_header_error()
            return

        while not (
            self.symbol.type == Symbol.KEYWORD and self.symbol.text == "end"
        ):
            # check for abrupt end of file before module finished
            if self.symbol.type == Symbol.EOF:
                error_message = (
                    self._get_syntax_error() + "Unexpected End of File."
                )
                self.errors.append(error_message)
                self.error_count += 1
                break
            # parse module lines
            self.parse_statement()

        # end of module
        self.expect(Symbol.KEYWORD, "end")
        self.expect(Symbol.PUNCTUATION, ";")

    def parse_port_list(self) -> tuple[list[str], bool]:
        ports = []
        if self.symbol.type == Symbol.NAME:
            port = self.parse_port()
            ports.append(port)
            while self.accept(Symbol.PUNCTUATION, ","):
                port = self.parse_port()
                if port == False:
                    return [], False
                ports.append(port)
            return ports, True
        elif self.symbol.text == "->" or self.symbol.text == ";":
            return [], True
        else:
            self.expect(Symbol.NAME)
            return [], False

    def parse_port(self):
        if self.symbol.type == Symbol.NAME:
            port_name = f"__{self.symbol.text}__{self.current_module_name}__"
            # create 1-AND buffer as inputs
            [port_id] = self.names.lookup([port_name])
            if self.devices.get_device(port_id) is None:
                self.devices.make_device(port_id, self.devices.AND, 1)

            # Wires and buffers receive their input on port 'I1'
            [target_port_id] = self.names.lookup([f"I1__{port_name}"])

            self.next_symbol()
            return port_name
        else:
            self.expect(Symbol.NAME)
            return False

    def parse_statement(self):
        # parse keywords
        if self.symbol.type == Symbol.KEYWORD:
            if self.symbol.text in ["wire", "clock", "switch", "dtype"]:
                # create wire/clock/switch/dtype
                self.parse_declaration()
            elif self.symbol.text == "monitor":
                # create monitor
                self.parse_monitor()
            elif self.symbol.text == "instance":
                # create instance
                self.parse_instance()
            else:
                # mainly used in development for not implemented errors
                error_message = (
                    self._get_syntax_error()
                    + f"unexpected keyword '{self.symbol.text}' in statement."
                )
                self.errors.append(error_message)
                self.error_count += 1
                self.next_symbol()

        elif self.symbol.type == Symbol.NAME:
            self.parse_assignment()
        else:
            error_message = (
                self._get_syntax_error()
                + f"invalid statement starting with '{self.symbol.text}'."
            )
            self.errors.append(error_message)
            self.error_count += 1
            self.next_symbol()

    def _parse_device_thing(self, device_type: str) -> str | None:
        if self.symbol.type == Symbol.NAME:
            device_name = f"__{self.symbol.text}__{self.current_module_name}__"
            if self.names.query(
                device_name
            ):  # Check if device_name already exists.
                error_message = f"Semantic Error: duplicate {device_type} name '{self.names.prettify_name(device_name)}' in module '{self.current_module_name}'."
                self.errors.append(error_message)
                self.error_count += 1
            [device_id] = self.names.lookup([device_name])
            self.next_symbol()
            return device_id
        else:
            self.expect(Symbol.NAME)
            return None

    def parse_declaration(self):
        if self.accept(Symbol.KEYWORD, "wire"):
            wire_id = self._parse_device_thing("wire")
            if wire_id is not None:
                self.devices.make_device(wire_id, self.devices.AND, 1)
            self.expect(Symbol.PUNCTUATION, ";")

        elif self.accept(Symbol.KEYWORD, "clock"):
            clock_id = self._parse_device_thing("clock")
            if clock_id is not None:
                self.expect(Symbol.PUNCTUATION, "[")

                if self.symbol.type == Symbol.NUMBER:
                    period = int(self.symbol.text)
                    self.next_symbol()
                    self.devices.make_device(
                        clock_id, self.devices.CLOCK, period
                    )
                else:
                    self.expect(Symbol.NUMBER)
                    return

            self.expect(Symbol.PUNCTUATION, "]")
            self.expect(Symbol.PUNCTUATION, ";")

        elif self.accept(Symbol.KEYWORD, "switch"):
            switch_id = self._parse_device_thing("switch")
            if switch_id is not None:
                self.expect(Symbol.PUNCTUATION, "=")
                if self.symbol.type == Symbol.NUMBER and self.symbol.text in [
                    "0",
                    "1",
                ]:
                    # Valid, add device
                    state = int(self.symbol.text)
                    self.devices.make_device(
                        switch_id, self.devices.SWITCH, state
                    )
                else:
                    error_message = (
                        self._get_syntax_error()
                        + "Expected 0 or 1 for switch state."
                    )
                    self.errors.append(error_message)
                    self.error_count += 1
                self.next_symbol()

            self.expect(Symbol.PUNCTUATION, ";")

        elif self.accept(Symbol.KEYWORD, "dtype"):
            dtype_id = self._parse_device_thing("dtype")
            if dtype_id is not None:
                self.devices.make_device(dtype_id, self.devices.D_TYPE)
            self.expect(Symbol.PUNCTUATION, ";")

    def parse_assignment(self) -> None:
        """Parse an assignment and connect the RHS to the LHS."""
        target_device_id, target_port_id = self.parse_lhs()
        target_text = self.names.get_pretty_name(target_device_id)
        if target_device_id is None:
            # error handled upstream
            return

        if not (
            self.accept(Symbol.PUNCTUATION, "=")
            or self.accept(Symbol.PUNCTUATION, "<=")
        ):
            error_message = (
                self._get_syntax_error()
                + f"Expected '=' or '<=' after NAME '{target_text}', got '{self.symbol.text}'."
            )
            self.errors.append(error_message)
            self.error_count += 1
            return

        source_device_id, source_port_id = self.parse_rhs()

        self.expect(Symbol.PUNCTUATION, ";")

        # If assigning to a standalone variable (e.g., A = ... rather than D1.DATA = ...)
        if target_port_id is None:
            # If this variable hasn't been instantiated yet, make it a buffer (1-input AND gate)
            if self.devices.get_device(target_device_id) is None:
                self.devices.make_device(target_device_id, self.devices.AND, 1)

            # Wires and buffers receive their input on port 'I1'
            [target_port_id] = self.names.lookup([f"I1__{target_device_id}"])

        # Wire the calculated right-hand expression to the target on the left
        error = self.network.make_connection(
            source_device_id, source_port_id, target_device_id, target_port_id
        )
        if error != self.network.NO_ERROR:
            error_message = (
                self._get_semantic_error()
                + f"Failed to connect. E:{error}, {self.map_error_code[error]}"
            )
            self.errors.append(error_message)
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

        gate_name = f"__{gate_type} {self.gate_counts[gate_type]}__{self.current_module_name}"
        [gate_id] = self.names.lookup([gate_name])

        if gate_type == "XOR":
            if len(inputs) == 2:
                # XOR gates need 2 inputs
                self.devices.make_device(gate_id, gates[gate_type][2], None)
            else:
                error_message = f"Semantic Error: Failed to create XOR gate, only 2 inputs allowed. Use brackets to separate into pairs."
                self.errors.append(error_message)
                self.error_count += 1
        else:
            self.devices.make_device(gate_id, gates[gate_type][2], len(inputs))

        for i, (src_dev, src_port) in enumerate(inputs, start=1):
            [input_port_id] = self.names.lookup([f"I{i}__{gate_id}"])
            self.network.make_connection(
                src_dev, src_port, gate_id, input_port_id
            )

        return gate_id, None

    def parse_or_expr(self):
        return self._parse_gate("OR")

    def parse_and_expr(self):
        return self._parse_gate("AND")

    def parse_xor_expr(self):
        return self._parse_gate("XOR")

    def parse_factor(self):
        invert = self.accept(Symbol.PUNCTUATION, "!")

        if self.accept(Symbol.PUNCTUATION, "("):
            signal = self.parse_or_expr()
            self.expect(Symbol.PUNCTUATION, ")")
        else:
            signal = self.parse_signal_or_port_ref()

        if invert:
            gate_name = (
                f"__NOT__{self.current_module_name}__{uuid.uuid4().hex}"
            )
            [gate_id] = self.names.lookup([gate_name])

            # A 1-input NAND functions as a NOT gate
            self.devices.make_device(gate_id, self.devices.NAND, 1)
            [input_port_id] = self.names.lookup([f"I1__{gate_id}"])

            self.network.make_connection(
                signal[0], signal[1], gate_id, input_port_id
            )
            return gate_id, None

        return signal, None

    def parse_signal_or_port_ref(self) -> tuple[str, str]:
        # Capture the device name
        if self.symbol.type == Symbol.NAME:
            name = f"__{self.symbol.text}__{self.current_module_name}__"
            [device_id] = self.names.lookup([name])
            self.next_symbol()
        else:
            device_id = None
            self.expect(Symbol.NAME)

        port_id = None
        # Check if a specific port is referenced (e.g., DTYPE.Q)
        if self.accept(Symbol.PUNCTUATION, "."):
            valid_ports = ["CLK", "DATA", "SET", "CLEAR", "Q", "QBAR"]
            if (
                self.symbol.type == Symbol.NAME
                and self.symbol.text in valid_ports
            ):
                port_name = (
                    f"__{self.symbol.text}__{self.current_module_name}__"
                )
                [port_id] = self.names.lookup([port_name])
                self.next_symbol()
            else:
                # TODO: error handling
                error_message = (
                    self._get_syntax_error()
                    + f"Expected valid port_name, got '{self.symbol.text}'."
                )
                self.errors.append(error_message)
                self.error_count += 1

        return device_id, port_id

    def parse_monitor(self) -> None:
        """Parse a monitor declaration and add it to the monitors list."""
        self.expect(Symbol.KEYWORD, "monitor")

        device_id, port_id = self.parse_signal_or_port_ref()
        self.expect(Symbol.PUNCTUATION, ";")

        if device_id is not None:
            error = self.monitors.make_monitor(device_id, port_id)

            if error != self.monitors.NO_ERROR:
                # TODO: error handling
                error_message = (
                    self._get_semantic_error()
                    + f"Failed to add monitor to '{self.names.get_pretty_name(device_id)}'. E:{error}, {self.map_error_code[error]}"
                )
                self.errors.append(error_message)
                self.error_count += 1

    def parse_instance(self) -> None:
        self.expect(Symbol.KEYWORD, "instance")

        if self.symbol.type == Symbol.NAME:
            # TODO: check module name exists
            module_name = self.symbol.text
            self.next_symbol()
        else:
            # TODO: error handling
            # f"module {module_name} not found or declared yet."
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
        # TODO: make module instance

    def parse_bind_list(self):
        signals = []
        if self.symbol.type == Symbol.NAME:
            signals.append(self.parse_signal_or_port_ref())

            while self.accept(Symbol.PUNCTUATION, ","):
                signals.append(self.parse_signal_or_port_ref())
        return signals
