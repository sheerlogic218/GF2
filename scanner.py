"""Read the circuit definition file and translate the characters into symbols.

Used in the Logic Simulator project to read the characters in the definition
file and translate them into symbols that are usable by the parser.

Classes
-------
Scanner - reads definition file and translates characters into symbols.
Symbol - encapsulates a symbol and stores its properties.
"""

from names import Names
import re


class Symbol:
    """Encapsulate a symbol and store its properties.

    Parameters
    ----------
    No parameters.

    Public methods
    --------------
    No public methods.
    """

    def __init__(self):
        """Initialise symbol properties."""
        self.type = None
        self.id = None


class Scanner:
    """Read circuit definition file and translate the characters into symbols.

    Once supplied with the path to a valid definition file, the scanner
    translates the sequence of characters in the definition file into symbols
    that the parser can use. It also skips over comments and irrelevant
    formatting characters, such as spaces and line breaks.

    Parameters
    ----------
    path: path to the circuit definition file.
    names: instance of the names.Names() class.

    Public methods
    -------------
    get_symbol(self): Translates the next sequence of characters into a symbol
                      and returns the symbol.
    """

    def __init__(self, path: str, names: Names) -> None:
        """Open specified file and initialise reserved words and IDs."""
        with open(path, "r") as f:
            self.text = f.read()

        self.names = names
        self.ptr = 0
        self.line_count = 1
        self.line_position = 1

        self.keywords = [
            "prog",
            "def",
            "end",
            "in",
            "out",
            "clk",
            "wire",
            "monitor",
            "nonblocking",
            "len",
            "assign",
        ]
        self.names.lookup(self.keywords)

    def group_brackets(self, val: str):
        re_exp = re.compile(r"(\([a-zA-Z0-9+*^! ]*\))")
        return re.split(re_exp, val)

    def expression(self, line: str):
        """Process an expression line."""
        parts = line.split("=")
        if len(parts) != 2:
            raise SyntaxError(f"Invalid expression line: {line}")
        var = parts[0].strip()
        val = parts[1].strip()

        # check there are no variables begining with strings

    def get_symbol(self):
        """Translate the next sequence of characters into a symbol."""
