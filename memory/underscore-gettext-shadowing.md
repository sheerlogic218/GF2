---
name: underscore-gettext-shadowing
description: gui.py aliases _ to wx.GetTranslation, so never use _ as a throwaway variable
metadata:
  type: project
---

In `gui.py`, `_ = wx.GetTranslation` is defined at module level (translation alias). Therefore `_` must NOT be reused as a throwaway loop/unpack variable in any scope that later calls `_("...")` — doing so rebinds `_` to a non-callable value and `_("text")` raises `TypeError: 'list'/'tuple'/'int' object is not callable` at runtime (compiles fine, only fails when that branch executes).

This already caused two crashes: the 3D `render()` loops (`for k, (key, _) in ...` → renamed to `_sig`) and `run_network` (`for _ in range(cycles)` → renamed to `_cycle`, which crashed on `_("Error: network oscillating.")`).

**How to apply:** use `_sig`, `_cycle`, `_unused`, etc. for throwaways in this file — never bare `_`.
