import tkinter as tk
from typing import Optional, Union

from PIL import Image, ImageGrab


class ScreenCapture:
    """
        Handles screen capture functionality with optional GUI selection interface

            Attributes:
                img: Captured image object
                bbox: Bounding box coordinates for capture region
                start_x: Starting x coordinate for selection
                start_y: Starting y coordinate for selection
                rect: Rectangle object for selection visualization
    """
    
    def __init__(self, bbox: Optional[tuple] = None) -> None:
        """
            Initialize screen capture with optional bounding box

                Args:
                    bbox: (left, top, right, bottom) — screen region to capture
                          If None, launch interactive snipping tool
        """
        self.img = None
        self.bbox = bbox
        self.start_x = None
        self.start_y = None
        self.rect = None

    def grab_region(self, bbox: tuple) -> None:
        """
            Capture a specific screen region and save it

                Args:
                    bbox: (left, top, right, bottom) coordinates for capture region
        """
        self.img = ImageGrab.grab(bbox=bbox)

    def on_mouse_down(self, event: tk.Event) -> None:
        """
            Handle mouse button press to start selection rectangle

                Args:
                    event: Mouse event containing position information
        """
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline='red', width=2
        )

    def on_mouse_drag(self, event: tk.Event) -> None:
        """
            Handle mouse drag to update selection rectangle

                Args:
                    event: Mouse event containing position information
        """
        if self.rect and self.start_x and self.start_y:
            cur_x, cur_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_mouse_up(self, event: tk.Event) -> None:
        """
            Handle mouse button release to complete selection and capture region

                Args:
                    event: Mouse event containing position information
        """
        if self.start_x and self.start_y:
            end_x = self.canvas.canvasx(event.x)
            end_y = self.canvas.canvasy(event.y)

            x1, y1 = int(min(self.start_x, end_x)), int(min(self.start_y, end_y))
            x2, y2 = int(max(self.start_x, end_x)), int(max(self.start_y, end_y))

            self.root.destroy()
            self.grab_region((x1, y1, x2, y2))

    def on_escape(self, event: tk.Event) -> None:
        """
            Cancel capture on Escape key

                Args:
                    event: The keyboard event
        """
        self.img = None
        self.root.destroy()

    def run_gui(self) -> None:
        """
            Launch an interactive snip overlay
        """
        self.root = tk.Tk()
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-alpha', 0.3)
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)  # no title bar or taskbar icon
        self.root.config(cursor='cross')

        self.canvas = tk.Canvas(self.root, bg='black', cursor='cross')
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # bind mouse and keyboard events
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.root.bind("<Escape>", self.on_escape)

        # force focus and capture input
        self.root.focus_force()
        self.root.grab_set()

        self.root.mainloop()

    def run(self) -> Optional[Image.Image]:
        """
            Execute the screen capture process

                Returns:
                    Captured image or None if cancelled
        """
        if self.bbox:
            self.grab_region(self.bbox)
        else:
            self.run_gui()
        return self.img
