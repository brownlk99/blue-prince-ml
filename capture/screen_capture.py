import tkinter as tk

from PIL import ImageGrab


class ScreenCapture:
    def __init__(self, bbox=None):
        """
        bbox: (left, top, right, bottom) — screen region to capture.
        If None, launch interactive snipping tool.
        """
        self.img = None
        self.bbox = bbox
        self.start_x = None
        self.start_y = None
        self.rect = None

    def grab_region(self, bbox):
        """Capture a specific screen region and save it."""
        self.img = ImageGrab.grab(bbox=bbox)

    def on_mouse_down(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline='red', width=2
        )

    def on_mouse_drag(self, event):
        if self.rect and self.start_x and self.start_y:
            cur_x, cur_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_mouse_up(self, event):
        if self.start_x and self.start_y:
            end_x = self.canvas.canvasx(event.x)
            end_y = self.canvas.canvasy(event.y)

            x1, y1 = int(min(self.start_x, end_x)), int(min(self.start_y, end_y))
            x2, y2 = int(max(self.start_x, end_x)), int(max(self.start_y, end_y))

            self.root.destroy()
            self.grab_region((x1, y1, x2, y2))

    def on_escape(self, event):
        """Cancel capture on Escape key."""
        self.img = None
        self.root.destroy()

    def run_gui(self):
        """Launch an interactive snip overlay."""
        self.root = tk.Tk()
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-alpha', 0.3)
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)  # no title bar or taskbar icon
        self.root.config(cursor='cross')

        self.canvas = tk.Canvas(self.root, bg='black', cursor='cross')
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Bind mouse and keyboard events
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.root.bind("<Escape>", self.on_escape)

        # Force focus and capture input
        self.root.focus_force()
        self.root.grab_set()

        self.root.mainloop()

    def run(self):
        if self.bbox:
            self.grab_region(self.bbox)
        else:
            self.run_gui()
        return self.img
