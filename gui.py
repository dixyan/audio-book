import PyPDF2
import pyttsx3
import tkinter as tk
from tkinter import filedialog, messagebox, Text

# Function to extract text from a PDF file
def extract_text_from_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ''
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text += page.extract_text()
        return text

# Function to convert text to speech
def text_to_speech(text):
    engine = pyttsx3.init()  # Initialize the TTS engine
    engine.setProperty('rate', 150)  # Speed of speech
    engine.setProperty('volume', 1)  # Volume level (0.0 to 1.0)

    # Speak out the text
    engine.say(text)
    engine.runAndWait()

# Function to load PDF file
def load_pdf():
    pdf_path = filedialog.askopenfilename(
        title="Select a PDF file", filetypes=[("PDF files", "*.pdf")]
    )
    if pdf_path:
        extracted_text.set(extract_text_from_pdf(pdf_path))
        display_text.delete(1.0, tk.END)
        display_text.insert(tk.END, extracted_text.get())
    else:
        messagebox.showwarning("Warning", "Please select a PDF file")

# Function to search text within the PDF
def search_text():
    query = search_entry.get()
    content = extracted_text.get()

    if query in content:
        start_idx = content.index(query)
        end_idx = start_idx + len(query)
        display_text.tag_add('highlight', f"1.0+{start_idx}c", f"1.0+{end_idx}c")
        display_text.tag_config('highlight', background='yellow', foreground='black')
    else:
        messagebox.showinfo("Result", f"'{query}' not found in the document.")

# Function to convert PDF content to speech
def read_pdf_aloud():
    content = extracted_text.get()
    if content:
        text_to_speech(content)
    else:
        messagebox.showwarning("Warning", "No text available to read.")

# Setting up the GUI
root = tk.Tk()
root.title("PDF Reader and Narrator")
root.geometry("600x500")

# Text variable to store extracted PDF content
extracted_text = tk.StringVar()

# Buttons and widgets
upload_button = tk.Button(root, text="Upload PDF", command=load_pdf)
upload_button.pack(pady=10)

search_label = tk.Label(root, text="Search in PDF:")
search_label.pack()

search_entry = tk.Entry(root, width=50)
search_entry.pack(pady=5)

search_button = tk.Button(root, text="Search", command=search_text)
search_button.pack(pady=5)

read_button = tk.Button(root, text="Read Aloud", command=read_pdf_aloud)
read_button.pack(pady=10)

# Text area to display PDF content
display_text = Text(root, height=15, width=70)
display_text.pack(pady=10)

# Run the Tkinter loop
root.mainloop()
