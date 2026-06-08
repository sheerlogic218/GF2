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
