"""Implement the graphical user interface for the Logic Simulator.

Used in the Logic Simulator project to enable the user to run the simulation
or adjust the network properties.

Classes:
--------
MyGLCanvas - handles all canvas drawing operations.
Gui - configures the main window and all the widgets.
"""

from email.mime import message
from tkinter import dialog

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


class MyGLCanvas(wxcanvas.GLCanvas):
    """Handle all drawing operations.

    This class contains functions for drawing onto the canvas. It
    also contains handlers for events relating to the canvas.

    Parameters
    ----------
    parent: parent window.
    devices: instance of the devices.Devices() class.
    monitors: instance of the monitors.Monitors() class.

    Public methods
    --------------
    init_gl(self): Configures the OpenGL context.

    render(self, text): Handles all drawing operations.

    on_paint(self, event): Handles the paint event.

    on_size(self, event): Handles the canvas resize event.

    on_mouse(self, event): Handles mouse events.

    render_text(self, text, x_pos, y_pos): Handles text drawing
                                           operations.
    """

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
        self.last_mouse_x = 0  # previous mouse x position
        self.last_mouse_y = 0  # previous mouse y position

        # Initialise variables for zooming
        self.zoom = 1

        # Bind events to the canvas
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.on_mouse)

    def init_gl(self):
        """Configure and initialise the OpenGL context."""
        size = self.GetClientSize()
        self.SetCurrent(self.context)
        GL.glDrawBuffer(GL.GL_BACK)
        GL.glClearColor(0.07, 0.10, 0.16, 0.9)#dark blue background
        GL.glViewport(0, 0, size.width, size.height)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GL.glOrtho(0, size.width, 0, size.height, -1, 1)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        GL.glTranslated(self.pan_x, self.pan_y, 0.0)
        GL.glScaled(self.zoom, self.zoom, self.zoom)

    def render(self, text):
        """Handle all drawing operations."""
        self.SetCurrent(self.context)
        if not self.init:
            # Configure the viewport, modelview and projection matrices
            self.init_gl()
            self.init = True

        # Clear everything
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)

        # Draw specified text at position (10, 10)
        self.render_text(text, 10, 10)

        # Draw a sample signal trace
        GL.glColor3f(0.0, 0.0, 1.0)  # signal trace is blue
        GL.glBegin(GL.GL_LINE_STRIP)
        for i in range(10):
            x = (i * 20) + 10
            x_next = (i * 20) + 30
            if i % 2 == 0:
                y = 75
            else:
                y = 100
            GL.glVertex2f(x, y)
            GL.glVertex2f(x_next, y)
        GL.glEnd()

        # We have been drawing to the back buffer, flush the graphics pipeline
        # and swap the back buffer to the front
        GL.glFlush()
        self.SwapBuffers()

    def on_paint(self, event):
        """Handle the paint event."""
        self.SetCurrent(self.context)
        if not self.init:
            # Configure the viewport, modelview and projection matrices
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
        """Handle the canvas resize event."""
        # Forces reconfiguration of the viewport, modelview and projection
        # matrices on the next paint event
        self.init = False

    def on_mouse(self, event):
        """Handle mouse events."""
        text = ""
        # Calculate object coordinates of the mouse position
        size = self.GetClientSize()
        ox = (event.GetX() - self.pan_x) / self.zoom
        oy = (size.height - event.GetY() - self.pan_y) / self.zoom
        old_zoom = self.zoom
        if event.ButtonDown():
            self.last_mouse_x = event.GetX()
            self.last_mouse_y = event.GetY()
            text = "".join(
                [
                    "Mouse button pressed at: ",
                    str(event.GetX()),
                    ", ",
                    str(event.GetY()),
                ]
            )
        if event.ButtonUp():
            text = "".join(
                [
                    "Mouse button released at: ",
                    str(event.GetX()),
                    ", ",
                    str(event.GetY()),
                ]
            )
        if event.Leaving():
            text = "".join(
                ["Mouse left canvas at: ", str(event.GetX()), ", ", str(event.GetY())]
            )
        if event.Dragging():
            self.pan_x += event.GetX() - self.last_mouse_x
            self.pan_y -= event.GetY() - self.last_mouse_y
            self.last_mouse_x = event.GetX()
            self.last_mouse_y = event.GetY()
            self.init = False
            text = "".join(
                [
                    "Mouse dragged to: ",
                    str(event.GetX()),
                    ", ",
                    str(event.GetY()),
                    ". Pan is now: ",
                    str(self.pan_x),
                    ", ",
                    str(self.pan_y),
                ]
            )
        if event.GetWheelRotation() < 0:
            self.zoom *= 1.0 + (event.GetWheelRotation() / (20 * event.GetWheelDelta()))
            # Adjust pan so as to zoom around the mouse position
            self.pan_x -= (self.zoom - old_zoom) * ox
            self.pan_y -= (self.zoom - old_zoom) * oy
            self.init = False
            text = "".join(
                ["Negative mouse wheel rotation. Zoom is now: ", str(self.zoom)]
            )
        if event.GetWheelRotation() > 0:
            self.zoom /= 1.0 - (event.GetWheelRotation() / (20 * event.GetWheelDelta()))
            # Adjust pan so as to zoom around the mouse position
            self.pan_x -= (self.zoom - old_zoom) * ox
            self.pan_y -= (self.zoom - old_zoom) * oy
            self.init = False
            text = "".join(
                ["Positive mouse wheel rotation. Zoom is now: ", str(self.zoom)]
            )
        if text:
            self.render(text)
        else:
            self.Refresh()  # triggers the paint event

    def render_text(self, text, x_pos, y_pos):
        """Handle text drawing operations."""
        GL.glColor3f(0.0, 0.0, 0.0)  # text is black
        GL.glRasterPos2f(x_pos, y_pos)
        font = GLUT.GLUT_BITMAP_HELVETICA_12

        for character in text:
            if character == "\n":
                y_pos = y_pos - 20
                GL.glRasterPos2f(x_pos, y_pos)
            else:
                GLUT.glutBitmapCharacter(font, ord(character))


class Gui(wx.Frame):
    """Configure the main window and all the widgets.

    This class provides a graphical user interface for the Logic Simulator and
    enables the user to change the circuit properties and run simulations.

    Parameters
    ----------
    title: title of the window.

    Public methods
    --------------
    on_menu(self, event): Event handler for the file menu.

    on_spin(self, event): Event handler for when the user changes the spin
                           control value.

    on_run_button(self, event): Event handler for when the user clicks the run
                                button.

    on_text_box(self, event): Event handler for when the user enters text.
    """

    def __init__(self, title, path, names, devices, network, monitors):
        """Initialise widgets and layout."""
        super().__init__(parent=None, title=title, size=(800, 600))

        # Configure the file menu
        fileMenu = wx.Menu()
        menuBar = wx.MenuBar()
        fileMenu.Append(wx.ID_OPEN, "&Open")
        fileMenu.Append(wx.ID_SAVE, "&Save")
        fileMenu.AppendSeparator()
        fileMenu.Append(wx.ID_ABOUT, "&About")
        fileMenu.Append(wx.ID_EXIT, "&Exit")
        menuBar.Append(fileMenu, "&File")
        self.SetMenuBar(menuBar)

        # Canvas for drawing signals
        self.canvas = MyGLCanvas(self, devices, monitors)

        # Configure the widgets
        self.cycles_label = wx.StaticText(self, wx.ID_ANY, "Cycles")
        self.spin = wx.SpinCtrl(self, wx.ID_ANY, "10", min=1, max=1000)
        self.run_button = wx.Button(self, wx.ID_ANY, "Run")
        self.continue_button = wx.Button(self, wx.ID_ANY, "Continue")

        self.switch_label = wx.StaticText(self, wx.ID_ANY, "Select switch:")
        self.switch_choice = wx.Choice(self, wx.ID_ANY, 
                               choices=["SW1", "SW2", "SW3"])
        self.switch_on = wx.Button(self, wx.ID_ANY, "Set ON")
        self.switch_off = wx.Button(self, wx.ID_ANY, "Set OFF")

        self.monitors_label = wx.StaticText(self, wx.ID_ANY, "Monitors:")
        self.monitors_list = wx.ListBox(self, wx.ID_ANY, choices=["Signal1", "Signal2"], style=wx.LB_SINGLE)
        self.add_monitor_btn = wx.Button(self, wx.ID_ANY, "Add Monitor")
        self.remove_monitor_btn = wx.Button(self, wx.ID_ANY, "Remove Monitor")

        self.reset_button = wx.Button(self, wx.ID_ANY, "Reset")

        self.console = wx.TextCtrl(self, wx.ID_ANY, "",style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        console_font = wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.console.SetFont(console_font)


        self.run_button.SetToolTip("Run the simulation from scratch for N cycles")
        self.continue_button.SetToolTip("Continue the simulation for N additional cycles")
        self.reset_button.SetToolTip("Reset the simulation to its initial state")
        self.switch_on.SetToolTip("Set the selected switch to ON (1)")
        self.switch_off.SetToolTip("Set the selected switch to OFF (0)")
        self.add_monitor_btn.SetToolTip("Add a monitor to the selected signal")
        self.remove_monitor_btn.SetToolTip("Remove the selected monitor")
        self.spin.SetToolTip("Number of cycles to run or continue")

        self.run_button.SetBackgroundColour(wx.Colour(100, 200, 100))   # green
        self.reset_button.SetBackgroundColour(wx.Colour(200, 100, 100)) # red
        self.continue_button.SetBackgroundColour(wx.Colour(100, 100, 200)) # blue
        


        #bind events to the widgets
        self.Bind(wx.EVT_MENU, self.on_menu)
        self.spin.Bind(wx.EVT_SPINCTRL, self.on_spin)
        self.run_button.Bind(wx.EVT_BUTTON, self.on_run_button)
        self.continue_button.Bind(wx.EVT_BUTTON, self.on_continue_button)

        self.switch_on.Bind(wx.EVT_BUTTON, self.on_switch_on)
        self.switch_off.Bind(wx.EVT_BUTTON, self.on_switch_off)

        self.add_monitor_btn.Bind(wx.EVT_BUTTON, self.on_add_monitor)
        self.remove_monitor_btn.Bind(wx.EVT_BUTTON, self.on_remove_monitor)

        self.reset_button.Bind(wx.EVT_BUTTON, self.on_reset_button)

        # Configure sizers for layout
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        side_sizer = wx.BoxSizer(wx.VERTICAL)

        main_sizer.Add(self.canvas, 5, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(side_sizer, 1, wx.ALL, 5)
        side_sizer.SetMinSize((200, -1))  # set a minimum width for the side panel

        # Simulation controls box
        sim_box = wx.StaticBox(self, wx.ID_ANY, "Simulation")
        sim_sizer = wx.StaticBoxSizer(sim_box, wx.VERTICAL)
        sim_sizer.Add(self.cycles_label, 0, wx.ALL, 5)
        sim_sizer.Add(self.spin, 0, wx.EXPAND | wx.ALL, 5)
        sim_sizer.Add(self.run_button, 0, wx.EXPAND | wx.ALL, 5)
        sim_sizer.Add(self.continue_button, 0, wx.EXPAND | wx.ALL, 5)
        sim_sizer.Add(self.reset_button, 0, wx.EXPAND | wx.ALL, 5)


        # Switches box
        switch_box = wx.StaticBox(self, wx.ID_ANY, "Switches")
        switch_sizer = wx.StaticBoxSizer(switch_box, wx.VERTICAL)
        switch_sizer.Add(self.switch_label, 0, wx.ALL, 5)
        switch_sizer.Add(self.switch_choice, 0, wx.EXPAND | wx.ALL, 5)

        # Monitors box
        monitor_box = wx.StaticBox(self, wx.ID_ANY, "Monitors")
        monitor_sizer = wx.StaticBoxSizer(monitor_box, wx.VERTICAL)
        monitor_sizer.Add(self.monitors_label, 0, wx.ALL, 5)
        monitor_sizer.Add(self.monitors_list, 0, wx.EXPAND | wx.ALL, 5)
        monitor_sizer.Add(self.add_monitor_btn, 0, wx.EXPAND | wx.ALL, 5)
        monitor_sizer.Add(self.remove_monitor_btn, 0, wx.EXPAND | wx.ALL, 5)

        console_box = wx.StaticBox(self, wx.ID_ANY, "Console")
        console_sizer = wx.StaticBoxSizer(console_box, wx.VERTICAL)
        console_sizer.Add(self.console, 1, wx.EXPAND | wx.ALL, 5)

        # Put the two switch buttons side by side
        switch_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        switch_btn_sizer.Add(self.switch_on, 1, wx.ALL, 5)
        switch_btn_sizer.Add(self.switch_off, 1, wx.ALL, 5)
        switch_sizer.Add(switch_btn_sizer, 0, wx.EXPAND)

        side_sizer.Add(sim_sizer, 0, wx.EXPAND | wx.ALL, 5)
        side_sizer.Add(switch_sizer, 0, wx.EXPAND | wx.ALL, 5)
        side_sizer.Add(monitor_sizer, 0, wx.EXPAND | wx.ALL, 5)
        side_sizer.Add(console_sizer, 1, wx.EXPAND | wx.ALL, 5)

        
        self.SetSizeHints(600, 600)
        self.SetSizer(main_sizer)

        self.CreateStatusBar()
        self.SetStatusText("Ready")

        

    def on_menu(self, event):
        """Handle the event when the user selects a menu item."""
        Id = event.GetId()
        if Id == wx.ID_EXIT:
            self.Close(True)
        if Id == wx.ID_ABOUT:
            wx.MessageBox(
                "Logic Simulator\nGF2 Software Project\n"
                "Cambridge University Engineering Department\n2026",
                "About Logic Simulator",
                wx.ICON_INFORMATION | wx.OK,
            )
        if Id == wx.ID_OPEN:
            wildcard = "Circuit definition files (*.txt)|*.txt|All files (*.*)|*.*"
            dialog = wx.FileDialog(self, "Open circuit definition file",wildcard=wildcard,style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)

            if dialog.ShowModal() == wx.ID_OK:
                path = dialog.GetPath()
                self.SetTitle("Logic Simulator - " + path)
                self.SetStatusText("Opened: " + path)
                self.log("Opened file: " + path)
            dialog.Destroy()

    def on_spin(self, event):
        """Handle the event when the user changes the spin control value."""
        spin_value = self.spin.GetValue()
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
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.console.AppendText(f"[{timestamp}] {message}\n")