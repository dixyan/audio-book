import PyPDF2
import pyttsx3
import tkinter as tk
from tkinter import filedialog, messagebox, Text, ttk, Menu
import threading
import json
import os
from pathlib import Path
import re
from gtts import gTTS
import pygame
import tempfile
import requests

class PDFReaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Enhanced PDF Reader and Narrator")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # Initialize variables
        self.extracted_text = ""
        self.current_pdf_path = ""
        self.tts_engine = None
        self.is_reading = False
        self.search_results = []
        self.current_search_index = 0
        self.tts_method = tk.StringVar(value="pyttsx3")  # Default to offline TTS
        self.temp_audio_files = []  # Track temporary audio files
        
        # Initialize internet_available BEFORE setup_ui()
        self.internet_available = False
        
        # Check internet connectivity first
        self.check_internet_connection()
        
        # Initialize pygame for audio playback
        try:
            pygame.mixer.init()
        except Exception as e:
            print(f"Pygame mixer initialization error: {e}")
        
        # Settings file
        self.settings_file = "pdf_reader_settings.json"
        self.recent_files = self.load_recent_files()
        
        # Initialize TTS engine in a separate thread
        threading.Thread(target=self.init_tts_engine, daemon=True).start()
        
        self.setup_ui()
        self.setup_menu()
        
    def init_tts_engine(self):
        """Initialize TTS engine in background"""
        try:
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', 150)
            self.tts_engine.setProperty('volume', 1.0)
        except Exception as e:
            print(f"pyttsx3 initialization error: {e}")
    
    # Check internet connectivity for gTTS
        

    def check_internet_connection(self):
        """Check if internet is available for gTTS"""
        try:
            requests.get("https://www.google.com", timeout=3)
            self.internet_available = True
        except:
            self.internet_available = False
    
    def setup_menu(self):
        """Create menu bar"""
        menubar = Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open PDF", command=self.load_pdf, accelerator="Ctrl+O")
        file_menu.add_separator()
        
        # Recent files submenu
        self.recent_menu = Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Recent Files", menu=self.recent_menu)
        self.update_recent_menu()
        
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Edit menu
        edit_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Find", command=self.focus_search, accelerator="Ctrl+F")
        edit_menu.add_command(label="Find Next", command=self.find_next, accelerator="F3")
        
        # Speech menu
        speech_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Speech", menu=speech_menu)
        speech_menu.add_command(label="Read All", command=self.read_pdf_aloud)
        speech_menu.add_command(label="Read Selection", command=self.read_selection)
        speech_menu.add_command(label="Stop Reading", command=self.stop_reading)
        
        # Bind keyboard shortcuts
        self.root.bind('<Control-o>', lambda e: self.load_pdf())
        self.root.bind('<Control-f>', lambda e: self.focus_search())
        self.root.bind('<F3>', lambda e: self.find_next())
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # File selection frame
        file_frame = ttk.LabelFrame(main_frame, text="File Operations", padding="5")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Button(file_frame, text="Upload PDF", command=self.load_pdf).grid(row=0, column=0, padx=(0, 10))
        
        self.file_label = ttk.Label(file_frame, text="No file selected", foreground="gray")
        self.file_label.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Progress bar
        self.progress = ttk.Progressbar(file_frame, mode='indeterminate')
        self.progress.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Search frame
        search_frame = ttk.LabelFrame(main_frame, text="Search", padding="5")
        search_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        search_frame.columnconfigure(1, weight=1)
        
        ttk.Label(search_frame, text="Find:").grid(row=0, column=0, padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        self.search_entry.bind('<Return>', lambda e: self.search_text())
        
        ttk.Button(search_frame, text="Search", command=self.search_text).grid(row=0, column=2, padx=(0, 5))
        ttk.Button(search_frame, text="Next", command=self.find_next).grid(row=0, column=3, padx=(0, 5))
        ttk.Button(search_frame, text="Clear", command=self.clear_search).grid(row=0, column=4)
        
        self.search_info = ttk.Label(search_frame, text="", foreground="blue")
        self.search_info.grid(row=1, column=0, columnspan=5, sticky=tk.W, pady=(5, 0))
        
        # Speech controls frame
        speech_frame = ttk.LabelFrame(main_frame, text="Speech Controls", padding="5")
        speech_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(speech_frame, text="Read All", command=self.read_pdf_aloud).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(speech_frame, text="Read Selection", command=self.read_selection).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(speech_frame, text="Stop", command=self.stop_reading).grid(row=0, column=2, padx=(0, 5))
        
        # Speech settings
        ttk.Label(speech_frame, text="Speed:").grid(row=0, column=3, padx=(20, 5))
        self.speed_var = tk.IntVar(value=150)
        speed_scale = ttk.Scale(speech_frame, from_=50, to=300, variable=self.speed_var, 
                              orient=tk.HORIZONTAL, length=100, command=self.update_speech_rate)
        speed_scale.grid(row=0, column=4, padx=(0, 10))
        
        self.speed_label = ttk.Label(speech_frame, text="150")
        self.speed_label.grid(row=0, column=5)
        
        # TTS Method selection
        ttk.Label(speech_frame, text="Voice:").grid(row=1, column=0, padx=(0, 5), sticky=tk.W)

        tts_frame = ttk.Frame(speech_frame)
        tts_frame.grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=(5, 0))

        ttk.Radiobutton(tts_frame, text="Offline (pyttsx3)", variable=self.tts_method, 
                        value="pyttsx3").grid(row=0, column=0, padx=(0, 10))

        internet_text = "Online (gTTS)" if self.internet_available else "Online (gTTS) - No Internet"
        internet_state = tk.NORMAL if self.internet_available else tk.DISABLED

        ttk.Radiobutton(tts_frame, text=internet_text, variable=self.tts_method, 
                        value="gtts", state=internet_state).grid(row=0, column=1)

        # Language selection for gTTS
        ttk.Label(speech_frame, text="Language:").grid(row=1, column=3, padx=(20, 5), sticky=tk.W)
        self.language_var = tk.StringVar(value="en")
        language_combo = ttk.Combobox(speech_frame, textvariable=self.language_var, 
                                     values=["en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh"], 
                                     width=5, state="readonly")
        language_combo.grid(row=1, column=4, padx=(0, 10))
        
        # Text display frame
        text_frame = ttk.LabelFrame(main_frame, text="Document Content", padding="5")
        text_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        # Text widget with scrollbar
        text_container = ttk.Frame(text_frame)
        text_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        text_container.columnconfigure(0, weight=1)
        text_container.rowconfigure(0, weight=1)
        
        self.display_text = Text(text_container, wrap=tk.WORD, font=('Arial', 11))
        scrollbar = ttk.Scrollbar(text_container, orient=tk.VERTICAL, command=self.display_text.yview)
        self.display_text.configure(yscrollcommand=scrollbar.set)
        
        self.display_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Configure text tags
        self.display_text.tag_configure('highlight', background='yellow', foreground='black')
        self.display_text.tag_configure('current_highlight', background='orange', foreground='black')
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
    
    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF with better error handling"""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ''
                total_pages = len(reader.pages)
                
                for page_num in range(total_pages):
                    page = reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + '\n\n'
                    
                    # Update progress (this would be called from a thread)
                    progress = (page_num + 1) / total_pages * 100
                    self.root.after(0, lambda p=progress: self.update_progress(p))
                
                return text.strip()
        except Exception as e:
            raise Exception(f"Error reading PDF: {str(e)}")
    
    def update_progress(self, value):
        """Update progress bar"""
        if value >= 100:
            self.progress.stop()
            self.progress.grid_remove()
        else:
            self.progress['value'] = value
    
    def load_pdf(self):
        """Load PDF file with threading"""
        pdf_path = filedialog.askopenfilename(
            title="Select a PDF file", 
            filetypes=[("PDF files", "*.pdf")]
        )
        
        if pdf_path:
            self.progress.grid()
            self.progress.start()
            self.status_var.set("Loading PDF...")
            
            # Load PDF in separate thread
            threading.Thread(target=self._load_pdf_thread, args=(pdf_path,), daemon=True).start()
    
    def _load_pdf_thread(self, pdf_path):
        """Load PDF in background thread"""
        try:
            text = self.extract_text_from_pdf(pdf_path)
            
            # Update UI in main thread
            self.root.after(0, lambda: self._pdf_loaded_callback(pdf_path, text))
            
        except Exception as e:
            self.root.after(0, lambda: self._pdf_error_callback(str(e)))
    
    def _pdf_loaded_callback(self, pdf_path, text):
        """Callback when PDF is successfully loaded"""
        self.extracted_text = text
        self.current_pdf_path = pdf_path
        
        # Update UI
        self.display_text.delete(1.0, tk.END)
        self.display_text.insert(tk.END, text)
        
        filename = os.path.basename(pdf_path)
        self.file_label.config(text=f"Loaded: {filename}")
        
        # Add to recent files
        self.add_recent_file(pdf_path)
        
        self.progress.stop()
        self.progress.grid_remove()
        self.status_var.set(f"Loaded {len(text)} characters from {filename}")
    
    def _pdf_error_callback(self, error_msg):
        """Callback when PDF loading fails"""
        self.progress.stop()
        self.progress.grid_remove()
        self.status_var.set("Error loading PDF")
        messagebox.showerror("Error", error_msg)
    
    def search_text(self):
        """Enhanced search with multiple results"""
        query = self.search_var.get().strip()
        if not query or not self.extracted_text:
            return
        
        # Clear previous highlights
        self.display_text.tag_remove('highlight', '1.0', tk.END)
        self.display_text.tag_remove('current_highlight', '1.0', tk.END)
        
        # Find all occurrences (case-insensitive)
        self.search_results = []
        text_lower = self.extracted_text.lower()
        query_lower = query.lower()
        
        start = 0
        while True:
            pos = text_lower.find(query_lower, start)
            if pos == -1:
                break
            self.search_results.append(pos)
            start = pos + 1
        
        if self.search_results:
            self.current_search_index = 0
            self.highlight_search_results(query)
            self.show_current_result()
            self.search_info.config(text=f"Found {len(self.search_results)} matches")
        else:
            self.search_info.config(text="No matches found")
    
    def highlight_search_results(self, query):
        """Highlight all search results"""
        for pos in self.search_results:
            start_idx = f"1.0+{pos}c"
            end_idx = f"1.0+{pos + len(query)}c"
            self.display_text.tag_add('highlight', start_idx, end_idx)
    
    def show_current_result(self):
        """Show current search result"""
        if not self.search_results:
            return
        
        query = self.search_var.get()
        pos = self.search_results[self.current_search_index]
        
        # Remove previous current highlight
        self.display_text.tag_remove('current_highlight', '1.0', tk.END)
        
        # Add current highlight
        start_idx = f"1.0+{pos}c"
        end_idx = f"1.0+{pos + len(query)}c"
        self.display_text.tag_add('current_highlight', start_idx, end_idx)
        
        # Scroll to current result
        self.display_text.see(start_idx)
        
        # Update info
        self.search_info.config(text=f"Match {self.current_search_index + 1} of {len(self.search_results)}")
    
    def find_next(self):
        """Find next search result"""
        if self.search_results:
            self.current_search_index = (self.current_search_index + 1) % len(self.search_results)
            self.show_current_result()
    
    def clear_search(self):
        """Clear search results"""
        self.search_var.set("")
        self.display_text.tag_remove('highlight', '1.0', tk.END)
        self.display_text.tag_remove('current_highlight', '1.0', tk.END)
        self.search_results = []
        self.search_info.config(text="")
    
    def focus_search(self):
        """Focus on search entry"""
        self.search_entry.focus_set()
        self.search_entry.select_range(0, tk.END)
    
    def update_speech_rate(self, value):
        """Update TTS speech rate"""
        rate = int(float(value))
        self.speed_label.config(text=str(rate))
        if self.tts_engine:
            self.tts_engine.setProperty('rate', rate)
    
    def read_pdf_aloud(self):
        """Read entire PDF content aloud"""
        if not self.extracted_text:
            messagebox.showwarning("Warning", "No text available to read.")
            return
        
        if self.is_reading:
            self.stop_reading()
            return
        
        self.is_reading = True
        self.status_var.set("Reading aloud...")
        threading.Thread(target=self._speak_text, args=(self.extracted_text,), daemon=True).start()
    
    def read_selection(self):
        """Read selected text aloud"""
        try:
            selected_text = self.display_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            if selected_text.strip():
                if self.is_reading:
                    self.stop_reading()
                
                self.is_reading = True
                self.status_var.set("Reading selection...")
                threading.Thread(target=self._speak_text, args=(selected_text,), daemon=True).start()
            else:
                messagebox.showinfo("Info", "Please select some text to read.")
        except tk.TclError:
            messagebox.showinfo("Info", "Please select some text to read.")
    
    def _speak_text(self, text):
        """Speak text using selected TTS method"""
        try:
            if self.tts_method.get() == "gtts" and self.internet_available:
                self._speak_with_gtts(text)
            else:
                self._speak_with_pyttsx3(text)
        except Exception as e:
            print(f"TTS error: {e}")
            self.root.after(0, lambda: messagebox.showerror("TTS Error", f"Error during speech: {str(e)}"))
        finally:
            self.is_reading = False
            self.root.after(0, lambda: self.status_var.set("Ready"))

    def _speak_with_pyttsx3(self, text):
        """Speak using pyttsx3 (offline)"""
        if self.tts_engine and text:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()

    def _speak_with_gtts(self, text):
        """Speak using gTTS (online)"""
        if not text.strip():
            return
        
        try:
            # Update status
            self.root.after(0, lambda: self.status_var.set("Generating speech with gTTS..."))
            
            # Create gTTS object
            tts = gTTS(text=text, lang=self.language_var.get(), slow=False)
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            temp_file.close()
            
            # Save audio
            tts.save(temp_file.name)
            self.temp_audio_files.append(temp_file.name)
            
            # Update status
            self.root.after(0, lambda: self.status_var.set("Playing gTTS audio..."))
            
            # Play audio using pygame
            pygame.mixer.music.load(temp_file.name)
            pygame.mixer.music.play()
            
            # Wait for playback to finish
            while pygame.mixer.music.get_busy() and self.is_reading:
                pygame.time.wait(100)
                
        except Exception as e:
            raise Exception(f"gTTS error: {str(e)}")
    
    def stop_reading(self):
        """Stop text-to-speech"""
        if self.is_reading:
            if self.tts_method.get() == "gtts":
                pygame.mixer.music.stop()
            elif self.tts_engine:
                self.tts_engine.stop()
        
        self.is_reading = False
        self.status_var.set("Stopped reading")
    
    def load_recent_files(self):
        """Load recent files from settings"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                    return data.get('recent_files', [])
        except Exception:
            pass
        return []
    
    def save_recent_files(self):
        """Save recent files to settings"""
        try:
            data = {'recent_files': self.recent_files}
            with open(self.settings_file, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass
    
    def add_recent_file(self, filepath):
        """Add file to recent files list"""
        if filepath in self.recent_files:
            self.recent_files.remove(filepath)
        
        self.recent_files.insert(0, filepath)
        self.recent_files = self.recent_files[:10]  # Keep only 10 recent files
        
        self.save_recent_files()
        self.update_recent_menu()
    
    def update_recent_menu(self):
        """Update recent files menu"""
        self.recent_menu.delete(0, tk.END)
        
        for filepath in self.recent_files:
            if os.path.exists(filepath):
                filename = os.path.basename(filepath)
                self.recent_menu.add_command(
                    label=filename,
                    command=lambda f=filepath: self._load_recent_file(f)
                )
        
        if not self.recent_files:
            self.recent_menu.add_command(label="No recent files", state=tk.DISABLED)
    
    def _load_recent_file(self, filepath):
        """Load a recent file"""
        if os.path.exists(filepath):
            self.progress.grid()
            self.progress.start()
            self.status_var.set("Loading PDF...")
            threading.Thread(target=self._load_pdf_thread, args=(filepath,), daemon=True).start()
        else:
            messagebox.showerror("Error", f"File not found: {filepath}")
            self.recent_files.remove(filepath)
            self.save_recent_files()
            self.update_recent_menu()

    def refresh_internet_status(self):
        """Refresh internet connectivity status"""
        threading.Thread(target=self._check_internet_thread, daemon=True).start()

    def _check_internet_thread(self):
        """Check internet in background thread"""
        try:
            requests.get("https://www.google.com", timeout=3)
            internet_available = True
        except:
            internet_available = False
        
        self.root.after(0, lambda: self._update_internet_status(internet_available))

    def _update_internet_status(self, available):
        """Update internet status in UI"""
        self.internet_available = available
        # You could update the radio button text here if needed

def main():
    root = tk.Tk()
    app = PDFReaderApp(root)
    
    # Handle window closing
    def on_closing():
        if app.is_reading:
            app.stop_reading()
    
        # Clean up temporary audio files
        for temp_file in app.temp_audio_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
    
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
