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
        GL.glClearColor(0.07, 0.10, 0.16, 0.9)  # dark blue background
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
            self.init_gl()
            self.init = True

        # 1. Clear the back buffer completely
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)

        # 2. Get dynamic window boundaries from wxPython
        size = self.GetClientSize()
        canvas_width = size.width
        canvas_height = size.height

        # --- DYNAMIC GRID & SIGNAL CONSTANTS ---
        # Horizontal boundaries (stretch close to edges)
        box_x_start = 60
        box_x_end = canvas_width - 20  
        
        # Vertical boundaries (stretch to fill the available height dynamically)
        box_y_bot = 20
        box_y_top = canvas_height - 20  # Reaches nearly the bottom of the window
        
        # Distribute the High and Low logic levels proportionally within that height
        high_y = box_y_bot + (box_y_top - box_y_bot) * 0.75
        low_y = box_y_bot + (box_y_top - box_y_bot) * 0.25
        
        num_cycles = 10
        
        # Calculate how wide each clock cycle should be to fill the box evenly
        cycle_width = (box_x_end - box_x_start) / num_cycles 

        # --- DRAW Y-AXIS LABELS ---
        self.render_text("High", 20, high_y - 4)
        self.render_text("Low", 25, low_y - 4)

        # --- DRAW BOUNDING BOX ---
        GL.glColor3f(0.3, 0.4, 0.5)  # Steel blue border
        GL.glLineWidth(1.5)
        GL.glBegin(GL.GL_LINE_LOOP)
        GL.glVertex2f(box_x_start, box_y_bot)
        GL.glVertex2f(box_x_end, box_y_bot)
        GL.glVertex2f(box_x_end, box_y_top)
        GL.glVertex2f(box_x_start, box_y_top)
        GL.glEnd()

        # --- DRAW CLOCK CYCLES (VERTICAL DASHED LINES) ---
        GL.glEnable(GL.GL_LINE_STIPPLE)
        GL.glLineStipple(1, 0x00FF)  # Dashed pattern
        GL.glColor3f(0.2, 0.3, 0.4)  # Faint line color
        GL.glBegin(GL.GL_LINES)
        for i in range(num_cycles + 1):
            x = box_x_start + (i * cycle_width)
            GL.glVertex2f(x, box_y_bot)
            GL.glVertex2f(x, box_y_top)
        GL.glEnd()
        GL.glDisable(GL.GL_LINE_STIPPLE)

        # --- DRAW DYNAMIC SIGNAL TRACE ---
        GL.glColor3f(0.0, 1.0, 0.4)  # Signal trace is bright green
        GL.glLineWidth(2.5)
        GL.glBegin(GL.GL_LINE_STRIP)
        
        for i in range(num_cycles):
            x = box_x_start + (i * cycle_width)
            x_next = box_x_start + ((i + 1) * cycle_width)
            
            # Determine current state (alternating for demonstration)
            current_y = high_y if i % 2 == 0 else low_y
            
            # Draw horizontal state line
            GL.glVertex2f(x, current_y)
            GL.glVertex2f(x_next, current_y)
            
            # Draw vertical transition edge (if not the last cycle)
            if i < num_cycles - 1:
                next_y = low_y if i % 2 == 0 else high_y
                GL.glVertex2f(x_next, current_y)
                GL.glVertex2f(x_next, next_y)
                
        GL.glEnd()
        GL.glLineWidth(1.0) # Reset line width

        # --- DRAW TEXT ON TOP OF GRAPHICS ---
        self.render_text(text, 10, canvas_height - 20)

        # 3. SINGLE SWAP AT THE END
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
        """Handle the canvas resize event."""
        self.init = False

        size = self.GetClientSize()

        width = max(1, size.width)
        height = max(1, size.height)

        self.SetCurrent(self.context)
        GL.glViewport(0, 0, width, height)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()

        GL.glOrtho(0, width, height, 0, -1, 1)

        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()

        self.Refresh()
    
    def on_mouse(self, event):
        """Handle mouse events."""
        text = ""
        size = self.GetClientSize()
        ox = (event.GetX() - self.pan_x) / self.zoom
        oy = (size.height - event.GetY() - self.pan_y) / self.zoom
        old_zoom = self.zoom
        
        if event.ButtonDown():
            self.last_mouse_x = event.GetX()
            self.last_mouse_y = event.GetY()
            text = f"Mouse button pressed at: {event.GetX()}, {event.GetY()}"
            
        if event.ButtonUp():
            text = f"Mouse button released at: {event.GetX()}, {event.GetY()}"
            
        if event.Leaving():
            text = f"Mouse left canvas at: {event.GetX()}, {event.GetY()}"
            
        if event.Dragging():
            self.pan_x += event.GetX() - self.last_mouse_x
            self.pan_y -= event.GetY() - self.last_mouse_y
            self.last_mouse_x = event.GetX()
            self.last_mouse_y = event.GetY()
            self.init = False
            text = f"Mouse dragged. Pan is now: {self.pan_x}, {self.pan_y}"
            
        if event.GetWheelRotation() < 0:
            self.zoom *= 1.0 + (event.GetWheelRotation() / (20 * event.GetWheelDelta()))
            self.pan_x -= (self.zoom - old_zoom) * ox
            self.pan_y -= (self.zoom - old_zoom) * oy
            self.init = False
            text = f"Negative mouse wheel rotation. Zoom is now: {self.zoom}"
            
        if event.GetWheelRotation() > 0:
            self.zoom /= 1.0 - (event.GetWheelRotation() / (20 * event.GetWheelDelta()))
            self.pan_x -= (self.zoom - old_zoom) * ox
            self.pan_y -= (self.zoom - old_zoom) * oy
            self.init = False
            text = f"Positive mouse wheel rotation. Zoom is now: {self.zoom}"
            
        if text:
            self.render(text)
        else:
            self.Refresh()

    def render_text(self, text, x_pos, y_pos):
        """Handle text drawing operations."""
        GL.glColor3f(1.0, 1.0, 1.0)  # Text is now white for visibility
        GL.glRasterPos2f(x_pos, y_pos)
        font = GLUT.GLUT_BITMAP_HELVETICA_12

        for character in text:
            if character == "\n":
                y_pos = y_pos - 20
                GL.glRasterPos2f(x_pos, y_pos)
            else:
                GLUT.glutBitmapCharacter(font, ord(character))


class Gui(wx.Frame):
    """Configure the main window and all the widgets."""

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

        #create a splitter window to divide the canvas and the side panel
        self.splitter = wx.SplitterWindow(self)

        # Canvas for drawing signals
        self.canvas = MyGLCanvas(self.splitter, devices, monitors)

        self.top_panel = wx.Panel(self.splitter)




        # Configure the widgets
        self.cycles_label = wx.StaticText(self.top_panel, wx.ID_ANY, "Cycles")
        self.spin = wx.SpinCtrl(self.top_panel, wx.ID_ANY, "10", min=1, max=1000)
        self.run_button = wx.Button(self.top_panel, wx.ID_ANY, "Run")
        self.continue_button = wx.Button(self.top_panel, wx.ID_ANY, "Continue")

        self.switch_label = wx.StaticText(self.top_panel, wx.ID_ANY, "Select switch:")
        self.switch_choice = wx.Choice(self.top_panel, wx.ID_ANY, 
                               choices=["SW1", "SW2", "SW3"])
        self.switch_on = wx.Button(self.top_panel, wx.ID_ANY, "Set ON")
        self.switch_off = wx.Button(self.top_panel, wx.ID_ANY, "Set OFF")

        self.monitors_label = wx.StaticText(self.top_panel, wx.ID_ANY, "Monitors:")
        self.monitors_list = wx.ListBox(self.top_panel, wx.ID_ANY, choices=["Signal1", "Signal2"], style=wx.LB_SINGLE)
        self.add_monitor_btn = wx.Button(self.top_panel, wx.ID_ANY, "Add Monitor")
        self.remove_monitor_btn = wx.Button(self.top_panel, wx.ID_ANY, "Remove Monitor")

        self.reset_button = wx.Button(self.top_panel, wx.ID_ANY, "Reset")

        self.console = wx.TextCtrl(self.top_panel, wx.ID_ANY, "",style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
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

        self.zoom_label = wx.StaticText(self.top_panel, wx.ID_ANY, "Zoom:")
        self.zoom_slider = wx.Slider(self.top_panel, wx.ID_ANY, value=100, minValue=10, maxValue=300, style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS)
        self.zoom_slider.SetToolTip("Zoom in/out of the signal view (10% to 300%)")

        self.zoom_slider.Bind(wx.EVT_SLIDER, self.on_zoom_slider)

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
        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.top_panel.SetSizer(top_sizer)
        top_sizer.SetMinSize((-1, 400))  # Set minimum height for the top panel


        # Simulation controls box
        sim_box = wx.StaticBox(self.top_panel, wx.ID_ANY, "Simulation")
        sim_sizer = wx.StaticBoxSizer(sim_box, wx.VERTICAL)
        sim_sizer.Add(self.cycles_label, 0, wx.ALL, 5)
        sim_sizer.Add(self.spin, 0, wx.EXPAND | wx.ALL, 5)
        sim_sizer.Add(self.run_button, 0, wx.EXPAND | wx.ALL, 5)
        sim_sizer.Add(self.continue_button, 0, wx.EXPAND | wx.ALL, 5)
        sim_sizer.Add(self.reset_button, 0, wx.EXPAND | wx.ALL, 5)
        sim_sizer.Add(self.zoom_label, 0, wx.ALL, 5)
        sim_sizer.Add(self.zoom_slider, 0, wx.EXPAND | wx.ALL, 5)

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
        monitor_sizer.Add(self.add_monitor_btn, 0, wx.EXPAND | wx.ALL, 5)
        monitor_sizer.Add(self.remove_monitor_btn, 0, wx.EXPAND | wx.ALL, 5)

        console_box = wx.StaticBox(self.top_panel, wx.ID_ANY, "Console")
        console_sizer = wx.StaticBoxSizer(console_box, wx.VERTICAL)
        console_sizer.Add(self.console, 1, wx.EXPAND | wx.ALL, 5)

        # Put the two switch buttons side by side
        switch_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        switch_btn_sizer.Add(self.switch_on, 1, wx.ALL, 5)
        switch_btn_sizer.Add(self.switch_off, 1, wx.ALL, 5)
        switch_sizer.Add(switch_btn_sizer, 0, wx.EXPAND)

        top_sizer.Add(sim_sizer, 0, wx.EXPAND | wx.ALL, 2)
        top_sizer.Add(switch_sizer, 0, wx.EXPAND | wx.ALL, 2)
        top_sizer.Add(monitor_sizer, 0, wx.EXPAND | wx.ALL, 2)
        top_sizer.Add(console_sizer, 1, wx.EXPAND | wx.ALL, 2)
        
        self.splitter.SplitHorizontally(self.top_panel, self.canvas, 200)
        self.splitter.SetMinimumPaneSize(120)  # Set minimum pane size to prevent collapsing


        main_sizer= wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.splitter, 1, wx.EXPAND | wx.ALL, 0)

        
        self.SetSizeHints(700, 400)
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

    def on_zoom_slider(self, event):
        """Handle the event when the user changes the zoom slider."""
        # Convert slider value (10-300) back to a float multiplier (0.1 to 3.0)
        new_zoom = self.zoom_slider.GetValue() / 100.0
        
        # Update the canvas zoom property
        self.canvas.zoom = new_zoom
        
        # Force OpenGL to rebuild the projection matrix
        self.canvas.init = False 
        
        # Trigger a redraw
        self.canvas.Refresh()
        self.log(f"Signal scaled to {new_zoom}x")