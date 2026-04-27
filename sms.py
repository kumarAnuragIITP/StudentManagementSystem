import tkinter as tk
from tkinter import filedialog, messagebox
from pydub import AudioSegment
from datetime import datetime
from pymongo import MongoClient
import tempfile
import os
import re

# MongoDB Setup
client = MongoClient("mongodb://localhost:27017/")
db = client["custom_voice_tts"]
collection = db["scripts"]

# === Simulated Voice Cloning ===
def clone_voice_from_sample(text, voice_sample_path, speed=1.0):
    # Load voice sample (support MP3 and WAV)
    try:
        original_audio = AudioSegment.from_file(voice_sample_path)
    except Exception as e:
        print(f"Error loading voice sample: {e}")
        return None

    # Simulate audio duration based on text
    duration = 1000 + len(text) * 25
    audio = AudioSegment.silent(duration=int(duration / speed))

    # Export to temporary WAV file (used by pydub internally)
    tmp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
    audio.export(tmp_path, format="wav")
    return tmp_path

# === GUI Setup ===
root = tk.Tk()
root.title("🗣️ Custom Voice TTS Generator")
root.geometry("800x650")

voice_sample_path = tk.StringVar()

# === Upload Voice Sample ===
def upload_sample():
    file = filedialog.askopenfilename(filetypes=[("Audio files", "*.wav *.mp3")])
    if file:
        voice_sample_path.set(file)
        messagebox.showinfo("Voice Sample Loaded", f"✔ Voice sample loaded:\n{file}")

tk.Button(root, text="🎙️ Upload Your Voice Sample (WAV or MP3)", command=upload_sample, font=("Arial", 12)).pack(pady=10)

# === Script Input ===
tk.Label(root, text="📝 Paste Script (Supports #pause, #speed=1.2, #delay=500)", font=("Arial", 11)).pack()
text_input = tk.Text(root, height=20, font=("Arial", 12), wrap="word")
text_input.pack(padx=10, pady=10, fill="both", expand=True)

# === Controls ===
tk.Label(root, text="Global Pitch:").pack()
pitch_slider = tk.Scale(root, from_=0.8, to=1.2, resolution=0.05, orient="horizontal")
pitch_slider.set(1.0)
pitch_slider.pack()

tk.Label(root, text="Global Volume (dB):").pack()
volume_slider = tk.Scale(root, from_=-20, to=10, resolution=1, orient="horizontal")
volume_slider.set(0)
volume_slider.pack()

# === Generate Audio Function ===
def generate_audio():
    script = text_input.get("1.0", "end").strip()
    if not script:
        messagebox.showerror("Error", "Please paste the script.")
        return
    if not voice_sample_path.get():
        messagebox.showerror("Error", "Please upload your voice sample.")
        return

    # Change the default file extension to .wav
    output_path = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV", "*.wav")])
    if not output_path:
        return

    pitch = pitch_slider.get()
    volume = volume_slider.get()
    current_speed = 1.0
    current_delay = 300  # milliseconds

    lines = script.splitlines()
    final_audio = AudioSegment.silent(duration=500)

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Commands
        if line.startswith("#"):
            if "#pause" in line:
                final_audio += AudioSegment.silent(duration=1000)
            if "#delay=" in line:
                match = re.search(r"#delay=(\d+)", line)
                if match:
                    current_delay = int(match.group(1))
            if "#speed=" in line:
                match = re.search(r"#speed=([\d.]+)", line)
                if match:
                    current_speed = float(match.group(1))
            continue

        try:
            cloned_path = clone_voice_from_sample(line, voice_sample_path.get(), current_speed)
            if not cloned_path:
                continue
            segment = AudioSegment.from_file(cloned_path)

            # Apply pitch change
            if pitch != 1.0:
                segment = segment._spawn(segment.raw_data, overrides={
                    "frame_rate": int(segment.frame_rate * pitch)
                }).set_frame_rate(segment.frame_rate)

            # Apply volume
            segment += volume
            final_audio += segment + AudioSegment.silent(duration=current_delay)

        except Exception as e:
            print(f"Error processing line: {line}\n{e}")

    # Save the audio as .wav instead of .mp3
    final_audio.export(output_path, format="wav")

    # Save metadata to MongoDB
    collection.insert_one({
        "script": script,
        "voice_sample_used": voice_sample_path.get(),
        "output_file": output_path,
        "timestamp": datetime.now(),
        "global_pitch": pitch,
        "global_volume": volume
    })

    messagebox.showinfo("✅ Success", f"Audio saved at:\n{output_path}")

tk.Button(root, text="🎧 Generate Audio", font=("Arial", 14), command=generate_audio).pack(pady=20)

root.mainloop()
