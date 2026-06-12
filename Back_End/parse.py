"""Parse the definition file and build the logic network.

Used in the Logic Simulator project to analyse the syntactic and semantic
correctness of the symbols received from the scanner and then builds the
logic network.

Classes
-------
Parser - parses the definition file and builds the logic network.
"""

# TODO look at the issue of comments causing crash instead of error

import uuid

from .scanner import Symbol


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

        self.current_module_name = "Main"
        self.anon_instance_count = 0

        # dict of { module_name : [ [inputs],[outputs] ] }
        self.module_mappings = {}

        # dict of gate:count
        self.gate_counts = {}

    def _error_location(self):
        if self.symbol:
            return f"at line {self.symbol.line} pos {self.symbol.pos}: "
        else:
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

    def check_inputs(self):
        if self.error_count == 0:
            unconnected = []
            for device_id in self.devices.find_devices():
                device = self.devices.get_device(device_id)
                for input_id in device.inputs:
                    if (
                        self.network.get_connected_output(device_id, input_id)
                        is None
                    ):
                        dev_name = self.names.get_pretty_name(device_id)
                        port_name = self.names.get_pretty_name(input_id)
                        unconnected.append(f"{dev_name}.{port_name}")

            if unconnected:
                self.errors.append(
                    f"Semantic Error: Unconnected inputs detected on: {', '.join(unconnected)}"
                )
                self.error_count += 1

    def parse_network(self):
        """Parse the circuit definition file."""
        # TODO - temporary fix with try except look
        try:
            # get first symbol
            self.next_symbol()

            while self.symbol.type != Symbol.EOF:
                if (
                    self.symbol.type == Symbol.KEYWORD
                    and self.symbol.text == "module"
                ):
                    self.parse_prog_defn()
                else:
                    self.parse_statement()

            self.check_inputs()
        except SyntaxError:
            # next_symbol() raises SyntaxError for invalid characters and has
            # already appended the error message to self.errors.
            pass
        return self.error_count == 0  # no errors, returns True

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
        previous_scope = self.current_module_name
        try:
            # Should start with module
            if not self.expect(Symbol.KEYWORD, "module"):
                self._handle_module_header_error()
                return

            # Then module name
            if self.symbol.type == Symbol.NAME:
                if self.symbol.text == "Main":
                    error_message = (
                        self._get_semantic_error()
                        + "The module name 'Main' is reserved for the top-level scope."
                    )
                    self.errors.append(error_message)
                    self.error_count += 1
                    self._handle_module_header_error()
                    return
                self.current_module_name = self.symbol.text
                self.next_symbol()
            else:
                self.expect(Symbol.NAME)
                self._handle_module_header_error()
                return

            if self.current_module_name in self.module_mappings:
                error_message = (
                    self._get_semantic_error()
                    + f"Duplicate module definition '{self.current_module_name}'"
                )
                self.errors.append(error_message)
                self.error_count += 1
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
            self.module_mappings[self.current_module_name] = {
                "inputs": module_inputs,
                "outputs": module_outputs,
                "symbols": [],
            }

            # End of module header
            if not self.expect(Symbol.PUNCTUATION, ";"):
                self._handle_module_header_error()
                return

            while not (
                self.symbol.type == Symbol.KEYWORD
                and self.symbol.text == "end"
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
                # self.parse_statement()
                self.module_mappings[self.current_module_name][
                    "symbols"
                ].append(self.symbol)
                self.next_symbol()
            # end of module
            self.expect(Symbol.KEYWORD, "end")
            self.expect(Symbol.PUNCTUATION, ";")
        finally:
            # restore scope
            self.current_module_name = previous_scope

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
            # port_name = f"__{self.symbol.text}__{self.current_module_name}__"
            port_name = self.symbol.text
            self.next_symbol()
            return port_name
        else:
            self.expect(Symbol.NAME)
            return False

    def parse_statement(self):
        # parse keywords
        if self.symbol.type == Symbol.KEYWORD:
            if self.symbol.text in [
                "wire",
                "clock",
                "siggen",
                "rc",
                "switch",
                "dtype",
            ]:
                # create wire/clock/switch/dtype
                self.parse_declaration()
            elif self.symbol.text == "monitor":
                # create monitor
                self.parse_monitor()
            # elif self.symbol.text == "instance":
            #     # create instance
            #     self.parse_instance()
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
            if self.symbol.text in self.module_mappings:
                self.parse_instance()
            else:
                self.parse_assignment()
        else:
            error_message = (
                self._get_syntax_error()
                + f"invalid statement starting with '{self.symbol.text}'."
            )
            self.errors.append(error_message)
            self.error_count += 1
            self.next_symbol()

    def _parse_device(self, device_type: str) -> str | None:
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
            wire_id = self._parse_device("wire")
            if wire_id is not None:
                self.devices.make_device(wire_id, self.devices.AND, 1)
            self.expect(Symbol.PUNCTUATION, ";")

        elif self.accept(Symbol.KEYWORD, "clock"):
            clock_id = self._parse_device("clock")
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

        elif self.accept(Symbol.KEYWORD, "siggen"):
            siggen_id = self._parse_device("siggen")
            if siggen_id is not None:
                self.expect(Symbol.PUNCTUATION, "=")
                self.expect(Symbol.PUNCTUATION, "[")

                signals = []
                while self.symbol.type == Symbol.NUMBER:
                    val = int(self.symbol.text)
                    if val not in [0, 1]:
                        self.errors.append(
                            f"Semantic Error: SIGGEN accepts only 0 or 1, got {val}."
                        )
                        self.error_count += 1
                    signals.append(val)
                    self.next_symbol()
                    if self.accept(Symbol.PUNCTUATION, ","):
                        continue
                    else:
                        break

                if signals == []:
                    error_message = (
                        self._get_semantic_error()
                        + "SIGGEN array cannot be empty."
                    )
                    self.errors.append(error_message)
                    self.error_count += 1
                    signals = [0]

                self.devices.make_device(
                    siggen_id, self.devices.SIGGEN, signals
                )
            self.expect(Symbol.PUNCTUATION, "]")
            self.expect(Symbol.PUNCTUATION, ";")

        elif self.accept(Symbol.KEYWORD, "rc"):
            rc_id = self._parse_device("rc")
            if rc_id is not None:
                self.expect(Symbol.PUNCTUATION, "[")

                if self.symbol.type == Symbol.NUMBER:
                    time_constant = int(self.symbol.text)
                    self.next_symbol()
                    self.devices.make_device(
                        rc_id, self.devices.RC, time_constant
                    )
                else:
                    self.expect(Symbol.NUMBER)
                    return

            self.expect(Symbol.PUNCTUATION, "]")
            self.expect(Symbol.PUNCTUATION, ";")

        elif self.accept(Symbol.KEYWORD, "switch"):
            switch_id = self._parse_device("switch")
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
            dtype_id = self._parse_device("dtype")
            if dtype_id is not None:
                self.devices.make_device(dtype_id, self.devices.D_TYPE)
            self.expect(Symbol.PUNCTUATION, ";")

    def parse_assignment(self) -> None:
        """Parse an assignment and connect the RHS to the LHS."""
        target_device_id, target_port_id = self.parse_lhs()
        if target_device_id is None:
            return
        target_text = self.names.get_pretty_name(target_device_id)

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
        self.expect(Symbol.PUNCTUATION, ";")

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

        gate_info = gates.get(gate_type)
        if gate_info is None:
            self.errors.append(
                self._get_semantic_error()
                + f"Internal Error: Unknown gate type '{gate_type}'."
            )
            self.error_count += 1
            return None, None

        inputs = [gate_info[0]()]
        operator = gate_info[1]
        device_kind = gate_info[2]

        while self.accept(Symbol.PUNCTUATION, operator):
            inputs.append(gate_info[0]())

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
                self.devices.make_device(gate_id, device_kind, None)
            else:
                error_message = (
                    self._get_semantic_error()
                    + "Failed to create XOR gate, only 2 inputs allowed. Use brackets to separate into pairs."
                )
                self.errors.append(error_message)
                self.error_count += 1
        else:
            self.devices.make_device(gate_id, device_kind, len(inputs))

        for i, source in enumerate(inputs, start=1):
            if source is None or source == (None, None):
                continue
            src_dev, src_port = source
            if src_dev is None:
                continue

            [input_port_id] = self.names.lookup([f"I{i}__{gate_id}"])

            # create device if it doesnt exist
            if self.devices.get_device(src_dev) is None:
                self.devices.make_device(src_dev, self.devices.AND, 1)

            error = self.network.make_connection(
                src_dev, src_port, gate_id, input_port_id
            )
            if error != self.network.NO_ERROR:
                self.errors.append(
                    f"Semantic Error: Gate connection failed. E:{error}, {self.map_error_code[error]}"
                )
                self.error_count += 1

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

        return signal

    def parse_signal_or_port_ref(self) -> tuple[str | None, str | None]:
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
                # port_name = (
                #     f"__{self.symbol.text}__{self.current_module_name}__"
                # )
                port_name = self.symbol.text
                [port_id] = self.names.lookup([port_name])
                self.next_symbol()
            else:
                error_message = (
                    self._get_syntax_error()
                    + f"Expected valid port_name, got '{self.symbol.text}'."
                )
                self.errors.append(error_message)
                self.error_count += 1
                return None, None

        return device_id, port_id

    def parse_monitor(self) -> None:
        """Parse a monitor declaration and add it to the monitors list."""
        self.expect(Symbol.KEYWORD, "monitor")

        device_id, port_id = self.parse_signal_or_port_ref()

        if device_id is not None:
            error = self.monitors.make_monitor(device_id, port_id)

            if error != self.monitors.NO_ERROR:
                error_message = (
                    self._get_semantic_error()
                    + f"Failed to add monitor to '{self.names.get_pretty_name(device_id)}'. E:{error}, {self.map_error_code[error]}"
                )
                self.errors.append(error_message)
                self.error_count += 1
        self.expect(Symbol.PUNCTUATION, ";")

    def parse_instance(self) -> None:
        # self.expect(Symbol.KEYWORD, "instance")
        module_name = self.symbol.text
        self.next_symbol()

        # Instance name
        if self.symbol.type == Symbol.NAME:
            instance_name = self.symbol.text
            self.next_symbol()
            self.expect(Symbol.PUNCTUATION, "(")

        elif self.accept(Symbol.PUNCTUATION, "("):
            self.anon_instance_count += 1
            instance_name = f"anon_{module_name}_{self.anon_instance_count}"
        else:
            error_message = (
                self._get_syntax_error()
                + f"Expected instance name or '(', got '{self.symbol.text}'."
            )
            self.errors.append(error_message)
            self.error_count += 1
            # self.expect(Symbol.NAME)
            return

        if self.accept(Symbol.PUNCTUATION, ")"):
            module_inputs = []
            module_outputs = []
        else:
            module_inputs = self.parse_bind_list()
            self.expect(Symbol.PUNCTUATION, "->")
            module_outputs = self.parse_bind_list()
            self.expect(Symbol.PUNCTUATION, ")")

        self.expect(Symbol.PUNCTUATION, ";")

        # check form of I/O against module def
        expected_inputs = self.module_mappings[module_name]["inputs"]
        expected_outputs = self.module_mappings[module_name]["outputs"]

        mismatch = False

        if len(module_inputs) != len(expected_inputs):
            error_message = (
                self._get_semantic_error()
                + f"Instance inputs do not match module inputs [{len(module_inputs)}]."
            )
            self.errors.append(error_message)
            self.error_count += 1
            mismatch = True
        if len(module_outputs) != len(expected_outputs):
            error_message = (
                self._get_semantic_error()
                + f"Instance outputs do not match module outputs [{len(module_outputs)}]."
            )
            self.errors.append(error_message)
            self.error_count += 1
            mismatch = True

        if mismatch:
            return

        # re-instantiate the module in this place
        unique_instance_scope = f"{instance_name}__{self.current_module_name}"

        self.instantiate_module(
            module_name, unique_instance_scope, module_inputs, module_outputs
        )

    def instantiate_module(
        self, module_name, instance_name, bound_inputs, bound_outputs
    ):
        template = self.module_mappings.get(module_name)
        if not template:
            error_message = (
                self._get_semantic_error()
                + f"Module '{module_name}' is not defined."
            )
            self.errors.append(error_message)
            self.error_count += 1
            return

        # # Inputs
        instance_input_ids = []
        for port_name in template["inputs"]:
            scoped_port = f"__{port_name}__{instance_name}__"
            [inst_in_id] = self.names.lookup([scoped_port])
            self.devices.make_device(inst_in_id, self.devices.AND, 1)
            instance_input_ids.append(inst_in_id)

        for caller_sig, inst_in_id in zip(bound_inputs, instance_input_ids):
            caller_dev, caller_port = caller_sig

            if caller_dev is None:
                continue

            if self.devices.get_device(caller_dev) is None:
                self.devices.make_device(caller_dev, self.devices.AND, 1)

            [inst_in_port] = self.names.lookup([f"I1__{inst_in_id}"])
            error = self.network.make_connection(
                caller_dev, caller_port, inst_in_id, inst_in_port
            )
            if error != self.network.NO_ERROR:
                self.errors.append(
                    f"Semantic Error: Instance input binding failed. E:{error}"
                )
                self.error_count += 1

        instance_output_ids = []
        for port_name in template["outputs"]:
            scoped_port = f"__{port_name}__{instance_name}__"
            [inst_out_id] = self.names.lookup([scoped_port])
            self.devices.make_device(inst_out_id, self.devices.AND, 1)
            instance_output_ids.append(inst_out_id)
        for inst_out_id, caller_sig in zip(instance_output_ids, bound_outputs):
            caller_dev, caller_port = caller_sig

            if caller_dev is None:
                continue

            if self.devices.get_device(caller_dev) is None:
                self.devices.make_device(caller_dev, self.devices.AND, 1)

            if caller_port is None:
                [caller_port] = self.names.lookup([f"I1__{caller_dev}"])

            error = self.network.make_connection(
                inst_out_id, None, caller_dev, caller_port
            )
            if error != self.network.NO_ERROR:
                self.errors.append(
                    f"Semantic Error: Instance output binding failed. E:{error}"
                )
                self.error_count += 1

        # "playback" the saved symbols
        previous_module_name = self.current_module_name
        self.current_module_name = instance_name

        previous_symbol = self.symbol
        original_next_symbol = self.next_symbol

        class TokenStream:
            def __init__(self, symbols):
                self.symbols = symbols
                self.ptr = 0

            def get_next(self):
                if self.ptr < len(self.symbols):
                    sym = self.symbols[self.ptr]
                    self.ptr += 1
                    return sym
                sym = Symbol()
                sym.type = Symbol.EOF
                if self.symbols:
                    sym.line = self.symbols[-1].line
                    sym.pos = self.symbols[-1].pos
                return sym

        stream = TokenStream(template["symbols"])

        # Override the parser's feed to read from our stored symbols
        def mock_next_symbol():
            self.symbol = stream.get_next()

        self.next_symbol = mock_next_symbol
        self.next_symbol()  # Load the first token of the module body

        while self.symbol.type != Symbol.EOF:
            self.parse_statement()

        # Restore original parser state
        self.next_symbol = original_next_symbol
        self.symbol = previous_symbol
        self.current_module_name = previous_module_name

    def parse_bind_list(self):
        signals = []
        if self.symbol.type == Symbol.NAME:
            signals.append(self.parse_signal_or_port_ref())

            while self.accept(Symbol.PUNCTUATION, ","):
                signals.append(self.parse_signal_or_port_ref())
        return signals
