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

    (
        KEYWORD,
        NAME,
        NUMBER,
        PUNCTUATION,
        EOF,
    ) = range(5)

    def __init__(self):
        """Initialise symbol properties."""
        self.type = None
        self.id = None
        self.text = ""
        self.line = 0
        self.pos = 0


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
        # handle file errors
        with open(path, "r") as f:
            self.text = f.read()

        self.names = names
        self.ptr = 0
        self.line_count = 1
        self.line_position = 1

        self.keywords = [
            "module",
            "wire",
            "clock",
            "switch",
            "dtype",
            "monitor",
            "end",
        ]
        self.names.lookup(self.keywords)

    def advance(self) -> None:
        """Advance the pointer to the next character."""
        if self.ptr < len(self.text):
            if self.text[self.ptr] == "\n":
                self.line_count += 1
                self.line_position = 1
            else:
                self.line_position += 1
            self.ptr += 1

    def get_current_char(self) -> str:
        """Get the current character."""
        if self.ptr >= len(self.text):
            return ""
        return self.text[self.ptr]

    def get_next_char(self) -> str:
        """Get the next character."""
        if self.ptr + 1 >= len(self.text):
            return ""
        return self.text[self.ptr + 1]

    def skip_whitespace(self) -> None:
        """Skip whitespace."""
        while self.get_current_char().isspace():
            self.advance()

    def get_symbol(self):
        """Translate the next sequence of characters into a symbol."""
        self.skip_whitespace()

        symbol = Symbol()
        symbol.line = self.line_count
        symbol.pos = self.line_position

        char = self.get_current_char()

        # End of file
        if char == "":
            symbol.type = Symbol.EOF
            return symbol

        # Words/Keywords
        if char.isalpha():
            text = ""
            while char.isalnum() or char == "_":
                text += char
                self.advance()
                char = self.get_current_char()

            symbol.text = text
            if text in self.keywords:
                symbol.type = Symbol.KEYWORD
                symbol.id = self.names.query(text)
            else:
                symbol.type = Symbol.NAME
                [symbol.id] = self.names.lookup([text])
            return symbol

        # Numbers
        if char.isdigit():
            text = ""
            while char.isdigit():
                text += char
                self.advance()
                char = self.get_current_char()
            symbol.type = Symbol.NUMBER
            symbol.text = text
            symbol.id = int(text)
            return symbol

        # multi character punctuation
        if (text := char + self.get_next_char()) in ["->", "<="]:
            symbol.type = Symbol.PUNCTUATION
            symbol.text = text
            [symbol.id] = self.names.lookup([text])
            self.advance()
            self.advance()
            return symbol

        # if (
        #     char == "-"
        #     and self.ptr + 1 < len(self.text)
        #     and self.text[self.ptr + 1] == ">"
        # ):
        #     symbol.type = Symbol.PUNCTUATION
        #     symbol.text = "->"
        #     [symbol.id] = self.names.lookup([symbol.text])
        #     self.advance()
        #     self.advance()
        #     return symbol
        #
        # if (
        #     char == "<"
        #     and self.ptr + 1 < len(self.text)
        #     and self.text[self.ptr + 1] == "="
        # ):
        #     symbol.type = Symbol.PUNCTUATION
        #     symbol.text = "<="
        #     [symbol.id] = self.names.lookup([symbol.text])
        #     self.advance()
        #     self.advance()
        #     return symbol

        if char in "=+*^!,.;:[]()":
            symbol.type = Symbol.PUNCTUATION
            symbol.text = char
            self.advance()
            return symbol

        raise SyntaxError(f"Invalid character {char}")

    # def group_brackets(self, val: str):
    #     re_exp = re.compile(r"(\([a-zA-Z0-9+*^! ]*\))")
    #     return re.split(re_exp, val)
    #
    # def expression(self, line: str):
    #     """Process an expression line."""
    #     parts = line.split("=")
    #     if len(parts) != 2:
    #         raise SyntaxError(f"Invalid expression line: {line}")
    #     var = parts[0].strip()
    #     val = parts[1].strip()
    #
    #     # check there are no variables beginning with strings
