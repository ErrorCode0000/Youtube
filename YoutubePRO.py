import os
import sys
import tkinter as tk
from tkinter import messagebox, filedialog, ttk

# Proxy ayarlarını temizle
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)

# pip komutunu doğru şekilde çalıştır
def install_package(package):
    try:
        import importlib
        importlib.import_module(package)
    except ImportError:
        if sys.platform == "darwin":  # macOS için
            os.system(f"{sys.executable} -m pip install {package}")
        else:
            os.system(f"pip install {package}")

# yt-dlp'yi yükle
try:
    import yt_dlp
except ImportError:
    install_package("yt-dlp")
    try:
        import yt_dlp
    except ImportError:
        messagebox.showerror("Error", "yt-dlp yüklenemedi. Lütfen manuel olarak yükleyin.")
        sys.exit(1)

# Dil sözlükleri
LANGUAGES = {
    "Türkçe": {
        "title": "YouTube Video İndirici",
        "enter_url": "Video URL'sini Girin:",
        "download": "İndir",
        "select_folder": "İndirme Klasörünü Seçin",
        "error": "Hata",
        "success": "Başarılı",
        "error_no_url": "Lütfen bir video URL'si girin.",
        "error_no_folder": "Lütfen videoyu kaydetmek için bir klasör seçin.",
        "downloading": "İndiriliyor... Lütfen bekleyin.",
        "download_success": "Video başarıyla indirildi!",
        "download_error": "Bir hata oluştu: ",
    },
    "English": {
        "title": "YouTube Video Downloader",
        "enter_url": "Enter Video URL:",
        "download": "Download",
        "select_folder": "Select Download Folder",
        "error": "Error",
        "success": "Success",
        "error_no_url": "Please enter a video URL.",
        "error_no_folder": "Please select a folder to save the video.",
        "downloading": "Downloading... Please wait.",
        "download_success": "Video downloaded successfully!",
        "download_error": "An error occurred: ",
    },
    "Deutsch": {
        "title": "YouTube Video Downloader",
        "enter_url": "Geben Sie die Video-URL ein:",
        "download": "Herunterladen",
        "select_folder": "Download-Ordner auswählen",
        "error": "Fehler",
        "success": "Erfolg",
        "error_no_url": "Bitte geben Sie eine Video-URL ein.",
        "error_no_folder": "Bitte wählen Sie einen Ordner zum Speichern des Videos aus.",
        "downloading": "Wird heruntergeladen... Bitte warten.",
        "download_success": "Video erfolgreich heruntergeladen!",
        "download_error": "Ein Fehler ist aufgetreten: ",
    },
}

# Varsayılan dil
current_language = LANGUAGES["Türkçe"]

def set_language(language):
    global current_language
    current_language = LANGUAGES[language]
    update_ui_language()

def update_ui_language():
    root.title(current_language["title"])
    url_label.config(text=current_language["enter_url"])
    download_button.config(text=current_language["download"])
    status_label.config(text="")

def download_video():
    video_url = url_entry.get()
    if not video_url:
        messagebox.showwarning(current_language["error"], current_language["error_no_url"])
        return

    save_path = filedialog.askdirectory(title=current_language["select_folder"])
    if not save_path:
        messagebox.showwarning(current_language["error"], current_language["error_no_folder"])
        return

    status_label.config(text=current_language["downloading"])
    root.update()

    ydl_opts = {
        'format': 'best',
        'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
        'nocheckcertificate': True,
        'no_warnings': False,
        'proxy': '',  # Proxy kullanma
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        status_label.config(text=current_language["download_success"])
        messagebox.showinfo(current_language["success"], current_language["download_success"])
    except Exception as e:
        status_label.config(text=current_language["error"])
        messagebox.showerror(current_language["error"], f"{current_language['download_error']}{e}")

# Ana tkinter penceresi
root = tk.Tk()
root.title(current_language["title"])
root.geometry("500x250")

# Dil seçici
language_label = tk.Label(root, text="Dil / Language / Sprache:")
language_label.pack(pady=5)
language_var = tk.StringVar(value="Türkçe")
language_menu = ttk.Combobox(root, textvariable=language_var, values=list(LANGUAGES.keys()), state="readonly")
language_menu.pack(pady=5)
language_menu.bind("<<ComboboxSelected>>", lambda e: set_language(language_var.get()))

# URL giriş alanı
url_label = tk.Label(root, text=current_language["enter_url"])
url_label.pack(pady=5)
url_entry = tk.Entry(root, width=50)
url_entry.pack(pady=5)

# İndirme butonu
download_button = tk.Button(root, text=current_language["download"], command=download_video)
download_button.pack(pady=10)

# Durum etiketi
status_label = tk.Label(root, text="")
status_label.pack(pady=5)

# Tkinter döngüsünü başlat
root.mainloop()
