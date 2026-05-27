"""Implement the graphical user interface for the Logic Simulator.

Used in the Logic Simulator project to enable the user to run the simulation
or adjust the network properties.

Classes:
--------
MyGLCanvas - handles all canvas drawing operations.
Gui - configures the main window and all the widgets.
"""

import wx
import wx.glcanvas as wxcanvas
from OpenGL import GL, GLUT
import datetime
from names import Names
from devices import Devices
from network import Network
from monitors import Monitors
from scanner import Scanner
from parse import Parser

# Custom menu ID for the file viewer toggle
ID_TOGGLE_VIEWER = wx.NewIdRef()


class MyGLCanvas(wxcanvas.GLCanvas):
    """Handle all drawing operations."""

    def __init__(self, parent, devices, monitors):
        """Initialise canvas properties and useful variables."""
        super().__init__(
            parent,
            -1,
            attribList=[
                wxcanvas.WX_GL_RGBA,
                wxcanvas.WX_GL_DOUBLEBUFFER,
                wxcanvas.WX_GL_DEPTH_SIZE,
                16,
                0,
            ],
        )
        GLUT.glutInit()
        self.init = False
        self.context = wxcanvas.GLContext(self)

        # Initialise variables for panning
        self.pan_x = 0
        self.pan_y = 0
        self.pan_x_pct = 0.0
        self.pan_y_pct = 0.0
        self.last_mouse_x = 0  # previous mouse x position
        self.last_mouse_y = 0  # previous mouse y position

        # Initialise variables for zooming
        self.zoom = 1.0

        # Bind events to the canvas
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.on_mouse)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

    def init_gl(self):
        """Configure and initialise the OpenGL context and camera."""
        size = self.GetClientSize()
        width = max(1, size.width)
        height = max(1, size.height)

        GL.glViewport(0, 0, width, height)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()

        zoom_factor = getattr(self, 'zoom', 1.0)
        pan_x_pct = getattr(self, 'pan_x_pct', 0.0)
        pan_y_pct = getattr(self, 'pan_y_pct', 0.0)

        visible_width = width / zoom_factor
        visible_height = height / zoom_factor

        max_pan_x = max(0.0, width - visible_width)
        max_pan_y = max(0.0, height - visible_height)

        self.pan_x = max_pan_x * pan_x_pct
        self.pan_y = max_pan_y * pan_y_pct

        left = self.pan_x
        right = self.pan_x + visible_width
        bottom = self.pan_y + visible_height
        top = self.pan_y

        GL.glOrtho(left, right, bottom, top, -1, 1)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()

    def render(self, text=""):
        """Handle all drawing operations."""
        self.SetCurrent(self.context)
        if not self.init:
            self.init_gl()
            self.init = True

        GL.glClear(GL.GL_COLOR_BUFFER_BIT)

        size = self.GetClientSize()
        canvas_width = size.width
        canvas_height = size.height

        box_x_start = 80
        box_x_end = canvas_width - 40

        box_y_bot = 20
        box_y_top = canvas_height - 20

        high_y = box_y_bot + (box_y_top - box_y_bot) * 0.25
        low_y = box_y_bot + (box_y_top - box_y_bot) * 0.75

        num_cycles = 10
        cycle_width = (box_x_end - box_x_start) / num_cycles

        hud_x_position = self.pan_x + 20

        self.render_text("High", hud_x_position, high_y - 4)
        self.render_text("Low", hud_x_position, low_y - 4)

        GL.glColor3f(0.3, 0.4, 0.5)
        GL.glLineWidth(1.5)
        GL.glBegin(GL.GL_LINE_LOOP)
        GL.glVertex2f(box_x_start, box_y_bot)
        GL.glVertex2f(box_x_end, box_y_bot)
        GL.glVertex2f(box_x_end, box_y_top)
        GL.glVertex2f(box_x_start, box_y_top)
        GL.glEnd()

        GL.glEnable(GL.GL_LINE_STIPPLE)
        GL.glLineStipple(1, 0x00FF)
        GL.glColor3f(0.4, 0.4, 0.4)
        GL.glLineWidth(1.0)
        GL.glBegin(GL.GL_LINES)
        GL.glVertex2f(box_x_start, high_y)
        GL.glVertex2f(box_x_end, high_y)
        GL.glVertex2f(box_x_start, low_y)
        GL.glVertex2f(box_x_end, low_y)
        GL.glEnd()
        GL.glDisable(GL.GL_LINE_STIPPLE)

        GL.glEnable(GL.GL_LINE_STIPPLE)
        GL.glLineStipple(1, 0x00FF)
        GL.glColor3f(0.2, 0.3, 0.4)
        GL.glBegin(GL.GL_LINES)
        for i in range(num_cycles + 1):
            x = box_x_start + (i * cycle_width)
            GL.glVertex2f(x, box_y_bot)
            GL.glVertex2f(x, box_y_top)
        GL.glEnd()
        GL.glDisable(GL.GL_LINE_STIPPLE)

        GL.glColor3f(0.0, 1.0, 0.4)
        GL.glLineWidth(2.5)
        GL.glBegin(GL.GL_LINE_STRIP)
        for i in range(num_cycles):
            x = box_x_start + (i * cycle_width)
            x_next = box_x_start + ((i + 1) * cycle_width)
            current_y = high_y if i % 2 == 0 else low_y

            GL.glVertex2f(x, current_y)
            GL.glVertex2f(x_next, current_y)

            if i < num_cycles - 1:
                next_y = low_y if i % 2 == 0 else high_y
                GL.glVertex2f(x_next, current_y)
                GL.glVertex2f(x_next, next_y)
        GL.glEnd()
        GL.glLineWidth(1.0)

        GL.glFlush()
        self.SwapBuffers()

    def on_paint(self, event):
        """Handle the paint event."""
        self.SetCurrent(self.context)
        if not self.init:
            self.init_gl()
            self.init = True

        size = self.GetClientSize()
        text = "".join(
            [
                "Canvas redrawn on paint event, size is ",
                str(size.width),
                ", ",
                str(size.height),
            ]
        )
        self.render(text)

    def on_size(self, event):
        """Handle canvas resize events cleanly without duplicating ortho configurations."""
        self.init = False
        self.Refresh()
        
        # Notify Gui to update scrollbars on resize
        gui = self.GetParent()
        while gui and not hasattr(gui, 'update_scrollbars'):
            gui = gui.GetParent()
        if gui:
            gui.update_scrollbars()
        if event.Entering():
            self.SetFocus()

    def on_mouse(self, event):
        """Handle mouse events (navigation handled by scrollbars and mouse wheel/dragging)."""
        # Find the parent Gui frame to trigger scrollbar updates
        gui = self.GetParent()
        while gui and not hasattr(gui, 'update_scrollbars'):
            gui = gui.GetParent()

        # Handle mouse wheel zooming
        rotation = event.GetWheelRotation()
        if rotation != 0:
            old_zoom = self.zoom
            if rotation > 0:
                self.zoom = min(5.0, self.zoom * 1.1)
            else:
                self.zoom = max(1.0, self.zoom / 1.1)

            if self.zoom != old_zoom:
                # Clamp pan percentages if they got out of range under new zoom
                size = self.GetClientSize()
                width = max(1, size.width)
                height = max(1, size.height)
                visible_width = width / self.zoom
                visible_height = height / self.zoom
                max_pan_x = max(0.0, width - visible_width)
                max_pan_y = max(0.0, height - visible_height)

                self.pan_x = max(0.0, min(self.pan_x, max_pan_x))
                self.pan_y = max(0.0, min(self.pan_y, max_pan_y))
                self.pan_x_pct = self.pan_x / max_pan_x if max_pan_x > 0 else 0.0
                self.pan_y_pct = self.pan_y / max_pan_y if max_pan_y > 0 else 0.0

                self.init = False
                self.Refresh()
                if gui:
                    gui.update_scrollbars()

        # Handle mouse dragging for panning
        elif event.ButtonDown(wx.MOUSE_BTN_LEFT):
            self.last_mouse_x, self.last_mouse_y = event.GetPosition()
        elif event.Dragging() and event.LeftIsDown():
            curr_x, curr_y = event.GetPosition()
            dx = curr_x - self.last_mouse_x
            dy = curr_y - self.last_mouse_y
            self.last_mouse_x, self.last_mouse_y = curr_x, curr_y

            size = self.GetClientSize()
            width = max(1, size.width)
            height = max(1, size.height)
            visible_width = width / self.zoom
            visible_height = height / self.zoom
            max_pan_x = max(0.0, width - visible_width)
            max_pan_y = max(0.0, height - visible_height)

            gl_dx = (dx / width) * visible_width
            gl_dy = (dy / height) * visible_height

            new_pan_x = self.pan_x - gl_dx
            new_pan_y = self.pan_y - gl_dy

            new_pan_x = max(0.0, min(new_pan_x, max_pan_x))
            new_pan_y = max(0.0, min(new_pan_y, max_pan_y))

            self.pan_x_pct = new_pan_x / max_pan_x if max_pan_x > 0 else 0.0
            self.pan_y_pct = new_pan_y / max_pan_y if max_pan_y > 0 else 0.0

            self.init = False
            self.Refresh()
            if gui:
                gui.update_scrollbars()

    def render_text(self, text, x_pos, y_pos):
        """Handle text drawing operations."""
        GL.glColor3f(1.0, 1.0, 1.0)
        GL.glRasterPos2f(x_pos, y_pos)
        font = GLUT.GLUT_BITMAP_HELVETICA_12

        for character in text:
            if character == "\n":
                y_pos = y_pos - 20
                GL.glRasterPos2f(x_pos, y_pos)
            else:
                GLUT.glutBitmapCharacter(font, ord(character))
    
    def on_key_down(self, event):
        """Zoom in/out with Ctrl+= or Ctrl+- when canvas has focus."""
        if event.ControlDown():
            key = event.GetKeyCode()
            gui = self.GetParent()
            while gui and not hasattr(gui, 'on_zoom_in'):
                gui = gui.GetParent()
            if gui:
                if key in (wx.WXK_NUMPAD_ADD, ord("="), ord("+")):
                    gui.on_zoom_in(None)
                elif key in (wx.WXK_NUMPAD_SUBTRACT, ord("-")):
                    gui.on_zoom_out(None)
        event.Skip()


class Gui(wx.Frame):
    """Configure the main window and all the widgets."""

    def __init__(self, title, path, names, devices, network, monitors):
        """Initialise widgets and layout."""
        super().__init__(parent=None, title=title, size=(1100, 600))

        # Track the currently viewed file path
        self._viewer_path = path
        self._viewer_visible = False

        # ── Menu bar ────────────────────────────────────────────────────────
        fileMenu = wx.Menu()
        fileMenu.Append(wx.ID_OPEN, "&Open")
        fileMenu.Append(wx.ID_SAVE, "&Save")
        fileMenu.AppendSeparator()
        fileMenu.Append(wx.ID_ABOUT, "&About")
        fileMenu.Append(wx.ID_EXIT, "&Exit")

        viewMenu = wx.Menu()
        self._viewer_menu_item = viewMenu.AppendCheckItem(
            ID_TOGGLE_VIEWER, "&Show File Viewer\tCtrl+Shift+F"
        )

        menuBar = wx.MenuBar()
        menuBar.Append(fileMenu, "&File")
        menuBar.Append(viewMenu, "&View")
        self.SetMenuBar(menuBar)

        # ── Outer horizontal splitter (simulator | file viewer) ─────────────
        # SP_LIVE_UPDATE gives smooth dragging; SP_NO_XP_THEME keeps it clean.
        self.outer_splitter = wx.SplitterWindow(
            self, style=wx.SP_LIVE_UPDATE | wx.SP_NO_XP_THEME
        )
        self.outer_splitter.SetMinimumPaneSize(200)

        # Left pane wraps the existing horizontal (controls / canvas) layout
        self.left_pane = wx.Panel(self.outer_splitter)

        # Right pane: file viewer – built before the splitter is configured
        self._build_file_viewer(self.outer_splitter)

        # Start with only the left pane visible
        self.outer_splitter.Initialize(self.left_pane)

        # ── Inner horizontal splitter (controls top | GL canvas bottom) ─────
        self.splitter = wx.SplitterWindow(
            self.left_pane, style=wx.SP_LIVE_UPDATE | wx.SP_NO_XP_THEME
        )

        # Container panel for canvas and scrollbars
        self.canvas_panel = wx.Panel(self.splitter)

        # Canvas for drawing signals
        self.canvas = MyGLCanvas(self.canvas_panel, devices, monitors)

        # Scrollbars
        self.v_scroll = wx.ScrollBar(self.canvas_panel, style=wx.SB_VERTICAL)
        self.h_scroll = wx.ScrollBar(self.canvas_panel, style=wx.SB_HORIZONTAL)

        self.v_scroll.Bind(wx.EVT_SCROLL, self.on_v_scroll)
        self.h_scroll.Bind(wx.EVT_SCROLL, self.on_h_scroll)

        # Arrange canvas and scrollbars like on a document
        canvas_sizer = wx.GridBagSizer(0, 0)
        canvas_sizer.Add(self.canvas, pos=(0, 0), flag=wx.EXPAND)
        canvas_sizer.Add(self.v_scroll, pos=(0, 1), flag=wx.EXPAND)
        canvas_sizer.Add(self.h_scroll, pos=(1, 0), flag=wx.EXPAND)
        canvas_sizer.AddGrowableCol(0)
        canvas_sizer.AddGrowableRow(0)
        self.canvas_panel.SetSizer(canvas_sizer)

        self.top_panel = wx.Panel(self.splitter)

        # ── Widgets ──────────────────────────────────────────────────────────
        self.cycles_label = wx.StaticText(self.top_panel, wx.ID_ANY, "Cycles")
        self.spin = wx.SpinCtrl(self.top_panel, wx.ID_ANY, "10", min=1, max=1000, size=(110, -1))
        self.run_button = wx.Button(self.top_panel, wx.ID_ANY, "▶", size=(32, 28))
        self.continue_button = wx.Button(self.top_panel, wx.ID_ANY, "+10", size=(45, 28))

        self.switch_label = wx.StaticText(self.top_panel, wx.ID_ANY, "Select switch:")
        self.switch_choice = wx.Choice(self.top_panel, wx.ID_ANY,
                                       choices=["SW1", "SW2", "SW3"])
        self.switch_on = wx.Button(self.top_panel, wx.ID_ANY, "Set ON")
        self.switch_off = wx.Button(self.top_panel, wx.ID_ANY, "Set OFF")

        self.monitors_label = wx.StaticText(self.top_panel, wx.ID_ANY, "Monitors:")
        self.monitors_list = wx.ListBox(
            self.top_panel, wx.ID_ANY,
            choices=["Signal1", "Signal2"],
            style=wx.LB_SINGLE
        )
        self.add_monitor_btn = wx.Button(self.top_panel, wx.ID_ANY, "+")
        self.remove_monitor_btn = wx.Button(self.top_panel, wx.ID_ANY, "-")

        self.reset_button = wx.Button(self.top_panel, wx.ID_ANY, "↺", size=(32, 28))

        self.console = wx.TextCtrl(
            self.top_panel, wx.ID_ANY, "",
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL
        )
        console_font = wx.Font(
            9, wx.FONTFAMILY_TELETYPE,
            wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL
        )
        self.console.SetFont(console_font)

        # Tooltips
        self.run_button.SetToolTip("Run the simulation from scratch for N cycles")
        self.continue_button.SetToolTip("Continue the simulation for N additional cycles")
        self.reset_button.SetToolTip("Reset the simulation to its initial state")
        self.switch_on.SetToolTip("Set the selected switch to ON (1)")
        self.switch_off.SetToolTip("Set the selected switch to OFF (0)")
        self.add_monitor_btn.SetToolTip("Add a monitor to the selected signal")
        self.remove_monitor_btn.SetToolTip("Remove the selected monitor")
        self.spin.SetToolTip("Number of cycles to run or continue")

        # ── Event bindings ───────────────────────────────────────────────────
        self.Bind(wx.EVT_MENU, self.on_menu)
        self.spin.Bind(wx.EVT_SPINCTRL, self.on_spin)
        self.run_button.Bind(wx.EVT_BUTTON, self.on_run_button)
        self.continue_button.Bind(wx.EVT_BUTTON, self.on_continue_button)
        self.switch_on.Bind(wx.EVT_BUTTON, self.on_switch_on)
        self.switch_off.Bind(wx.EVT_BUTTON, self.on_switch_off)
        self.add_monitor_btn.Bind(wx.EVT_BUTTON, self.on_add_monitor)
        self.remove_monitor_btn.Bind(wx.EVT_BUTTON, self.on_remove_monitor)
        self.reset_button.Bind(wx.EVT_BUTTON, self.on_reset_button)

        # ── Control-panel sizer ──────────────────────────────────────────────
        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.top_panel.SetSizer(top_sizer)
        top_sizer.SetMinSize((-1, 150))

        # Simulation box
        sim_box = wx.StaticBox(self.top_panel, wx.ID_ANY, "Simulation")
        sim_sizer = wx.StaticBoxSizer(sim_box, wx.VERTICAL)
        sim_sizer.Add(self.cycles_label, 0, wx.ALL, 5)
        sim_sizer.Add(self.spin, 0, wx.EXPAND | wx.ALL, 5)

        # Buttons laid out side-by-side
        sim_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sim_btn_sizer.Add(self.run_button, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        sim_btn_sizer.Add(self.continue_button, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        sim_btn_sizer.Add(self.reset_button, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        sim_sizer.Add(sim_btn_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP | wx.BOTTOM, 3)

        # Switches box
        switch_box = wx.StaticBox(self.top_panel, wx.ID_ANY, "Switches")
        switch_sizer = wx.StaticBoxSizer(switch_box, wx.VERTICAL)
        switch_sizer.Add(self.switch_label, 0, wx.ALL, 5)
        switch_sizer.Add(self.switch_choice, 0, wx.EXPAND | wx.ALL, 5)

        # Monitors box
        monitor_box = wx.StaticBox(self.top_panel, wx.ID_ANY, "Monitors")
        monitor_sizer = wx.StaticBoxSizer(monitor_box, wx.VERTICAL)
        monitor_sizer.Add(self.monitors_label, 0, wx.ALL, 5)
        monitor_sizer.Add(self.monitors_list, 0, wx.EXPAND | wx.ALL, 5)
        # Side-by-side '+' and '-' buttons
        monitor_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        monitor_btn_sizer.Add(self.add_monitor_btn, 1, wx.ALL, 2)
        monitor_btn_sizer.Add(self.remove_monitor_btn, 1, wx.ALL, 2)
        monitor_sizer.Add(monitor_btn_sizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 3)

        # Console box
        console_box = wx.StaticBox(self.top_panel, wx.ID_ANY, "Console")
        console_sizer = wx.StaticBoxSizer(console_box, wx.VERTICAL)
        console_sizer.Add(self.console, 1, wx.EXPAND | wx.ALL, 5)

        # View controls box
        self.view_box = wx.StaticBox(self.top_panel, label="View Controls")
        self.view_sizer = wx.StaticBoxSizer(self.view_box, wx.VERTICAL)

        self.zoom_label = wx.StaticText(self.top_panel, label="Zoom: 100%")
        self.zoom_in_btn = wx.Button(self.top_panel, label="Zoom In (+)", size=(-1, 28))
        self.zoom_out_btn = wx.Button(self.top_panel, label="Zoom Out (-)", size=(-1, 28))

        self.zoom_in_btn.SetToolTip("Zoom in on the simulation canvas")
        self.zoom_out_btn.SetToolTip("Zoom out on the simulation canvas")

        self.zoom_in_btn.Bind(wx.EVT_BUTTON, self.on_zoom_in)
        self.zoom_out_btn.Bind(wx.EVT_BUTTON, self.on_zoom_out)

        self.reset_view_btn = wx.Button(self.top_panel, label="Reset View")
        self.reset_view_btn.SetToolTip("Reset zoom and pan to default")
        self.reset_view_btn.Bind(wx.EVT_BUTTON, self.on_reset_view)

        zoom_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        zoom_btn_sizer.Add(self.zoom_in_btn, 1, wx.ALL, 2)
        zoom_btn_sizer.Add(self.zoom_out_btn, 1, wx.ALL, 2)

        self.view_sizer.Add(self.zoom_label, 0, wx.LEFT | wx.TOP | wx.BOTTOM, 5)
        self.view_sizer.Add(zoom_btn_sizer, 0, wx.EXPAND | wx.BOTTOM, 5)
        self.view_sizer.Add(self.reset_view_btn, 0, wx.EXPAND | wx.ALL, 2)

        # Switch ON/OFF buttons side-by-side
        switch_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        switch_btn_sizer.Add(self.switch_on, 1, wx.ALL, 5)
        switch_btn_sizer.Add(self.switch_off, 1, wx.ALL, 5)
        switch_sizer.Add(switch_btn_sizer, 0, wx.EXPAND)

        top_sizer.Add(sim_sizer, 0, wx.EXPAND | wx.ALL, 2)
        top_sizer.Add(switch_sizer, 0, wx.EXPAND | wx.ALL, 2)
        top_sizer.Add(monitor_sizer, 0, wx.EXPAND | wx.ALL, 2)
        top_sizer.Add(self.view_sizer, 0, wx.EXPAND | wx.ALL, 2)
        top_sizer.Add(console_sizer, 1, wx.EXPAND | wx.ALL, 2)

        # ── Inner splitter split ─────────────────────────────────────────────
        self.splitter.SplitHorizontally(self.top_panel, self.canvas_panel, 180)
        self.splitter.SetMinimumPaneSize(145)

        # ── Left-pane sizer wraps the inner splitter ─────────────────────────
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        left_sizer.Add(self.splitter, 1, wx.EXPAND)
        self.left_pane.SetSizer(left_sizer)

        # ── Frame sizer wraps the outer splitter ─────────────────────────────
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.outer_splitter, 1, wx.EXPAND)
        self.SetSizeHints(700, 400)
        self.SetSizer(main_sizer)

        self.CreateStatusBar()
        self.SetStatusText("Ready")

        # Initialise scrollbar state
        self.update_scrollbars()

        # Load the initial file into the viewer if one was provided
        if path:
            self._load_file_into_viewer(path)

    # ── File viewer ──────────────────────────────────────────────────────────

    def _build_file_viewer(self, parent):
        """Create the right-hand file-viewer panel and attach it to parent."""
        self.viewer_panel = wx.Panel(parent)
        self.viewer_panel.Hide()  # prevent rendering at (0,0) before first split
        viewer_sizer = wx.BoxSizer(wx.VERTICAL)

        # Header bar: label + close button
        header_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._viewer_title = wx.StaticText(
            self.viewer_panel, label="File Viewer",
            style=wx.ST_ELLIPSIZE_END
        )
        title_font = self._viewer_title.GetFont()
        title_font.SetWeight(wx.FONTWEIGHT_BOLD)
        self._viewer_title.SetFont(title_font)

        save_btn = wx.Button(self.viewer_panel, label="Save", size=(50, 28))
        save_btn.SetToolTip("Save changes to file")
        save_btn.Bind(wx.EVT_BUTTON, self._on_save_viewer)

        close_btn = wx.Button(self.viewer_panel, label="X", size=(28, 28))
        close_btn.SetToolTip("Close file viewer")
        close_btn.Bind(wx.EVT_BUTTON, self._on_close_viewer)

        header_sizer.Add(self._viewer_title, 1, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 6)
        header_sizer.Add(save_btn, 0, wx.ALL, 2)
        header_sizer.Add(close_btn, 0, wx.ALL, 2)

        # Read-only text area with monospace font
        self._file_text = wx.TextCtrl(
            self.viewer_panel,
            style=wx.TE_MULTILINE | wx.TE_DONTWRAP | wx.HSCROLL
        )
        mono_font = wx.Font(
            10, wx.FONTFAMILY_TELETYPE,
            wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL
        )
        self._file_text.SetFont(mono_font)
        self._file_text.SetBackgroundColour(wx.Colour(20, 24, 32))
        self._file_text.SetForegroundColour(wx.Colour(210, 220, 235))

        viewer_sizer.Add(header_sizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 4)
        viewer_sizer.Add(
            wx.StaticLine(self.viewer_panel), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 4
        )
        viewer_sizer.Add(self._file_text, 1, wx.EXPAND | wx.ALL, 4)
        self.viewer_panel.SetSizer(viewer_sizer)

    def _load_file_into_viewer(self, path):
        """Read path and display its contents in the file viewer."""
        try:
            with open(path, "r") as fh:
                content = fh.read()
            self._file_text.SetValue(content)
            filename = path.split("/")[-1].split("\\")[-1]
            self._viewer_title.SetLabel(f"File Viewer — {filename}")
            self._viewer_title.SetToolTip(path)
        except OSError as exc:
            self._file_text.SetValue(f"Could not open file:\n{exc}")
            self._viewer_title.SetLabel("File Viewer — error")

    def _show_viewer(self):
        """Slide the file viewer in by splitting the outer splitter."""
        if not self._viewer_visible:
            w = self.GetClientSize().width
            self.outer_splitter.SplitVertically(
                self.left_pane, self.viewer_panel,
                w - 380          # viewer starts at 380 px wide
            )
            self._viewer_visible = True
            self._viewer_menu_item.Check(True)
            self.SetStatusText("File viewer opened.")

    def _hide_viewer(self):
        """Collapse the file viewer by un-splitting."""
        if self._viewer_visible:
            self.outer_splitter.Unsplit(self.viewer_panel)
            self._viewer_visible = False
            self._viewer_menu_item.Check(False)
            self.SetStatusText("File viewer closed.")

    def _on_save_viewer(self, event):
        """Save the current contents of the file viewer back to disk."""
        if not self._viewer_path:
            wx.MessageBox(
                "No file is open — nothing to save.",
                "Save", wx.ICON_WARNING | wx.OK
            )
            return
        try:
            with open(self._viewer_path, "w") as fh:
                fh.write(self._file_text.GetValue())
            self.SetStatusText(f"Saved: {self._viewer_path}")
            self.log(f"File saved: {self._viewer_path}")
        except OSError as exc:
            wx.MessageBox(
                f"Could not save file:\n{exc}",
                "Save Error", wx.ICON_ERROR | wx.OK
            )

    def _on_close_viewer(self, event):
        """Handle the X button inside the viewer panel."""
        self._hide_viewer()

    # ── Menu ─────────────────────────────────────────────────────────────────

    def on_menu(self, event):
        """Handle the event when the user selects a menu item."""
        Id = event.GetId()
        if Id == wx.ID_EXIT:
            self.Close(True)

        elif Id == wx.ID_ABOUT:
            wx.MessageBox(
                "Logic Simulator\nGF2 Software Project\n"
                "Cambridge University Engineering Department\n2026",
                "About Logic Simulator",
                wx.ICON_INFORMATION | wx.OK,
            )

        elif Id == wx.ID_SAVE:
            self._on_save_viewer(event)

        elif Id == wx.ID_OPEN:
            wildcard = "Circuit definition files (*.txt)|*.txt|All files (*.*)|*.*"
            dlg = wx.FileDialog(
                self, "Open circuit definition file",
                wildcard=wildcard,
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
            )
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                self._viewer_path = path
                self.SetTitle("Logic Simulator - " + path)
                self.SetStatusText("Opened: " + path)
                self.log("Opened file: " + path)
                # Load into viewer and show the panel
                self._load_file_into_viewer(path)
                self._show_viewer()
            dlg.Destroy()

        elif Id == ID_TOGGLE_VIEWER:
            if self._viewer_visible:
                self._hide_viewer()
            else:
                # Reload current file before showing
                if self._viewer_path:
                    self._load_file_into_viewer(self._viewer_path)
                self._show_viewer()

    # ── Widget event handlers ─────────────────────────────────────────────────

    def on_spin(self, event):
        """Handle the event when the user changes the spin control value."""
        spin_value = self.spin.GetValue()
        self.continue_button.SetLabel(f"+{spin_value}")
        text = "".join(["New spin control value: ", str(spin_value)])
        self.canvas.render(text)
        self.log(text)

    def on_run_button(self, event):
        """Handle the event when the user clicks the run button."""
        cycles = self.spin.GetValue()
        self.SetStatusText("Running for " + str(cycles) + " cycles...")
        self.log("Run clicked: " + str(cycles) + " cycles requested.")
        self.canvas.render("")

    def on_continue_button(self, event):
        """Handle the event when the user clicks the continue button."""
        cycles = self.spin.GetValue()
        self.SetStatusText("Continuing for " + str(cycles) + " cycles...")
        self.log("Continue clicked: " + str(cycles) + " cycles requested.")

    def on_switch_on(self, event):
        """Handle the event when the user clicks the switch on button."""
        selection = self.switch_choice.GetSelection()
        if selection == wx.NOT_FOUND:
            self.SetStatusText("Error: please select a switch first.")
            return
        switch = self.switch_choice.GetString(selection)
        self.SetStatusText("Switch " + switch + " set ON.")
        self.log("Switch " + switch + " set ON.")

    def on_switch_off(self, event):
        """Handle the event when the user clicks the switch off button."""
        selection = self.switch_choice.GetSelection()
        if selection == wx.NOT_FOUND:
            self.SetStatusText("Error: please select a switch first.")
            return
        switch = self.switch_choice.GetString(selection)
        self.SetStatusText("Switch " + switch + " set OFF.")
        self.log("Switch " + switch + " set OFF.")

    def on_add_monitor(self, event):
        """Handle the event when the user clicks the add monitor button."""
        text = "Add monitor pressed."
        self.canvas.render(text)
        self.log("Add monitor pressed.")

    def on_remove_monitor(self, event):
        """Handle the event when the user clicks the remove monitor button."""
        text = "Remove monitor pressed."
        self.canvas.render(text)
        self.log("Remove monitor pressed.")

    def on_reset_button(self, event):
        """Handle the event when the user clicks the reset button."""
        self.SetStatusText("Simulation reset.")
        self.canvas.render("Simulation reset.")
        self.log("Simulation reset.")

    def log(self, message):
        """Append a time-stamped message to the console output."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.console.AppendText(f"[{timestamp}] {message}\n")

    def on_h_scroll(self, event):
        """Handle horizontal scrollbar scrolling."""
        zoom = getattr(self.canvas, 'zoom', 1.0)
        range_max = 10000
        thumb_size = int(range_max / zoom)
        scrollable_x = range_max - thumb_size
        
        if scrollable_x > 0:
            pos = self.h_scroll.GetThumbPosition()
            self.canvas.pan_x_pct = pos / scrollable_x
        else:
            self.canvas.pan_x_pct = 0.0
            
        self.canvas.init = False
        self.canvas.Refresh()

    def on_v_scroll(self, event):
        """Handle vertical scrollbar scrolling."""
        zoom = getattr(self.canvas, 'zoom', 1.0)
        range_max = 10000
        thumb_size = int(range_max / zoom)
        scrollable_y = range_max - thumb_size
        
        if scrollable_y > 0:
            pos = self.v_scroll.GetThumbPosition()
            self.canvas.pan_y_pct = pos / scrollable_y
        else:
            self.canvas.pan_y_pct = 0.0
            
        self.canvas.init = False
        self.canvas.Refresh()

    def on_zoom_in(self, event):
        """Zoom in by 10%."""
        self.canvas.zoom = min(5.0, self.canvas.zoom * 1.1)
        self.update_canvas_after_zoom()

    def on_zoom_out(self, event):
        """Zoom out by 10%."""
        self.canvas.zoom = max(1.0, self.canvas.zoom / 1.1)
        self.update_canvas_after_zoom()

    def update_canvas_after_zoom(self):
        """Refresh canvas and update scrollbars after zoom factor changes."""
        self.canvas.init = False
        self.canvas.Refresh()
        self.update_scrollbars()

    def update_scrollbars(self):
        """Update scrollbar ranges, thumb sizes, and positions based on canvas state."""
        zoom = getattr(self.canvas, 'zoom', 1.0)
        pan_x_pct = getattr(self.canvas, 'pan_x_pct', 0.0)
        pan_y_pct = getattr(self.canvas, 'pan_y_pct', 0.0)

        range_max = 10000
        thumb_size = int(range_max / zoom)
        
        scrollable_x = range_max - thumb_size
        scrollable_y = range_max - thumb_size
        
        pos_x = int(pan_x_pct * scrollable_x) if scrollable_x > 0 else 0
        pos_y = int(pan_y_pct * scrollable_y) if scrollable_y > 0 else 0
        
        page_size = thumb_size

        self.h_scroll.SetScrollbar(pos_x, thumb_size, range_max, page_size, refresh=True)
        self.v_scroll.SetScrollbar(pos_y, thumb_size, range_max, page_size, refresh=True)
        
        if hasattr(self, 'zoom_label'):
            self.zoom_label.SetLabel(f"Zoom: {int(zoom * 100)}%")

    def on_reset_view(self, event):
        """Reset all view parameters back to defaults and refresh canvas."""
        self.canvas.zoom = 1.0
        self.canvas.pan_x_pct = 0.0
        self.canvas.pan_y_pct = 0.0
        self.canvas.pan_x = 0.0
        self.canvas.pan_y = 0.0
        self.canvas.init = False
        self.canvas.Refresh()
        self.update_scrollbars()
        self.SetStatusText("View reset to default dimensions.")
        self.log("View reset to default dimensions.")

    
    