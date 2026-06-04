import pytest
import tempfile, os
from names import Names
from scanner import Scanner, Symbol

def make_scanner(text):
    """Helper: write text to a temp file and return a Scanner."""
    names = Names()
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt',
                                     delete=False) as f:
        f.write(text)
        path = f.name
    scanner = Scanner(path, names)
    yield scanner
    os.unlink(path)

@pytest.fixture
def scanner_factory():
    """Return a factory for creating scanners from text strings."""
    created = []
    def _make(text):
        names = Names()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt',
                                          delete=False) as f:
            f.write(text)
            path = f.name
        created.append(path)
        return Scanner(path, names)
    yield _make
    for p in created:
        os.unlink(p)

# --- Keywords ---
def test_keyword_module(scanner_factory):
    s = scanner_factory("module")
    sym = s.get_symbol()
    assert sym.type == Symbol.KEYWORD
    assert sym.text == "module"

@pytest.mark.parametrize("kw", [
    "module", "wire", "clock", "switch", "dtype", "monitor", "end", "instance"
])
def test_all_keywords_recognised(scanner_factory, kw):
    s = scanner_factory(kw)
    sym = s.get_symbol()
    assert sym.type == Symbol.KEYWORD
    assert sym.text == kw

# --- Names ---
def test_name_symbol(scanner_factory):
    s = scanner_factory("mySignal")
    sym = s.get_symbol()
    assert sym.type == Symbol.NAME
    assert sym.text == "mySignal"

def test_name_with_digits(scanner_factory):
    s = scanner_factory("sig1")
    sym = s.get_symbol()
    assert sym.type == Symbol.NAME
    assert sym.text == "sig1"

def test_name_with_underscore(scanner_factory):
    s = scanner_factory("my_wire")
    sym = s.get_symbol()
    assert sym.type == Symbol.NAME
    assert sym.text == "my_wire"

# --- Numbers ---
def test_number_symbol(scanner_factory):
    s = scanner_factory("42")
    sym = s.get_symbol()
    assert sym.type == Symbol.NUMBER
    assert sym.text == "42"

def test_number_zero(scanner_factory):
    s = scanner_factory("0")
    sym = s.get_symbol()
    assert sym.type == Symbol.NUMBER
    assert sym.text == "0"

# --- Punctuation ---
@pytest.mark.parametrize("char", list("=+*^!,.;:[]()"))
def test_single_char_punctuation(scanner_factory, char):
    s = scanner_factory(char)
    sym = s.get_symbol()
    assert sym.type == Symbol.PUNCTUATION
    assert sym.text == char

def test_arrow_punctuation(scanner_factory):
    s = scanner_factory("->")
    sym = s.get_symbol()
    assert sym.type == Symbol.PUNCTUATION
    assert sym.text == "->"

def test_nonblocking_assign_punctuation(scanner_factory):
    s = scanner_factory("<=")
    sym = s.get_symbol()
    assert sym.type == Symbol.PUNCTUATION
    assert sym.text == "<="

# --- EOF ---
def test_eof(scanner_factory):
    s = scanner_factory("")
    sym = s.get_symbol()
    assert sym.type == Symbol.EOF

# --- Whitespace skipping ---
def test_skips_spaces(scanner_factory):
    s = scanner_factory("   wire")
    sym = s.get_symbol()
    assert sym.type == Symbol.KEYWORD
    assert sym.text == "wire"

def test_skips_newlines(scanner_factory):
    s = scanner_factory("\n\nswitch")
    sym = s.get_symbol()
    assert sym.type == Symbol.KEYWORD

# --- Comment skipping ---
def test_skips_line_comment(scanner_factory):
    s = scanner_factory("// this is a comment\nwire")
    sym = s.get_symbol()
    assert sym.type == Symbol.KEYWORD
    assert sym.text == "wire"

def test_comment_at_end_of_line(scanner_factory):
    s = scanner_factory("wire // comment\nclock")
    sym1 = s.get_symbol()
    sym2 = s.get_symbol()
    assert sym1.text == "wire"
    assert sym2.text == "clock"

# --- Line/position tracking ---
def test_line_number_tracking(scanner_factory):
    s = scanner_factory("wire\nclock")
    s.get_symbol()  # wire on line 1
    sym = s.get_symbol()  # clock on line 2
    assert sym.line == 2

def test_position_tracking(scanner_factory):
    s = scanner_factory("wire")
    sym = s.get_symbol()
    assert sym.pos == 1

# --- Multiple symbols sequence ---
def test_sequence_of_symbols(scanner_factory):
    s = scanner_factory("module myMod : ;")
    types = []
    while True:
        sym = s.get_symbol()
        types.append(sym.type)
        if sym.type == Symbol.EOF:
            break
    assert types == [
        Symbol.KEYWORD,     # module
        Symbol.NAME,        # myMod
        Symbol.PUNCTUATION, # :
        Symbol.PUNCTUATION, # ;
        Symbol.EOF
    ]

# --- Invalid character ---
def test_invalid_character_raises(scanner_factory):
    s = scanner_factory("@")
    with pytest.raises(SyntaxError):
        s.get_symbol()