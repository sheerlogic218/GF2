"""Implement the graphical user interface for the Logic Simulator.

Used in the Logic Simulator project to enable the user to run the simulation
or adjust the network properties.

Classes:
--------
MyGLCanvas - handles all canvas drawing operations.
Gui - configures the main window and all the widgets.
"""

import datetime

import wx
import wx.glcanvas as wxcanvas
from OpenGL import GL, GLUT

from devices import Devices
from monitors import Monitors
from names import Names
from network import Network
from parse import Parser
from scanner import Scanner

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

        self.devices = devices
        self.monitors = monitors

        # Initialise variables for panning
        self.pan_x = 0
        self.pan_y = 0
        self.pan_x_pct = 0.0
        self.pan_y_pct = 0.0
        self.last_mouse_x = 0  # previous mouse x position
        self.last_mouse_y = 0  # previous mouse y position

        # Initialise variables for zooming
        self.zoom = 1.0
        self.visible_cycles = None
        self.previous_signal_traces = {}

        # Bind events to the canvas
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.on_mouse)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_click)

    def init_gl(self):
        """Configure and initialise the OpenGL context and camera."""
        size = self.GetClientSize()
        width = max(1, size.width)
        height = max(1, size.height)

        GL.glViewport(0, 0, width, height)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()

        zoom_factor = getattr(self, "zoom", 1.0)
        pan_x_pct = getattr(self, "pan_x_pct", 0.0)
        pan_y_pct = getattr(self, "pan_y_pct", 0.0)

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
        """Render the canvas graphics, plotting active monitor
        waveforms dynamically."""
        self.SetCurrent(self.context)
        if not self.init:
            self.init_gl()
            self.init = True

        GL.glClear(GL.GL_COLOR_BUFFER_BIT)

        # 1. Establish canvas and viewport plotting limits
        size = self.GetClientSize()
        canvas_width, canvas_height = size.width, size.height
        box_x_start, box_x_end = 80, canvas_width - 40
        box_y_bot, box_y_top = 20, canvas_height - 20

        # 2. Draw outer border layout box
        GL.glColor3f(0.3, 0.4, 0.5)
        GL.glLineWidth(1.5)
        GL.glBegin(GL.GL_LINE_LOOP)
        GL.glVertex2f(box_x_start, box_y_bot)
        GL.glVertex2f(box_x_end, box_y_bot)
        GL.glVertex2f(box_x_end, box_y_top)
        GL.glVertex2f(box_x_start, box_y_top)
        GL.glEnd()

        num_monitors = len(self.monitors.monitors_dict)
        if num_monitors == 0:
            GL.glFlush()
            self.SwapBuffers()
            return

        # 3. Calculate max cycles and draw universal background vertical grids
        visible_signals = {
            monitor: self._visible_signal_list(monitor, signal_list)
            for monitor, signal_list in self.monitors.monitors_dict.items()
        }
        num_cycles = max(
            (len(lst) for lst in visible_signals.values()), default=0
        )
        if num_cycles > 0:
            cycle_width = (box_x_end - box_x_start) / num_cycles

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
        else:
            # Safely exit if no simulation cycles have run yet
            GL.glFlush()
            self.SwapBuffers()
            return

        # 4. Dynamic Multi-Row Channel Rendering Loop
        row_height = (box_y_top - box_y_bot) / num_monitors
        for k, ((device_id, output_id), signal_list) in enumerate(
            visible_signals.items()
        ):
            # Define individualized vertical tracks for this specific row channel
            signal_y_bot = box_y_bot + (k * row_height)
            high_y = signal_y_bot + row_height * 0.25
            low_y = signal_y_bot + row_height * 0.75

            # Render row text identifiers and markers
            monitor_name = self.devices.get_signal_name(device_id, output_id)
            self.render_text(
                monitor_name, self.pan_x + 10, (high_y + low_y) / 2
            )
            self.render_text("High", self.pan_x + 50, high_y - 4)
            self.render_text("Low", self.pan_x + 50, low_y - 4)

            # Draw row horizontal boundary reference guidelines
            GL.glEnable(GL.GL_LINE_STIPPLE)
            GL.glLineStipple(1, 0x00FF)
            GL.glColor3f(0.4, 0.4, 0.4)
            GL.glBegin(GL.GL_LINES)
            GL.glVertex2f(box_x_start, high_y)
            GL.glVertex2f(box_x_end, high_y)
            GL.glVertex2f(box_x_start, low_y)
            GL.glVertex2f(box_x_end, low_y)
            GL.glEnd()
            GL.glDisable(GL.GL_LINE_STIPPLE)

            # Plot live signal trace using real backend constants.
            trace_segments = self._signal_trace_segments(
                signal_list, box_x_start, cycle_width, high_y, low_y
            )
            if trace_segments:
                GL.glColor3f(0.0, 1.0, 0.4)  # green trace
                GL.glLineWidth(2.5)
                GL.glBegin(GL.GL_LINES)
                for x1, y1, x2, y2 in trace_segments:
                    GL.glVertex2f(x1, y1)
                    GL.glVertex2f(x2, y2)
                GL.glEnd()
                GL.glLineWidth(1.0)

            if k < num_monitors - 1:
                channel_divider_y = signal_y_bot + row_height
                GL.glColor3f(0.3, 0.4, 0.5)
                GL.glLineWidth(2.0)
                GL.glBegin(GL.GL_LINES)
                GL.glVertex2f(box_x_start, channel_divider_y)
                GL.glVertex2f(box_x_end, channel_divider_y)
                GL.glEnd()

        GL.glFlush()
        self.SwapBuffers()

    def _signal_trace_segments(
        self, signal_list, x_start, cycle_width, high_y, low_y
    ):
        """Return drawable line segments for a backend monitor signal list."""
        segments = []
        previous_y = None

        for i, state in enumerate(signal_list):
            x = x_start + (i * cycle_width)
            x_next = x_start + ((i + 1) * cycle_width)

            if state == self.devices.HIGH:
                current_y_start = high_y
                current_y_end = high_y
            elif state == self.devices.LOW:
                current_y_start = low_y
                current_y_end = low_y
            elif state == self.devices.RISING:
                current_y_start = low_y
                current_y_end = high_y
            elif state == self.devices.FALLING:
                current_y_start = high_y
                current_y_end = low_y
            else:
                previous_y = None
                continue

            if previous_y is not None and current_y_start != previous_y:
                segments.append((x, previous_y, x, current_y_start))

            segments.append((x, current_y_start, x_next, current_y_end))
            previous_y = current_y_end

        return segments

    def _visible_signal_list(self, monitor, signal_list):
        """Return the whole trace or only the configured final cycles."""
        if self.visible_cycles is None:
            return signal_list
        previous_signal_list = self.previous_signal_traces.get(monitor, [])
        return (previous_signal_list + signal_list)[-self.visible_cycles :]

    def on_paint(self, event):
        """Handle the paint event by validating the DC and calling render."""
        dc = wx.PaintDC(self)
        self.render()

    def on_size(self, event):
        """Handle canvas resize events cleanly without duplicating ortho configurations."""
        self.init = False
        self.Refresh()

        # Notify Gui to update scrollbars on resize
        gui = wx.GetTopLevelParent(self)
        if gui and hasattr(gui, "update_scrollbars"):
            gui.update_scrollbars()

    def on_mouse(self, event):
        """Handle mouse events (navigation handled by scrollbars and mouse wheel/dragging)."""

        if event.Entering():
            self.SetFocus()
        # Find the parent Gui frame to trigger scrollbar updates
        gui = wx.GetTopLevelParent(self)
        if gui and hasattr(gui, "update_scrollbars"):
            gui.update_scrollbars()

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
                self.pan_x_pct = (
                    self.pan_x / max_pan_x if max_pan_x > 0 else 0.0
                )
                self.pan_y_pct = (
                    self.pan_y / max_pan_y if max_pan_y > 0 else 0.0
                )

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

    def on_right_click(self, event):
        """Show a context menu on right click."""
        menu = wx.Menu()
        reset_item = menu.Append(wx.ID_ANY, "Reset View")
        menu.AppendSeparator()
        save_item = menu.Append(wx.ID_ANY, "Save Image...")
        copy_item = menu.Append(wx.ID_ANY, "Copy Image")

        gui = wx.GetTopLevelParent(self)
        if gui and hasattr(gui, "update_scrollbars"):
            gui.update_scrollbars()

        self.Bind(wx.EVT_MENU, self.on_save_image, save_item)
        self.Bind(wx.EVT_MENU, self.on_copy_image, copy_item)

        self.PopupMenu(menu)
        menu.Destroy()

    def _capture_bitmap(self):
        """Capture the current canvas contents as a wx.Bitmap."""
        size = self.GetClientSize()
        bitmap = wx.Bitmap(size.width, size.height)
        dc = wx.MemoryDC(bitmap)
        dc.Blit(0, 0, size.width, size.height, wx.ClientDC(self), 0, 0)
        dc.SelectObject(wx.NullBitmap)
        return bitmap

    def on_save_image(self, event):
        """Save the canvas contents to an image file."""
        wildcard = "PNG files (*.png)|*.png|JPEG files (*.jpg)|*.jpg"
        dlg = wx.FileDialog(
            self,
            "Save Image",
            wildcard=wildcard,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            fmt = (
                wx.BITMAP_TYPE_JPEG
                if path.endswith(".jpg")
                else wx.BITMAP_TYPE_PNG
            )
            self._capture_bitmap().SaveFile(path, fmt)
        dlg.Destroy()

    def on_copy_image(self, event):
        """Copy the canvas contents to the clipboard."""
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(
                wx.BitmapDataObject(self._capture_bitmap())
            )
            wx.TheClipboard.Close()

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
            gui = wx.GetTopLevelParent(self)
            while gui and not hasattr(gui, "on_zoom_in"):
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
        self.devices = devices
        self.names = names
        self.network = network
        self.monitors = monitors
        self.cycles_completed = 0

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

        helpMenu = wx.Menu()
        helpMenu.Append(wx.ID_HELP, "&Documentation")
        menuBar.Append(helpMenu, "&Help")

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
        self.spin = wx.SpinCtrl(
            self.top_panel, wx.ID_ANY, "10", min=1, max=1000, size=(110, -1)
        )
        self.run_button = wx.Button(
            self.top_panel, wx.ID_ANY, "▶", size=(32, 28)
        )
        self.continue_button = wx.Button(
            self.top_panel, wx.ID_ANY, "+10", size=(45, 28)
        )
        self.last_cycles_check = wx.CheckBox(self.top_panel, wx.ID_ANY, "Last")
        self.last_cycles_spin = wx.SpinCtrl(
            self.top_panel, wx.ID_ANY, "10", min=1, max=1000, size=(70, -1)
        )

        self.switch_label = wx.StaticText(
            self.top_panel, wx.ID_ANY, "Select switch:"
        )
        self.switch_choice = wx.Choice(
            self.top_panel, wx.ID_ANY, choices=self._get_switch_names()
        )
        self.switch_on = wx.Button(self.top_panel, wx.ID_ANY, "Set ON")
        self.switch_off = wx.Button(self.top_panel, wx.ID_ANY, "Set OFF")

        self.monitors_label = wx.StaticText(
            self.top_panel, wx.ID_ANY, "Monitors:"
        )
        self.monitors_list = wx.ListBox(
            self.top_panel, wx.ID_ANY, choices=[], style=wx.LB_SINGLE
        )
        self.add_monitor_btn = wx.Button(self.top_panel, wx.ID_ANY, "+")
        self.remove_monitor_btn = wx.Button(self.top_panel, wx.ID_ANY, "-")

        self.reset_button = wx.Button(
            self.top_panel, wx.ID_ANY, "↺", size=(32, 28)
        )

        self.console = wx.TextCtrl(
            self.top_panel,
            wx.ID_ANY,
            "",
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL,
        )
        console_font = wx.Font(
            9,
            wx.FONTFAMILY_TELETYPE,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        )
        self.console.SetFont(console_font)

        # Tooltips
        initial_cycles = self.spin.GetValue()
        self.run_button.SetToolTip(
            f"Run the simulation from scratch for {initial_cycles} cycles"
        )
        self.continue_button.SetToolTip(
            f"Continue the simulation for {initial_cycles} additional cycles"
        )
        self.reset_button.SetToolTip(
            "Reset the simulation to its initial state"
        )
        self.switch_on.SetToolTip("Set the selected switch to ON (1)")
        self.switch_off.SetToolTip("Set the selected switch to OFF (0)")
        self.add_monitor_btn.SetToolTip("Add a monitor to the selected signal")
        self.remove_monitor_btn.SetToolTip("Remove the selected monitor")
        self.spin.SetToolTip("Number of cycles to run or continue")
        self.last_cycles_check.SetToolTip("Show only the most recent cycles")
        self.last_cycles_spin.SetToolTip("Number of recent cycles to show")
        self.last_cycles_spin.Enable(False)

        # ── Event bindings ───────────────────────────────────────────────────
        self.Bind(wx.EVT_MENU, self.on_menu)
        self.spin.Bind(wx.EVT_SPINCTRL, self.on_spin)
        self.run_button.Bind(wx.EVT_BUTTON, self.on_run_button)
        self.continue_button.Bind(wx.EVT_BUTTON, self.on_continue_button)
        self.last_cycles_check.Bind(
            wx.EVT_CHECKBOX, self.on_last_cycles_change
        )
        self.last_cycles_spin.Bind(wx.EVT_SPINCTRL, self.on_last_cycles_change)
        self.last_cycles_spin.Bind(wx.EVT_TEXT, self.on_last_cycles_change)
        self.switch_on.Bind(wx.EVT_BUTTON, self.on_switch_on)
        self.switch_off.Bind(wx.EVT_BUTTON, self.on_switch_off)
        self.add_monitor_btn.Bind(wx.EVT_BUTTON, self.on_add_monitor)
        self.remove_monitor_btn.Bind(wx.EVT_BUTTON, self.on_remove_monitor)
        self.reset_button.Bind(wx.EVT_BUTTON, self.on_reset_button)
        self.Bind(wx.EVT_MENU, self.on_help_menu, id=wx.ID_HELP)
        # ── Control-panel sizer ──────────────────────────────────────────────
        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.top_panel.SetSizer(top_sizer)
        top_sizer.SetMinSize((-1, 150))

        # Simulation box
        sim_box = wx.StaticBox(self.top_panel, wx.ID_ANY, "Simulation")
        sim_sizer = wx.StaticBoxSizer(sim_box, wx.VERTICAL)
        sim_sizer.Add(self.cycles_label, 0, wx.ALL, 5)
        sim_sizer.Add(self.spin, 0, wx.EXPAND | wx.ALL, 5)

        view_cycles_sizer = wx.BoxSizer(wx.HORIZONTAL)
        view_cycles_sizer.Add(
            self.last_cycles_check, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2
        )
        view_cycles_sizer.Add(
            self.last_cycles_spin, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2
        )
        sim_sizer.Add(
            view_cycles_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.BOTTOM, 3
        )

        # Buttons laid out side-by-side
        sim_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sim_btn_sizer.Add(
            self.run_button, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2
        )
        sim_btn_sizer.Add(
            self.continue_button, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2
        )
        sim_btn_sizer.Add(
            self.reset_button, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2
        )
        sim_sizer.Add(
            sim_btn_sizer,
            0,
            wx.ALIGN_CENTER_HORIZONTAL | wx.TOP | wx.BOTTOM,
            3,
        )

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
        monitor_sizer.Add(
            monitor_btn_sizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 3
        )

        # Console box
        console_box = wx.StaticBox(self.top_panel, wx.ID_ANY, "Console")
        console_sizer = wx.StaticBoxSizer(console_box, wx.VERTICAL)
        console_sizer.Add(self.console, 1, wx.EXPAND | wx.ALL, 5)

        # Switch ON/OFF buttons side-by-side
        switch_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        switch_btn_sizer.Add(self.switch_on, 1, wx.ALL, 5)
        switch_btn_sizer.Add(self.switch_off, 1, wx.ALL, 5)
        switch_sizer.Add(switch_btn_sizer, 0, wx.EXPAND)

        top_sizer.Add(sim_sizer, 0, wx.EXPAND | wx.ALL, 2)
        top_sizer.Add(switch_sizer, 0, wx.EXPAND | wx.ALL, 2)
        top_sizer.Add(monitor_sizer, 0, wx.EXPAND | wx.ALL, 2)
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
        self.update_monitors_list()

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
            self.viewer_panel, label="File Viewer", style=wx.ST_ELLIPSIZE_END
        )
        title_font = self._viewer_title.GetFont()
        title_font.SetWeight(wx.FONTWEIGHT_BOLD)
        self._viewer_title.SetFont(title_font)

        self._viewer_title.SetMinSize((50, -1))

        save_btn = wx.Button(self.viewer_panel, label="Save", size=(50, 28))
        save_btn.SetToolTip("Save changes to file")
        save_btn.Bind(wx.EVT_BUTTON, self._on_save_viewer)

        implement_btn = wx.Button(
            self.viewer_panel, label="Implement", size=(80, 28)
        )
        implement_btn.SetToolTip("Run the simulator using this file")
        implement_btn.Bind(wx.EVT_BUTTON, self._on_implement_viewer)

        close_btn = wx.Button(self.viewer_panel, label="X", size=(28, 28))
        close_btn.SetToolTip("Close file viewer")
        close_btn.Bind(wx.EVT_BUTTON, self._on_close_viewer)

        header_sizer.Add(
            self._viewer_title, 1, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 6
        )
        header_sizer.Add(save_btn, 0, wx.ALL, 2)
        header_sizer.Add(implement_btn, 0, wx.ALL, 2)
        header_sizer.Add(close_btn, 0, wx.ALL, 2)

        # Read-only text area with monospace font
        self._file_text = wx.TextCtrl(
            self.viewer_panel,
            style=wx.TE_MULTILINE | wx.TE_DONTWRAP | wx.HSCROLL,
        )
        mono_font = wx.Font(
            10,
            wx.FONTFAMILY_TELETYPE,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        )
        self._file_text.SetFont(mono_font)
        self._file_text.SetBackgroundColour(wx.Colour(20, 24, 32))
        self._file_text.SetForegroundColour(wx.Colour(210, 220, 235))

        viewer_sizer.Add(header_sizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 4)
        viewer_sizer.Add(
            wx.StaticLine(self.viewer_panel),
            0,
            wx.EXPAND | wx.LEFT | wx.RIGHT,
            4,
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
                self.left_pane,
                self.viewer_panel,
                w - 380,  # viewer starts at 380 px wide
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
                "Save",
                wx.ICON_WARNING | wx.OK,
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
                "Save Error",
                wx.ICON_ERROR | wx.OK,
            )

    def _save_viewer_contents(self):
        """Save viewer contents and return whether it succeeded."""
        if not self._viewer_path:
            wx.MessageBox(
                "No file is open - nothing to implement.",
                "Implement",
                wx.ICON_WARNING | wx.OK,
            )
            return False
        try:
            with open(self._viewer_path, "w") as fh:
                fh.write(self._file_text.GetValue())
            self.SetStatusText(f"Saved: {self._viewer_path}")
            self.log(f"File saved: {self._viewer_path}")
            return True
        except OSError as exc:
            wx.MessageBox(
                f"Could not save file:\n{exc}",
                "Save Error",
                wx.ICON_ERROR | wx.OK,
            )
            return False

    def _on_implement_viewer(self, event):
        """Use the file currently shown in the viewer as the active circuit."""
        if not self._save_viewer_contents():
            return

        names = Names()
        devices = Devices(names)
        network = Network(names, devices)
        monitors = Monitors(names, devices, network)
        scanner = Scanner(self._viewer_path, names)
        parser = Parser(names, devices, network, monitors, scanner)

        if not parser.parse_network():
            wx.MessageBox(
                "Could not implement this file because it contains errors.",
                "Implement Error",
                wx.ICON_ERROR | wx.OK,
            )
            self.SetStatusText("Implement failed: parse errors in file.")
            self.log("Implement failed: parse errors in " + self._viewer_path)
            return

        self.names = names
        self.devices = devices
        self.network = network
        self.monitors = monitors
        self.cycles_completed = 0
        self.canvas.devices = devices
        self.canvas.monitors = monitors
        self.canvas.previous_signal_traces = {}

        self.switch_choice.Set(self._get_switch_names())
        self.update_monitors_list()
        self.update_scrollbars()
        self.canvas.render()
        self.SetTitle("Logic Simulator - " + self._viewer_path)
        self.SetStatusText("Implemented: " + self._viewer_path)
        self.log("Implemented file: " + self._viewer_path)

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
            wildcard = (
                "Circuit definition files (*.txt)|*.txt|All files (*.*)|*.*"
            )
            dlg = wx.FileDialog(
                self,
                "Open circuit definition file",
                wildcard=wildcard,
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
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

    def run_network(self, cycles):
        """Run the backend network and record monitor signals for each cycle."""
        for _ in range(cycles):
            if self.network.execute_network():
                self.monitors.record_signals()
            else:
                self.SetStatusText("Error: network oscillating.")
                self.log("Error: network oscillating.")
                return False
        return True

    def archive_current_traces(self):
        """Store current monitor traces for the next cycle-windowed run view."""
        self.canvas.previous_signal_traces = {
            monitor: list(signal_list)
            for monitor, signal_list in self.monitors.monitors_dict.items()
            if signal_list
        }

    def update_monitors_list(self):
        """Refresh the monitor list from backend monitor state."""
        monitored_signals, non_monitored_signals = (
            self.monitors.get_signal_names()
        )
        # TODO
        display_names = [
            self.names.prettify_name(name) + " (on)"
            for name in monitored_signals
        ]
        display_names.extend(
            [self.names.prettify_name(name) for name in non_monitored_signals]
        )
        self.monitors_list.Set(display_names)
        self._monitor_choices = {
            self.names.prettify_name(name) + " (on)": name
            for name in monitored_signals
        }
        self._monitor_choices.update(
            {
                self.names.prettify_name(name): name
                for name in non_monitored_signals
            }
        )

    def on_last_cycles_change(self, event):
        """Update the canvas cycle-window view."""
        if self.last_cycles_check.GetValue():
            visible_cycles = self.last_cycles_spin.GetValue()
            self.last_cycles_spin.Enable(True)
            self.canvas.visible_cycles = visible_cycles
            self.SetStatusText(
                "Showing last " + str(visible_cycles) + " cycles."
            )
        else:
            self.last_cycles_spin.Enable(False)
            self.canvas.visible_cycles = None
            self.SetStatusText("Showing all recorded cycles.")
        self.canvas.render()

    def on_spin(self, event):
        """Handle the event when the user changes the spin control value."""
        spin_value = self.spin.GetValue()

        # Update button label
        self.continue_button.SetLabel(f"+{spin_value}")

        # Update tooltips dynamically
        self.run_button.SetToolTip(
            f"Run the simulation from scratch for {spin_value} cycles"
        )
        self.continue_button.SetToolTip(
            f"Continue the simulation for {spin_value} additional cycles"
        )

        text = "".join(["New spin control value: ", str(spin_value)])
        self.canvas.render(text)
        self.log(text)

    def on_run_button(self, event):
        """Handle the event when the user clicks the run button."""
        cycles = self.spin.GetValue()
        self.SetStatusText("Running for " + str(cycles) + " cycles...")
        self.log("Run clicked: " + str(cycles) + " cycles requested.")
        self.archive_current_traces()
        self.cycles_completed = 0
        self.monitors.reset_monitors()
        self.devices.cold_startup()
        if self.run_network(cycles):
            self.cycles_completed = cycles
            self.SetStatusText("Completed " + str(cycles) + " cycles.")
            self.log("Completed " + str(cycles) + " cycles.")
        self.update_monitors_list()
        self.canvas.render()

    def on_continue_button(self, event):
        """Handle the event when the user clicks the continue button."""
        cycles = self.spin.GetValue()
        if self.cycles_completed == 0:
            self.SetStatusText("Error: nothing to continue. Run first.")
            self.log("Continue ignored: run the simulation first.")
            return
        self.SetStatusText("Continuing for " + str(cycles) + " cycles...")
        self.log("Continue clicked: " + str(cycles) + " cycles requested.")
        if self.run_network(cycles):
            self.cycles_completed += cycles
            self.SetStatusText(
                "Completed " + str(self.cycles_completed) + " cycles."
            )
            self.log(
                "Completed " + str(self.cycles_completed) + " total cycles."
            )
        self.update_monitors_list()
        self.canvas.render()

    def on_switch_on(self, event):
        """Handle the event when the user clicks the switch on button."""
        selection = self.switch_choice.GetSelection()
        if selection == wx.NOT_FOUND:
            self.SetStatusText("Error: please select a switch first.")
            return
        switch_name = self.switch_choice.GetString(selection)
        switch_id = self.names.query(switch_name)
        if self.devices.set_switch(switch_id, self.devices.HIGH):
            self.SetStatusText(f"Switch {switch_name} set ON.")
            self.log(f"Switch {switch_name} set ON.")
            self.canvas.render()
        else:
            self.SetStatusText(f"Error: could not set switch {switch_name}.")

    def on_switch_off(self, event):
        """Handle the event when the user clicks the switch off button."""
        selection = self.switch_choice.GetSelection()
        if selection == wx.NOT_FOUND:
            self.SetStatusText("Error: please select a switch first.")
            return
        switch_name = self.switch_choice.GetString(selection)
        switch_id = self.names.query(switch_name)
        if self.devices.set_switch(switch_id, self.devices.LOW):
            self.SetStatusText(f"Switch {switch_name} set OFF.")
            self.log(f"Switch {switch_name} set OFF.")
            self.canvas.render()
        else:
            self.SetStatusText(f"Error: could not set switch {switch_name}.")

    def on_add_monitor(self, event):
        """Handle the event when the user clicks the add monitor button."""
        selection = self.monitors_list.GetSelection()
        if selection == wx.NOT_FOUND:
            self.SetStatusText("Error: please select a signal first.")
            return

        display_name = self.monitors_list.GetString(selection)
        signal_name = self._monitor_choices.get(display_name, display_name)
        signal_ids = self.devices.get_signal_ids(signal_name)
        if signal_ids is None:
            self.SetStatusText("Error: selected signal was not found.")
            return

        device_id, output_id = signal_ids
        monitor_error = self.monitors.make_monitor(
            device_id, output_id, self.cycles_completed
        )
        if monitor_error == self.monitors.NO_ERROR:
            self.SetStatusText("Added monitor: " + signal_name)
            self.log("Added monitor: " + signal_name)
        elif monitor_error == self.monitors.MONITOR_PRESENT:
            self.SetStatusText("Monitor already active: " + signal_name)
        else:
            self.SetStatusText("Error: could not add monitor " + signal_name)
        self.update_monitors_list()
        self.canvas.render()

    def on_remove_monitor(self, event):
        """Handle the event when the user clicks the remove monitor button."""
        selection = self.monitors_list.GetSelection()
        if selection == wx.NOT_FOUND:
            self.SetStatusText("Error: please select a monitor first.")
            return

        display_name = self.monitors_list.GetString(selection)
        signal_name = self._monitor_choices.get(display_name, display_name)
        signal_ids = self.devices.get_signal_ids(signal_name)
        if signal_ids is None:
            self.SetStatusText("Error: selected signal was not found.")
            return

        device_id, output_id = signal_ids
        if self.monitors.remove_monitor(device_id, output_id):
            self.SetStatusText("Removed monitor: " + signal_name)
            self.log("Removed monitor: " + signal_name)
        else:
            self.SetStatusText("Error: monitor is not active: " + signal_name)
        self.update_monitors_list()
        self.canvas.render()

    def on_reset_button(self, event):
        """Handle the event when the user clicks the reset button."""
        self.cycles_completed = 0
        self.monitors.reset_monitors()
        self.canvas.previous_signal_traces = {}
        self.devices.cold_startup()
        self.SetStatusText("Simulation reset.")
        self.canvas.render("Simulation reset.")
        self.log("Simulation reset.")

    def log(self, message):
        """Append a time-stamped message to the console output."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.console.AppendText(f"[{timestamp}] {message}\n")

    def on_h_scroll(self, event):
        """Handle horizontal scrollbar scrolling."""
        zoom = getattr(self.canvas, "zoom", 1.0)
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
        zoom = getattr(self.canvas, "zoom", 1.0)
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
        zoom = getattr(self.canvas, "zoom", 1.0)
        pan_x_pct = getattr(self.canvas, "pan_x_pct", 0.0)
        pan_y_pct = getattr(self.canvas, "pan_y_pct", 0.0)

        range_max = 10000
        thumb_size = int(range_max / zoom)

        scrollable_x = range_max - thumb_size
        scrollable_y = range_max - thumb_size

        pos_x = int(pan_x_pct * scrollable_x) if scrollable_x > 0 else 0
        pos_y = int(pan_y_pct * scrollable_y) if scrollable_y > 0 else 0

        page_size = thumb_size

        self.h_scroll.SetScrollbar(
            pos_x, thumb_size, range_max, page_size, refresh=True
        )
        self.v_scroll.SetScrollbar(
            pos_y, thumb_size, range_max, page_size, refresh=True
        )

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

    def on_help_menu(self, event):
        """Display a pop-up dialog describing the GUI functionality and user controls."""
        help_text = (
            "Welcome to the Logic Simulator!\n\n"
            "Here is a summary of the available interface functions:\n\n"
            "1. Simulation Controls:\n"
            "   - Use the spin box to adjust the target simulation cycle count.\n"
            "   - Click '▶' to start or restart the simulation from zero.\n"
            "   - Click '+10' (or your step button) to continue running further cycles.\n"
            "   - Click '↺' to clear current history and reset the network.\n\n"
            "2. Interacting with the Canvas:\n"
            "   - Drag with Left Mouse Button to pan across the logic waveforms.\n"
            "   - Scroll your Mouse Wheel to zoom in/out smoothly on active lines.\n"
            "   - Right-click inside the canvas to copy or save a snapshot image.\n\n"
            "3. Switches & Monitors:\n"
            "   - Select a switch from the dropdown menu and toggle its state via 'Set ON' / 'Set OFF'.\n"
            "   - Add (+) or remove (-) selected component signals using the Monitors listbox.\n\n"
            "4. View Options:\n"
            "   - Toggle the live text definition panel under View -> Show File Viewer."
        )

        # Create and display the modal information dialogue box
        dlg = wx.MessageDialog(
            self, help_text, "GUI Usage Guide", wx.OK | wx.ICON_INFORMATION
        )
        dlg.ShowModal()
        dlg.Destroy()

    def _get_switch_names(self):
        """Return a list of switch device name strings from the backend."""
        switch_ids = self.devices.find_devices(self.devices.SWITCH)
        return [self.names.get_name_string(sid) for sid in switch_ids]
