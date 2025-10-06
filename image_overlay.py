import tkinter as tk
from tkinter import messagebox, filedialog
from io import BytesIO
from PIL import Image, ImageTk
import requests
import ctypes
import threading
import os

OPACITY = 0.3
TARGET_WIDTH = 1000
TARGET_HEIGHT = 500
overlay_x = 550
overlay_y = 300

overlay_window = None
overlay_label = None
current_img = None
original_img = None
move_job = None

def make_window_clickthrough(window, opacity=0.4):
    if os.name != "nt":
        return
    window.update_idletasks()
    hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
    styles = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
    ctypes.windll.user32.SetWindowLongW(hwnd, -20, styles | 0x80000 | 0x20)
    alpha = int(opacity * 255)
    ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, 0, alpha, 2)

def load_local_image(path, callback):
    try:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        img = Image.open(path)
        gui.after(0, lambda: callback(img))
    except Exception as e:
        gui.after(0, lambda: callback(None, e))

def load_url_image(url, callback):
    try:
        response = requests.get(url)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        gui.after(0, lambda: callback(img))
    except Exception as e:
        gui.after(0, lambda: callback(None, e))

def show_image_overlay(img):
    global current_img, original_img
    if img is None:
        messagebox.showerror("Error", "Failed to load image")
        return

    original_img = img.copy()

    if undo_var.get():
        current_img = original_img.copy()
    else:
        current_img = img.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)

    update_overlay(current_img)

def update_overlay(img):
    global overlay_window, overlay_label, overlay_x, overlay_y
    if overlay_window is None or not overlay_window.winfo_exists():
        overlay_window = tk.Toplevel(gui)
        overlay_window.overrideredirect(True)
        overlay_window.attributes("-topmost", True)
        overlay_window.attributes("-alpha", OPACITY)
        overlay_window.geometry(f"{img.width}x{img.height}+{overlay_x}+{overlay_y}")
        overlay_window.bind("<Escape>", lambda e: hide_overlay())

        overlay_label = tk.Label(overlay_window, borderwidth=0, highlightthickness=0)
        overlay_label.pack()

        make_window_clickthrough(overlay_window, OPACITY)

    tk_img = ImageTk.PhotoImage(img)
    overlay_label.configure(image=tk_img)
    overlay_label.image = tk_img

def hide_overlay():
    global overlay_window
    if overlay_window and overlay_window.winfo_exists():
        overlay_window.destroy()
        overlay_window = None

def move_overlay(dx, dy):
    global overlay_x, overlay_y, overlay_window
    overlay_x += dx
    overlay_y += dy
    if overlay_window and overlay_window.winfo_exists():
        overlay_window.geometry(f"{current_img.width}x{current_img.height}+{overlay_x}+{overlay_y}")

def resize_overlay(factor):
    global current_img
    if current_img is None:
        return
    new_w = int(current_img.width * factor)
    new_h = int(current_img.height * factor)
    resized = current_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    current_img = resized
    update_overlay(resized)

def undo_resize():
    global current_img
    if original_img is None:
        return
    current_img = original_img.copy()
    update_overlay(current_img)
    if overlay_window and overlay_window.winfo_exists():
        overlay_window.geometry(f"{current_img.width}x{current_img.height}+{overlay_x}+{overlay_y}")


def start_moving(dx, dy):
    global move_job
    move_overlay(dx, dy)
    move_job = gui.after(100, lambda: start_moving(dx, dy))

def stop_moving(event=None):
    global move_job
    if move_job is not None:
        gui.after_cancel(move_job)
        move_job = None


def browse_file():
    file_path = filedialog.askopenfilename(
        title="Select Image",
        filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif")]
    )
    if file_path:
        path_entry.delete(0, tk.END)
        path_entry.insert(0, file_path)
        start_overlay_local()

def start_overlay_local(event=None):
    path = path_entry.get().strip()
    if not path:
        return

    def callback(img, error=None):
        if error:
            messagebox.showerror("Error", f"Failed to load image:\n{error}")
        else:
            show_image_overlay(img)

    threading.Thread(target=load_local_image, args=(path, callback), daemon=True).start()

def start_overlay_url(event=None):
    url = url_entry.get().strip()
    if not url:
        return

    def callback(img, error=None):
        if error:
            messagebox.showerror("Error", f"Failed to load image:\n{error}")
        else:
            show_image_overlay(img)

    threading.Thread(target=load_url_image, args=(url, callback), daemon=True).start()


gui = tk.Tk()
gui.title("Image Overlay Launcher")
gui.geometry("520x450")
gui.resizable(False, False)

tk.Label(gui, text="Local Image Path:").pack(pady=2)
path_entry = tk.Entry(gui, width=55)
path_entry.pack(pady=2)
browse_btn = tk.Button(gui, text="Browse...", command=browse_file)
browse_btn.pack(pady=2)

tk.Label(gui, text="Image URL:").pack(pady=2)
url_entry = tk.Entry(gui, width=55)
url_entry.pack(pady=2)
url_entry.bind("<Return>", start_overlay_url)

controls_frame = tk.Frame(gui)
controls_frame.pack(pady=10)

btn_up = tk.Button(controls_frame, text="⬆️", width=5)
btn_up.grid(row=0, column=1)
btn_up.bind("<ButtonPress-1>", lambda e: start_moving(0, -10))
btn_up.bind("<ButtonRelease-1>", stop_moving)

btn_left = tk.Button(controls_frame, text="⬅️", width=5)
btn_left.grid(row=1, column=0)
btn_left.bind("<ButtonPress-1>", lambda e: start_moving(-10, 0))
btn_left.bind("<ButtonRelease-1>", stop_moving)

btn_right = tk.Button(controls_frame, text="➡️", width=5)
btn_right.grid(row=1, column=2)
btn_right.bind("<ButtonPress-1>", lambda e: start_moving(10, 0))
btn_right.bind("<ButtonRelease-1>", stop_moving)

btn_down = tk.Button(controls_frame, text="⬇️", width=5)
btn_down.grid(row=2, column=1)
btn_down.bind("<ButtonPress-1>", lambda e: start_moving(0, 10))
btn_down.bind("<ButtonRelease-1>", stop_moving)

zoom_frame = tk.Frame(gui)
zoom_frame.pack(pady=5)
tk.Button(zoom_frame, text="🔍 Zoom In", width=10, command=lambda: resize_overlay(1.2)).pack(side="left", padx=5)
tk.Button(zoom_frame, text="🔎 Zoom Out", width=10, command=lambda: resize_overlay(0.8)).pack(side="left", padx=5)

undo_var = tk.BooleanVar(value=False)
def toggle_undo():
    if undo_var.get():
        undo_resize()
    else:
        if original_img is not None:
            fitted = original_img.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)
            update_overlay(fitted)

undo_checkbox = tk.Checkbutton(gui, text="Resize", variable=undo_var, command=toggle_undo)
undo_checkbox.pack(pady=5)
undo_checkbox.select()

hide_btn = tk.Button(gui, text="Hide Overlay", command=hide_overlay, bg="red", fg="white")
hide_btn.pack(pady=5)

gui.mainloop()
