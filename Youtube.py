import os
import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog

try:
    import yt_dlp
except ImportError:
    if os.name == "nt":
        os.system("pip install yt-dlp")
    else:
        os.system("python3 -m pip install yt-dlp")
    try:
        import yt_dlp
    except ImportError:
        messagebox.showerror("Error", "Unable to install yt-dlp. Please install it manually.")
        exit()

def download_video():
    video_url = url_entry.get()
    if not video_url:
        messagebox.showwarning("Input Error", "Please enter a video URL.")
        return

    save_path = filedialog.askdirectory(title="Select Download Folder")
    if not save_path:
        messagebox.showwarning("Folder Error", "Please select a folder to save the video.")
        return

    ydl_opts = {
        'format': 'best',
        'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),  # Save file in selected folder
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        messagebox.showinfo("Success", "Video downloaded successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

# Create the main tkinter window
root = tk.Tk()
root.title("YouTube Video Downloader")

# Create and place widgets
tk.Label(root, text="Enter Video URL:").pack(pady=5)
url_entry = tk.Entry(root, width=50)
url_entry.pack(pady=5)

download_button = tk.Button(root, text="Download", command=download_video)
download_button.pack(pady=10)

# Run the tkinter event loop
root.mainloop()
