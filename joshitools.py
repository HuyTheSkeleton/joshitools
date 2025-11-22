import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
import threading
import os
import zipfile
import sys
import shutil
import subprocess
import ctypes # Required for the taskbar fix

# Configuration
VERSION = "v1.4.0"
APP_NAME = f"joshitools {VERSION}"
GITHUB_USER = "HuyTheSkeleton"
REPO_NAME = "joshitools"
DOWNLOAD_DIR = "Downloads"

# Colors
COLOR_PRIMARY = "#8bc28b"  # Greenish
COLOR_SECONDARY = "#a7dbe9" # Bluish (Brighter)
COLOR_BG = "#2c3e50"       # Dark Background
COLOR_TEXT = "#ffffff"
COLOR_HOVER = "#7ab07a"
COLOR_DISABLED = "#555555"
COLOR_TROUGH = "#1a252f"   # Darker shade for progress bar background

class ModernButton(tk.Canvas):
    """A custom styled button to match the theme"""
    def __init__(self, parent, text, command, width=200, height=40):
        super().__init__(parent, width=width, height=height, bg=COLOR_BG, highlightthickness=0)
        self.command = command
        self.text = text
        self.width = width
        self.height = height
        self.enabled = True
        
        # Draw rounded rect (simulated)
        self.rect = self.create_rectangle(2, 2, width-2, height-2, fill=COLOR_PRIMARY, outline=COLOR_PRIMARY, width=0)
        self.label = self.create_text(width/2, height/2, text=text, fill="#333333", font=("Segoe UI", 10, "bold"))
        
        self.bind("<Button-1>", self.on_click)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def set_state(self, state):
        if state == "disabled":
            self.enabled = False
            self.itemconfig(self.rect, fill=COLOR_DISABLED, outline=COLOR_DISABLED)
            self.itemconfig(self.label, fill="#888888")
        else:
            self.enabled = True
            self.itemconfig(self.rect, fill=COLOR_PRIMARY, outline=COLOR_PRIMARY)
            self.itemconfig(self.label, fill="#333333")

    def on_enter(self, e):
        if self.enabled:
            self.itemconfig(self.rect, fill=COLOR_SECONDARY, outline=COLOR_SECONDARY) # Hover to Blue
            self.config(cursor="hand2")

    def on_leave(self, e):
        if self.enabled:
            self.itemconfig(self.rect, fill=COLOR_PRIMARY, outline=COLOR_PRIMARY)
            self.config(cursor="")

    def on_click(self, e):
        if self.enabled and self.command:
            self.command()

class JoshiToolsApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("400x530")
        self.root.configure(bg=COLOR_BG)
        
        # --- FIX: Remove title bar but keep taskbar icon (Windows) ---
        self.root.overrideredirect(True)
        # Increased delay slightly to 50ms to ensure window handle is ready
        self.root.after(50, self.set_appwindow) 
        
        # State variables
        self.lol_config_path = ""
        self.last_downloaded_file = None
        self.buttons = []
        
        # Center the window
        self.center_window()
        
        # UI Setup
        self.setup_title_bar()
        self.setup_main_ui()

    def set_appwindow(self):
        """
        Robust Windows-specific hack to show the window in the taskbar.
        Prevents Alt-Tab crashes/disappearing windows.
        """
        if sys.platform == "win32":
            try:
                GWL_EXSTYLE = -20
                WS_EX_APPWINDOW = 0x00040000
                WS_EX_TOOLWINDOW = 0x00000080
                
                # Get handle. Try GetParent first, if 0, use winfo_id directly
                hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
                if hwnd == 0:
                    hwnd = self.root.winfo_id()
                
                style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                style = style & ~WS_EX_TOOLWINDOW
                style = style | WS_EX_APPWINDOW
                ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
                
                # Force re-render to apply style
                self.root.wm_withdraw()
                self.root.after(10, lambda: self.root.wm_deiconify())
            except Exception as e:
                print(f"Taskbar fix warning: {e}")

    def center_window(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 400) // 2
        y = (screen_height - 530) // 2
        self.root.geometry(f"400x530+{x}+{y}")

    def setup_title_bar(self):
        """Custom Title Bar with Dragging and Close"""
        self.title_bar = tk.Frame(self.root, bg=COLOR_PRIMARY, relief="flat", height=35)
        self.title_bar.pack(fill="x", side="top")
        self.title_bar.pack_propagate(False)

        # Title Label
        title_lbl = tk.Label(self.title_bar, text=APP_NAME, bg=COLOR_PRIMARY, fg="white", font=("Segoe UI", 11, "bold"))
        title_lbl.pack(side="left", padx=10)

        # Close Button
        close_btn = tk.Label(self.title_bar, text="✕", bg=COLOR_PRIMARY, fg="white", font=("Arial", 12), width=4, cursor="hand2")
        close_btn.pack(side="right", fill="y")
        close_btn.bind("<Button-1>", lambda e: self.root.destroy())
        close_btn.bind("<Enter>", lambda e: close_btn.config(bg="#cc5555"))
        close_btn.bind("<Leave>", lambda e: close_btn.config(bg=COLOR_PRIMARY))

        # Dragging Logic
        def start_move(event):
            self.x = event.x
            self.y = event.y

        def do_move(event):
            deltax = event.x - self.x
            deltay = event.y - self.y
            x = self.root.winfo_x() + deltax
            y = self.root.winfo_y() + deltay
            self.root.geometry(f"+{x}+{y}")

        self.title_bar.bind("<Button-1>", start_move)
        self.title_bar.bind("<B1-Motion>", do_move)
        title_lbl.bind("<Button-1>", start_move)
        title_lbl.bind("<B1-Motion>", do_move)

    def setup_main_ui(self):
        container = tk.Frame(self.root, bg=COLOR_BG)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # Status Area
        self.status_label = tk.Label(container, text="Ready", bg=COLOR_BG, fg="#aaaaaa", font=("Segoe UI", 9), wraplength=350)
        self.status_label.pack(pady=(0, 5))

        # Progress Bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(container, variable=self.progress_var, maximum=100, style="Big.Horizontal.TProgressbar")
        self.progress_bar.pack(fill="x", pady=(0, 20))

        # Style the progress bar (Thicker and Blue for visibility)
        style = ttk.Style()
        style.theme_use('alt')
        style.configure("Big.Horizontal.TProgressbar", 
                        background=COLOR_SECONDARY,  # Bright blue bar
                        troughcolor=COLOR_TROUGH,    # Dark background
                        thickness=20,                # Much thicker
                        borderwidth=0)

        # Buttons
        btn_defs = [
            ("Download DraftGap Plus", self.thread_download_draftgap),
            ("Download Gallium (Zip)", self.thread_download_gallium),
            ("Locate LoL Config Folder", self.locate_lol_folder),
            ("Sync Cloud Settings", self.thread_sync_settings),
            ("Show File in Folder", self.open_last_file)
        ]

        for text, cmd in btn_defs:
            btn = ModernButton(container, text, cmd, width=360, height=45)
            btn.pack(pady=6)
            self.buttons.append(btn)

        # Footer Credit
        footer = tk.Label(container, text="GitHub: HuyTheSkeleton", bg=COLOR_BG, fg="#556677", font=("Segoe UI", 8))
        footer.pack(side="bottom", pady=10)

    # --- Helpers ---

    def set_busy(self, busy=True):
        """Toggle cursor and buttons"""
        if busy:
            self.root.config(cursor="wait") # Spinning cursor
            for btn in self.buttons:
                btn.set_state("disabled")
        else:
            self.root.config(cursor="") # Normal cursor
            for btn in self.buttons:
                btn.set_state("normal")

    def update_status(self, text, percent=0):
        self.status_label.config(text=f"{text} ({percent}%)" if percent > 0 else text)
        self.progress_var.set(percent)
        self.root.update_idletasks()

    def download_file(self, url, dest_filename, is_config=False):
        """Generic download with progress"""
        try:
            # Determine path: if config, use absolute lol path, otherwise use Downloads folder
            if is_config:
                final_path = dest_filename
            else:
                # Ensure downloads directory exists right before using it
                if not os.path.exists(DOWNLOAD_DIR):
                    try:
                        os.makedirs(DOWNLOAD_DIR)
                    except Exception:
                        pass 
                final_path = os.path.join(DOWNLOAD_DIR, dest_filename)

            # Ensure the directory for the file exists (covers both Downloads and nested Config paths)
            os.makedirs(os.path.dirname(final_path), exist_ok=True)

            self.update_status(f"Starting download: {os.path.basename(final_path)}...", 0)
            
            response = requests.get(url, stream=True)
            
            # Handle 404 specifically
            if response.status_code == 404:
                raise Exception(f"404 Not Found: {url}")
            
            response.raise_for_status()
            
            total_length = response.headers.get('content-length')

            with open(final_path, "wb") as f:
                if total_length is None: 
                    f.write(response.content)
                    self.update_status("Download complete", 100)
                else:
                    dl = 0
                    total_length = int(total_length)
                    for data in response.iter_content(chunk_size=4096):
                        dl += len(data)
                        f.write(data)
                        percent = int((dl / total_length) * 100)
                        self.update_status(f"Downloading {os.path.basename(final_path)}...", percent)
            
            # Save reference to opening later
            if not is_config:
                self.last_downloaded_file = os.path.abspath(final_path)
            else:
                # If it's a config, we set the folder as the 'file to open'
                self.last_downloaded_file = os.path.dirname(final_path)

            self.update_status(f"Saved to {os.path.basename(final_path)}", 100)
            return True
        except Exception as e:
            print(e)
            self.update_status(f"Error: {str(e)}")
            return False

    # --- Button Commands (Threaded) ---

    def thread_wrapper(self, target_func):
        """Wraps functions to handle busy state automatically"""
        def worker():
            self.set_busy(True)
            try:
                target_func()
            finally:
                self.set_busy(False)
        threading.Thread(target=worker, daemon=True).start()

    def thread_download_draftgap(self):
        self.thread_wrapper(self.download_draftgap)

    def thread_download_gallium(self):
        self.thread_wrapper(self.download_gallium)

    def thread_sync_settings(self):
        self.thread_wrapper(self.sync_settings)

    # --- Core Logic ---

    def download_draftgap(self):
        self.update_status("Fetching release info...")
        try:
            api_url = "https://api.github.com/repos/HuyTheSkeleton/draftgap-plus/releases/latest"
            resp = requests.get(api_url)
            resp.raise_for_status()
            data = resp.json()
            
            if "assets" in data and len(data["assets"]) > 0:
                asset = data["assets"][0]
                download_url = asset["browser_download_url"]
                filename = asset["name"]
                self.download_file(download_url, filename)
            else:
                self.update_status("No assets found in latest release.")
        except Exception as e:
            self.update_status(f"API Error: {str(e)}")

    def download_gallium(self):
        url = "https://github.com/GalileoBlues/Gallium/archive/refs/heads/main.zip"
        self.download_file(url, "Gallium-main.zip")

    def locate_lol_folder(self):
        self.update_status("Waiting for folder selection...")
        path = filedialog.askdirectory(title="Select League of Legends Folder")
        if path:
            config_check = os.path.join(path, "Config")
            if os.path.exists(config_check):
                self.lol_config_path = config_check
            elif path.endswith("Config") and os.path.exists(path):
                self.lol_config_path = path
            else:
                self.lol_config_path = os.path.join(path, "Config")
            
            self.update_status(f"Path: .../{os.path.basename(self.lol_config_path)}")
        else:
            self.update_status("Selection cancelled.")

    def sync_settings(self):
        if not self.lol_config_path:
            self.update_status("Error: Select LoL folder first!")
            return

        if not os.path.exists(self.lol_config_path):
            try:
                os.makedirs(self.lol_config_path)
            except OSError:
                self.update_status("Error: Config folder not found/creatable.")
                return

        # CASE SENSITIVE FILE NAMES
        files_to_sync = ["PersistedSettings.json", "game.cfg"]
        
        # We try 'main' first, if 404, we try 'master'
        branches = ["main", "master"]
        
        success_count = 0
        
        for filename in files_to_sync:
            success = False
            dest_path = os.path.join(self.lol_config_path, filename)
            
            for branch in branches:
                url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/{branch}/{filename}"
                self.update_status(f"Trying {branch}/{filename}...", 50)
                
                if self.download_file(url, dest_path, is_config=True):
                    success = True
                    break # Stop trying branches if this one worked
            
            if success:
                success_count += 1
            else:
                self.update_status(f"Failed to find {filename} on main/master")
                return

        if success_count == len(files_to_sync):
            self.update_status("Settings synced successfully!", 100)

    def open_last_file(self):
        """
        Opens the Explorer/Finder with the file selected, 
        BUT DOES NOT RUN THE FILE.
        """
        path = self.last_downloaded_file
        
        # If nothing downloaded yet, try opening the Downloads folder
        if not path:
            path = os.path.abspath(DOWNLOAD_DIR)
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)

        if path and os.path.exists(path):
            self.update_status(f"Showing: {os.path.basename(path)}")
            
            if sys.platform == 'win32':
                # explorer /select,"PATH" highlights the file
                subprocess.Popen(f'explorer /select,"{path}"')
            elif sys.platform == 'darwin':
                # open -R highlights the file
                subprocess.run(["open", "-R", path])
            else:
                # Linux usually just opens the folder
                subprocess.run(["xdg-open", os.path.dirname(path)])
        else:
            self.update_status("Nothing to open.")

if __name__ == "__main__":
    root = tk.Tk()
    app = JoshiToolsApp(root)
    root.mainloop()