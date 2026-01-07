import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import subprocess
import json
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv
import platform
import uuid
import soundfile as sf
import numpy as np
import librosa

load_dotenv()

elevenlabs = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
print(os.getenv("ELEVENLABS_API_KEY"))
# Configuration management
def load_config():
    if os.path.exists('config.json'):
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_config(config):
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

# Audio files management


# Core functions imported from core_engine
from core_engine import (
    generate_script,
    parse_dialogues,
    get_available_voices,
    generate_audio,
    save_audio_files,
    load_audio_files,
    create_video,
    trim_audio_file,
    arrange_audio
)



# GUI Application
class ReelGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Instagram Reel Generator")
        self.config = load_config()
        self.audio_files = []
        self.voice_map = {"Savita": "IdRW0GWvYFZcsf742E1w", "Suraj": "6tc9rOFMURVIqzk0oGJW"}
        self.setup_gui()
        # Load existing audio files and update dialogue list
        try:
            saved_audio_data = load_audio_files()
            self.audio_files = saved_audio_data.get('audio_files', [])
            self.voice_map = saved_audio_data.get('voice_map', self.voice_map)
            if self.audio_files:
                self.update_dialogue_list()
        except FileNotFoundError:
            # No error message on startup; handle in generate_content
            pass

    def setup_gui(self):
        tk.Label(self.root, text="Script Input:").grid(row=0, column=0, padx=5, pady=5)
        self.script_text = tk.Text(self.root, height=10, width=50)
        self.script_text.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        self.script_text.insert(tk.END, self.config.get('script', ''))

        tk.Label(self.root, text="Or Enter Prompt:").grid(row=2, column=0, padx=5, pady=5)
        self.prompt_entry = tk.Entry(self.root, width=40)
        self.prompt_entry.grid(row=2, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Generate Script", command=self.generate_script_from_prompt).grid(row=2, column=2, padx=5, pady=5)

        tk.Label(self.root, text="Speaker 1 (Savita) Image:").grid(row=3, column=0, padx=5, pady=5)
        self.savita_img_path = tk.StringVar(value=self.config.get('savita_img', 'savita.png'))
        tk.Entry(self.root, textvariable=self.savita_img_path, width=30).grid(row=3, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Upload", command=lambda: self.upload_image('savita')).grid(row=3, column=2, padx=5, pady=5)

        tk.Label(self.root, text="Speaker 2 (Suraj) Image:").grid(row=4, column=0, padx=5, pady=5)
        self.suraj_img_path = tk.StringVar(value=self.config.get('suraj_img', 'suraj.png'))
        tk.Entry(self.root, textvariable=self.suraj_img_path, width=30).grid(row=4, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Upload", command=lambda: self.upload_image('suraj')).grid(row=4, column=2, padx=5, pady=5)

        self.voices = get_available_voices()
        voice_names = [name for name, _ in self.voices]
        
        tk.Label(self.root, text="Savita Voice:").grid(row=5, column=0, padx=5, pady=5)
        self.savita_voice = ttk.Combobox(self.root, values=voice_names)
        self.savita_voice.grid(row=5, column=1, padx=5, pady=5)
        self.savita_voice.set(self.config.get('savita_voice_name', voice_names[0]))

        tk.Label(self.root, text="Suraj Voice:").grid(row=6, column=0, padx=5, pady=5)
        self.suraj_voice = ttk.Combobox(self.root, values=voice_names)
        self.suraj_voice.grid(row=6, column=1, padx=5, pady=5)
        self.suraj_voice.set(self.config.get('suraj_voice_name', voice_names[0]))

        self.generate_audio_var = tk.BooleanVar()
        self.generate_video_var = tk.BooleanVar()
        tk.Checkbutton(self.root, text="Generate Audio", variable=self.generate_audio_var).grid(row=7, column=0, padx=5, pady=5)
        tk.Checkbutton(self.root, text="Generate Video", variable=self.generate_video_var).grid(row=7, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Generate", command=self.generate_content).grid(row=7, column=2, padx=5, pady=5)

        self.dialogue_frame = tk.Frame(self.root)
        self.dialogue_frame.grid(row=8, column=0, columnspan=3, padx=5, pady=5, sticky='ew')

    def generate_script_from_prompt(self):
        prompt = self.prompt_entry.get()
        script = generate_script(prompt)
        self.script_text.delete(1.0, tk.END)
        self.script_text.insert(tk.END, script)

    def upload_image(self, speaker):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg")])
        if path:
            if speaker == 'savita':
                self.savita_img_path.set(path)
            else:
                self.suraj_img_path.set(path)

    def generate_content(self):
        script = self.script_text.get(1.0, tk.END).strip()
        if not script:
            messagebox.showerror("Error", "Please provide a script")
            return

        # Save config
        savita_voice_id = next((vid for name, vid in self.voices if name == self.savita_voice.get()), self.voice_map["Savita"])
        suraj_voice_id = next((vid for name, vid in self.voices if name == self.suraj_voice.get()), self.voice_map["Suraj"])
        self.config = {
            'script': script,
            'savita_img': self.savita_img_path.get(),
            'suraj_img': self.suraj_img_path.get(),
            'savita_voice_name': self.savita_voice.get(),
            'suraj_voice_name': self.suraj_voice.get(),
            'savita_voice_id': savita_voice_id,
            'suraj_voice_id': suraj_voice_id
        }
        save_config(self.config)
        self.voice_map = {"Savita": savita_voice_id, "Suraj": suraj_voice_id}

        dialogues = parse_dialogues(script)
        
        # Generate audio if requested
        if self.generate_audio_var.get():
            self.audio_files = generate_audio(dialogues, self.voice_map)
            save_audio_files(self.audio_files, self.voice_map)
            self.update_dialogue_list()

        # Generate video if requested
        if self.generate_video_var.get():
            if not self.audio_files:
                try:
                    saved_audio_data = load_audio_files()
                    self.audio_files = saved_audio_data.get('audio_files', [])
                    self.voice_map = saved_audio_data.get('voice_map', self.voice_map)
                    if not self.audio_files:
                        raise FileNotFoundError("No audio files available.")
                    self.update_dialogue_list()
                except FileNotFoundError:
                    messagebox.showerror("Error", "No audio files found. Please generate audio first.")
                    return
            # Validate audio files exist on disk
            for audio in self.audio_files:
                if not os.path.exists(audio['path']):
                    messagebox.showerror("Error", f"Audio file {audio['path']} is missing. Please regenerate audio.")
                    return
            final_audio, _ = arrange_audio(self.audio_files)
            if final_audio:
                video_path = create_video(self.audio_files, final_audio, 
                                        self.savita_img_path.get(), 
                                        self.suraj_img_path.get())
                if video_path:
                    messagebox.showinfo("Success", f"Video generated: {video_path}")

    def update_dialogue_list(self):
        for widget in self.dialogue_frame.winfo_children():
            widget.destroy()
        
        for idx, audio in enumerate(self.audio_files):
            tk.Label(self.dialogue_frame, text=f"{audio['speaker']}: {audio['text'][:30]}...").grid(row=idx, column=0, padx=5, pady=2)
            tk.Button(self.dialogue_frame, text="Play", command=lambda i=idx: self.play_audio(i)).grid(row=idx, column=1, padx=5, pady=2)
            tk.Button(self.dialogue_frame, text="Refresh", command=lambda i=idx: self.regenerate_dialogue(i)).grid(row=idx, column=2, padx=5, pady=2)

    def play_audio(self, index):
        audio_path = self.audio_files[index]["path"]
        try:
            if platform.system() == "Windows":
                subprocess.run(["start", "", audio_path], shell=True, check=True)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", audio_path], check=True)
            else:  # Linux
                subprocess.run(["xdg-open", audio_path], check=True)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to play audio: {e}")

    def regenerate_dialogue(self, index):
        dialogue = self.audio_files[index]
        new_audio = generate_audio([dialogue], self.voice_map, start_idx=index)[0]
        self.audio_files[index] = new_audio
        save_audio_files(self.audio_files, self.voice_map)
        self.update_dialogue_list()

def main():
    root = tk.Tk()
    app = ReelGeneratorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()