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

# Audio files management
def load_audio_files(base_dir="."):
    path = os.path.join(base_dir, 'audio_files.json')
    if not os.path.exists(path):
        return {"audio_files": [], "voice_map": {}}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_audio_files(audio_files, voice_map, base_dir="."):
    data = {
        "audio_files": audio_files,
        "voice_map": voice_map
    }
    path = os.path.join(base_dir, 'audio_files.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Core functions
def generate_script(prompt="APIs"):
    # This acts as a fallback or mock if no prompt is provided, 
    # but likely you'd want to hook this up to an LLM like Gemini/OpenAI in the future.
    # For now, it returns the hardcoded sample from the original script.
    return """Suraj: भाभी, अगर JavaScript एक समय में सिर्फ एक काम कर सकती है, तो सब कुछ स्मूथ कैसे चलता है?
Savita: सूरज, तुम बिना इवेंट लूप समझे कोडिंग कर रहे हो? ये ऐसे नहीं चलेगा!
Suraj: पर ये इवेंट लूप आखिर है क्या?
Savita: इसे ऐसे समझो JavaScript का एक छोटा सा वर्कर होता है एक समय पर एक काम! जब कोई बड़ा काम आता है जैसे API कॉल उसे बैकग्राउंड में भेज देते हैं छोटे काम पहले खत्म कर लेता है"""

def parse_dialogues(script):
    dialogues = []
    lines = script.split('\n')
    for line in lines:
        if line.strip() and ':' in line:
            speaker, text = line.split(':', 1)
            dialogues.append({"speaker": speaker.strip(), "text": text.strip()})
    return dialogues

def get_available_voices():
    try:
        voices = elevenlabs.voices.get_all()
        return [(voice.name, voice.voice_id) for voice in voices.voices]
    except Exception as e:
        print(f"Error fetching voices: {e}")
        return [("Savita Default", "dLOTGOs0t2iYc3SUvT9a"), ("Suraj Default", "fQfxDzO64w9yyG68IUUa")]

def detect_silence(audio_data, sr, threshold=0.01, min_silence_len=0.4):
    """
    Detect silent intervals in audio.
    Returns list of (start, end) times for non-silent segments.
    """
    # Normalize audio
    if np.max(np.abs(audio_data)) > 0:
        audio_data = audio_data / np.max(np.abs(audio_data))
    
    # Compute amplitude envelope
    frame_length = int(sr * 0.025)  # 25ms frame
    hop_length = int(sr * 0.010)    # 10ms hop
    rms = librosa.feature.rms(y=audio_data, frame_length=frame_length, hop_length=hop_length)[0]
    
    # Identify non-silent frames (above threshold)
    non_silent_frames = rms > threshold
    non_silent_times = librosa.frames_to_time(np.where(non_silent_frames)[0], sr=sr, hop_length=hop_length)
    
    if len(non_silent_times) == 0:
        return []
    
    # Group into non-silent segments
    segments = []
    start = non_silent_times[0]
    prev_time = start
    
    for t in non_silent_times[1:]:
        if t - prev_time > min_silence_len:
            segments.append((start, prev_time))
            start = t
        prev_time = t
    
    segments.append((start, prev_time))
    return segments

def trim_audio_file(audio_path, max_gap=0.4, silence_threshold=0.01):
    """
    Trim silence from audio file to reduce gaps.
    """
    try:
        # Load audio
        y, sr = librosa.load(audio_path, sr=None)
        
        # Detect non-silent segments
        segments = detect_silence(y, sr, threshold=silence_threshold, min_silence_len=max_gap)
        
        if not segments:
            print(f"No non-silent segments detected in {audio_path}")
            return

        # Concatenate non-silent segments with max_gap spacing
        new_audio = []
        prev_end = segments[0][1]
        
        # Add first segment
        start_sample = int(segments[0][0] * sr)
        end_sample = int(segments[0][1] * sr)
        new_audio.append(y[start_sample:end_sample])
        
        for start, end in segments[1:]:
            gap = start - prev_end
            if gap > max_gap:
                # Add silence of max_gap duration
                silence_samples = int(max_gap * sr)
                new_audio.append(np.zeros(silence_samples))
                
                # Add next segment
                start_sample = int(start * sr)
                end_sample = int(end * sr)
                new_audio.append(y[start_sample:end_sample])
            else:
                 # Simplified logic: always insert gap to maintain rhythm but keep short pauses short
                actual_gap_samples = int((start - prev_end) * sr)
                new_audio.append(np.zeros(actual_gap_samples))
                
                start_sample = int(start * sr)
                end_sample = int(end * sr)
                new_audio.append(y[start_sample:end_sample])
            
            prev_end = end
            
        final_audio = np.concatenate(new_audio)
        
        # Write to temporary wav, then use ffmpeg to overwrite original mp3
        temp_wav = audio_path.replace('.mp3', '_temp.wav')
        sf.write(temp_wav, final_audio, sr)
        
        # Convert back to mp3
        subprocess.run(['ffmpeg', '-y', '-i', temp_wav, '-c:a', 'libmp3lame', '-q:a', '2', audio_path], 
                       check=True, capture_output=True)
        os.remove(temp_wav)
        print(f"Trimmed audio: {audio_path}")
        
    except Exception as e:
        print(f"Error trimming audio {audio_path}: {e}")

def get_audio_duration(audio_path):
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of',
            'default=noprint_wrappers=1:nokey=1', audio_path
        ], capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except:
        return 3.0

def generate_audio(dialogues, voice_map, output_dir="audio", start_idx=0):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    audio_files = []
    for idx, dialogue in enumerate(dialogues):
        speaker = dialogue["speaker"]
        text = dialogue["text"]
        
        # Default fallback voices if map is empty/missing key
        # Using IDs from previous script context
        default_voice = "dLOTGOs0t2iYc3SUvT9a" if speaker == "Savita" else "fQfxDzO64w9yyG68IUUa"
        voice_id = voice_map.get(speaker, voice_map.get("Savita", default_voice))
        
        try:
            audio_stream = elevenlabs.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )
            audio_path = f"{output_dir}/dialogue_{start_idx + idx}.mp3"
            with open(audio_path, "wb") as f:
                for chunk in audio_stream:
                    f.write(chunk)
            
            # Trim silence to reduce gaps
            trim_audio_file(audio_path)
            
            duration = get_audio_duration(audio_path)
            audio_files.append({
                "path": audio_path,
                "speaker": speaker,
                "duration": duration,
                "text": text
            })
        except Exception as e:
            print(f"Error generating audio for {speaker}: {e}")
    return audio_files

def arrange_audio(audio_files, output_dir="audio"):
    audio_list_file = f"{output_dir}/audio_list.txt"
    final_audio_list = [audio["path"] for audio in audio_files]
    if not final_audio_list:
        return None, 0
    with open(audio_list_file, 'w') as f:
        for audio_path in final_audio_list:
            f.write(f"file '{os.path.abspath(audio_path)}'\n")
    output_audio = f"{output_dir}/final_audio.mp3"
    total_duration = sum(audio['duration'] for audio in audio_files)
    try:
        subprocess.run([
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', audio_list_file, '-c', 'copy', output_audio
        ], check=True)
        return output_audio, total_duration
    except Exception as e:
        print(f"Error arranging audio: {e}")
        return None, total_duration

def split_text(text, words_per_segment=6):
    words = text.split()
    return [' '.join(words[i:i+words_per_segment]) for i in range(0, len(words), words_per_segment)]

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

def generate_srt(audio_files):
    srt_content = ""
    index = 1
    current_time = 0
    for audio in audio_files:
        segments = split_text(audio['text'])
        N = len(segments)
        if N > 0:
            duration_per_segment = audio['duration'] / N
            for segment in segments:
                start_time = current_time
                end_time = current_time + duration_per_segment
                srt_content += f"{index}\n{format_time(start_time)} --> {format_time(end_time)}\n{segment}\n\n"
                index += 1
                current_time = end_time
    return srt_content

def create_synced_video_with_assets(audio_files, final_audio_path, output_video, total_duration, 
                                  bg_video, savita_img, suraj_img, srt_path):
    # Dynamic path for subtitles text file in current directory
    # Use forward slashes to avoid escape hell, and only escape the colon for the filter
    current_dir = os.getcwd().replace('\\', '/')
    # FFmpeg subtitles filter syntax quirk: drive letter colon needs escaping 'C\:/path'
    
    # Ensure srt_path is absolute for FFmpeg
    srt_abs_path = os.path.abspath(srt_path).replace('\\', '/')
    escaped_srt_path = srt_abs_path.replace(':', '\\:')
    
    escaped_logo_path = "logo.png"
    
    # Background video processing with white bar and text
    filter_parts = []
    filter_parts.append(
        f'[0:v]loop=-1:size=ceil({total_duration}*30):start=0,'
        f'scale=1080:1920:force_original_aspect_ratio=decrease,'
        f'pad=1080:1920:(ow-iw)/2:(oh-ih)/2,'
        f'setpts=PTS-STARTPTS,'
        f'drawbox=y=0:color=white@1:width=1080:height=350:t=fill,'
        f'drawtext=text=\'When you realise this page teaches\':'
        f'fontcolor=black:fontsize=40:fontfile=arial.ttf:x=(w-text_w)/2:y=200,'
        f'drawtext=text=\'more than your B.Tech\':'
        f'fontcolor=black:fontsize=40:fontfile=arial.ttf:x=(w-text_w)/2:y=260[bg]'
    )
    overlay_chain = '[bg]'
    current_time = 0
    for idx, audio in enumerate(audio_files):
        start_time = current_time
        end_time = current_time + audio['duration']
        if audio['speaker'] == 'Savita':
            filter_parts.append(
                f'[1:v]scale=800:-1[scaled_savita];{overlay_chain}[scaled_savita]overlay=100:H-h-10:enable=\'between(t,{start_time:.3f},{end_time:.3f})\'[v{idx}]'
            )
        elif audio['speaker'] == 'Suraj':
            filter_parts.append(
                f'[2:v]scale=800:-1[scaled_suraj];{overlay_chain}[scaled_suraj]overlay=100:H-h-10:enable=\'between(t,{start_time:.3f},{end_time:.3f})\'[v{idx}]'
            )
        overlay_chain = f'[v{idx}]'
        current_time += audio['duration']

    # Logo overlay with position changes every 5 seconds
    logo_positions = [
        'x=10:y=360',  # Top-left (y=260 to respect top constraint)
        'x=1080-310:y=260',  # Top-right (1080 - 300 - 10, y=260)
        'x=10:y=1460',  # Bottom-left (y=1920-160-300 to respect bottom constraint)
        'x=1080-310:y=1460'  # Bottom-right (1080 - 300 - 10, y=1920-160-300)
    ]
    logo_filters = []
    for i in range(0, int(total_duration), 5):
        pos_idx = (i // 5) % len(logo_positions)
        start = i
        end = min(i + 5, total_duration)
        logo_filters.append(
            f'[3:v]scale=300:-1,format=rgba,colorchannelmixer=aa=0.5[logo{i}];'
            f'{overlay_chain}[logo{i}]overlay={logo_positions[pos_idx]}:enable=\'between(t,{start},{end})\'[vlogo{i}]'
        )
        overlay_chain = f'[vlogo{i}]'

    filter_parts.extend(logo_filters)
    filter_parts.append(
        f'{overlay_chain}subtitles=\'{escaped_srt_path}\':force_style=\'FontName=Arial,Fontsize=14,PrimaryColour=&Hffffff,BackColour=&H000000@0.7,BorderStyle=1,MarginV=170\'[out]'
    )
    filter_complex = ';'.join(filter_parts)
    cmd = [
        'ffmpeg', '-y', '-i', bg_video, '-i', savita_img, '-i', suraj_img, '-i', escaped_logo_path.replace('\\\\', '\\'), '-i', final_audio_path,
        '-filter_complex', filter_complex, '-map', '[out]', '-map', '4:a', '-c:v', 'libx264', '-c:a', 'aac',
        '-t', str(total_duration), '-r', '30', '-b:v', '2M', output_video
    ]
    try:
        # Check if logo file exists
        logo_file = escaped_logo_path.replace('\\\\', '\\')
        if not os.path.exists(logo_file):
            raise FileNotFoundError(f"Logo file not found at {logo_file}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"FFmpeg output: {result.stdout}")
        return output_video
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e.stderr}")
        print(f"Error creating video: {e}")
        return None
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return None

def create_video(audio_files, final_audio_path, savita_img, suraj_img, output_dir="output"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    output_video = f"{output_dir}/reel_{uuid.uuid4()}.mp4"
    srt_content = generate_srt(audio_files)
    srt_path = "subtitles.srt"
    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write(srt_content)
    total_duration = sum(audio['duration'] for audio in audio_files)
    return create_synced_video_with_assets(audio_files, final_audio_path, output_video, total_duration, 
                                         "tech_bg.mp4", savita_img, suraj_img, srt_path)
