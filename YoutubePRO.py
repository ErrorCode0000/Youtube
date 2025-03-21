import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from tkinter.font import Font
import threading
import time
import re
from datetime import datetime
import webbrowser
import platform

# Try to import required libraries, install if missing
required_packages = ['yt_dlp', 'pillow', 'requests']
missing_packages = []

for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        missing_packages.append(package)

if missing_packages:
    if messagebox.askyesno("Missing Dependencies", 
                          f"The following packages are required but not installed:\n{', '.join(missing_packages)}\n\nWould you like to install them now?"):
        try:
            import subprocess
            for package in missing_packages:
                if os.name == "nt":  # Windows
                    subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                else:  # macOS/Linux
                    subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            messagebox.showinfo("Success", "Dependencies installed successfully. The application will now restart.")
            # Restart the application
            os.execl(sys.executable, sys.executable, *sys.argv)
        except Exception as e:
            messagebox.showerror("Installation Error", f"Failed to install dependencies: {e}\nPlease install them manually.")
            sys.exit(1)
    else:
        messagebox.showerror("Required Dependencies", "Cannot continue without required dependencies.")
        sys.exit(1)

# Now import the installed packages
import yt_dlp
from PIL import Image, ImageTk
import requests
from io import BytesIO

# Global variables
TEMP_DIR = os.path.join(os.path.expanduser("~"), ".youtube_downloader")
CONFIG_FILE = os.path.join(TEMP_DIR, "config.txt")
HISTORY_FILE = os.path.join(TEMP_DIR, "history.txt")
DEFAULT_DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
VERSION = "2.0.0"

# Create temp directory if it doesn't exist
os.makedirs(TEMP_DIR, exist_ok=True)

# Theme colors
DARK_MODE = {
    "bg": "#2E2E2E",
    "fg": "#FFFFFF",
    "button_bg": "#4A4A4A",
    "button_fg": "#FFFFFF",
    "entry_bg": "#3E3E3E",
    "entry_fg": "#FFFFFF",
    "highlight_bg": "#505050",
    "highlight_fg": "#FFFFFF",
    "success": "#4CAF50",
    "warning": "#FFC107",
    "error": "#F44336",
    "info": "#2196F3"
}

LIGHT_MODE = {
    "bg": "#F5F5F5",
    "fg": "#212121",
    "button_bg": "#E0E0E0",
    "button_fg": "#212121",
    "entry_bg": "#FFFFFF",
    "entry_fg": "#212121",
    "highlight_bg": "#BBDEFB",
    "highlight_fg": "#212121",
    "success": "#4CAF50",
    "warning": "#FFC107",
    "error": "#F44336",
    "info": "#2196F3"
}

# Default theme
CURRENT_THEME = DARK_MODE

class DownloadManager:
    def __init__(self):
        self.active_downloads = []
        self.download_history = []
        self.load_history()
    
    def load_history(self):
        """Load download history from file"""
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            parts = line.strip().split('|')
                            if len(parts) >= 4:
                                self.download_history.append({
                                    'title': parts[0],
                                    'url': parts[1],
                                    'path': parts[2],
                                    'date': parts[3],
                                    'format': parts[4] if len(parts) > 4 else 'Unknown'
                                })
                        except Exception:
                            continue
        except Exception as e:
            print(f"Error loading history: {e}")
    
    def save_history(self):
        """Save download history to file"""
        try:
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                for item in self.download_history:
                    f.write(f"{item['title']}|{item['url']}|{item['path']}|{item['date']}|{item['format']}\n")
        except Exception as e:
            print(f"Error saving history: {e}")
    
    def add_to_history(self, title, url, path, format_name):
        """Add a download to history"""
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.download_history.insert(0, {
            'title': title,
            'url': url,
            'path': path,
            'date': date,
            'format': format_name
        })
        # Keep only the last 100 entries
        if len(self.download_history) > 100:
            self.download_history = self.download_history[:100]
        self.save_history()

class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader Pro")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Set icon if available
        try:
            if os.name == "nt":  # Windows
                self.root.iconbitmap("youtube.ico")
        except:
            pass
        
        # Initialize download manager
        self.download_manager = DownloadManager()
        
        # Load configuration
        self.config = self.load_config()
        
        # Apply theme
        self.apply_theme()
        
        # Create main frame
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.download_tab = ttk.Frame(self.notebook)
        self.playlist_tab = ttk.Frame(self.notebook)
        self.search_tab = ttk.Frame(self.notebook)
        self.history_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.download_tab, text="Download Video")
        self.notebook.add(self.playlist_tab, text="Download Playlist")
        self.notebook.add(self.search_tab, text="Search Videos")
        self.notebook.add(self.history_tab, text="Download History")
        self.notebook.add(self.settings_tab, text="Settings")
        
        # Setup each tab
        self.setup_download_tab()
        self.setup_playlist_tab()
        self.setup_search_tab()
        self.setup_history_tab()
        self.setup_settings_tab()
        
        # Create status bar
        self.status_bar = ttk.Label(root, text=f"YouTube Downloader Pro v{VERSION} | Ready", anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind events
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Check for updates
        threading.Thread(target=self.check_for_updates, daemon=True).start()
    
    def apply_theme(self):
        """Apply the current theme to the application"""
        style = ttk.Style()
        
        # Configure ttk styles
        style.configure("TFrame", background=CURRENT_THEME["bg"])
        style.configure("TLabel", background=CURRENT_THEME["bg"], foreground=CURRENT_THEME["fg"])
        style.configure("TButton", background=CURRENT_THEME["button_bg"], foreground=CURRENT_THEME["button_fg"])
        style.configure("TEntry", fieldbackground=CURRENT_THEME["entry_bg"], foreground=CURRENT_THEME["entry_fg"])
        style.configure("TNotebook", background=CURRENT_THEME["bg"], foreground=CURRENT_THEME["fg"])
        style.configure("TNotebook.Tab", background=CURRENT_THEME["button_bg"], foreground=CURRENT_THEME["button_fg"])
        
        # Configure root window
        self.root.configure(bg=CURRENT_THEME["bg"])
    
    def load_config(self):
        """Load configuration from file"""
        config = {
            "download_dir": DEFAULT_DOWNLOAD_DIR,
            "theme": "dark",
            "default_format": "best",
            "auto_convert_audio": False,
            "include_subtitles": False,
            "max_search_results": 10
        }
        
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    for line in f:
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            if key in config:
                                if value.lower() in ['true', 'false']:
                                    config[key] = value.lower() == 'true'
                                elif value.isdigit():
                                    config[key] = int(value)
                                else:
                                    config[key] = value
        except Exception as e:
            print(f"Error loading config: {e}")
        
        # Apply theme from config
        global CURRENT_THEME
        CURRENT_THEME = DARK_MODE if config["theme"].lower() == "dark" else LIGHT_MODE
        
        return config
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                for key, value in self.config.items():
                    f.write(f"{key}={value}\n")
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def setup_download_tab(self):
        """Setup the download tab UI"""
        # URL Frame
        url_frame = ttk.Frame(self.download_tab)
        url_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(url_frame, text="Enter YouTube URL:").pack(side=tk.LEFT, padx=5)
        
        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(url_frame, textvariable=self.url_var, width=50)
        url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        paste_button = ttk.Button(url_frame, text="Paste", command=self.paste_url)
        paste_button.pack(side=tk.LEFT, padx=5)
        
        fetch_button = ttk.Button(url_frame, text="Fetch Video Info", command=self.fetch_video_info)
        fetch_button.pack(side=tk.LEFT, padx=5)
        
        # Video Info Frame
        self.video_info_frame = ttk.LabelFrame(self.download_tab, text="Video Information")
        self.video_info_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=5)
        
        # Left side - Thumbnail
        self.thumbnail_frame = ttk.Frame(self.video_info_frame)
        self.thumbnail_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        
        self.thumbnail_label = ttk.Label(self.thumbnail_frame)
        self.thumbnail_label.pack(pady=5)
        
        # Right side - Video details
        details_frame = ttk.Frame(self.video_info_frame)
        details_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.title_label = ttk.Label(details_frame, text="Title: ", wraplength=400, justify=tk.LEFT)
        self.title_label.pack(anchor=tk.W, pady=2)
        
        self.channel_label = ttk.Label(details_frame, text="Channel: ", justify=tk.LEFT)
        self.channel_label.pack(anchor=tk.W, pady=2)
        
        self.duration_label = ttk.Label(details_frame, text="Duration: ", justify=tk.LEFT)
        self.duration_label.pack(anchor=tk.W, pady=2)
        
        self.views_label = ttk.Label(details_frame, text="Views: ", justify=tk.LEFT)
        self.views_label.pack(anchor=tk.W, pady=2)
        
        # Format selection frame
        format_frame = ttk.LabelFrame(self.download_tab, text="Download Options")
        format_frame.pack(fill=tk.X, pady=10, padx=5)
        
        # Format selection
        ttk.Label(format_frame, text="Select Format:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.format_var = tk.StringVar(value="best")
        self.format_combo = ttk.Combobox(format_frame, textvariable=self.format_var, state="readonly", width=40)
        self.format_combo["values"] = [
            "best (Best video and audio quality)",
            "bestvideo+bestaudio (Best video and audio, separate files merged)",
            "bestvideo[height<=1080]+bestaudio (1080p)",
            "bestvideo[height<=720]+bestaudio (720p)",
            "bestvideo[height<=480]+bestaudio (480p)",
            "bestvideo[height<=360]+bestaudio (360p)",
            "bestaudio[ext=m4a] (Best audio quality)",
            "worstaudio (Smallest audio file)"
        ]
        self.format_combo.current(0)
        self.format_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Output directory
        ttk.Label(format_frame, text="Save to:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        
        output_frame = ttk.Frame(format_frame)
        output_frame.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        
        self.output_var = tk.StringVar(value=self.config["download_dir"])
        output_entry = ttk.Entry(output_frame, textvariable=self.output_var, width=40)
        output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        browse_button = ttk.Button(output_frame, text="Browse", command=self.browse_output)
        browse_button.pack(side=tk.LEFT, padx=5)
        
        # Additional options
        options_frame = ttk.Frame(format_frame)
        options_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)
        
        self.subtitle_var = tk.BooleanVar(value=self.config["include_subtitles"])
        subtitle_check = ttk.Checkbutton(options_frame, text="Download subtitles", variable=self.subtitle_var)
        subtitle_check.pack(side=tk.LEFT, padx=5)
        
        self.convert_audio_var = tk.BooleanVar(value=self.config["auto_convert_audio"])
        convert_check = ttk.Checkbutton(options_frame, text="Convert audio to MP3", variable=self.convert_audio_var)
        convert_check.pack(side=tk.LEFT, padx=5)
        
        # Download button
        download_button = ttk.Button(self.download_tab, text="Download", command=self.download_video)
        download_button.pack(pady=10)
        
        # Progress frame
        self.progress_frame = ttk.LabelFrame(self.download_tab, text="Download Progress")
        self.progress_frame.pack(fill=tk.X, pady=10, padx=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=10, pady=10)
        
        self.progress_label = ttk.Label(self.progress_frame, text="Ready")
        self.progress_label.pack(pady=5)
        
        # Initialize with empty video info
        self.current_video_info = None
    
    def setup_playlist_tab(self):
        """Setup the playlist tab UI"""
        # URL Frame
        url_frame = ttk.Frame(self.playlist_tab)
        url_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(url_frame, text="Enter Playlist URL:").pack(side=tk.LEFT, padx=5)
        
        self.playlist_url_var = tk.StringVar()
        url_entry = ttk.Entry(url_frame, textvariable=self.playlist_url_var, width=50)
        url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        paste_button = ttk.Button(url_frame, text="Paste", command=self.paste_playlist_url)
        paste_button.pack(side=tk.LEFT, padx=5)
        
        fetch_button = ttk.Button(url_frame, text="Fetch Playlist Info", command=self.fetch_playlist_info)
        fetch_button.pack(side=tk.LEFT, padx=5)
        
        # Playlist Info Frame
        self.playlist_info_frame = ttk.LabelFrame(self.playlist_tab, text="Playlist Information")
        self.playlist_info_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=5)
        
        # Playlist details
        details_frame = ttk.Frame(self.playlist_info_frame)
        details_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.playlist_title_label = ttk.Label(details_frame, text="Title: ", wraplength=400, justify=tk.LEFT)
        self.playlist_title_label.pack(anchor=tk.W, pady=2)
        
        self.playlist_channel_label = ttk.Label(details_frame, text="Channel: ", justify=tk.LEFT)
        self.playlist_channel_label.pack(anchor=tk.W, pady=2)
        
        self.playlist_count_label = ttk.Label(details_frame, text="Videos: ", justify=tk.LEFT)
        self.playlist_count_label.pack(anchor=tk.W, pady=2)
        
        # Videos list
        videos_frame = ttk.Frame(self.playlist_info_frame)
        videos_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        ttk.Label(videos_frame, text="Videos in playlist:").pack(anchor=tk.W)
        
        # Create a frame with scrollbar for the videos list
        list_frame = ttk.Frame(videos_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.playlist_videos_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, 
                                                 bg=CURRENT_THEME["entry_bg"], 
                                                 fg=CURRENT_THEME["entry_fg"],
                                                 selectbackground=CURRENT_THEME["highlight_bg"],
                                                 selectforeground=CURRENT_THEME["highlight_fg"])
        self.playlist_videos_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=self.playlist_videos_listbox.yview)
        
        # Format selection frame
        format_frame = ttk.LabelFrame(self.playlist_tab, text="Download Options")
        format_frame.pack(fill=tk.X, pady=10, padx=5)
        
        # Format selection
        ttk.Label(format_frame, text="Select Format:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.playlist_format_var = tk.StringVar(value="best")
        self.playlist_format_combo = ttk.Combobox(format_frame, textvariable=self.playlist_format_var, state="readonly", width=40)
        self.playlist_format_combo["values"] = [
            "best (Best video and audio quality)",
            "bestvideo[height<=720]+bestaudio (720p)",
            "bestvideo[height<=480]+bestaudio (480p)",
            "bestvideo[height<=360]+bestaudio (360p)",
            "bestaudio[ext=m4a] (Best audio quality)"
        ]
        self.playlist_format_combo.current(0)
        self.playlist_format_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Output directory
        ttk.Label(format_frame, text="Save to:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        
        output_frame = ttk.Frame(format_frame)
        output_frame.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        
        self.playlist_output_var = tk.StringVar(value=self.config["download_dir"])
        output_entry = ttk.Entry(output_frame, textvariable=self.playlist_output_var, width=40)
        output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        browse_button = ttk.Button(output_frame, text="Browse", command=self.browse_playlist_output)
        browse_button.pack(side=tk.LEFT, padx=5)
        
        # Additional options
        options_frame = ttk.Frame(format_frame)
        options_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)
        
        self.playlist_subtitle_var = tk.BooleanVar(value=self.config["include_subtitles"])
        subtitle_check = ttk.Checkbutton(options_frame, text="Download subtitles", variable=self.playlist_subtitle_var)
        subtitle_check.pack(side=tk.LEFT, padx=5)
        
        self.playlist_convert_audio_var = tk.BooleanVar(value=self.config["auto_convert_audio"])
        convert_check = ttk.Checkbutton(options_frame, text="Convert audio to MP3", variable=self.playlist_convert_audio_var)
        convert_check.pack(side=tk.LEFT, padx=5)
        
        # Download options
        download_frame = ttk.Frame(self.playlist_tab)
        download_frame.pack(fill=tk.X, pady=10)
        
        download_all_button = ttk.Button(download_frame, text="Download All Videos", command=self.download_playlist)
        download_all_button.pack(side=tk.LEFT, padx=5)
        
        download_selected_button = ttk.Button(download_frame, text="Download Selected Videos", command=self.download_selected_videos)
        download_selected_button.pack(side=tk.LEFT, padx=5)
        
        # Progress frame
        self.playlist_progress_frame = ttk.LabelFrame(self.playlist_tab, text="Download Progress")
        self.playlist_progress_frame.pack(fill=tk.X, pady=10, padx=5)
        
        self.playlist_progress_var = tk.DoubleVar()
        self.playlist_progress_bar = ttk.Progressbar(self.playlist_progress_frame, variable=self.playlist_progress_var, maximum=100)
        self.playlist_progress_bar.pack(fill=tk.X, padx=10, pady=10)
        
        self.playlist_progress_label = ttk.Label(self.playlist_progress_frame, text="Ready")
        self.playlist_progress_label.pack(pady=5)
        
        # Initialize with empty playlist info
        self.current_playlist_info = None
    
    def setup_search_tab(self):
        """Setup the search tab UI"""
        # Search Frame
        search_frame = ttk.Frame(self.search_tab)
        search_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(search_frame, text="Search YouTube:").pack(side=tk.LEFT, padx=5)
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=50)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        search_entry.bind("<Return>", lambda e: self.search_videos())
        
        search_button = ttk.Button(search_frame, text="Search", command=self.search_videos)
        search_button.pack(side=tk.LEFT, padx=5)
        
        # Results Frame
        self.search_results_frame = ttk.LabelFrame(self.search_tab, text="Search Results")
        self.search_results_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=5)
        
        # Create a canvas with scrollbar for the results
        canvas_frame = ttk.Frame(self.search_results_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.results_canvas = tk.Canvas(canvas_frame, bg=CURRENT_THEME["bg"])
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.results_canvas.yview)
        
        self.results_frame = ttk.Frame(self.results_canvas)
        self.results_frame.bind("<Configure>", lambda e: self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all")))
        
        self.results_canvas.create_window((0, 0), window=self.results_frame, anchor=tk.NW)
        self.results_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.results_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Initial message
        self.search_message = ttk.Label(self.results_frame, text="Enter a search term above to find videos")
        self.search_message.pack(pady=20)
        
        # Search results will be dynamically added here
        self.search_results = []
    
    def setup_history_tab(self):
        """Setup the history tab UI"""
        # History Frame
        history_frame = ttk.Frame(self.history_tab)
        history_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=5)
        
        # Create a treeview for the history
        columns = ("title", "date", "format", "path")
        self.history_tree = ttk.Treeview(history_frame, columns=columns, show="headings")
        
        # Define headings
        self.history_tree.heading("title", text="Video Title")
        self.history_tree.heading("date", text="Download Date")
        self.history_tree.heading("format", text="Format")
        self.history_tree.heading("path", text="Saved To")
        
        # Define columns
        self.history_tree.column("title", width=300)
        self.history_tree.column("date", width=150)
        self.history_tree.column("format", width=100)
        self.history_tree.column("path", width=200)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack elements
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add right-click menu
        self.history_menu = tk.Menu(self.root, tearoff=0)
        self.history_menu.add_command(label="Open File", command=self.open_history_file)
        self.history_menu.add_command(label="Open Folder", command=self.open_history_folder)
        self.history_menu.add_separator()
        self.history_menu.add_command(label="Download Again", command=self.redownload_from_history)
        self.history_menu.add_command(label="Copy URL", command=self.copy_history_url)
        self.history_menu.add_separator()
        self.history_menu.add_command(label="Remove from History", command=self.remove_from_history)
        
        self.history_tree.bind("<Button-3>", self.show_history_menu)
        
        # Buttons frame
        buttons_frame = ttk.Frame(self.history_tab)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        clear_button = ttk.Button(buttons_frame, text="Clear History", command=self.clear_history)
        clear_button.pack(side=tk.LEFT, padx=5)
        
        refresh_button = ttk.Button(buttons_frame, text="Refresh", command=self.refresh_history)
        refresh_button.pack(side=tk.LEFT, padx=5)
        
        # Populate history
        self.refresh_history()
    
    def setup_settings_tab(self):
        """Setup the settings tab UI"""
        # Settings Frame
        settings_frame = ttk.LabelFrame(self.settings_tab, text="Application Settings")
        settings_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=5)
        
        # Default download directory
        dir_frame = ttk.Frame(settings_frame)
        dir_frame.pack(fill=tk.X, pady=10, padx=5)
        
        ttk.Label(dir_frame, text="Default Download Directory:").pack(anchor=tk.W)
        
        dir_input_frame = ttk.Frame(dir_frame)
        dir_input_frame.pack(fill=tk.X, pady=5)
        
        self.default_dir_var = tk.StringVar(value=self.config["download_dir"])
        default_dir_entry = ttk.Entry(dir_input_frame, textvariable=self.default_dir_var, width=50)
        default_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        browse_button = ttk.Button(dir_input_frame, text="Browse", command=self.browse_default_dir)
        browse_button.pack(side=tk.LEFT, padx=5)
        
        # Theme selection
        theme_frame = ttk.Frame(settings_frame)
        theme_frame.pack(fill=tk.X, pady=10, padx=5)
        
        ttk.Label(theme_frame, text="Application Theme:").pack(anchor=tk.W)
        
        self.theme_var = tk.StringVar(value=self.config["theme"])
        theme_light = ttk.Radiobutton(theme_frame, text="Light Mode", variable=self.theme_var, value="light")
        theme_light.pack(anchor=tk.W, padx=20, pady=2)
        
        theme_dark = ttk.Radiobutton(theme_frame, text="Dark Mode", variable=self.theme_var, value="dark")
        theme_dark.pack(anchor=tk.W, padx=20, pady=2)
        
        # Default format
        format_frame = ttk.Frame(settings_frame)
        format_frame.pack(fill=tk.X, pady=10, padx=5)
        
        ttk.Label(format_frame, text="Default Download Format:").pack(anchor=tk.W)
        
        self.default_format_var = tk.StringVar(value=self.config["default_format"])
        format_combo = ttk.Combobox(format_frame, textvariable=self.default_format_var, state="readonly", width=40)
        format_combo["values"] = [
            "best",
            "bestvideo+bestaudio",
            "bestvideo[height<=1080]+bestaudio",
            "bestvideo[height<=720]+bestaudio",
            "bestvideo[height<=480]+bestaudio",
            "bestaudio[ext=m4a]"
        ]
        format_combo.pack(anchor=tk.W, padx=20, pady=5)
        
        # Other options
        options_frame = ttk.Frame(settings_frame)
        options_frame.pack(fill=tk.X, pady=10, padx=5)
        
        ttk.Label(options_frame, text="Additional Options:").pack(anchor=tk.W)
        
        self.default_subtitle_var = tk.BooleanVar(value=self.config["include_subtitles"])
        subtitle_check = ttk.Checkbutton(options_frame, text="Download subtitles by default", variable=self.default_subtitle_var)
        subtitle_check.pack(anchor=tk.W, padx=20, pady=2)
        
        self.default_convert_var = tk.BooleanVar(value=self.config["auto_convert_audio"])
        convert_check = ttk.Checkbutton(options_frame, text="Convert audio to MP3 by default", variable=self.default_convert_var)
        convert_check.pack(anchor=tk.W, padx=20, pady=2)
        
        self.max_results_var = tk.IntVar(value=self.config["max_search_results"])
        max_results_frame = ttk.Frame(options_frame)
        max_results_frame.pack(anchor=tk.W, padx=20, pady=5)
        
        ttk.Label(max_results_frame, text="Max search results:").pack(side=tk.LEFT)
        max_results_spinbox = ttk.Spinbox(max_results_frame, from_=5, to=50, width=5, textvariable=self.max_results_var)
        max_results_spinbox.pack(side=tk.LEFT, padx=5)
        
        # Buttons
        buttons_frame = ttk.Frame(settings_frame)
        buttons_frame.pack(fill=tk.X, pady=20, padx=5)
        
        save_button = ttk.Button(buttons_frame, text="Save Settings", command=self.save_settings)
        save_button.pack(side=tk.LEFT, padx=5)
        
        reset_button = ttk.Button(buttons_frame, text="Reset to Defaults", command=self.reset_settings)
        reset_button.pack(side=tk.LEFT, padx=5)
        
        # About section
        about_frame = ttk.LabelFrame(self.settings_tab, text="About")
        about_frame.pack(fill=tk.X, pady=10, padx=5)
        
        about_text = f"""YouTube Downloader Pro v{VERSION}
        
A powerful YouTube video and playlist downloader with search capabilities.
        
This application uses yt-dlp to download videos from YouTube and other platforms.
        
© 2025 - Open Source Software"""
        
        about_label = ttk.Label(about_frame, text=about_text, justify=tk.CENTER)
        about_label.pack(pady=10, padx=10)
        
        check_updates_button = ttk.Button(about_frame, text="Check for Updates", command=self.check_for_updates)
        check_updates_button.pack(pady=5)
        
        # Credits
        credits_frame = ttk.Frame(about_frame)
        credits_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(credits_frame, text="Powered by:").pack()
        
        links_frame = ttk.Frame(credits_frame)
        links_frame.pack()
        
        yt_dlp_link = ttk.Label(links_frame, text="yt-dlp", foreground=CURRENT_THEME["info"], cursor="hand2")
        yt_dlp_link.pack(side=tk.LEFT, padx=5)
        yt_dlp_link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/yt-dlp/yt-dlp"))
        
        python_link = ttk.Label(links_frame, text="Python", foreground=CURRENT_THEME["info"], cursor="hand2")
        python_link.pack(side=tk.LEFT, padx=5)
        python_link.bind("<Button-1>", lambda e: webbrowser.open("https://www.python.org"))
        
        tkinter_link = ttk.Label(links_frame, text="Tkinter", foreground=CURRENT_THEME["info"], cursor="hand2")
        tkinter_link.pack(side=tk.LEFT, padx=5)
        tkinter_link.bind("<Button-1>", lambda e: webbrowser.open("https://docs.python.org/3/library/tkinter.html"))
    
    # Helper methods
    def paste_url(self):
        """Paste clipboard content to URL entry"""
        try:
            self.url_var.set(self.root.clipboard_get())
        except:
            pass
    
    def paste_playlist_url(self):
        """Paste clipboard content to playlist URL entry"""
        try:
            self.playlist_url_var.set(self.root.clipboard_get())
        except:
            pass
    
    def browse_output(self):
        """Browse for output directory"""
        directory = filedialog.askdirectory(initialdir=self.output_var.get())
        if directory:
            self.output_var.set(directory)
    
    def browse_playlist_output(self):
        """Browse for playlist output directory"""
        directory = filedialog.askdirectory(initialdir=self.playlist_output_var.get())
        if directory:
            self.playlist_output_var.set(directory)
    
    def browse_default_dir(self):
        """Browse for default download directory"""
        directory = filedialog.askdirectory(initialdir=self.default_dir_var.get())
        if directory:
            self.default_dir_var.set(directory)
    
    def save_settings(self):
        """Save settings to config"""
        self.config["download_dir"] = self.default_dir_var.get()
        self.config["theme"] = self.theme_var.get()
        self.config["default_format"] = self.default_format_var.get()
        self.config["include_subtitles"] = self.default_subtitle_var.get()
        self.config["auto_convert_audio"] = self.default_convert_var.get()
        self.config["max_search_results"] = self.max_results_var.get()
        
        self.save_config()
        
        # Apply theme if changed
        if CURRENT_THEME == DARK_MODE and self.config["theme"] == "light":
            global CURRENT_THEME
            CURRENT_THEME = LIGHT_MODE
            self.apply_theme()
            messagebox.showinfo("Settings", "Theme changed to Light Mode. Some changes will take effect after restart.")
        elif CURRENT_THEME == LIGHT_MODE and self.config["theme"] == "dark":
            CURRENT_THEME = DARK_MODE
            self.apply_theme()
            messagebox.showinfo("Settings", "Theme changed to Dark Mode. Some changes will take effect after restart.")
        else:
            messagebox.showinfo("Settings", "Settings saved successfully")
    
    def reset_settings(self):
        """Reset settings to defaults"""
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings to default values?"):
            self.config = {
                "download_dir": DEFAULT_DOWNLOAD_DIR,
                "theme": "dark",
                "default_format": "best",
                "auto_convert_audio": False,
                "include_subtitles": False,
                "max_search_results": 10
            }
            
            self.default_dir_var.set(self.config["download_dir"])
            self.theme_var.set(self.config["theme"])
            self.default_format_var.set(self.config["default_format"])
            self.default_subtitle_var.set(self.config["include_subtitles"])
            self.default_convert_var.set(self.config["auto_convert_audio"])
            self.max_results_var.set(self.config["max_search_results"])
            
            self.save_config()
            
            global CURRENT_THEME
            CURRENT_THEME = DARK_MODE
            self.apply_theme()
            
            messagebox.showinfo("Settings", "Settings have been reset to defaults")
    
    def fetch_video_info(self):
        """Fetch video information from URL"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Input Error", "Please enter a video URL")
            return
        
        # Update status
        self.status_bar.config(text="Fetching video information...")
        self.progress_label.config(text="Fetching video information...")
        
        # Start fetching in a separate thread
        threading.Thread(target=self._fetch_video_info, args=(url,), daemon=True).start()
    
    def _fetch_video_info(self, url):
        """Background thread for fetching video info"""
        try:
            # Configure yt-dlp options
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'format': 'best',
            }
            
            # Extract info
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # For playlists, get the first video
                if 'entries' in info:
                    messagebox.showinfo("Playlist Detected", 
                                       "This URL contains a playlist. Please use the Playlist tab to download playlists.")
                    self.notebook.select(1)  # Switch to playlist tab
                    self.playlist_url_var.set(url)
                    self.fetch_playlist_info()
                    return
                
                # Store video info
                self.current_video_info = info
                
                # Update UI in the main thread
                self.root.after(0, self._update_video_info_ui, info)
        
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to fetch video information: {str(e)}"))
            self.root.after(0, lambda: self.status_bar.config(text="Error fetching video information"))
            self.root.after(0, lambda: self.progress_label.config(text="Error fetching video information"))
    
    def _update_video_info_ui(self, info):
        """Update UI with video information"""
        # Update title
        self.title_label.config(text=f"Title: {info.get('title', 'Unknown')}")
        
        # Update channel
        self.channel_label.config(text=f"Channel: {info.get('uploader', 'Unknown')}")
        
        # Update duration
        duration = info.get('duration')
        if duration:
            minutes, seconds = divmod(int(duration), 60)
            hours, minutes = divmod(minutes, 60)
            if hours > 0:
                duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                duration_str = f"{minutes}:{seconds:02d}"
            self.duration_label.config(text=f"Duration: {duration_str}")
        else:
            self.duration_label.config(text="Duration: Unknown")
        
        # Update views
        view_count = info.get('view_count')
        if view_count:
            view_str = f"{view_count:,}"
            self.views_label.config(text=f"Views: {view_str}")
        else:
            self.views_label.config(text="Views: Unknown")
        
        # Load thumbnail
        threading.Thread(target=self._load_thumbnail, args=(info.get('thumbnail'),), daemon=True).start()
        
        # Update status
        self.status_bar.config(text="Video information loaded")
        self.progress_label.config(text="Ready to download")
    
    def _load_thumbnail(self, thumbnail_url):
        """Load thumbnail image from URL"""
        if not thumbnail_url:
            return
        
        try:
            # Download thumbnail
            response = requests.get(thumbnail_url)
            img_data = BytesIO(response.content)
            img = Image.open(img_data)
            
            # Resize to fit
            img = img.resize((240, 135), Image.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(img)
            
            # Update UI in main thread
            self.root.after(0, lambda: self._set_thumbnail(photo))
        except Exception as e:
            print(f"Error loading thumbnail: {e}")
    
    def _set_thumbnail(self, photo):
        """Set thumbnail in UI"""
        self.thumbnail_label.config(image=photo)
        self.thumbnail_label.image = photo  # Keep a reference
    
    def download_video(self):
        """Download the video"""
        if not self.current_video_info:
            messagebox.showwarning("No Video", "Please fetch video information first")
            return
        
        url = self.url_var.get().strip()
        output_dir = self.output_var.get()
        
        if not os.path.isdir(output_dir):
            messagebox.showwarning("Invalid Directory", "Please select a valid download directory")
            return
        
        # Get selected format
        format_selection = self.format_var.get().split(" ")[0]  # Get the format code
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': format_selection,
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [self._progress_hook],
        }
        
        # Add subtitle option if selected
        if self.subtitle_var.get():
            ydl_opts.update({
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en'],
                'subtitlesformat': 'srt',
            })
        
        # Add audio conversion if selected
        if self.convert_audio_var.get() and "audio" in format_selection:
            ydl_opts.update({
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        
        # Update UI
        self.progress_var.set(0)
        self.progress_label.config(text="Starting download...")
        self.status_bar.config(text="Downloading video...")
        
        # Start download in a separate thread
        threading.Thread(target=self._download_video, args=(url, ydl_opts), daemon=True).start()
    
    def _download_video(self, url, ydl_opts):
        """Background thread for downloading video"""
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
                # Add to history
                title = self.current_video_info.get('title', 'Unknown')
                format_name = self.format_var.get().split(" ")[0]
                self.download_manager.add_to_history(title, url, ydl_opts['outtmpl'], format_name)
                
                # Update UI in main thread
                self.root.after(0, lambda: self.progress_label.config(text="Download completed successfully!"))
                self.root.after(0, lambda: self.status_bar.config(text="Download completed"))
                self.root.after(0, lambda: self.refresh_history())
                self.root.after(0, lambda: messagebox.showinfo("Success", f"Video '{title}' downloaded successfully!"))
        
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: messagebox.showerror("Download Error", f"Failed to download video: {error_msg}"))
            self.root.after(0, lambda: self.progress_label.config(text=f"Error: {error_msg}"))
            self.root.after(0, lambda: self.status_bar.config(text="Download failed"))
    
    def _progress_hook(self, d):
        """Progress hook for yt-dlp"""
        if d['status'] == 'downloading':
            # Calculate progress
            if 'total_bytes' in d and d['total_bytes'] > 0:
                percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
            elif 'total_bytes_estimate' in d and d['total_bytes_estimate'] > 0:
                percent = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
            else:
                percent = 0
            
            # Format download speed
            if 'speed' in d and d['speed']:
                speed = d['speed']
                if speed < 1024:
                    speed_str = f"{speed:.1f} B/s"
                elif speed < 1024 * 1024:
                    speed_str = f"{speed/1024:.1f} KB/s"
                else:
                    speed_str = f"{speed/(1024*1024):.1f} MB/s"
            else:
                speed_str = "-- KB/s"
            
            # Format ETA
            eta_str = d.get('eta', '--')
            if eta_str != '--':
                minutes, seconds = divmod(eta_str, 60)
                hours, minutes = divmod(minutes, 60)
                if hours > 0:
                    eta_str = f"{hours}h {minutes}m {seconds}s"
                elif minutes > 0:
                    eta_str = f"{minutes}m {seconds}s"
                else:
                    eta_str = f"{seconds}s"
            
            # Update UI in main thread
            self.root.after(0, lambda: self.progress_var.set(percent))
            self.root.after(0, lambda: self.progress_label.config(
                text=f"Downloading: {percent:.1f}% | Speed: {speed_str} | ETA: {eta_str}"))
            self.root.after(0, lambda: self.status_bar.config(
                text=f"Downloading: {d.get('filename', '').split('/')[-1]}"))
        
        elif d['status'] == 'finished':
            self.root.after(0, lambda: self.progress_label.config(text="Download finished, processing file..."))
            self.root.after(0, lambda: self.status_bar.config(text="Processing downloaded file..."))
    
    def fetch_playlist_info(self):
        """Fetch playlist information"""
        url = self.playlist_url_var.get().strip()
        if not url:
            messagebox.showwarning("Input Error", "Please enter a playlist URL")
            return
        
        # Update status
        self.status_bar.config(text="Fetching playlist information...")
        self.playlist_progress_label.config(text="Fetching playlist information...")
        
        # Start fetching in a separate thread
        threading.Thread(target=self._fetch_playlist_info, args=(url,), daemon=True).start()
    
    def _fetch_playlist_info(self, url):
        """Background thread for fetching playlist info"""
        try:
            # Configure yt-dlp options
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'extract_flat': True,
            }
            
            # Extract info
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Check if it's a playlist
                if 'entries' not in info:
                    self.root.after(0, lambda: messagebox.showinfo("Not a Playlist", 
                                                                 "This URL does not contain a playlist. Redirecting to video download tab."))
                    self.root.after(0, lambda: self.notebook.select(0))  # Switch to video tab
                    self.root.after(0, lambda: self.url_var.set(url))
                    self.root.after(0, lambda: self.fetch_video_info())
                    return
                
                # Store playlist info
                self.current_playlist_info = info
                
                # Update UI in the main thread
                self.root.after(0, self._update_playlist_info_ui, info)
        
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to fetch playlist information: {str(e)}"))
            self.root.after(0, lambda: self.status_bar.config(text="Error fetching playlist information"))
            self.root.after(0, lambda: self.playlist_progress_label.config(text="Error fetching playlist information"))
    
    def _update_playlist_info_ui(self, info):
        """Update UI with playlist information"""
        # Update title
        self.playlist_title_label.config(text=f"Title: {info.get('title', 'Unknown')}")
        
        # Update channel
        self.playlist_channel_label.config(text=f"Channel: {info.get('uploader', 'Unknown')}")
        
        # Update video count
        entries = info.get('entries', [])
        self.playlist_count_label.config(text=f"Videos: {len(entries)}")
        
        # Clear and update videos list
        self.playlist_videos_listbox.delete(0, tk.END)
        
        for i, entry in enumerate(entries):
            title = entry.get('title', f'Video {i+1}')
            self.playlist_videos_listbox.insert(tk.END, f"{i+1}. {title}")
        
        # Update status
        self.status_bar.config(text="Playlist information loaded")
        self.playlist_progress_label.config(text="Ready to download")
    
    def download_playlist(self):
        """Download all videos in the playlist"""
        if not self.current_playlist_info:
            messagebox.showwarning("No Playlist", "Please fetch playlist information first")
            return
        
        url = self.playlist_url_var.get().strip()
        output_dir = self.playlist_output_var.get()
        
        if not os.path.isdir(output_dir):
            messagebox.showwarning("Invalid Directory", "Please select a valid download directory")
            return
        
        # Get selected format
        format_selection = self.playlist_format_var.get().split(" ")[0]  # Get the format code
        
        # Create playlist folder
        playlist_title = self.current_playlist_info.get('title', 'Playlist')
        playlist_dir = os.path.join(output_dir, re.sub(r'[\\/*?:"<>|]', "_", playlist_title))
        os.makedirs(playlist_dir, exist_ok=True)
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': format_selection,
            'outtmpl': os.path.join(playlist_dir, '%(playlist_index)s-%(title)s.%(ext)s'),
            'progress_hooks': [self._playlist_progress_hook],
        }
        
        # Add subtitle option if selected
        if self.playlist_subtitle_var.get():
            ydl_opts.update({
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en'],
                'subtitlesformat': 'srt',
            })
        
        # Add audio conversion if selected
        if self.playlist_convert_audio_var.get() and "audio" in format_selection:
            ydl_opts.update({
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        
        # Update UI
        self.playlist_progress_var.set(0)
        self.playlist_progress_label.config(text="Starting playlist download...")
        self.status_bar.config(text="Downloading playlist...")
        
        # Start download in a separate thread
        threading.Thread(target=self._download_playlist, args=(url, ydl_opts, playlist_dir), daemon=True).start()
    
    def _download_playlist(self, url, ydl_opts, playlist_dir):
        """Background thread for downloading playlist"""
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
                # Add to history
                playlist_title = self.current_playlist_info.get('title', 'Playlist')
                format_name = self.playlist_format_var.get().split(" ")[0]
                self.download_manager.add_to_history(f"Playlist: {playlist_title}", 
                                                   url, playlist_dir, format_name)
                
                # Update UI in main thread
                self.root.after(0, lambda: self.playlist_progress_label.config(text="Playlist download completed successfully!"))
                self.root.after(0, lambda: self.status_bar.config(text="Playlist download completed"))
                self.root.after(0, lambda: self.refresh_history())
                self.root.after(0, lambda: messagebox.showinfo("Success", f"Playlist '{playlist_title}' downloaded successfully!"))
        
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: messagebox.showerror("Download Error", f"Failed to download playlist: {error_msg}"))
            self.root.after(0, lambda: self.playlist_progress_label.config(text=f"Error: {error_msg}"))
            self.root.after(0, lambda: self.status_bar.config(text="Playlist download failed"))
    
    def _playlist_progress_hook(self, d):
        """Progress hook for playlist download"""
        if d['status'] == 'downloading':
            # Calculate progress for current video
            if 'total_bytes' in d and d['total_bytes'] > 0:
                percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
            elif 'total_bytes_estimate' in d and d['total_bytes_estimate'] > 0:
                percent = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
            else:
                percent = 0
            
            # Format download speed
            if 'speed' in d and d['speed']:
                speed = d['speed']
                if speed < 1024:
                    speed_str = f"{speed:.1f} B/s"
                elif speed < 1024 * 1024:
                    speed_str = f"{speed/1024:.1f} KB/s"
                else:
                    speed_str = f"{speed/(1024*1024):.1f} MB/s"
            else:
                speed_str = "-- KB/s"
            
            # Get current video info
            filename = d.get('filename', '').split('/')[-1]
            
            # Update UI in main thread
            self.root.after(0, lambda: self.playlist_progress_var.set(percent))
            self.root.after(0, lambda: self.playlist_progress_label.config(
                text=f"Downloading: {filename} | {percent:.1f}% | Speed: {speed_str}"))
            self.root.after(0, lambda: self.status_bar.config(
                text=f"Downloading playlist video: {filename}"))
        
        elif d['status'] == 'finished':
            self.root.after(0, lambda: self.playlist_progress_label.config(text="Video finished, processing next..."))
            self.root.after(0, lambda: self.status_bar.config(text="Processing downloaded video..."))
    
    def download_selected_videos(self):
        """Download selected videos from playlist"""
        if not self.current_playlist_info:
            messagebox.showwarning("No Playlist", "Please fetch playlist information first")
            return
        
        # Get selected indices
        selected_indices = self.playlist_videos_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select videos to download")
            return
        
        # Get playlist entries
        entries = self.current_playlist_info.get('entries', [])
        
        # Get selected videos
        selected_videos = [entries[i] for i in selected_indices if i < len(entries)]
        
        if not selected_videos:
            messagebox.showwarning("Error", "Failed to get selected videos")
            return
        
        # Get output directory
        output_dir = self.playlist_output_var.get()
        if not os.path.isdir(output_dir):
            messagebox.showwarning("Invalid Directory", "Please select a valid download directory")
            return
        
        # Get selected format
        format_selection = self.playlist_format_var.get().split(" ")[0]  # Get the format code
        # Create playlist folder
        playlist_title = self.current_playlist_info.get('title', 'Selected Videos')
        playlist_dir = os.path.join(output_dir, re.sub(r'[\\/*?:"<>|]', "_", playlist_title) + "_selected")
        os.makedirs(playlist_dir, exist_ok=True)

        # Configure yt-dlp options
        ydl_opts = {
            'format': format_selection,
            'outtmpl': os.path.join(playlist_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [self._playlist_progress_hook],
        }

        # Add subtitle option if selected
        if self.playlist_subtitle_var.get():
            ydl_opts.update({
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en'],
                'subtitlesformat': 'srt',
            })

        # Add audio conversion if selected
        if self.playlist_convert_audio_var.get() and "audio" in format_selection:
            ydl_opts.update({
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })

        # Update UI
        self.playlist_progress_var.set(0)
        self.playlist_progress_label.config(text=f"Starting download of {len(selected_videos)} selected videos...")
        self.status_bar.config(text="Downloading selected videos...")

        # Start download in a separate thread
        threading.Thread(target=self._download_selected_videos,
                        args=(selected_videos, ydl_opts, playlist_dir), daemon=True).start()

    def _download_selected_videos(self, videos, ydl_opts, playlist_dir):
        """Background thread for downloading selected videos"""
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                for video in videos:
                    url = video.get('url') or f"https://www.youtube.com/watch?v={video.get('id')}"
                    ydl.download([url])

            # Add to history
            playlist_title = self.current_playlist_info.get('title', 'Playlist')
            format_name = self.playlist_format_var.get().split(" ")[0]
            self.download_manager.add_to_history(f"Selected videos from: {playlist_title}",
                                               self.playlist_url_var.get(), playlist_dir, format_name)

            # Update UI in main thread
            self.root.after(0, lambda: self.playlist_progress_label.config(text="Selected videos downloaded successfully!"))
            self.root.after(0, lambda: self.status_bar.config(text="Selected videos download completed"))
            self.root.after(0, lambda: self.refresh_history())
            self.root.after(0, lambda: messagebox.showinfo("Success", f"{len(videos)} videos downloaded successfully!"))

        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: messagebox.showerror("Download Error", f"Failed to download videos: {error_msg}"))
            self.root.after(0, lambda: self.playlist_progress_label.config(text=f"Error: {error_msg}"))
            self.root.after(0, lambda: self.status_bar.config(text="Selected videos download failed"))

    def search_videos(self):
        """Search for videos on YouTube"""
        query = self.search_var.get().strip()
        if not query:
            messagebox.showwarning("Input Error", "Please enter a search term")
            return

        # Update status
        self.status_bar.config(text=f"Searching for: {query}...")

        # Clear previous results
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        # Show loading message
        loading_label = ttk.Label(self.results_frame, text="Searching YouTube...")
        loading_label.pack(pady=20)
        self.results_frame.update()

        # Start search in a separate thread
        threading.Thread(target=self._search_videos, args=(query,), daemon=True).start()

    def _search_videos(self, query):
        """Background thread for searching videos"""
        try:
            # Configure yt-dlp options
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'extract_flat': True,
                'default_search': 'ytsearch',
                'max_downloads': self.config["max_search_results"],
            }

            # Search for videos
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                search_query = f"ytsearch{self.config['max_search_results']}:{query}"
                info = ydl.extract_info(search_query, download=False)

                # Store search results
                self.search_results = info.get('entries', [])

                # Update UI in the main thread
                self.root.after(0, self._update_search_results_ui)

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Search Error", f"Failed to search videos: {str(e)}"))
            self.root.after(0, lambda: self.status_bar.config(text="Search failed"))

            # Clear loading message
            self.root.after(0, lambda: [w.destroy() for w in self.results_frame.winfo_children()])
            self.root.after(0, lambda: ttk.Label(self.results_frame, text=f"Search failed: {str(e)}").pack(pady=20))

    def _update_search_results_ui(self):
        """Update UI with search results"""
        # Clear previous results
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        if not self.search_results:
            ttk.Label(self.results_frame, text="No results found").pack(pady=20)
            self.status_bar.config(text="No search results found")
            return

        # Update status
        self.status_bar.config(text=f"Found {len(self.search_results)} videos")

        # Create result items
        for i, video in enumerate(self.search_results):
            # Create frame for this result
            result_frame = ttk.Frame(self.results_frame)
            result_frame.pack(fill=tk.X, padx=10, pady=5)

            # Add separator except for the first item
            if i > 0:
                ttk.Separator(self.results_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=5)

            # Title and info
            info_frame = ttk.Frame(result_frame)
            info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            # Title with link
            title = video.get('title', f'Video {i+1}')
            title_label = ttk.Label(info_frame, text=title, wraplength=500,
                                   font=('TkDefaultFont', 10, 'bold'),
                                   foreground=CURRENT_THEME["info"], cursor="hand2")
            title_label.pack(anchor=tk.W, pady=(0, 5))

            # Bind click event to open in browser
            video_url = f"https://www.youtube.com/watch?v={video.get('id')}"
            title_label.bind("<Button-1>", lambda e, url=video_url: webbrowser.open(url))

            # Channel
            channel = video.get('uploader', 'Unknown channel')
            ttk.Label(info_frame, text=f"Channel: {channel}").pack(anchor=tk.W)

            # Duration if available
            if 'duration' in video and video['duration']:
                minutes, seconds = divmod(int(video['duration']), 60)
                hours, minutes = divmod(minutes, 60)
                if hours > 0:
                    duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
                else:
                    duration_str = f"{minutes}:{seconds:02d}"
                ttk.Label(info_frame, text=f"Duration: {duration_str}").pack(anchor=tk.W)

            # Buttons frame
            buttons_frame = ttk.Frame(result_frame)
            buttons_frame.pack(side=tk.RIGHT, padx=10)

            # Download button
            download_button = ttk.Button(buttons_frame, text="Download",
                                        command=lambda v=video: self.download_search_result(v))
            download_button.pack(pady=2)

            # Copy URL button
            copy_button = ttk.Button(buttons_frame, text="Copy URL",
                                    command=lambda url=video_url: self.copy_to_clipboard(url))
            copy_button.pack(pady=2)

    def download_search_result(self, video):
        """Download a video from search results"""
        # Set the video URL in the download tab
        video_url = f"https://www.youtube.com/watch?v={video.get('id')}"
        self.url_var.set(video_url)

        # Switch to download tab
        self.notebook.select(0)

        # Fetch video info
        self.fetch_video_info()

    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_bar.config(text="URL copied to clipboard")

    def refresh_history(self):
        """Refresh the download history"""
        # Clear current items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        # Add history items
        for item in self.download_manager.download_history:
            self.history_tree.insert("", "end", values=(
                item['title'],
                item['date'],
                item['format'],
                item['path']
            ))

    def show_history_menu(self, event):
        """Show context menu for history items"""
        # Get the item under cursor
        item = self.history_tree.identify_row(event.y)
        if not item:
            return

        # Select the item
        self.history_tree.selection_set(item)

        # Show the menu
        self.history_menu.post(event.x_root, event.y_root)

    def open_history_file(self):
        """Open the selected file from history"""
        selected = self.history_tree.selection()
        if not selected:
            return

        # Get the path
        item_values = self.history_tree.item(selected[0], "values")
        path = item_values[3]

        # Check if it's a directory or file
        if os.path.isdir(path):
            # Try to find the first media file in the directory
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith(('.mp4', '.mkv', '.webm', '.mp3', '.m4a')):
                        file_path = os.path.join(root, file)
                        self._open_file(file_path)
                        return

            # If no media file found, open the directory
            self._open_file(path)
        else:
            # Open the file directly
            self._open_file(path)

    def _open_file(self, path):
        """Open a file with the default application"""
        try:
            if platform.system() == 'Windows':
                os.startfile(path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.call(['open', path])
            else:  # Linux
                subprocess.call(['xdg-open', path])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file: {e}")

    def open_history_folder(self):
        """Open the folder containing the selected file"""
        selected = self.history_tree.selection()
        if not selected:
            return

        # Get the path
        item_values = self.history_tree.item(selected[0], "values")
        path = item_values[3]

        # Open the directory
        if os.path.isfile(path):
            path = os.path.dirname(path)

        self._open_file(path)

    def redownload_from_history(self):
        """Download the selected item again"""
        selected = self.history_tree.selection()
        if not selected:
            return

        # Get the URL
        item_index = self.history_tree.index(selected[0])
        if item_index < len(self.download_manager.download_history):
            url = self.download_manager.download_history[item_index]['url']

            # Set the URL in the download tab
            self.url_var.set(url)

            # Switch to download tab
            self.notebook.select(0)

            # Fetch video info
            self.fetch_video_info()

    def copy_history_url(self):
        """Copy the URL of the selected history item"""
        selected = self.history_tree.selection()
        if not selected:
            return

        # Get the URL
        item_index = self.history_tree.index(selected[0])
        if item_index < len(self.download_manager.download_history):
            url = self.download_manager.download_history[item_index]['url']
            self.copy_to_clipboard(url)

    def remove_from_history(self):
        """Remove the selected item from history"""
        selected = self.history_tree.selection()
        if not selected:
            return

        # Get the index
        item_index = self.history_tree.index(selected[0])

        # Remove from history
        if item_index < len(self.download_manager.download_history):
            del self.download_manager.download_history[item_index]
            self.download_manager.save_history()

            # Refresh the view
            self.refresh_history()

    def clear_history(self):
        """Clear all download history"""
        if messagebox.askyesno("Clear History", "Are you sure you want to clear all download history?"):
            self.download_manager.download_history = []
            self.download_manager.save_history()
            self.refresh_history()

    def check_for_updates(self):
        """Check for updates to the application"""
        try:
            # This is a placeholder for actual update checking
            # In a real application, you would check a server for updates

            # Simulate checking for updates
            time.sleep(1)

            # No updates available
            self.status_bar.config(text=f"YouTube Downloader Pro v{VERSION} | No updates available")
        except Exception as e:
            print(f"Error checking for updates: {e}")

    def on_close(self):
        """Handle application close"""
        # Save any pending changes
        self.save_config()

        # Close the application
        self.root.destroy()

def main():
    """Main function to start the application"""
    root = tk.Tk()
    app = YouTubeDownloader(root)
    root.mainloop()

if __name__ == "__main__":
    main()
