import speech_recognition as sr
from googletrans import Translator
from gtts import gTTS
import pygame
import os
import tempfile
import time

def main():
    recognizer = sr.Recognizer()
    translator = Translator()

    # Initialize pygame mixer for audio playback
    pygame.mixer.init()

    target_language = 'es' # Default to Spanish for example, can be configured

    print("Live Translator Started.")
    print("Speak into your microphone. Press Ctrl+C to stop.")

    with sr.Microphone() as source:
        # Adjust for ambient noise
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print("Listening...")

        while True:
            try:
                # Listen for speech
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)

                # Recognize speech using Google Web Speech API (free)
                text = recognizer.recognize_google(audio)
                print(f"Recognized: {text}")

                # Translate text
                translation = translator.translate(text, dest=target_language)
                print(f"Translated ({target_language}): {translation.text}")

                # Convert translated text to speech
                tts = gTTS(text=translation.text, lang=target_language)

                # Save to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                    temp_filename = fp.name
                    tts.save(temp_filename)

                # Play audio
                pygame.mixer.music.load(temp_filename)
                pygame.mixer.music.play()

                # Wait until audio finishes playing
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)

                # Cleanup temp file
                pygame.mixer.music.unload()
                os.remove(temp_filename)

            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                print("Could not understand audio.")
            except sr.RequestError as e:
                print(f"Could not request results; {e}")
            except KeyboardInterrupt:
                print("\nStopping translator.")
                break
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    main()
