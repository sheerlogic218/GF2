"""flatbutton.py — flat, owner-drawn buttons for wxPython.

A single FlatButton class gives you flat fills, anti-aliased rounded
corners, and hover / press states.  It fires wx.EVT_BUTTON just like a
native wx.Button, so existing handlers bound with
``button.Bind(wx.EVT_BUTTON, handler)`` keep working unchanged.

Variants
--------
- "filled"  : solid accent fill, contrasting text  (primary actions)
- "ghost"   : transparent until hovered            (icon / tertiary buttons)
- "outline" : thin border, fills faintly on hover  (secondary actions)

Set ``pill=True`` for fully rounded ends; with equal width/height that
gives a circle (ideal for small icon buttons like ▶, +, −).

Toggle mode
-----------
Pass ``toggle=True`` to make the button stay pressed on click (like a
wx.ToggleButton).  It fires wx.EVT_TOGGLEBUTTON; call ``GetValue()`` /
``SetValue()`` to read or force the pressed state.  When toggled on the
button is always painted with the "filled" look regardless of variant.
"""

import wx

# Theme-matched defaults: dark-navy / light-panel palette.
ACCENT = wx.Colour(30, 45, 80)          # dark navy — matches caption bars
ACCENT_TEXT = wx.Colour(210, 220, 240)  # pale blue-white text on navy fill
GHOST_TEXT = wx.Colour(45, 55, 75)      # dark text for ghost / outline buttons
_GREEN = wx.Colour(0x1D, 0xB9, 0x54)   # green accent for "go" actions
_GREEN_TEXT = wx.Colour(10, 30, 10)     # near-black text on green fill


def _shift(colour, amount):
    """Lighten (amount > 0) or darken (amount < 0) a colour; amount in [-1,1]."""

    def adj(c):
        return int(c + (255 - c) * amount) if amount >= 0 else int(c * (1 + amount))

    return wx.Colour(adj(colour.Red()), adj(colour.Green()), adj(colour.Blue()))


class FlatButton(wx.Control):
    """A flat, themeable, owner-drawn button."""

    def __init__(
        self,
        parent,
        label="",
        *,
        variant="filled",
        accent=ACCENT,
        fg=None,
        pill=False,
        radius=8,
        font=None,
        size=wx.DefaultSize,
        id=wx.ID_ANY,
        toggle=False,
    ):
        super().__init__(parent, id, size=size, style=wx.BORDER_NONE)

        self._label = label
        self._variant = variant
        self._accent = accent
        self._fg = fg
        self._pill = pill
        self._radius = radius
        self._hover = False
        self._pressed = False
        self._toggle = toggle
        self._toggled = False

        if font is None:
            font = parent.GetFont().Bold()
        self.SetFont(font)

        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.SetCursor(wx.Cursor(wx.CURSOR_HAND))

        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)
        self.Bind(wx.EVT_SIZE, lambda e: (e.Skip(), self.Refresh()))
        self.Bind(wx.EVT_ENTER_WINDOW, self._on_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self._on_leave)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_down)
        self.Bind(wx.EVT_LEFT_UP, self._on_up)
        self.Bind(wx.EVT_LEFT_DCLICK, self._on_down)

    # ── public API (mirrors wx.Button / wx.ToggleButton) ────────────────────
    def SetLabel(self, label):
        self._label = label
        self.InvalidateBestSize()
        self.Refresh()

    def GetLabel(self):
        return self._label

    def SetAccent(self, colour):
        self._accent = colour
        self.Refresh()

    def GetValue(self):
        """Return toggle state (True = on). Only meaningful when toggle=True."""
        return self._toggled

    def SetValue(self, val: bool):
        """Set toggle state without firing an event."""
        self._toggled = bool(val)
        self.Refresh()

    # ── sizing ──────────────────────────────────────────────────────────────
    def DoGetBestSize(self):
        dc = wx.ClientDC(self)
        dc.SetFont(self.GetFont())
        tw, th = dc.GetTextExtent(self._label or "Ag")
        return wx.Size(tw + 32, th + 16)

    # ── interaction handlers ────────────────────────────────────────────────
    def _on_enter(self, _e):
        self._hover = True
        self.Refresh()

    def _on_leave(self, _e):
        self._hover = self._pressed = False
        self.Refresh()

    def _on_down(self, _e):
        if not self.IsThisEnabled():
            return
        self._pressed = True
        if not self.HasCapture():
            self.CaptureMouse()
        self.Refresh()

    def _on_up(self, e):
        if self.HasCapture():
            self.ReleaseMouse()
        was_pressed, self._pressed = self._pressed, False
        if (
            was_pressed
            and self.IsThisEnabled()
            and self.GetClientRect().Contains(e.GetPosition())
        ):
            if self._toggle:
                self._toggled = not self._toggled
                self.Refresh()
                evt = wx.CommandEvent(wx.wxEVT_TOGGLEBUTTON, self.GetId())
                evt.SetInt(1 if self._toggled else 0)
                evt.SetEventObject(self)
                wx.PostEvent(self.GetEventHandler(), evt)
            else:
                self.Refresh()
                evt = wx.CommandEvent(wx.wxEVT_BUTTON, self.GetId())
                evt.SetEventObject(self)
                wx.PostEvent(self.GetEventHandler(), evt)
        else:
            self.Refresh()

    # ── painting ────────────────────────────────────────────────────────────
    def _on_paint(self, _e):
        w, h = self.GetClientSize()
        dc = wx.BufferedPaintDC(self)
        dc.SetBackground(wx.Brush(self.GetParent().GetBackgroundColour()))
        dc.Clear()  # corners blend into the panel

        gc = wx.GCDC(dc)
        radius = h / 2 if self._pill else self._radius
        enabled = self.IsThisEnabled()

        # Toggled-on buttons always render as "filled".
        effective = "filled" if (self._toggle and self._toggled) else self._variant

        if effective == "filled":
            fill = self._accent
            if self._pressed:
                fill = _shift(fill, -0.18)
            elif self._hover:
                fill = _shift(fill, 0.12)
            border = None
            text = self._fg or ACCENT_TEXT
        elif effective == "outline":
            fill = (
                _shift(self._accent, 0.85) if (self._hover or self._pressed) else None
            )
            border = self._accent
            text = self._fg or self._accent
        else:  # "ghost"
            base = self.GetParent().GetBackgroundColour()
            fill = (
                _shift(base, -0.10)
                if self._pressed
                else (_shift(base, -0.05) if self._hover else None)
            )
            border = None
            text = self._fg or GHOST_TEXT

        if not enabled:
            fill = _shift(fill, 0.4) if fill else None
            text = _shift(text, 0.5)

        gc.SetPen(wx.Pen(border, 1) if border else wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(fill) if fill else wx.TRANSPARENT_BRUSH)
        if fill or border:
            gc.DrawRoundedRectangle(0, 0, w - 1, h - 1, radius)

        gc.SetFont(self.GetFont())
        gc.SetTextForeground(text)
        tw, th = gc.GetTextExtent(self._label)
        gc.DrawText(self._label, (w - tw) // 2, (h - th) // 2)


# ── FlatChoice ───────────────────────────────────────────────────────────────

class _FlatChoicePopup(wx.PopupTransientWindow):
    """Owner-drawn drop-down list spawned by FlatChoice."""

    _PAD_X = 10

    def __init__(self, owner: "FlatChoice"):
        super().__init__(owner, wx.BORDER_NONE)
        self._owner = owner
        self._hot = -1

        self.SetFont(owner.GetFont())
        dc = wx.ClientDC(self)
        dc.SetFont(self.GetFont())
        _, th = dc.GetTextExtent("Ag")
        self._item_h = th + 12

        n = len(owner._choices)
        w = max(owner.GetSize().width, 60)
        h = self._item_h * n + 2  # 1-px border top + bottom
        self.SetSize((w, h))

        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)
        self.Bind(wx.EVT_MOTION, self._on_motion)
        self.Bind(wx.EVT_LEFT_UP, self._on_click)
        self.Bind(wx.EVT_LEAVE_WINDOW, self._on_leave)

    def _idx_at(self, y):
        idx = (y - 1) // self._item_h
        return idx if 0 <= idx < len(self._owner._choices) else -1

    def _on_motion(self, e):
        hot = self._idx_at(e.GetY())
        if hot != self._hot:
            self._hot = hot
            self.Refresh()

    def _on_leave(self, _e):
        if self._hot != -1:
            self._hot = -1
            self.Refresh()

    def _on_click(self, e):
        idx = self._idx_at(e.GetY())
        if idx >= 0:
            self._owner._selection = idx
            self._owner.Refresh()
            self.Dismiss()
            evt = wx.CommandEvent(wx.wxEVT_CHOICE, self._owner.GetId())
            evt.SetInt(idx)
            evt.SetString(self._owner._choices[idx])
            evt.SetEventObject(self._owner)
            wx.PostEvent(self._owner.GetEventHandler(), evt)

    def _on_paint(self, _e):
        w, h = self.GetClientSize()
        dc = wx.BufferedPaintDC(self)
        gc = wx.GCDC(dc)

        accent = self._owner._accent
        fg = self._owner._fg or ACCENT_TEXT
        border_col = _shift(accent, 0.35)

        gc.SetPen(wx.Pen(border_col, 1))
        gc.SetBrush(wx.Brush(accent))
        gc.DrawRectangle(0, 0, w, h)

        gc.SetFont(self.GetFont())
        for i, text in enumerate(self._owner._choices):
            y = 1 + i * self._item_h
            if i == self._hot:
                gc.SetPen(wx.TRANSPARENT_PEN)
                gc.SetBrush(wx.Brush(_shift(accent, 0.18)))
                gc.DrawRectangle(1, y, w - 2, self._item_h)
            gc.SetTextForeground(fg)
            _, th = gc.GetTextExtent(text)
            gc.DrawText(text, self._PAD_X, y + (self._item_h - th) // 2)


class FlatChoice(wx.Control):
    """Owner-drawn drop-down styled like FlatButton (filled variant by default).

    Drop-in replacement for wx.Choice — same API: GetSelection / SetSelection /
    GetString / GetStringSelection / GetCount / Append / Clear / Set.
    Fires wx.EVT_CHOICE on selection just like the native widget.
    """

    def __init__(
        self,
        parent,
        id=wx.ID_ANY,
        *,
        choices=None,
        variant="filled",
        accent=ACCENT,
        fg=None,
        pill=False,
        radius=8,
        font=None,
        size=wx.DefaultSize,
        dropup=False,
    ):
        super().__init__(parent, id, size=size, style=wx.BORDER_NONE)
        self._choices = list(choices or [])
        self._selection = 0
        self._variant = variant
        self._accent = accent
        self._fg = fg
        self._pill = pill
        self._radius = radius
        self._hover = False
        self._pressed = False
        self._dropup = dropup

        if font is None:
            font = parent.GetFont().Bold()
        self.SetFont(font)

        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.SetCursor(wx.Cursor(wx.CURSOR_HAND))

        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)
        self.Bind(wx.EVT_SIZE, lambda e: (e.Skip(), self.Refresh()))
        self.Bind(wx.EVT_ENTER_WINDOW, self._on_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self._on_leave)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_down)
        self.Bind(wx.EVT_LEFT_UP, self._on_up)

    # ── wx.Choice-compatible API ─────────────────────────────────────────────
    def GetSelection(self):
        return self._selection

    def SetSelection(self, n):
        self._selection = int(n)
        self.Refresh()

    def GetString(self, n):
        return self._choices[n] if 0 <= n < len(self._choices) else ""

    def GetStringSelection(self):
        return self.GetString(self._selection)

    def SetStringSelection(self, s):
        if s in self._choices:
            self._selection = self._choices.index(s)
            self.Refresh()

    def GetCount(self):
        return len(self._choices)

    def Append(self, item):
        self._choices.append(item)
        self.InvalidateBestSize()
        self.Refresh()

    def Clear(self):
        self._choices.clear()
        self._selection = 0
        self.Refresh()

    def Set(self, choices):
        self._choices = list(choices)
        self._selection = 0
        self.InvalidateBestSize()
        self.Refresh()

    # ── sizing ───────────────────────────────────────────────────────────────
    def DoGetBestSize(self):
        dc = wx.ClientDC(self)
        dc.SetFont(self.GetFont())
        max_w = max((dc.GetTextExtent(c)[0] for c in self._choices), default=40)
        th = dc.GetTextExtent("Ag")[1]
        return wx.Size(max_w + 48, th + 16)

    # ── interaction ──────────────────────────────────────────────────────────
    def _on_enter(self, _e):
        self._hover = True
        self.Refresh()

    def _on_leave(self, _e):
        self._hover = self._pressed = False
        self.Refresh()

    def _on_down(self, _e):
        if not self.IsThisEnabled():
            return
        self._pressed = True
        if not self.HasCapture():
            self.CaptureMouse()
        self.Refresh()

    def _on_up(self, e):
        if self.HasCapture():
            self.ReleaseMouse()
        was_pressed, self._pressed = self._pressed, False
        self.Refresh()
        if (
            was_pressed
            and self.IsThisEnabled()
            and self.GetClientRect().Contains(e.GetPosition())
        ):
            popup = _FlatChoicePopup(self)
            if self._dropup:
                pos = self.ClientToScreen((0, -popup.GetSize().height))
            else:
                pos = self.ClientToScreen((0, self.GetSize().height))
            popup.SetPosition(pos)
            popup.Popup()

    # ── painting ─────────────────────────────────────────────────────────────
    def _on_paint(self, _e):
        w, h = self.GetClientSize()
        dc = wx.BufferedPaintDC(self)
        dc.SetBackground(wx.Brush(self.GetParent().GetBackgroundColour()))
        dc.Clear()
        gc = wx.GCDC(dc)
        radius = h / 2 if self._pill else self._radius

        fill = self._accent
        if self._pressed:
            fill = _shift(fill, -0.18)
        elif self._hover:
            fill = _shift(fill, 0.12)
        text_col = self._fg or ACCENT_TEXT

        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(fill))
        gc.DrawRoundedRectangle(0, 0, w - 1, h - 1, radius)

        gc.SetFont(self.GetFont())
        gc.SetTextForeground(text_col)

        arrow = "▴" if self._dropup else "▾"
        aw, _ = gc.GetTextExtent(arrow)
        arrow_x = w - aw - 8
        _, ah = gc.GetTextExtent(arrow)
        gc.DrawText(arrow, arrow_x, (h - ah) // 2)

        label = self.GetStringSelection()
        tw, th_ = gc.GetTextExtent(label)
        gc.DrawText(label, (arrow_x - tw) // 2, (h - th_) // 2)


# ── quick visual demo ────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = wx.App()
    frame = wx.Frame(None, title="FlatButton demo", size=(480, 120))
    bg = wx.Colour(240, 242, 247)
    frame.SetBackgroundColour(bg)
    panel = wx.Panel(frame)
    panel.SetBackgroundColour(bg)
    s = wx.BoxSizer(wx.HORIZONTAL)
    for btn in [
        FlatButton(panel, "▶", variant="filled", accent=_GREEN, fg=_GREEN_TEXT, pill=True, size=(40, 40)),
        FlatButton(panel, "Logic Viewer", variant="outline", size=(-1, 40)),
        FlatButton(panel, "3D", variant="ghost", toggle=True, size=(52, 40)),
        FlatButton(panel, "ON", variant="filled", accent=_GREEN, fg=_GREEN_TEXT, size=(-1, 40)),
        FlatButton(panel, "OFF", variant="outline", size=(-1, 40)),
        FlatButton(panel, "↺", variant="ghost", pill=True, size=(40, 40)),
    ]:
        s.Add(btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 8)
    panel.SetSizer(s)
    frame.Show()
    app.MainLoop()
