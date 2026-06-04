import pytest
import tempfile, os
from names import Names
from devices import Devices
from network import Network
from monitors import Monitors
from scanner import Scanner
from parse import Parser

def parse_text(text):
    """Helper: parse a string and return (success, parser)."""
    names = Names()
    devices = Devices(names)
    network = Network(names, devices)
    monitors = Monitors(names, devices, network)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt',
                                      delete=False) as f:
        f.write(text)
        path = f.name
    try:
        scanner = Scanner(path, names)
        parser = Parser(names, devices, network, monitors, scanner)
        success = parser.parse_network()
        return success, parser
    finally:
        os.unlink(path)

# ── Valid programs ──────────────────────────────────────────────────────────

def test_empty_module_parses():
    ok, _ = parse_text("module m : -> ; end ;")
    assert ok

def test_switch_declaration():
    ok, _ = parse_text("module m : -> ; switch A = 0 ; end ;")
    assert ok

def test_switch_high():
    ok, _ = parse_text("module m : -> ; switch A = 1 ; end ;")
    assert ok

def test_clock_declaration():
    ok, _ = parse_text("module m : -> ; clock clk [5] ; end ;")
    assert ok

def test_wire_declaration():
    ok, _ = parse_text("module m : -> ; wire w ; end ;")
    assert ok

def test_dtype_declaration():
    ok, _ = parse_text("module m : -> ; dtype FF ; end ;")
    assert ok

def test_simple_assignment():
    ok, _ = parse_text("""
        module m : -> ;
            switch A = 1 ;
            switch B = 0 ;
            wire w ;
            w = A + B ;
        end ;
    """)
    assert ok

def test_not_operator():
    ok, _ = parse_text("""
        module m : -> ;
            switch A = 1 ;
            wire w ;
            w = !A ;
        end ;
    """)
    assert ok

def test_and_expression():
    ok, _ = parse_text("""
        module m : -> ;
            switch A = 1 ;
            switch B = 1 ;
            wire w ;
            w = A * B ;
        end ;
    """)
    assert ok

def test_xor_expression():
    ok, _ = parse_text("""
        module m : -> ;
            switch A = 0 ;
            switch B = 1 ;
            wire w ;
            w = A ^ B ;
        end ;
    """)
    assert ok

def test_bracketed_expression():
    ok, _ = parse_text("""
        module m : -> ;
            switch A = 1 ;
            switch B = 0 ;
            switch C = 1 ;
            wire w ;
            w = (A + B) * C ;
        end ;
    """)
    assert ok

def test_monitor_statement():
    ok, _ = parse_text("""
        module m : -> ;
            switch A = 1 ;
            wire w ;
            w = A ;
            monitor w ;
        end ;
    """)
    assert ok

def test_dtype_port_assignment():
    ok, _ = parse_text("""
        module m : -> ;
            switch DATA_in = 1 ;
            switch SET_in = 0 ;
            switch CLR_in = 0 ;
            clock clk [3] ;
            dtype FF1 ;
            FF1.CLK <= clk ;
            FF1.DATA <= DATA_in ;
            FF1.SET <= SET_in ;
            FF1.CLEAR <= CLR_in ;
        end ;
    """)
    assert ok

def test_comment_is_ignored():
    ok, _ = parse_text("""
        module m : -> ;
            // this is a comment
            switch A = 1 ;
        end ;
    """)
    assert ok

def test_multiple_modules():
    ok, _ = parse_text("""
        module m1 : -> ; end ;
        module m2 : -> ; end ;
    """)
    assert ok

def test_complex_boolean_expression():
    """Circuit example 1 from interim report."""
    ok, _ = parse_text("""
        module complex_expr : -> ;
            switch A = 1 ;
            switch B = 0 ;
            switch C = 1 ;
            switch D = 0 ;
            wire out1 ;
            wire out2 ;
            wire out3 ;
            out1 = (A + B) * (C + D) ;
            out2 = !(A + B) ;
            out3 = (A ^ B) + (C * D) ;
            monitor out1 ;
            monitor out2 ;
            monitor out3 ;
        end ;
    """)
    assert ok

# ── Network construction tests ──────────────────────────────────────────────

def test_switch_device_created():
    _, p = parse_text("module m : -> ; switch A = 1 ; end ;")
    switch_ids = p.devices.find_devices(p.devices.SWITCH)
    assert len(switch_ids) == 1

def test_clock_device_created():
    _, p = parse_text("module m : -> ; clock clk [4] ; end ;")
    clock_ids = p.devices.find_devices(p.devices.CLOCK)
    assert len(clock_ids) == 1

def test_dtype_device_created():
    _, p = parse_text("module m : -> ; dtype FF ; end ;")
    dtype_ids = p.devices.find_devices(p.devices.D_TYPE)
    assert len(dtype_ids) == 1

def test_monitor_registered():
    _, p = parse_text("""
        module m : -> ;
            switch A = 1 ;
            wire w ;
            w = A ;
            monitor w ;
        end ;
    """)
    assert len(p.monitors.monitors_dictionary) == 1

# ── Syntax error cases ──────────────────────────────────────────────────────

def test_missing_end_keyword():
    ok, p = parse_text("module m : -> ; switch A = 0 ;")
    assert not ok
    assert p.error_count > 0

def test_missing_semicolon_after_switch():
    ok, p = parse_text("module m : -> ; switch A = 0 end ;")
    assert not ok

def test_invalid_switch_value():
    ok, p = parse_text("module m : -> ; switch A = 2 ; end ;")
    assert not ok

def test_missing_module_keyword():
    ok, p = parse_text("m : -> ; end ;")
    assert not ok

def test_missing_colon_in_header():
    ok, p = parse_text("module m -> ; end ;")
    assert not ok

def test_missing_arrow_in_header():
    ok, p = parse_text("module m : ; end ;")
    assert not ok

def test_missing_semicolon_after_end():
    ok, p = parse_text("module m : -> ; end")
    assert not ok

def test_invalid_port_name():
    ok, p = parse_text("""
        module m : -> ;
            dtype FF ;
            FF.INVALID <= FF ;
        end ;
    """)
    assert not ok

def test_empty_file():
    ok, p = parse_text("")
    # EOF with no module — should fail or produce 0 errors with no network
    # either way, no crash
    assert isinstance(ok, bool)

def test_clock_missing_period():
    ok, p = parse_text("module m : -> ; clock clk ; end ;")
    assert not ok

def test_expression_missing_operand():
    ok, p = parse_text("""
        module m : -> ;
            switch A = 1 ;
            wire w ;
            w = A + ;
        end ;
    """)
    assert not ok

# ── Error count tests ───────────────────────────────────────────────────────

def test_single_error_counted():
    _, p = parse_text("module m : -> ; switch A = 5 ; end ;")
    assert p.error_count >= 1

def test_no_errors_on_valid_input():
    _, p = parse_text("module m : -> ; switch A = 1 ; end ;")
    assert p.error_count == 0