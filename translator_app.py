import tkinter as tk
from tkinter import ttk
import threading
import speech_recognition as sr
from googletrans import Translator
from gtts import gTTS
import pygame
import os
import tempfile
import time

class TranslatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Live Translator")
        self.root.geometry("400x300")

        self.is_running = False
        self.thread = None

        self.recognizer = sr.Recognizer()
        self.translator = Translator()

        # Initialize pygame mixer for audio playback
        pygame.mixer.init()

        self.setup_gui()

    def setup_gui(self):
        # Title Label
        title_label = tk.Label(self.root, text="Live Translator", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=10)

        # Target Language Selection
        lang_frame = tk.Frame(self.root)
        lang_frame.pack(pady=10)

        tk.Label(lang_frame, text="Target Language:").pack(side=tk.LEFT, padx=5)

        self.languages = {
            'Spanish': 'es',
            'French': 'fr',
            'German': 'de',
            'Italian': 'it',
            'Hindi': 'hi',
            'Chinese (Simplified)': 'zh-cn',
            'Japanese': 'ja',
            'Korean': 'ko',
            'Russian': 'ru',
            'Arabic': 'ar'
        }

        self.lang_var = tk.StringVar(value='Spanish')
        self.lang_dropdown = ttk.Combobox(lang_frame, textvariable=self.lang_var, values=list(self.languages.keys()), state="readonly")
        self.lang_dropdown.pack(side=tk.LEFT, padx=5)

        # Start/Stop Button
        self.toggle_btn = tk.Button(self.root, text="Start Translating", command=self.toggle_translation, bg="green", fg="white", font=("Helvetica", 12))
        self.toggle_btn.pack(pady=20)

        # Status Label
        self.status_var = tk.StringVar(value="Status: Ready")
        self.status_label = tk.Label(self.root, textvariable=self.status_var, fg="blue")
        self.status_label.pack(pady=10)

    def toggle_translation(self):
        if self.is_running:
            self.stop_translation()
        else:
            self.start_translation()

    def start_translation(self):
        self.is_running = True
        self.toggle_btn.config(text="Stop Translating", bg="red")
        self.status_var.set("Status: Listening...")

        self.thread = threading.Thread(target=self.translation_loop, daemon=True)
        self.thread.start()

    def stop_translation(self):
        self.is_running = False
        self.toggle_btn.config(text="Start Translating", bg="green")
        self.status_var.set("Status: Stopped")

    def translation_loop(self):
        target_lang_code = self.languages.get(self.lang_var.get(), 'es')

        with sr.Microphone() as source:
            # Adjust for ambient noise
            self.root.after(0, self.status_var.set, "Status: Adjusting for ambient noise...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            self.root.after(0, self.status_var.set, "Status: Listening...")

            while self.is_running:
                try:
                    # Listen for speech
                    audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=10)

                    if not self.is_running:
                        break

                    self.root.after(0, self.status_var.set, "Status: Recognizing...")

                    # Recognize speech using Google Web Speech API (free)
                    text = self.recognizer.recognize_google(audio)
                    print(f"Recognized: {text}")

                    self.root.after(0, self.status_var.set, "Status: Translating...")

                    # Translate text
                    translation = self.translator.translate(text, dest=target_lang_code)
                    print(f"Translated ({target_lang_code}): {translation.text}")

                    self.root.after(0, self.status_var.set, "Status: Speaking...")

                    # Convert translated text to speech
                    tts = gTTS(text=translation.text, lang=target_lang_code)

                    # Save to a temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                        temp_filename = fp.name
                    # Save audio (we do this outside the 'with' block to avoid PermissionError on Windows)
                    tts.save(temp_filename)

                    # Play audio
                    pygame.mixer.music.load(temp_filename)
                    pygame.mixer.music.play()

                    # Wait until audio finishes playing or stop is requested
                    while pygame.mixer.music.get_busy() and self.is_running:
                        pygame.time.Clock().tick(10)

                    if not self.is_running and pygame.mixer.music.get_busy():
                        pygame.mixer.music.stop()

                    # Cleanup temp file
                    pygame.mixer.music.unload()
                    try:
                        os.remove(temp_filename)
                    except:
                        pass

                    self.root.after(0, self.status_var.set, "Status: Listening...")

                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    print("Could not understand audio.")
                except sr.RequestError as e:
                    print(f"Could not request results; {e}")
                    self.root.after(0, self.status_var.set, f"Status: Error - API Request Failed")
                    time.sleep(2)
                except Exception as e:
                    print(f"Error: {e}")
                    time.sleep(1)

def main():
    root = tk.Tk()
    app = TranslatorApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: on_closing(root, app))
    root.mainloop()

def on_closing(root, app):
    app.is_running = False
    root.destroy()

if __name__ == "__main__":
    main()
