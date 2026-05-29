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
        self.expect(Symbol.NAME)
        self.expect(Symbol.PUNCTUATION, ":")

        self.parse_port_list()
        self.expect(Symbol.PUNCTUATION, "->")
        self.parse_port_list()

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
        if self.symbol.type == Symbol.NAME:
            self.parse_port()
            while self.accept(Symbol.PUNCTUATION, ","):
                self.parse_port()

    def parse_port(self):
        self.expect(Symbol.NAME)
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
            print(f"Syntax Error: invalid statement starting with '{self.symbol.text}' at {self.scanner.line_position},{self.scanner.line_count}")
            self.error_count += 1
            self.next_symbol()

    def parse_declaration(self):
        if self.accept(Symbol.KEYWORD, "wire"):
            self.expect(Symbol.NAME)
            if self.accept(Symbol.PUNCTUATION, "["):
                self.expect(Symbol.NUMBER)
                self.expect(Symbol.PUNCTUATION, "]")
            self.expect(Symbol.PUNCTUATION, ";")

        elif self.accept(Symbol.KEYWORD, "clock"):
            self.expect(Symbol.NAME)
            self.expect(Symbol.PUNCTUATION, "[")
            self.expect(Symbol.NUMBER)
            self.expect(Symbol.PUNCTUATION, "]")
            self.expect(Symbol.PUNCTUATION, ";")

        elif self.accept(Symbol.KEYWORD, "switch"):
            self.expect(Symbol.NAME)
            self.expect(Symbol.PUNCTUATION, "=")
            if self.symbol.type == Symbol.NUMBER and self.symbol.text in ["0", "1"]:
                # Valid, add device
                id = uuid.uuid4()
                self.devices.make_device(id, self.devices.SWITCH, int(self.symbol.text))
                self.next_symbol()
            else:
                print("Syntax Error: Expected 0 or 1 for switch state")
                self.error_count += 1
            self.expect(Symbol.PUNCTUATION, ";")

        elif self.accept(Symbol.KEYWORD, "dtype"):
            self.expect(Symbol.NAME)
            self.expect(Symbol.PUNCTUATION, ";")

    def parse_assignment(self):
        self.parse_lhs()
        if self.accept(Symbol.PUNCTUATION, "=") or self.accept(
            Symbol.PUNCTUATION, "<="
        ):
            pass
        else:
            print(f"Syntax Error: Expected '=' or '<=', got {self.symbol.text}")
            self.error_count += 1
        self.parse_rhs()
        self.expect(Symbol.PUNCTUATION, ";")

    def parse_lhs(self):
        self.parse_signal_or_port_ref()

    def parse_rhs(self):
        self.parse_or_expr()

    def parse_or_expr(self):
        or_inputs = [self.parse_and_expr()]
        while self.accept(Symbol.PUNCTUATION, "+"):
            or_inputs.append(self.parse_and_expr())

        if len(or_inputs) == 1:
            return or_inputs[0]

        or_gate_id = uuid.uuid4()
        self.devices.make_device(or_gate_id,self.devices.OR, len(or_inputs))
        or_gate = self.devices.get_device(or_gate_id)
        print(f"OR GATE {or_gate}")
        return or_gate

    def parse_and_expr(self):
        and_inputs = [self.parse_xor_expr()]
        while self.accept(Symbol.PUNCTUATION, "*"):
            and_inputs.append(self.parse_xor_expr())

        if len(and_inputs) == 1:
            return and_inputs[0]

        and_gate_id = uuid.uuid4()
        self.devices.make_device(and_gate_id,self.devices.AND, len(and_inputs))
        and_gate = self.devices.get_device(and_gate_id)
        print(f"AND GATE {and_gate}")
        print(f"AND GATE INPUTS {and_inputs}")
        return and_gate



    def parse_xor_expr(self):
        xor_inputs = [self.parse_factor()]
        while self.accept(Symbol.PUNCTUATION, "^"):
            xor_inputs.append(self.parse_factor())

        if len(xor_inputs) == 1:
            return xor_inputs[0]

        xor_gate_id = uuid.uuid4()
        self.devices.make_device(xor_gate_id,self.devices.XOR, len(xor_inputs))
        xor_gate = self.devices.get_device(xor_gate_id)
        print(f"XOR GATE {xor_gate}")
        return xor_gate

    def parse_factor(self):
        self.accept(Symbol.PUNCTUATION, "!")

        if self.accept(Symbol.PUNCTUATION, "("):
            self.parse_or_expr()
            self.expect(Symbol.PUNCTUATION, ")")
        else:
            self.parse_signal_or_port_ref()

    def parse_signal_or_port_ref(self):
        self.expect(Symbol.NAME)

        # Port
        if self.accept(Symbol.PUNCTUATION, "."):
            valid_ports = ["CLK", "DATA", "SET", "CLEAR", "Q", "QBAR"]
            if self.symbol.type == Symbol.NAME and self.symbol.text in valid_ports:
                self.next_symbol()
            else:
                print(f"Syntax Error: Expected valid port_name, got {self.symbol.text}")
                self.error_count += 1

        # Signal
        elif self.accept(Symbol.PUNCTUATION, "["):
            self.expect(Symbol.NUMBER)
            if self.accept(Symbol.PUNCTUATION, ":"):
                self.expect(Symbol.NUMBER)
            self.expect(Symbol.PUNCTUATION, "]")

    def parse_monitor(self):
        self.expect(Symbol.KEYWORD, "monitor")
        self.parse_signal_or_port_ref()
        self.expect(Symbol.PUNCTUATION, ";")

    def parse_instance(self):
        self.expect(Symbol.NAME, "instance")
        self.expect(Symbol.NAME)
        self.expect(Symbol.PUNCTUATION, "(")

        self.parse_bind_list()
        self.expect(Symbol.PUNCTUATION, "->")
        self.parse_bind_list()

        self.expect(Symbol.PUNCTUATION, ")")
        self.expect(Symbol.PUNCTUATION, ";")

    def parse_bind_list(self):
        if self.symbol.type == Symbol.NAME:
            self.parse_signal_or_port_ref()
            while self.accept(Symbol.PUNCTUATION, ","):
                self.parse_signal_or_port_ref()
