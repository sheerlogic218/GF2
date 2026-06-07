"""Implement the graphical user interface for the Logic Simulator.

Used in the Logic Simulator project to enable the user to run the simulation
or adjust the network properties.

Classes:
--------
MyGLCanvas - handles all canvas drawing operations.
Gui - configures the main window and all the widgets.
"""

import datetime
import math
import re

import numpy as np
import wx
import wx.glcanvas as wxcanvas
import wx.lib.agw.aui as agw_aui
import wx.stc
from OpenGL import GL, GLU, GLUT

from devices import Devices
from monitors import Monitors
from names import Names
from network import Network
from parse import Parser
from scanner import Scanner

# Alias for gettext-style translation lookup.
# wx.Locale + a .mo catalog must be initialised before GUI widgets are created.
_ = wx.GetTranslation

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

        # Monitor row drag-to-reorder state
        self._drag_monitor_src = None
        self._drag_monitor_dst = None

        # Initialise variables for zooming
        self.zoom = 1.0
        self.x_zoom = 1.0
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

        # Content width expands with x_zoom; allow panning to reach the far edge
        x_zoom = getattr(self, "x_zoom", 1.0)
        content_right = 80 + (width - 120) * x_zoom + 40
        max_pan_x = max(0.0, content_right - visible_width)
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
        actual_box_x_end = (
            box_x_start + (box_x_end - box_x_start) * self.x_zoom
        )

        # 2. Draw outer border layout box
        GL.glColor3f(0.3, 0.4, 0.5)
        GL.glLineWidth(1.5)
        GL.glBegin(GL.GL_LINE_LOOP)
        GL.glVertex2f(box_x_start, box_y_bot)
        GL.glVertex2f(actual_box_x_end, box_y_bot)
        GL.glVertex2f(actual_box_x_end, box_y_top)
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
            cycle_width = (actual_box_x_end - box_x_start) / num_cycles

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

            # X-axis cycle number labels – pinned to the visible viewport bottom
            # so they remain on-screen at any zoom / pan position.
            _zoom = getattr(self, "zoom", 1.0)
            label_y = self.pan_y + canvas_height / _zoom - 8
            raw_step = math.ceil(28 / cycle_width) if cycle_width > 0 else 1
            label_step = next(
                (
                    n
                    for n in [1, 2, 5, 10, 20, 50, 100, 250, 500, 1000]
                    if n >= raw_step
                ),
                raw_step,
            )
            for i in range(label_step, num_cycles + 1, label_step):
                x = box_x_start + i * cycle_width
                label = str(i)
                self.render_text(label, x - len(label) * 3.5, label_y)
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
            clean_name = self.devices.names.prettify_name(monitor_name)
            self.render_text(clean_name, self.pan_x + 16, (high_y + low_y) / 2)
            self.render_text(_("High"), self.pan_x + 50, high_y - 4)
            self.render_text(_("Low"), self.pan_x + 50, low_y - 4)

            # Grip handle (drag-to-reorder indicator)
            grip_cx = self.pan_x + 7
            grip_cy = (high_y + low_y) / 2
            GL.glColor3f(0.35, 0.45, 0.55)
            GL.glLineWidth(1.0)
            GL.glBegin(GL.GL_LINE_LOOP)
            GL.glVertex2f(grip_cx - 6, grip_cy - 8)
            GL.glVertex2f(grip_cx + 6, grip_cy - 8)
            GL.glVertex2f(grip_cx + 6, grip_cy + 8)
            GL.glVertex2f(grip_cx - 6, grip_cy + 8)
            GL.glEnd()
            GL.glColor3f(0.6, 0.75, 0.85)
            GL.glLineWidth(1.5)
            GL.glBegin(GL.GL_LINES)
            for bar_dy in (-3.5, 0.0, 3.5):
                GL.glVertex2f(grip_cx - 3.5, grip_cy + bar_dy)
                GL.glVertex2f(grip_cx + 3.5, grip_cy + bar_dy)
            GL.glEnd()
            GL.glLineWidth(1.0)

            # Draw row horizontal boundary reference guidelines
            GL.glEnable(GL.GL_LINE_STIPPLE)
            GL.glLineStipple(1, 0x00FF)
            GL.glColor3f(0.4, 0.4, 0.4)
            GL.glBegin(GL.GL_LINES)
            GL.glVertex2f(box_x_start, high_y)
            GL.glVertex2f(actual_box_x_end, high_y)
            GL.glVertex2f(box_x_start, low_y)
            GL.glVertex2f(actual_box_x_end, low_y)
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
                GL.glVertex2f(actual_box_x_end, channel_divider_y)
                GL.glEnd()

        # Draw drag-to-reorder insertion indicator
        if (
            self._drag_monitor_src is not None
            and self._drag_monitor_dst != self._drag_monitor_src
        ):
            dst = self._drag_monitor_dst
            src = self._drag_monitor_src
            indicator_y = (
                box_y_bot + (dst + 1) * row_height
                if src < dst
                else box_y_bot + dst * row_height
            )
            GL.glColor3f(1.0, 0.6, 0.0)
            GL.glLineWidth(3.0)
            GL.glBegin(GL.GL_LINES)
            GL.glVertex2f(box_x_start, indicator_y)
            GL.glVertex2f(actual_box_x_end, indicator_y)
            GL.glEnd()
            GL.glLineWidth(1.0)

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

    def _get_monitor_row(self, screen_x, screen_y):
        """Return the monitor row index at the given screen position, or -1."""
        size = self.GetClientSize()
        canvas_height = max(1, size.height)
        gl_y = self.pan_y + screen_y / self.zoom
        box_y_bot, box_y_top = 20, canvas_height - 20
        num_monitors = len(self.monitors.monitors_dict)
        if num_monitors == 0 or gl_y < box_y_bot or gl_y > box_y_top:
            return -1
        row_height = (box_y_top - box_y_bot) / num_monitors
        k = int((gl_y - box_y_bot) / row_height)
        return max(0, min(k, num_monitors - 1))

    def _in_label_area(self, screen_x):
        """Return True if screen_x is within the row-label column."""
        return self.pan_x + screen_x / self.zoom < 80

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
                _xz = getattr(self, "x_zoom", 1.0)
                max_pan_x = max(
                    0.0, 80 + (width - 120) * _xz + 40 - visible_width
                )
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

        # Handle left button down: start monitor drag or pan
        elif event.ButtonDown(wx.MOUSE_BTN_LEFT):
            mx, my = event.GetPosition()
            self.last_mouse_x, self.last_mouse_y = mx, my
            if self._in_label_area(mx):
                row = self._get_monitor_row(mx, my)
                if row >= 0:
                    self._drag_monitor_src = row
                    self._drag_monitor_dst = row
                    return
            self._drag_monitor_src = None

        elif event.ButtonUp(wx.MOUSE_BTN_LEFT):
            if self._drag_monitor_src is not None:
                src, dst = self._drag_monitor_src, self._drag_monitor_dst
                self._drag_monitor_src = None
                self._drag_monitor_dst = None
                self.SetCursor(wx.Cursor(wx.CURSOR_DEFAULT))
                self.init = False
                self.Refresh()
                if src != dst and gui and hasattr(gui, "on_monitor_reorder"):
                    gui.on_monitor_reorder(src, dst)
                return

        elif event.Moving():
            mx, my = event.GetPosition()
            if (
                len(self.monitors.monitors_dict) > 0
                and self._in_label_area(mx)
                and self._get_monitor_row(mx, my) >= 0
            ):
                self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
            else:
                self.SetCursor(wx.Cursor(wx.CURSOR_DEFAULT))

        elif event.Dragging() and event.LeftIsDown():
            curr_x, curr_y = event.GetPosition()

            # Monitor row drag takes priority over panning
            if self._drag_monitor_src is not None:
                row = self._get_monitor_row(curr_x, curr_y)
                if row >= 0:
                    self._drag_monitor_dst = row
                self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
                self.init = False
                self.Refresh()
                return

            dx = curr_x - self.last_mouse_x
            dy = curr_y - self.last_mouse_y
            self.last_mouse_x, self.last_mouse_y = curr_x, curr_y

            size = self.GetClientSize()
            width = max(1, size.width)
            height = max(1, size.height)
            visible_width = width / self.zoom
            visible_height = height / self.zoom
            _xz = getattr(self, "x_zoom", 1.0)
            max_pan_x = max(0.0, 80 + (width - 120) * _xz + 40 - visible_width)
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
        reset_item = menu.Append(wx.ID_ANY, _("Reset View"))
        menu.AppendSeparator()
        save_item = menu.Append(wx.ID_ANY, _("Save Image..."))
        copy_item = menu.Append(wx.ID_ANY, _("Copy Image"))

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
        wildcard = _("PNG files (*.png)|*.png|JPEG files (*.jpg)|*.jpg")
        dlg = wx.FileDialog(
            self,
            _("Save Image"),
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


class MyGL3DCanvas(wxcanvas.GLCanvas):
    """3D OpenGL canvas – renders each monitor trace as a lane of solid cuboids."""

    _TRACK_COLORS = [
        (0.20, 0.85, 0.45),
        (0.35, 0.65, 1.00),
        (1.00, 0.55, 0.20),
        (0.90, 0.30, 0.85),
        (0.30, 0.90, 0.90),
        (1.00, 0.90, 0.20),
        (0.90, 0.40, 0.40),
        (0.55, 0.90, 0.30),
    ]

    def __init__(self, parent, devices, monitors):
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
        self._initial_rotate_done = False
        self.context = wxcanvas.GLContext(self)

        self.devices = devices
        self.monitors = monitors
        self.visible_cycles = None
        self.previous_signal_traces = {}

        self.no_ambient = [0.0, 0.0, 0.0, 1.0]
        self.dim_diffuse = [0.5, 0.5, 0.5, 1.0]
        self.med_diffuse = [0.75, 0.75, 0.75, 1.0]
        self.no_specular = [0.0, 0.0, 0.0, 1.0]
        self.top_right = [1.0, 1.0, 1.0, 0.0]
        self.straight_on = [0.0, 0.0, 1.0, 0.0]
        self.mat_specular = [0.5, 0.5, 0.5, 1.0]
        self.mat_shininess = [50.0]
        self.mat_diffuse = [0.0, 0.0, 0.0, 1.0]

        self.pan_x = 0.0
        self.pan_y = 0.0
        self.zoom = 8.0
        self.depth_offset = 1000
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.scene_rotate = np.identity(4, "f")

        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.on_mouse)

    def init_gl(self):
        """Configure the OpenGL context for 3D perspective rendering."""
        size = self.GetClientSize()
        self.SetCurrent(self.context)
        GL.glViewport(0, 0, max(1, size.width), max(1, size.height))

        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GLU.gluPerspective(
            45, max(1, size.width) / max(1, size.height), 10, 10000
        )

        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()

        GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, self.no_ambient)
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, self.med_diffuse)
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_SPECULAR, self.no_specular)
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_POSITION, self.top_right)
        GL.glLightfv(GL.GL_LIGHT1, GL.GL_AMBIENT, self.no_ambient)
        GL.glLightfv(GL.GL_LIGHT1, GL.GL_DIFFUSE, self.dim_diffuse)
        GL.glLightfv(GL.GL_LIGHT1, GL.GL_SPECULAR, self.no_specular)
        GL.glLightfv(GL.GL_LIGHT1, GL.GL_POSITION, self.straight_on)

        GL.glMaterialfv(GL.GL_FRONT, GL.GL_SPECULAR, self.mat_specular)
        GL.glMaterialfv(GL.GL_FRONT, GL.GL_SHININESS, self.mat_shininess)
        GL.glMaterialfv(
            GL.GL_FRONT, GL.GL_AMBIENT_AND_DIFFUSE, self.mat_diffuse
        )
        GL.glColorMaterial(GL.GL_FRONT, GL.GL_AMBIENT_AND_DIFFUSE)

        GL.glClearColor(0.05, 0.07, 0.12, 0.0)
        GL.glDepthFunc(GL.GL_LEQUAL)
        GL.glShadeModel(GL.GL_SMOOTH)
        GL.glDrawBuffer(GL.GL_BACK)
        GL.glCullFace(GL.GL_BACK)
        GL.glEnable(GL.GL_COLOR_MATERIAL)
        GL.glEnable(GL.GL_CULL_FACE)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_LIGHTING)
        GL.glEnable(GL.GL_LIGHT0)
        GL.glEnable(GL.GL_LIGHT1)
        GL.glEnable(GL.GL_NORMALIZE)

        # Set a pleasant default viewing angle on the first call
        if not self._initial_rotate_done:
            GL.glRotatef(25, 1, 0, 0)
            GL.glRotatef(-20, 0, 1, 0)
            GL.glGetFloatv(GL.GL_MODELVIEW_MATRIX, self.scene_rotate)
            self._initial_rotate_done = True
            GL.glLoadIdentity()

        GL.glTranslatef(0.0, 0.0, -self.depth_offset)
        GL.glTranslatef(self.pan_x, self.pan_y, 0.0)
        GL.glMultMatrixf(self.scene_rotate)
        GL.glScalef(self.zoom, self.zoom, self.zoom)

    def render(self):
        """Render each monitor as a row of 3D cuboids along the time axis."""
        self.SetCurrent(self.context)
        if not self.init:
            self.init_gl()
            self.init = True

        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        monitors_dict = self.monitors.monitors_dict
        if not monitors_dict:
            GL.glFlush()
            self.SwapBuffers()
            return

        signal_items = list(monitors_dict.items())
        num_signals = len(signal_items)

        visible = {}
        for key, sig_list in signal_items:
            if self.visible_cycles is None:
                visible[key] = sig_list
            else:
                prev = self.previous_signal_traces.get(key, [])
                visible[key] = (list(prev) + list(sig_list))[
                    -self.visible_cycles :
                ]

        max_cycles = max((len(v) for v in visible.values()), default=0)
        if max_cycles == 0:
            GL.glFlush()
            self.SwapBuffers()
            return

        CYCLE_W = 18.0
        LANE_D = 65.0
        TRACE_DEPTH = 22.0
        HIGH_H = 22.0
        LOW_H = 3.0

        for k, (key, _) in enumerate(signal_items):
            device_id, output_id = key
            sig_values = visible[key]
            z_center = (k - (num_signals - 1) / 2.0) * LANE_D
            color = self._TRACK_COLORS[k % len(self._TRACK_COLORS)]
            GL.glColor3f(*color)

            monitor_name = self.devices.get_signal_name(device_id, output_id)
            clean_name = self.devices.names.prettify_name(monitor_name)
            x_label = -(max_cycles / 2.0 + 2.0) * CYCLE_W
            self.render_text(clean_name, x_label, 5, z_center)

            for i, state in enumerate(sig_values):
                x_c = (i - max_cycles / 2.0 + 0.5) * CYCLE_W
                if state == self.devices.HIGH:
                    h = HIGH_H
                elif state == self.devices.LOW:
                    h = LOW_H
                elif state in (self.devices.RISING, self.devices.FALLING):
                    h = (HIGH_H + LOW_H) / 2
                else:
                    continue
                self.draw_cuboid(
                    x_c, z_center, CYCLE_W / 2 - 0.5, TRACE_DEPTH / 2, h
                )

        # Shared extents used by the floor grid, planes, and labels
        x_lo = -(max_cycles / 2.0) * CYCLE_W
        x_hi = (max_cycles / 2.0) * CYCLE_W
        z_lo = -(num_signals / 2.0) * LANE_D
        z_hi = (num_signals / 2.0) * LANE_D
        floor_y = -6.5

        # Floor grid (opaque)
        GL.glDisable(GL.GL_LIGHTING)
        GL.glColor3f(0.20, 0.25, 0.35)
        GL.glLineWidth(1.0)
        GL.glBegin(GL.GL_LINES)
        for i in range(max_cycles + 1):
            x = x_lo + i * CYCLE_W
            GL.glVertex3f(x, floor_y, z_lo)
            GL.glVertex3f(x, floor_y, z_hi)
        for k2 in range(num_signals + 1):
            z = (k2 - num_signals / 2.0) * LANE_D
            GL.glVertex3f(x_lo, floor_y, z)
            GL.glVertex3f(x_hi, floor_y, z)
        GL.glEnd()

        # HIGH and LOW reference planes – semi-transparent quads per lane
        GL.glDisable(GL.GL_CULL_FACE)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glDepthMask(GL.GL_FALSE)
        for k, (key, _) in enumerate(signal_items):
            z_c = (k - (num_signals - 1) / 2.0) * LANE_D
            z0 = z_c - TRACE_DEPTH / 2
            z1 = z_c + TRACE_DEPTH / 2
            r, g, b = self._TRACK_COLORS[k % len(self._TRACK_COLORS)]
            for plane_y, alpha in ((-6 + HIGH_H, 0.18), (-6 + LOW_H, 0.11)):
                GL.glColor4f(r, g, b, alpha)
                GL.glBegin(GL.GL_QUADS)
                GL.glVertex3f(x_lo, plane_y, z0)
                GL.glVertex3f(x_hi, plane_y, z0)
                GL.glVertex3f(x_hi, plane_y, z1)
                GL.glVertex3f(x_lo, plane_y, z1)
                GL.glEnd()
        GL.glDepthMask(GL.GL_TRUE)
        GL.glDisable(GL.GL_BLEND)
        GL.glEnable(GL.GL_CULL_FACE)

        # Plane border outlines (one solid-colour line loop per plane per lane)
        for k, (key, _) in enumerate(signal_items):
            z_c = (k - (num_signals - 1) / 2.0) * LANE_D
            z0 = z_c - TRACE_DEPTH / 2
            z1 = z_c + TRACE_DEPTH / 2
            r, g, b = self._TRACK_COLORS[k % len(self._TRACK_COLORS)]
            for plane_y, dim in ((-6 + HIGH_H, 0.70), (-6 + LOW_H, 0.40)):
                GL.glColor3f(r * dim, g * dim, b * dim)
                GL.glBegin(GL.GL_LINE_LOOP)
                GL.glVertex3f(x_lo, plane_y, z0)
                GL.glVertex3f(x_hi, plane_y, z0)
                GL.glVertex3f(x_hi, plane_y, z1)
                GL.glVertex3f(x_lo, plane_y, z1)
                GL.glEnd()

        # Cycle numbers along the X axis – at both the front and back edges
        GL.glColor3f(0.65, 0.70, 0.80)
        label_y = floor_y + 3
        raw_step = max(1, int(30 / CYCLE_W))
        step = next(
            (n for n in [1, 2, 5, 10, 20, 50, 100, 250] if n >= raw_step),
            raw_step,
        )
        for i in range(0, max_cycles + 1, step):
            x = x_lo + i * CYCLE_W
            self.render_text(str(i), x - 3, label_y, z_hi + 14)  # front edge
            self.render_text(str(i), x - 3, label_y, z_lo - 14)  # back edge

        # HIGH and LOW level labels — one pair at the right end of each lane
        for k, (key, _) in enumerate(signal_items):
            z_c = (k - (num_signals - 1) / 2.0) * LANE_D
            r, g, b = self._TRACK_COLORS[k % len(self._TRACK_COLORS)]
            GL.glColor3f(r * 0.9, g * 0.9, b * 0.9)
            self.render_text("HIGH", x_hi + 6, -6 + HIGH_H, z_c)
            self.render_text("LOW",  x_hi + 6, -6 + LOW_H,  z_c)

        GL.glEnable(GL.GL_LIGHTING)
        GL.glFlush()
        self.SwapBuffers()

    def draw_cuboid(self, x_pos, z_pos, half_width, half_depth, height):
        """Draw a solid cuboid (base at y=−6, top at y=−6+height)."""
        GL.glBegin(GL.GL_QUADS)
        GL.glNormal3f(0, -1, 0)
        GL.glVertex3f(x_pos - half_width, -6, z_pos - half_depth)
        GL.glVertex3f(x_pos + half_width, -6, z_pos - half_depth)
        GL.glVertex3f(x_pos + half_width, -6, z_pos + half_depth)
        GL.glVertex3f(x_pos - half_width, -6, z_pos + half_depth)
        GL.glNormal3f(0, 1, 0)
        GL.glVertex3f(x_pos + half_width, -6 + height, z_pos - half_depth)
        GL.glVertex3f(x_pos - half_width, -6 + height, z_pos - half_depth)
        GL.glVertex3f(x_pos - half_width, -6 + height, z_pos + half_depth)
        GL.glVertex3f(x_pos + half_width, -6 + height, z_pos + half_depth)
        GL.glNormal3f(-1, 0, 0)
        GL.glVertex3f(x_pos - half_width, -6 + height, z_pos - half_depth)
        GL.glVertex3f(x_pos - half_width, -6, z_pos - half_depth)
        GL.glVertex3f(x_pos - half_width, -6, z_pos + half_depth)
        GL.glVertex3f(x_pos - half_width, -6 + height, z_pos + half_depth)
        GL.glNormal3f(1, 0, 0)
        GL.glVertex3f(x_pos + half_width, -6, z_pos - half_depth)
        GL.glVertex3f(x_pos + half_width, -6 + height, z_pos - half_depth)
        GL.glVertex3f(x_pos + half_width, -6 + height, z_pos + half_depth)
        GL.glVertex3f(x_pos + half_width, -6, z_pos + half_depth)
        GL.glNormal3f(0, 0, -1)
        GL.glVertex3f(x_pos - half_width, -6, z_pos - half_depth)
        GL.glVertex3f(x_pos - half_width, -6 + height, z_pos - half_depth)
        GL.glVertex3f(x_pos + half_width, -6 + height, z_pos - half_depth)
        GL.glVertex3f(x_pos + half_width, -6, z_pos - half_depth)
        GL.glNormal3f(0, 0, 1)
        GL.glVertex3f(x_pos - half_width, -6 + height, z_pos + half_depth)
        GL.glVertex3f(x_pos - half_width, -6, z_pos + half_depth)
        GL.glVertex3f(x_pos + half_width, -6, z_pos + half_depth)
        GL.glVertex3f(x_pos + half_width, -6 + height, z_pos + half_depth)
        GL.glEnd()

    def on_paint(self, event):
        self.SetCurrent(self.context)
        if not self.init:
            self.init_gl()
            self.init = True
        self.render()

    def on_size(self, event):
        self.init = False
        self.Refresh()

    def on_mouse(self, event):
        """Left-drag rotates; right-drag pans; scroll wheel zooms."""
        self.SetCurrent(self.context)

        if event.ButtonDown():
            self.last_mouse_x = event.GetX()
            self.last_mouse_y = event.GetY()

        if event.Dragging():
            GL.glMatrixMode(GL.GL_MODELVIEW)
            GL.glLoadIdentity()
            x = event.GetX() - self.last_mouse_x
            y = event.GetY() - self.last_mouse_y
            if event.LeftIsDown():
                GL.glRotatef(math.sqrt(x * x + y * y), y, x, 0)
            if event.MiddleIsDown():
                GL.glRotatef(x + y, 0, 0, 1)
            if event.RightIsDown():
                self.pan_x += x
                self.pan_y -= y
            GL.glMultMatrixf(self.scene_rotate)
            GL.glGetFloatv(GL.GL_MODELVIEW_MATRIX, self.scene_rotate)
            self.last_mouse_x = event.GetX()
            self.last_mouse_y = event.GetY()
            self.init = False

        wheel = event.GetWheelRotation()
        if wheel < 0:
            self.zoom *= 1.0 + wheel / (20 * event.GetWheelDelta())
            self.zoom = max(0.05, self.zoom)
            self.init = False
        if wheel > 0:
            self.zoom /= 1.0 - wheel / (20 * event.GetWheelDelta())
            self.init = False

        self.Refresh()

    def render_text(self, text, x_pos, y_pos, z_pos):
        """Render a GLUT bitmap string at a 3D world position."""
        GL.glDisable(GL.GL_LIGHTING)
        GL.glRasterPos3f(x_pos, y_pos, z_pos)
        font = GLUT.GLUT_BITMAP_HELVETICA_12
        for ch in text:
            if ch == "\n":
                y_pos -= 20
                GL.glRasterPos3f(x_pos, y_pos, z_pos)
            else:
                GLUT.glutBitmapCharacter(font, ord(ch))
        GL.glEnable(GL.GL_LIGHTING)


class LogicViewerDialog(wx.Dialog):
    """Scrollable gate-level schematic of the implemented circuit."""

    _NODE_W = 104
    _ROW_GAP = 18
    _LAYER_GAP = 194
    _PAD = 50

    _BG = {
        "AND":    wx.Colour(25, 55, 95),
        "OR":     wx.Colour(20, 70, 50),
        "NAND":   wx.Colour(75, 25, 75),
        "NOR":    wx.Colour(75, 45, 20),
        "XOR":    wx.Colour(20, 70, 75),
        "CLOCK":  wx.Colour(75, 70, 15),
        "SWITCH": wx.Colour(50, 70, 25),
        "DTYPE":  wx.Colour(75, 35, 15),
        "UNKNOWN": wx.Colour(55, 55, 55),
    }

    _OUTLINE_COL = {
        "AND":    wx.Colour(100, 170, 255),
        "OR":     wx.Colour(80, 200, 140),
        "NAND":   wx.Colour(200, 100, 200),
        "NOR":    wx.Colour(220, 140, 80),
        "XOR":    wx.Colour(80, 200, 210),
        "CLOCK":  wx.Colour(220, 200, 80),
        "SWITCH": wx.Colour(130, 200, 80),
        "DTYPE":  wx.Colour(220, 140, 80),
        "UNKNOWN": wx.Colour(140, 140, 140),
    }

    def __init__(self, parent, devices, network, names):
        super().__init__(
            parent,
            title=_("Logic Viewer"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(980, 660),
        )
        self._devices = devices
        self._network = network
        self._names = names
        self._nodes = {}  # device_id → node dict
        self._edges = []  # (src_id, src_port_id, dst_id, dst_port_id)
        self._zoom = 1.0

        self._scroll = wx.ScrolledWindow(self, style=wx.HSCROLL | wx.VSCROLL)
        self._scroll.SetBackgroundColour(wx.Colour(18, 22, 30))
        self._scroll.Bind(wx.EVT_PAINT, self._on_paint)
        self._scroll.Bind(wx.EVT_MOUSEWHEEL, self._on_wheel)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self._scroll, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self._build_graph()
        self._layout()
        self._update_virtual_size()

    # ── graph building ──────────────────────────────────────────────────────

    def _kind_tag(self, device):
        """Return (short_label, kind_key) for a device."""
        d = self._devices
        k = device.device_kind
        table = {
            d.AND: ("AND", "AND"),
            d.OR: ("OR", "OR"),
            d.NAND: ("NAND", "NAND"),
            d.NOR: ("NOR", "NOR"),
            d.XOR: ("XOR", "XOR"),
            d.CLOCK: ("CLK", "CLOCK"),
            d.SWITCH: ("SW", "SWITCH"),
            d.D_TYPE: ("FF", "DTYPE"),
        }
        return table.get(k, ("?", "UNKNOWN"))

    def _build_graph(self):
        d = self._devices
        for dev_id in d.find_devices():
            dev = d.get_device(dev_id)
            if dev is None:
                continue
            label = self._names.get_pretty_name(dev_id) or "?"
            short, kind = self._kind_tag(dev)
            in_ports = list(dev.inputs.keys())
            out_ports = list(dev.outputs.keys())
            h = max(52, len(in_ports) * 22 + 20) if in_ports else 52
            self._nodes[dev_id] = {
                "x": 0,
                "y": 0,
                "w": self._NODE_W,
                "h": h,
                "label": label,
                "short": short,
                "kind": kind,
                "in_ports": in_ports,
                "out_ports": out_ports,
                "layer": 0,
            }

        for dev_id in d.find_devices():
            dev = d.get_device(dev_id)
            if dev is None:
                continue
            for inp_id, conn in dev.inputs.items():
                if conn is not None:
                    src_id, src_port = conn
                    if src_id in self._nodes and dev_id in self._nodes:
                        self._edges.append((src_id, src_port, dev_id, inp_id))

    # ── layout ──────────────────────────────────────────────────────────────

    def _layout(self):
        if not self._nodes:
            return

        succs = {nid: [] for nid in self._nodes}
        preds = {nid: [] for nid in self._nodes}
        for src, _, dst, _ in self._edges:
            if src != dst and src in self._nodes and dst in self._nodes:
                if dst not in succs[src]:
                    succs[src].append(dst)
                if src not in preds[dst]:
                    preds[dst].append(src)

        # Iterative longest-path layer assignment (handles back-edges gracefully)
        layer = {nid: 0 for nid in self._nodes}
        for _ in range(len(self._nodes)):
            changed = False
            for nid in self._nodes:
                for suc in succs[nid]:
                    if layer[suc] <= layer[nid]:
                        layer[suc] = layer[nid] + 1
                        changed = True
            if not changed:
                break

        for nid in self._nodes:
            self._nodes[nid]["layer"] = layer[nid]

        # Stack nodes within each layer
        by_layer = {}
        for nid, node in self._nodes.items():
            by_layer.setdefault(node["layer"], []).append(nid)

        for l_nodes in by_layer.values():
            y = self._PAD
            for nid in l_nodes:
                self._nodes[nid]["y"] = y
                y += self._nodes[nid]["h"] + self._ROW_GAP

        for nid, node in self._nodes.items():
            node["x"] = self._PAD + node["layer"] * self._LAYER_GAP

    # ── scrolling / zoom ────────────────────────────────────────────────────

    def _update_virtual_size(self):
        if not self._nodes:
            self._scroll.SetScrollRate(10, 10)
            self._scroll.SetVirtualSize(400, 300)
            return
        z = self._zoom
        max_x = max(n["x"] + n["w"] for n in self._nodes.values()) + self._PAD
        max_y = max(n["y"] + n["h"] for n in self._nodes.values()) + self._PAD
        self._scroll.SetVirtualSize(int(max_x * z), int(max_y * z))
        self._scroll.SetScrollRate(10, 10)

    def _on_wheel(self, event):
        factor = 1.1 if event.GetWheelRotation() > 0 else 1.0 / 1.1
        self._zoom = max(0.25, min(4.0, self._zoom * factor))
        self._update_virtual_size()
        self._scroll.Refresh()

    # ── drawing ─────────────────────────────────────────────────────────────

    def _port_y(self, node, port_id, side):
        """Y offset of a port within the node box."""
        ports = node["in_ports"] if side == "in" else node["out_ports"]
        n = len(ports)
        if n == 0:
            return node["h"] / 2
        try:
            idx = ports.index(port_id)
        except ValueError:
            return node["h"] / 2
        return (idx + 1) * node["h"] / (n + 1)

    def _on_paint(self, event):
        dc = wx.PaintDC(self._scroll)
        self._scroll.PrepareDC(dc)
        gc = wx.GraphicsContext.Create(dc)
        if gc is None:
            return
        z = self._zoom
        gc.Scale(z, z)

        if not self._nodes:
            gc.SetFont(
                wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL),
                wx.Colour(160, 160, 160),
            )
            gc.DrawText(_("No circuit implemented yet."), self._PAD, self._PAD)
            return

        # Wires (drawn beneath nodes)
        wire_pen = gc.CreatePen(
            wx.GraphicsPenInfo(wx.Colour(70, 150, 220)).Width(1.5 / z)
        )
        gc.SetPen(wire_pen)
        for src_id, src_port, dst_id, dst_port in self._edges:
            sn = self._nodes.get(src_id)
            dn = self._nodes.get(dst_id)
            if sn is None or dn is None:
                continue
            sx = sn["x"] + sn["w"]
            sy = sn["y"] + self._port_y(sn, src_port, "out")
            dx = dn["x"]
            dy = dn["y"] + self._port_y(dn, dst_port, "in")
            mid = (sx + dx) / 2
            path = gc.CreatePath()
            path.MoveToPoint(sx, sy)
            path.AddCurveToPoint(mid, sy, mid, dy, dx, dy)
            gc.StrokePath(path)

        for node in self._nodes.values():
            self._draw_node(gc, node, z)

    # ── gate body shapes ────────────────────────────────────────────────────

    def _draw_and_body(self, gc, x, y, w, h, z, negate):
        """D-shaped AND body; bubble at output for NAND."""
        k = 0.5523
        r = h / 2
        mx = w * 0.5
        path = gc.CreatePath()
        path.MoveToPoint(x, y)
        path.AddLineToPoint(x + mx, y)
        path.AddCurveToPoint(x + mx + k * r, y,    x + w, y + r - k * r, x + w, y + r)
        path.AddCurveToPoint(x + w, y + r + k * r, x + mx + k * r, y + h, x + mx, y + h)
        path.AddLineToPoint(x, y + h)
        path.CloseSubpath()
        gc.DrawPath(path)
        if negate:
            br = min(5.0, h / 8)
            gc.SetBrush(gc.CreateBrush(wx.Brush(wx.Colour(210, 210, 240))))
            gc.DrawEllipse(x + w - br, y + r - br, br * 2, br * 2)

    def _draw_or_body(self, gc, x, y, w, h, z, negate):
        """Pointed OR body; bubble at output for NOR."""
        back = w * 0.22
        path = gc.CreatePath()
        path.MoveToPoint(x, y)
        path.AddCurveToPoint(x + w * 0.50, y,           x + w * 0.90, y + h * 0.15, x + w, y + h * 0.5)
        path.AddCurveToPoint(x + w * 0.90, y + h * 0.85, x + w * 0.50, y + h,       x, y + h)
        path.AddCurveToPoint(x + back, y + h * 0.70, x + back, y + h * 0.30, x, y)
        path.CloseSubpath()
        gc.DrawPath(path)
        if negate:
            br = min(5.0, h / 8)
            gc.SetBrush(gc.CreateBrush(wx.Brush(wx.Colour(210, 210, 240))))
            gc.DrawEllipse(x + w - br, y + h / 2 - br, br * 2, br * 2)

    def _draw_xor_body(self, gc, x, y, w, h, z):
        """OR body plus an interior arc on the input side (XOR marking)."""
        self._draw_or_body(gc, x, y, w, h, z, negate=False)
        back = w * 0.22
        xoff = 10
        extra = gc.CreatePath()
        extra.MoveToPoint(x + xoff, y + 2)
        extra.AddCurveToPoint(
            x + back + xoff, y + h * 0.30,
            x + back + xoff, y + h * 0.70,
            x + xoff, y + h - 2,
        )
        gc.StrokePath(extra)

    # ── node rendering ───────────────────────────────────────────────────────

    def _draw_node(self, gc, node, z):
        x, y, w, h = node["x"], node["y"], node["w"], node["h"]
        kind = node["kind"]
        bg      = self._BG.get(kind, self._BG["UNKNOWN"])
        outline = self._OUTLINE_COL.get(kind, self._OUTLINE_COL["UNKNOWN"])

        gc.SetBrush(gc.CreateBrush(wx.Brush(bg)))
        gc.SetPen(gc.CreatePen(wx.GraphicsPenInfo(outline).Width(1.5 / z)))

        if kind in ("AND", "NAND"):
            self._draw_and_body(gc, x, y, w, h, z, negate=(kind == "NAND"))
        elif kind in ("OR", "NOR"):
            self._draw_or_body(gc, x, y, w, h, z, negate=(kind == "NOR"))
        elif kind == "XOR":
            self._draw_xor_body(gc, x, y, w, h, z)
        else:
            gc.DrawRoundedRectangle(x, y, w, h, 5)

        # Gate type label
        gc.SetFont(
            wx.Font(8, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD),
            wx.Colour(200, 225, 255),
        )
        gc.DrawText(node["short"], x + 5, y + 3)

        # Signal name (truncated)
        label = node["label"]
        if len(label) > 11:
            label = label[:10] + "…"
        gc.SetFont(
            wx.Font(7, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL),
            wx.Colour(150, 185, 215),
        )
        gc.DrawText(label, x + 5, y + 15)

        stub_pen = gc.CreatePen(
            wx.GraphicsPenInfo(wx.Colour(70, 150, 220)).Width(1.5 / z)
        )
        lbl_font = wx.Font(6, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

        # Input stubs
        in_ports = node["in_ports"]
        n_in = len(in_ports)
        for i, pid in enumerate(in_ports):
            py = y + (i + 1) * h / (n_in + 1)
            gc.SetPen(stub_pen)
            gc.StrokeLine(x - 10, py, x, py)
            pname = (
                (self._names.get_pretty_name(pid) or "")
                if pid is not None
                else ""
            )
            if pname:
                gc.SetFont(lbl_font, wx.Colour(120, 155, 190))
                gc.DrawText(pname[:5], x + 3, py - 9)

        # Output stubs
        out_ports = node["out_ports"]
        n_out = len(out_ports)
        for i, pid in enumerate(out_ports):
            py = y + (i + 1) * h / (n_out + 1)
            gc.SetPen(stub_pen)
            gc.StrokeLine(x + w, py, x + w + 10, py)
            pname = (
                (self._names.get_pretty_name(pid) or "")
                if pid is not None
                else ""
            )
            if pname:
                gc.SetFont(lbl_font, wx.Colour(120, 155, 190))
                gc.DrawText(pname[:5], x + w - 18, py - 9)

        # Clock triangle on the CLK input of a flip-flop
        if kind == "DTYPE" and n_in > 0:
            for i, pid in enumerate(in_ports):
                pname = (
                    (self._names.get_pretty_name(pid) or "")
                    if pid is not None
                    else ""
                )
                if "CLK" in pname.upper():
                    py = y + (i + 1) * h / (n_in + 1)
                    gc.SetPen(
                        gc.CreatePen(
                            wx.GraphicsPenInfo(wx.Colour(220, 200, 80)).Width(
                                1.0 / z
                            )
                        )
                    )
                    gc.SetBrush(wx.TRANSPARENT_BRUSH)
                    path = gc.CreatePath()
                    path.MoveToPoint(x + 2, py - 5)
                    path.AddLineToPoint(x + 9, py)
                    path.AddLineToPoint(x + 2, py + 5)
                    path.CloseSubpath()
                    gc.StrokePath(path)
                    break


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
        fileMenu.Append(wx.ID_OPEN, _("&Open"))
        fileMenu.Append(wx.ID_SAVE, _("&Save"))
        fileMenu.AppendSeparator()
        fileMenu.Append(wx.ID_ABOUT, _("&About"))
        fileMenu.Append(wx.ID_EXIT, _("&Exit"))

        viewMenu = wx.Menu()
        self._viewer_menu_item = viewMenu.AppendCheckItem(
            ID_TOGGLE_VIEWER, _("&Show File Viewer\tCtrl+Shift+F")
        )

        menuBar = wx.MenuBar()
        menuBar.Append(fileMenu, _("&File"))
        menuBar.Append(viewMenu, _("&View"))
        self.SetMenuBar(menuBar)

        helpMenu = wx.Menu()
        helpMenu.Append(wx.ID_HELP, _("&Documentation"))
        menuBar.Append(helpMenu, _("&Help"))

        # ── Outer horizontal splitter (simulator | file viewer) ─────────────
        self.outer_splitter = wx.SplitterWindow(
            self, style=wx.SP_LIVE_UPDATE | wx.SP_NO_XP_THEME
        )
        self.outer_splitter.SetSashGravity(
            0.0
        )  # allocate more space to left pane
        self.outer_splitter.SetMinimumPaneSize(200)

        # Left pane wraps the existing horizontal (controls / canvas) layout
        self.left_pane = wx.Panel(self.outer_splitter)
        self.left_pane.SetMinSize((650, -1))

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

        # Host panel holds 2D and 3D canvases; only one shown at a time
        self.canvas_host = wx.Panel(self.canvas_panel)
        self.canvas = MyGLCanvas(self.canvas_host, devices, monitors)
        self.canvas3d = MyGL3DCanvas(self.canvas_host, devices, monitors)
        self.canvas3d.Hide()
        self._is_3d = False
        _host_sizer = wx.BoxSizer(wx.VERTICAL)
        _host_sizer.Add(self.canvas, 1, wx.EXPAND)
        _host_sizer.Add(self.canvas3d, 1, wx.EXPAND)
        self.canvas_host.SetSizer(_host_sizer)

        # Scrollbars
        self.v_scroll = wx.ScrollBar(self.canvas_panel, style=wx.SB_VERTICAL)
        self.h_scroll = wx.ScrollBar(self.canvas_panel, style=wx.SB_HORIZONTAL)

        self.v_scroll.Bind(wx.EVT_SCROLL, self.on_v_scroll)
        self.h_scroll.Bind(wx.EVT_SCROLL, self.on_h_scroll)

        # X-axis zoom slider
        self.x_zoom_slider = wx.Slider(
            self.canvas_panel,
            value=1,
            minValue=1,
            maxValue=30,
            style=wx.SL_HORIZONTAL,
        )
        self.x_zoom_value_label = wx.StaticText(self.canvas_panel, label="1×")
        self.x_zoom_slider.Bind(wx.EVT_SLIDER, self.on_x_zoom)
        x_zoom_row = wx.BoxSizer(wx.HORIZONTAL)
        x_zoom_row.Add(
            wx.StaticText(self.canvas_panel, label=_("X Zoom:")),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.LEFT,
            6,
        )
        x_zoom_row.Add(
            self.x_zoom_slider, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 4
        )
        x_zoom_row.Add(
            self.x_zoom_value_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6
        )

        self._view_3d_btn = wx.ToggleButton(
            self.canvas_panel, label="3D", size=(38, 26)
        )
        self._view_3d_btn.SetToolTip(_("Switch to 3D signal view"))
        self._view_3d_btn.Bind(wx.EVT_TOGGLEBUTTON, self._on_toggle_3d)
        x_zoom_row.Add(
            self._view_3d_btn,
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT,
            6,
        )

        self._logic_viewer_btn = wx.Button(
            self.canvas_panel, label=_("Logic Viewer"), size=(-1, 26)
        )
        self._logic_viewer_btn.SetToolTip(_("Show gate-level circuit diagram"))
        self._logic_viewer_btn.Bind(wx.EVT_BUTTON, self._on_logic_viewer)
        x_zoom_row.Add(
            self._logic_viewer_btn,
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT,
            6,
        )

        # Arrange canvas, scrollbars, and zoom slider
        canvas_sizer = wx.GridBagSizer(0, 0)
        canvas_sizer.Add(self.canvas_host, pos=(0, 0), flag=wx.EXPAND)
        canvas_sizer.Add(self.v_scroll, pos=(0, 1), flag=wx.EXPAND)
        canvas_sizer.Add(self.h_scroll, pos=(1, 0), flag=wx.EXPAND)
        canvas_sizer.Add(x_zoom_row, pos=(2, 0), flag=wx.EXPAND)
        canvas_sizer.AddGrowableCol(0)
        canvas_sizer.AddGrowableRow(0)
        self.canvas_panel.SetSizer(canvas_sizer)

        # ── Base Control Panel & AUI Management Setup ────────────────────────
        self.top_panel = wx.Panel(self.splitter)
        # self.top_panel.SetMinSize((-1, 150))

        self.aui_manager = agw_aui.AuiManager(self.top_panel)

        # FIX: Create the sub-pane window panels BEFORE using them as parents
        sim_pane = wx.Panel(self.top_panel)
        switch_pane = wx.Panel(self.top_panel)
        monitor_pane = wx.Panel(self.top_panel)
        console_pane = wx.Panel(self.top_panel)

        # ── Widgets (Now attached to their correct, existing parents) ─────────
        self.cycles_label = wx.StaticText(sim_pane, wx.ID_ANY, _("Cycles"))
        self.spin = wx.SpinCtrl(
            sim_pane, wx.ID_ANY, "10", min=1, max=1000, size=(110, -1)
        )
        self.run_button = wx.Button(sim_pane, wx.ID_ANY, "▶", size=(32, 28))
        self.continue_button = wx.Button(
            sim_pane, wx.ID_ANY, "+10", size=(45, 28)
        )
        self.last_cycles_check = wx.CheckBox(sim_pane, wx.ID_ANY, _("Last"))
        self.last_cycles_spin = wx.SpinCtrl(
            sim_pane, wx.ID_ANY, "10", min=1, max=1000, size=(70, -1)
        )
        self.reset_button = wx.Button(sim_pane, wx.ID_ANY, "↺", size=(32, 28))

        self.switch_label = wx.StaticText(
            switch_pane, wx.ID_ANY, _("Select switch:")
        )
        self.switch_list = wx.ListCtrl(
            switch_pane,
            wx.ID_ANY,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_HRULES,
        )
        self.switch_list.InsertColumn(0, _("Switch"))
        self.switch_list.InsertColumn(1, _("Value"), wx.LIST_FORMAT_CENTER)
        self.switch_list.Bind(wx.EVT_SIZE, self._on_switch_list_size)
        self.switch_list.Bind(
            wx.EVT_LIST_COL_END_DRAG, self._on_switch_col_drag
        )
        self.switch_on = wx.Button(switch_pane, wx.ID_ANY, _("Set ON"))
        self.switch_off = wx.Button(switch_pane, wx.ID_ANY, _("Set OFF"))

        self.monitors_label = wx.StaticText(
            monitor_pane, wx.ID_ANY, _("Monitors:")
        )
        self.monitors_list = wx.ListBox(
            monitor_pane, wx.ID_ANY, choices=[], style=wx.LB_SINGLE
        )
        self.add_monitor_btn = wx.Button(monitor_pane, wx.ID_ANY, "+")
        self.remove_monitor_btn = wx.Button(monitor_pane, wx.ID_ANY, "-")
        self.monitor_up_btn = wx.Button(monitor_pane, wx.ID_ANY, "↑")
        self.monitor_down_btn = wx.Button(monitor_pane, wx.ID_ANY, "↓")

        self.console = wx.TextCtrl(
            console_pane,
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
            _("Run the simulation from scratch for %d cycles") % initial_cycles
        )
        self.continue_button.SetToolTip(
            _("Continue the simulation for %d additional cycles")
            % initial_cycles
        )
        self.reset_button.SetToolTip(
            _("Reset the simulation to its initial state")
        )
        self.switch_list.SetToolTip(
            _("Click a switch to select it, then use Set ON / Set OFF")
        )
        self.switch_on.SetToolTip(_("Set the selected switch to ON (1)"))
        self.switch_off.SetToolTip(_("Set the selected switch to OFF (0)"))
        self.add_monitor_btn.SetToolTip(
            _("Add a monitor to the selected signal")
        )
        self.remove_monitor_btn.SetToolTip(_("Remove the selected monitor"))
        self.monitor_up_btn.SetToolTip(_("Move selected monitor up"))
        self.monitor_down_btn.SetToolTip(_("Move selected monitor down"))
        self.spin.SetToolTip(_("Number of cycles to run or continue"))
        self.last_cycles_check.SetToolTip(
            _("Show only the most recent cycles")
        )
        self.last_cycles_spin.SetToolTip(_("Number of recent cycles to show"))
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
        self.monitor_up_btn.Bind(wx.EVT_BUTTON, self.on_monitor_move_up)
        self.monitor_down_btn.Bind(wx.EVT_BUTTON, self.on_monitor_move_down)
        self.reset_button.Bind(wx.EVT_BUTTON, self.on_reset_button)
        self.Bind(wx.EVT_MENU, self.on_help_menu, id=wx.ID_HELP)

        # ── Sizers and Structural Layout ────────────────────────────────────

        # 1. Simulation Container
        # StaticBoxSizer dropped: the AUI caption bar now provides the "Simulation"
        # title, so a second heading would be redundant.
        sim_sizer = wx.BoxSizer(wx.VERTICAL)
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
        sim_pane.SetSizer(sim_sizer)

        # 2. Switches Container
        switch_sizer = wx.BoxSizer(wx.VERTICAL)
        switch_sizer.Add(self.switch_label, 0, wx.ALL, 5)
        switch_sizer.Add(
            self.switch_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5
        )

        switch_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.switch_on.SetMinSize((50, -1))
        self.switch_off.SetMinSize((50, -1))
        switch_btn_sizer.Add(self.switch_on, 1, wx.ALL, 5)
        switch_btn_sizer.Add(self.switch_off, 1, wx.ALL, 5)
        switch_sizer.Add(switch_btn_sizer, 0, wx.EXPAND)
        switch_pane.SetSizer(switch_sizer)

        # 3. Monitors Container
        for _btn in (
            self.add_monitor_btn,
            self.remove_monitor_btn,
            self.monitor_up_btn,
            self.monitor_down_btn,
        ):
            _btn.SetMinSize((28, 28))

        monitor_sizer = wx.BoxSizer(wx.VERTICAL)
        monitor_sizer.Add(self.monitors_label, 0, wx.ALL, 5)
        monitor_sizer.Add(self.monitors_list, 1, wx.EXPAND | wx.ALL, 5)

        monitor_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        monitor_btn_sizer.Add(self.add_monitor_btn, 1, wx.EXPAND | wx.ALL, 2)
        monitor_btn_sizer.Add(
            self.remove_monitor_btn, 1, wx.EXPAND | wx.ALL, 2
        )
        monitor_btn_sizer.Add(self.monitor_up_btn, 1, wx.EXPAND | wx.ALL, 2)
        monitor_btn_sizer.Add(self.monitor_down_btn, 1, wx.EXPAND | wx.ALL, 2)
        monitor_sizer.Add(
            monitor_btn_sizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 3
        )
        monitor_pane.SetSizer(monitor_sizer)

        # 4. Console Container
        console_sizer = wx.BoxSizer(wx.VERTICAL)
        console_sizer.Add(self.console, 1, wx.EXPAND | wx.ALL, 5)
        console_pane.SetSizer(console_sizer)

        # The caption bar also doubles as the resize drag target between panes.
        _resizable_pane = lambda pos, caption: (
            agw_aui.AuiPaneInfo()
            .Caption(caption)
            .Top()
            .Layer(0)
            .Row(0)
            .Position(pos)
            .Resizable(True)
            .CloseButton(False)
            .Floatable(True)
            .TopDockable(True)
            .LeftDockable(False)
            .RightDockable(False)
            .BottomDockable(False)
        )

        self.aui_manager.AddPane(
            sim_pane,
            _resizable_pane(0, _("Simulation"))
            .Name("Simulation")
            .MinSize((120, 155))
            .BestSize((200, 195)),
        )

        self.aui_manager.AddPane(
            switch_pane,
            _resizable_pane(1, _("Switches"))
            .Name("Switches")
            .MinSize((120, 155))
            .BestSize((200, 195)),
        )

        self.aui_manager.AddPane(
            monitor_pane,
            _resizable_pane(2, _("Monitors"))
            .Name("Monitors")
            .MinSize((160, 155))
            .BestSize((200, 195)),
        )

        # Console gets a wider BestSize because wx.TextCtrl has no natural
        # fixed width of its own.
        self.aui_manager.AddPane(
            console_pane,
            _resizable_pane(3, _("Console"))
            .Name("Console")
            .MinSize((200, 155))
            .BestSize((450, 195)),
        )

        self.aui_manager.Update()
        self.top_panel.Bind(wx.EVT_SIZE, self._on_top_panel_size)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.on_destroy)

        # ── Inner splitter split ─────────────────────────────────────────────
        self.splitter.SplitHorizontally(self.top_panel, self.canvas_panel, 170)
        self.splitter.SetMinimumPaneSize(150)

        # ── Left-pane sizer wraps the inner splitter ─────────────────────────
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        left_sizer.Add(self.splitter, 1, wx.EXPAND)
        self.left_pane.SetSizer(left_sizer)

        # ── Frame sizer wraps the outer splitter ─────────────────────────────
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.outer_splitter, 1, wx.EXPAND)
        self.SetSizeHints(850, 400)  # minimum size to prevent extreme resizing
        self.SetSizer(main_sizer)

        self.CreateStatusBar()
        self.SetStatusText(_("Ready"))

        # Initialise scrollbar state
        self.update_scrollbars()
        self._switch_col_ratio = 0.5
        self._nonmonitored_order = (
            None  # persistent display order for inactive signals
        )
        self.update_switch_list()
        self.update_monitors_list()

        # Load the initial file into the viewer if one was provided
        if path:
            self._load_file_into_viewer(path)

    def on_destroy(self, event):
        """Safely detach and clean up the active AUI workspace layout layout engine."""
        if hasattr(self, "aui_manager"):
            self.aui_manager.UnInit()
        event.Skip()

    def _on_top_panel_size(self, event):
        """Keep AUI pane heights in sync with the top panel so they fill it."""
        event.Skip()
        wx.CallAfter(self._fit_aui_panes_to_panel)

    def _fit_aui_panes_to_panel(self):
        h = self.top_panel.GetClientSize().GetHeight()
        if h <= 0:
            return
        # agw_aui caches dock heights in dock.size and re-uses them on every
        # Update(), ignoring BestSize once set.  Patch the stored dock size
        # directly so the Top dock always fills the full panel height.
        AUI_DOCK_TOP = 1
        for dock in self.aui_manager._docks:
            if dock.dock_direction == AUI_DOCK_TOP:
                dock.size = h
        for name in ("Simulation", "Switches", "Monitors"):
            pane = self.aui_manager.GetPane(name)
            if pane.IsOk():
                pane.BestSize(pane.best_size.GetWidth(), h)
        self.aui_manager.Update()

    # ── File viewer ──────────────────────────────────────────────────────────

    def _build_file_viewer(self, parent):
        """Create the right-hand file-viewer panel and attach it to parent."""
        self.viewer_panel = wx.Panel(parent)
        self.viewer_panel.Hide()  # prevent rendering at (0,0) before first split
        viewer_sizer = wx.BoxSizer(wx.VERTICAL)

        # Header bar: label + close button
        header_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._viewer_title = wx.StaticText(
            self.viewer_panel,
            label=_("File Viewer"),
            style=wx.ST_ELLIPSIZE_END,
        )
        title_font = self._viewer_title.GetFont()
        title_font.SetWeight(wx.FONTWEIGHT_BOLD)
        self._viewer_title.SetFont(title_font)

        self._viewer_title.SetMinSize((50, -1))

        save_btn = wx.Button(self.viewer_panel, label=_("Save"), size=(50, 28))
        save_btn.SetToolTip(_("Save changes to file"))
        save_btn.Bind(wx.EVT_BUTTON, self._on_save_viewer)

        implement_btn = wx.Button(
            self.viewer_panel, label=_("Implement"), size=(80, 28)
        )
        implement_btn.SetToolTip(_("Run the simulator using this file"))
        implement_btn.Bind(wx.EVT_BUTTON, self._on_implement_viewer)

        close_btn = wx.Button(self.viewer_panel, label="X", size=(28, 28))
        close_btn.SetToolTip(_("Close file viewer"))
        close_btn.Bind(wx.EVT_BUTTON, self._on_close_viewer)

        header_sizer.Add(
            self._viewer_title, 1, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 6
        )
        header_sizer.Add(save_btn, 0, wx.ALL, 2)
        header_sizer.Add(implement_btn, 0, wx.ALL, 2)
        header_sizer.Add(close_btn, 0, wx.ALL, 2)

        # Scintilla editor with line numbers
        self._file_text = wx.stc.StyledTextCtrl(
            self.viewer_panel, style=wx.BORDER_NONE
        )
        self._file_text.SetLexer(wx.stc.STC_LEX_NULL)
        mono_font = wx.Font(
            10,
            wx.FONTFAMILY_TELETYPE,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        )
        self._file_text.StyleSetFont(wx.stc.STC_STYLE_DEFAULT, mono_font)
        self._file_text.StyleSetBackground(
            wx.stc.STC_STYLE_DEFAULT, wx.Colour(20, 24, 32)
        )
        self._file_text.StyleSetForeground(
            wx.stc.STC_STYLE_DEFAULT, wx.Colour(210, 220, 235)
        )
        self._file_text.StyleClearAll()
        self._file_text.SetCaretForeground(wx.Colour(210, 220, 235))
        self._file_text.SetWrapMode(wx.stc.STC_WRAP_WORD)

        # Line number margin
        self._file_text.SetMarginType(0, wx.stc.STC_MARGIN_NUMBER)
        self._file_text.SetMarginWidth(0, 48)
        self._file_text.StyleSetBackground(
            wx.stc.STC_STYLE_LINENUMBER, wx.Colour(30, 35, 45)
        )
        self._file_text.StyleSetForeground(
            wx.stc.STC_STYLE_LINENUMBER, wx.Colour(100, 120, 150)
        )
        # Margin 1: error indicator dots (14 px)
        self._file_text.SetMarginType(1, wx.stc.STC_MARGIN_SYMBOL)
        self._file_text.SetMarginWidth(1, 14)
        self._file_text.SetMarginSensitive(1, True)
        self._file_text.SetMarginMask(1, 0b11)  # show markers 0 and 1
        self._file_text.SetMarginWidth(2, 0)

        # Marker 0: red circle in error margin
        self._file_text.MarkerDefine(
            0,
            wx.stc.STC_MARK_CIRCLE,
            wx.Colour(220, 60, 60),
            wx.Colour(200, 40, 40),
        )
        # Marker 1: full-line red background
        self._file_text.MarkerDefine(
            1,
            wx.stc.STC_MARK_BACKGROUND,
            wx.Colour(80, 20, 20),
            wx.Colour(70, 18, 18),
        )

        # Style 40: red italic text used for inline error annotations
        self._file_text.StyleSetForeground(40, wx.Colour(255, 110, 110))
        self._file_text.StyleSetBackground(40, wx.Colour(50, 12, 12))
        self._file_text.StyleSetItalic(40, True)
        self._file_text.AnnotationSetVisible(2)  # 2 = STC_ANNOTATION_BOXED

        self._error_map = {}  # 0-indexed line → error string
        self._file_text.Bind(
            wx.stc.EVT_STC_MARGINCLICK, self._on_error_margin_click
        )

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
            self._file_text.SetText(content)
            self._file_text.MarkerDeleteAll(0)
            self._file_text.MarkerDeleteAll(1)
            self._file_text.AnnotationClearAll()
            self._error_map = {}
            filename = path.split("/")[-1].split("\\")[-1]
            self._viewer_title.SetLabel(_("File Viewer") + f" — {filename}")
            self._viewer_title.SetToolTip(path)
        except OSError as exc:
            self._file_text.SetText(_("Could not open file:\n%s") % exc)
            self._viewer_title.SetLabel(_("File Viewer — error"))

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
            self.SetStatusText(_("File viewer opened."))

    def _hide_viewer(self):
        """Collapse the file viewer by un-splitting."""
        if self._viewer_visible:
            self.outer_splitter.Unsplit(self.viewer_panel)
            self._viewer_visible = False
            self._viewer_menu_item.Check(False)
            self.SetStatusText(_("File viewer closed."))

    def _on_save_viewer(self, event):
        """Save the current contents of the file viewer back to disk."""
        if not self._viewer_path:
            wx.MessageBox(
                _("No file is open — nothing to save."),
                _("Save"),
                wx.ICON_WARNING | wx.OK,
            )
            return
        try:
            with open(self._viewer_path, "w") as fh:
                fh.write(self._file_text.GetText())
            self.SetStatusText(_("Saved: %s") % self._viewer_path)
            self.log(_("File saved: %s") % self._viewer_path)
        except OSError as exc:
            wx.MessageBox(
                _("Could not save file:\n%s") % exc,
                _("Save Error"),
                wx.ICON_ERROR | wx.OK,
            )

    def _save_viewer_contents(self):
        """Save viewer contents and return whether it succeeded."""
        if not self._viewer_path:
            wx.MessageBox(
                _("No file is open - nothing to implement."),
                _("Implement"),
                wx.ICON_WARNING | wx.OK,
            )
            return False
        try:
            with open(self._viewer_path, "w") as fh:
                fh.write(self._file_text.GetText())
            self.SetStatusText(_("Saved: %s") % self._viewer_path)
            self.log(_("File saved: %s") % self._viewer_path)
            return True
        except OSError as exc:
            wx.MessageBox(
                _("Could not save file:\n%s") % exc,
                _("Save Error"),
                wx.ICON_ERROR | wx.OK,
            )
            return False

    def _highlight_errors(self, errors):
        """Mark error lines with a red dot, background, and collapsible annotation."""
        self._file_text.MarkerDeleteAll(0)
        self._file_text.MarkerDeleteAll(1)
        self._file_text.AnnotationClearAll()
        self._error_map = {}
        first_line = None
        for err in errors:
            m = re.search(r"at\s+(?:line\s+)?(\d+)", err)
            if m:
                ln = int(m.group(1)) - 1  # STC lines are 0-indexed
                # Accumulate multiple errors on the same line
                if ln in self._error_map:
                    self._error_map[ln] += "\n  " + err
                else:
                    self._error_map[ln] = err
                self._file_text.MarkerAdd(ln, 0)
                self._file_text.MarkerAdd(ln, 1)
                if first_line is None:
                    first_line = ln
        # Show all annotations immediately; clicking the dot toggles them
        for ln, msg in self._error_map.items():
            self._file_text.AnnotationSetText(ln, "  " + msg)
            self._file_text.AnnotationSetStyle(ln, 40)
        if first_line is not None:
            self._file_text.GotoLine(first_line)

    def _on_error_margin_click(self, event):
        """Toggle the error annotation for the clicked line."""
        if event.GetMargin() != 1:
            event.Skip()
            return
        ln = self._file_text.LineFromPosition(event.GetPosition())
        if ln not in self._error_map:
            return
        if self._file_text.AnnotationGetText(ln):
            self._file_text.AnnotationSetText(ln, "")
        else:
            self._file_text.AnnotationSetText(ln, "  " + self._error_map[ln])
            self._file_text.AnnotationSetStyle(ln, 40)

    def _on_implement_viewer(self, event):
        """Use the file currently shown in the viewer as the active circuit."""
        if not self._save_viewer_contents():
            return

        # Clear all previous highlights before every parse attempt so stale
        # error markers never persist after the underlying issue is fixed.
        self._file_text.MarkerDeleteAll(0)
        self._file_text.MarkerDeleteAll(1)
        self._file_text.AnnotationClearAll()
        self._error_map = {}

        names = Names()
        devices = Devices(names)
        network = Network(names, devices)
        monitors = Monitors(names, devices, network)
        scanner = Scanner(self._viewer_path, names)
        parser = Parser(names, devices, network, monitors, scanner)

        if not parser.parse_network():
            wx.MessageBox(
                _("Could not implement this file because it contains errors."),
                _("Implement Error"),
                wx.ICON_ERROR | wx.OK,
            )
            self.SetStatusText(_("Implement failed: parse errors in file."))
            self.log(
                _("Implement failed: parse errors in %s") % self._viewer_path
            )
            for e in parser.errors:
                self.log(e)
            self._highlight_errors(parser.errors)
            return

        self.names = names
        self.devices = devices
        self.network = network
        self.monitors = monitors
        self.cycles_completed = 0
        self.canvas.devices = devices
        self.canvas.monitors = monitors
        self.canvas.previous_signal_traces = {}
        self.canvas3d.devices = devices
        self.canvas3d.monitors = monitors
        self.canvas3d.previous_signal_traces = {}
        self._nonmonitored_order = None  # reset ordering for the new circuit
        self.update_switch_list()
        self.update_monitors_list()
        self.update_scrollbars()
        self._render_canvas()
        self.SetTitle("Logic Simulator - " + self._viewer_path)
        self.SetStatusText(_("Implemented: %s") % self._viewer_path)
        self.log(_("Implemented file: %s") % self._viewer_path)

    def _on_close_viewer(self, event):
        """Handle the X button inside the viewer panel."""
        self._hide_viewer()

    # ── 2D / 3D canvas toggle ────────────────────────────────────────────────

    def _render_canvas(self):
        """Render whichever canvas is currently active."""
        if self._is_3d:
            self.canvas3d.render()
        else:
            self.canvas.render()

    def _on_logic_viewer(self, event):
        """Open the gate-level schematic dialog."""
        if not self.devices.find_devices():
            wx.MessageBox(
                _("Please implement a circuit file first."),
                _("No Circuit"),
                wx.OK | wx.ICON_INFORMATION,
            )
            return
        dlg = LogicViewerDialog(self, self.devices, self.network, self.names)
        dlg.ShowModal()
        dlg.Destroy()

    def _on_toggle_3d(self, event):
        """Switch between the 2D and 3D signal views."""
        self._is_3d = event.GetInt() == 1
        if self._is_3d:
            self.canvas.Hide()
            self.canvas3d.Show()
            self._view_3d_btn.SetLabel("2D")
            self._view_3d_btn.SetToolTip(_("Switch back to 2D signal view"))
            self.SetStatusText(
                _("3D view enabled — drag to rotate, scroll to zoom.")
            )
        else:
            self.canvas3d.Hide()
            self.canvas.Show()
            self._view_3d_btn.SetLabel("3D")
            self._view_3d_btn.SetToolTip(_("Switch to 3D signal view"))
            self.SetStatusText(_("2D view enabled."))
        self.canvas_host.Layout()
        self._render_canvas()

    # ── Menu ─────────────────────────────────────────────────────────────────

    def on_menu(self, event):
        """Handle the event when the user selects a menu item."""
        Id = event.GetId()
        if Id == wx.ID_EXIT:
            self.Close(True)

        elif Id == wx.ID_ABOUT:
            wx.MessageBox(
                _(
                    "Logic Simulator\nGF2 Software Project\n"
                    "Cambridge University Engineering Department\n2026"
                ),
                _("About Logic Simulator"),
                wx.ICON_INFORMATION | wx.OK,
            )

        elif Id == wx.ID_SAVE:
            self._on_save_viewer(event)

        elif Id == wx.ID_OPEN:
            wildcard = _(
                "Circuit definition files (*.txt)|*.txt|All files (*.*)|*.*"
            )
            dlg = wx.FileDialog(
                self,
                _("Open circuit definition file"),
                wildcard=wildcard,
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
            )
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                self._viewer_path = path
                self.SetTitle("Logic Simulator - " + path)
                self.SetStatusText(_("Opened: %s") % path)
                self.log(_("Opened file: %s") % path)
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
                self.SetStatusText(_("Error: network oscillating."))
                self.log(_("Error: network oscillating."))
                return False
        return True

    def archive_current_traces(self):
        """Store current monitor traces for the next cycle-windowed run view."""
        archived = {
            monitor: list(signal_list)
            for monitor, signal_list in self.monitors.monitors_dict.items()
            if signal_list
        }
        self.canvas.previous_signal_traces = archived
        self.canvas3d.previous_signal_traces = archived

    def update_monitors_list(self):
        """Refresh the monitor list from backend monitor state."""
        monitored_signals, non_monitored_signals = (
            self.monitors.get_signal_names()
        )

        # Build a lookup for non-monitored signals so we can apply the stored order.
        nm_dict = {
            clean_name: raw_name
            for clean_name, raw_name in non_monitored_signals
        }
        if self._nonmonitored_order is None:
            self._nonmonitored_order = list(nm_dict.keys())
        else:
            # Keep user-defined order; append newly-seen signals at the end.
            kept = [k for k in self._nonmonitored_order if k in nm_dict]
            added = [k for k in nm_dict if k not in self._nonmonitored_order]
            self._nonmonitored_order = kept + added

        display_names = [pair[0] + _(" (on)") for pair in monitored_signals]
        display_names.extend(self._nonmonitored_order)
        self.monitors_list.Set(display_names)

        self._monitor_choices = {
            clean_name + _(" (on)"): raw_name
            for clean_name, raw_name in monitored_signals
        }
        self._monitor_choices.update(
            {k: nm_dict[k] for k in self._nonmonitored_order}
        )

    def on_last_cycles_change(self, event):
        """Update the canvas cycle-window view."""
        if self.last_cycles_check.GetValue():
            visible_cycles = self.last_cycles_spin.GetValue()
            self.last_cycles_spin.Enable(True)
            self.canvas.visible_cycles = visible_cycles
            self.canvas3d.visible_cycles = visible_cycles
            self.SetStatusText(_("Showing last %d cycles.") % visible_cycles)
        else:
            self.last_cycles_spin.Enable(False)
            self.canvas.visible_cycles = None
            self.canvas3d.visible_cycles = None
            self.SetStatusText(_("Showing all recorded cycles."))
        self._render_canvas()

    def on_spin(self, event):
        """Handle the event when the user changes the spin control value."""
        spin_value = self.spin.GetValue()

        # Update button label
        self.continue_button.SetLabel(f"+{spin_value}")

        # Update tooltips dynamically
        self.run_button.SetToolTip(
            _("Run the simulation from scratch for %d cycles") % spin_value
        )
        self.continue_button.SetToolTip(
            _("Continue the simulation for %d additional cycles") % spin_value
        )

        self._render_canvas()
        self.log(_("New spin control value: %d") % spin_value)

    def on_run_button(self, event):
        """Handle the event when the user clicks the run button."""
        cycles = self.spin.GetValue()
        self.SetStatusText(_("Running for %d cycles...") % cycles)
        self.log(_("Run clicked: %d cycles requested.") % cycles)
        self.archive_current_traces()
        self.cycles_completed = 0
        self.monitors.reset_monitors()
        self.devices.cold_startup()
        if self.run_network(cycles):
            self.cycles_completed = cycles
            self.SetStatusText(_("Completed %d cycles.") % cycles)
            self.log(_("Completed %d cycles.") % cycles)
        self.update_monitors_list()
        self._render_canvas()

    def on_continue_button(self, event):
        """Handle the event when the user clicks the continue button."""
        cycles = self.spin.GetValue()
        if self.cycles_completed == 0:
            self.SetStatusText(_("Error: nothing to continue. Run first."))
            self.log(_("Continue ignored: run the simulation first."))
            return
        self.SetStatusText(_("Continuing for %d cycles...") % cycles)
        self.log(_("Continue clicked: %d cycles requested.") % cycles)
        if self.run_network(cycles):
            self.cycles_completed += cycles
            self.SetStatusText(
                _("Completed %d cycles.") % self.cycles_completed
            )
            self.log(_("Completed %d total cycles.") % self.cycles_completed)
        self.update_monitors_list()
        self._render_canvas()

    def on_switch_on(self, event):
        """Handle the event when the user clicks the switch on button."""
        selection = self.switch_list.GetFirstSelected()
        if selection == -1:
            self.SetStatusText(_("Error: please select a switch first."))
            return
        clean_switch_name = self.switch_list.GetItemText(selection, 0)
        raw_switch_name = self._switch_map.get(clean_switch_name)
        switch_id = self.names.query(raw_switch_name)

        if self.devices.set_switch(switch_id, self.devices.HIGH):
            self.SetStatusText(_("Switch %s set ON.") % clean_switch_name)
            self.log(_("Switch %s set ON.") % clean_switch_name)
            self.update_switch_list()
            self._render_canvas()
        else:
            self.SetStatusText(
                _("Error: could not set switch %s.") % clean_switch_name
            )

    def on_switch_off(self, event):
        """Handle the event when the user clicks the switch off button."""
        selection = self.switch_list.GetFirstSelected()
        if selection == -1:
            self.SetStatusText(_("Error: please select a switch first."))
            return

        clean_switch_name = self.switch_list.GetItemText(selection, 0)
        raw_switch_name = self._switch_map.get(clean_switch_name)
        switch_id = self.names.query(raw_switch_name)

        if self.devices.set_switch(switch_id, self.devices.LOW):
            self.SetStatusText(_("Switch %s set OFF.") % clean_switch_name)
            self.log(_("Switch %s set OFF.") % clean_switch_name)
            self.update_switch_list()
            self._render_canvas()
        else:
            self.SetStatusText(
                _("Error: could not set switch %s.") % clean_switch_name
            )

    def on_add_monitor(self, event):
        """Handle the event when the user clicks the add monitor button."""
        selection = self.monitors_list.GetSelection()
        if selection == wx.NOT_FOUND:
            self.SetStatusText(_("Error: please select a signal first."))
            return

        display_name = self.monitors_list.GetString(selection)
        signal_name = self._monitor_choices.get(display_name, display_name)
        signal_ids = self.devices.get_signal_ids(signal_name)
        if signal_ids is None:
            self.SetStatusText(_("Error: selected signal was not found."))
            return

        device_id, output_id = signal_ids
        monitor_error = self.monitors.make_monitor(
            device_id, output_id, self.cycles_completed
        )
        if monitor_error == self.monitors.NO_ERROR:
            self.SetStatusText(_("Added monitor: %s") % signal_name)
            self.log(_("Added monitor: %s") % signal_name)
        elif monitor_error == self.monitors.MONITOR_PRESENT:
            self.SetStatusText(_("Monitor already active: %s") % signal_name)
        else:
            self.SetStatusText(
                _("Error: could not add monitor %s") % signal_name
            )
        self.update_monitors_list()
        self._render_canvas()

    def on_remove_monitor(self, event):
        """Handle the event when the user clicks the remove monitor button."""
        selection = self.monitors_list.GetSelection()
        if selection == wx.NOT_FOUND:
            self.SetStatusText(_("Error: please select a monitor first."))
            return

        display_name = self.monitors_list.GetString(selection)
        signal_name = self._monitor_choices.get(display_name, display_name)
        signal_ids = self.devices.get_signal_ids(signal_name)
        if signal_ids is None:
            self.SetStatusText(_("Error: selected signal was not found."))
            return

        device_id, output_id = signal_ids
        if self.monitors.remove_monitor(device_id, output_id):
            self.SetStatusText(_("Removed monitor: %s") % signal_name)
            self.log(_("Removed monitor: %s") % signal_name)
        else:
            self.SetStatusText(
                _("Error: monitor is not active: %s") % signal_name
            )
        self.update_monitors_list()
        self._render_canvas()

    def on_monitor_reorder(self, src, dst):
        """Reorder monitors_dict when the user drag-drops a canvas waveform row."""
        keys = list(self.monitors.monitors_dict.keys())
        if not (0 <= src < len(keys) and 0 <= dst < len(keys)):
            return
        moved = keys.pop(src)
        keys.insert(dst, moved)
        old_dict = dict(self.monitors.monitors_dict)
        self.monitors.monitors_dict.clear()
        for key in keys:
            self.monitors.monitors_dict[key] = old_dict[key]
        self.update_monitors_list()
        self._render_canvas()

    def on_monitor_move_up(self, _):
        """Move the selected list entry one position earlier."""
        sel = self.monitors_list.GetSelection()
        if sel == wx.NOT_FOUND or sel == 0:
            return
        n_mon = len(self.monitors.monitors_dict)
        if sel < n_mon:
            # Active monitor — reorder monitors_dict
            self.on_monitor_reorder(sel, sel - 1)
        elif sel > n_mon:
            # Non-monitored signal — reorder the display list
            nm_idx = sel - n_mon
            order = self._nonmonitored_order
            order[nm_idx], order[nm_idx - 1] = order[nm_idx - 1], order[nm_idx]
            self.update_monitors_list()
        # sel == n_mon means first non-monitored entry; can't cross the boundary
        self.monitors_list.SetSelection(sel - 1 if sel != n_mon else sel)

    def on_monitor_move_down(self, _):
        """Move the selected list entry one position later."""
        sel = self.monitors_list.GetSelection()
        if sel == wx.NOT_FOUND:
            return
        n_mon = len(self.monitors.monitors_dict)
        total = self.monitors_list.GetCount()
        if sel >= total - 1:
            return
        if sel < n_mon - 1:
            # Active monitor — reorder monitors_dict
            self.on_monitor_reorder(sel, sel + 1)
        elif sel >= n_mon:
            # Non-monitored signal — reorder the display list
            nm_idx = sel - n_mon
            order = self._nonmonitored_order
            order[nm_idx], order[nm_idx + 1] = order[nm_idx + 1], order[nm_idx]
            self.update_monitors_list()
        # sel == n_mon - 1 means last active monitor; can't cross the boundary
        self.monitors_list.SetSelection(sel + 1 if sel != n_mon - 1 else sel)

    def on_reset_button(self, event):
        """Handle the event when the user clicks the reset button."""
        self.cycles_completed = 0
        self.monitors.reset_monitors()
        self.canvas.previous_signal_traces = {}
        self.canvas3d.previous_signal_traces = {}
        self.devices.cold_startup()
        self.SetStatusText(_("Simulation reset."))
        self._render_canvas()
        self.log(_("Simulation reset."))

    def log(self, message):
        """Append a time-stamped message to the console output."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.console.AppendText(f"[{timestamp}] {message}\n")

    def on_h_scroll(self, event):
        """Handle horizontal scrollbar scrolling."""
        zoom = getattr(self.canvas, "zoom", 1.0)
        x_zoom = getattr(self.canvas, "x_zoom", 1.0)
        range_max = 10000
        thumb_size = max(1, int(range_max / (zoom * x_zoom)))
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

    def on_x_zoom(self, event):
        """Handle x-axis zoom slider changes."""
        val = self.x_zoom_slider.GetValue()
        self.x_zoom_value_label.SetLabel(f"{val}×")
        self.canvas.x_zoom = float(val)
        self.canvas.init = False
        self.update_scrollbars()
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
        x_zoom = getattr(self.canvas, "x_zoom", 1.0)
        pan_x_pct = getattr(self.canvas, "pan_x_pct", 0.0)
        pan_y_pct = getattr(self.canvas, "pan_y_pct", 0.0)

        range_max = 10000
        h_thumb = max(1, int(range_max / (zoom * x_zoom)))
        v_thumb = max(1, int(range_max / zoom))

        scrollable_x = range_max - h_thumb
        scrollable_y = range_max - v_thumb

        pos_x = int(pan_x_pct * scrollable_x) if scrollable_x > 0 else 0
        pos_y = int(pan_y_pct * scrollable_y) if scrollable_y > 0 else 0

        self.h_scroll.SetScrollbar(
            pos_x, h_thumb, range_max, h_thumb, refresh=True
        )
        self.v_scroll.SetScrollbar(
            pos_y, v_thumb, range_max, v_thumb, refresh=True
        )

    def on_reset_view(self, event):
        """Reset all view parameters back to defaults and refresh canvas."""
        self.canvas.zoom = 1.0
        self.canvas.x_zoom = 1.0
        self.canvas.pan_x_pct = 0.0
        self.canvas.pan_y_pct = 0.0
        self.canvas.pan_x = 0.0
        self.canvas.pan_y = 0.0
        self.canvas.init = False
        self.x_zoom_slider.SetValue(1)
        self.x_zoom_value_label.SetLabel("1×")
        self.canvas.Refresh()
        self.update_scrollbars()
        self.SetStatusText(_("View reset to default dimensions."))
        self.log(_("View reset to default dimensions."))

    def on_help_menu(self, event):
        """Display a pop-up dialog describing the GUI functionality and user controls."""
        help_text = _(
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
            self, help_text, _("GUI Usage Guide"), wx.OK | wx.ICON_INFORMATION
        )
        dlg.ShowModal()
        dlg.Destroy()

    def update_switch_list(self):
        """Repopulate the switch list with current names and state (0/1) from backend."""
        sel = self.switch_list.GetFirstSelected()
        selected_name = (
            self.switch_list.GetItemText(sel, 0) if sel != -1 else None
        )

        self.switch_list.DeleteAllItems()
        self._switch_map = {}

        for switch_id in self.devices.find_devices(self.devices.SWITCH):
            raw_name = self.names.get_name_string(switch_id)
            clean_name = self.names.prettify_name(raw_name)
            self._switch_map[clean_name] = raw_name
            state = self.devices.get_device(switch_id).switch_state
            value = "1" if state == self.devices.HIGH else "0"
            idx = self.switch_list.InsertItem(
                self.switch_list.GetItemCount(), clean_name
            )
            self.switch_list.SetItem(idx, 1, value)

        wx.CallAfter(self._rescale_switch_cols)

        if selected_name is not None:
            for i in range(self.switch_list.GetItemCount()):
                if self.switch_list.GetItemText(i, 0) == selected_name:
                    self.switch_list.Select(i)
                    break

    def _rescale_switch_cols(self):
        """Fill the list width exactly using the stored column ratio."""
        total = self.switch_list.GetClientSize().width
        if total <= 0:
            return
        new_w0 = max(1, int(total * self._switch_col_ratio))
        self.switch_list.SetColumnWidth(0, new_w0)
        self.switch_list.SetColumnWidth(1, max(1, total - new_w0))

    def _on_switch_list_size(self, event):
        """Rescale columns to fill the new width when the list is resized."""
        event.Skip()
        wx.CallAfter(self._rescale_switch_cols)

    def _on_switch_col_drag(self, event):
        """Update the stored ratio when the user drags the column divider."""
        event.Skip()
        wx.CallAfter(self._capture_switch_col_ratio)

    def _capture_switch_col_ratio(self):
        """Record the proportion the user dragged to, clamped to avoid extremes."""
        w0 = self.switch_list.GetColumnWidth(0)
        total = self.switch_list.GetClientSize().width
        if total > 0:
            self._switch_col_ratio = max(0.1, min(0.9, w0 / total))
        wx.CallAfter(self._rescale_switch_cols)
