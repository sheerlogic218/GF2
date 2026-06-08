---
name: device-name-scoping
description: How the parser scopes device raw names (__name__scope__) and how to spot top-level user wires
metadata:
  type: reference
---

The parser names every device `__<name>__<scope>__`, nesting one scope segment per module instance. Splitting the raw name on `__` and dropping empties gives the segment count:

- **2 segments** = top-level user-declared signal, e.g. `__bob__Main__` → `['bob','Main']` (a `wire bob;`, switch, clock, dtype in the top/"Main" module).
- **3+ segments** = module-internal buffers/gates, e.g. `__output__gareth__Main__` → `['output','gareth','Main']`, `__AND 1__gareth__Main`, `__NOT__gareth__Main__<uuid>`.

`Names.prettify_name` returns the first segment (`__bob__Main__` → `bob`; `__output__gareth__Main__` → `output`), so pretty names alone can't tell a user wire from a module port buffer — use the **segment count**.

The Logic Viewer uses this in `_named_wire_label` (in [[underscore-gettext-shadowing]]'s gui.py) to surface only top-level named wires (bob/bill) at the producing gate's output. Verify by running parse.py standalone (no wx needed) on Test_files/.../ALL_FUNCTIONALITY_PASS.txt and dumping `names.get_name_string(did)`.
