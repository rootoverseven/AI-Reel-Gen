import numpy as np
from moviepy.editor import VideoFileClip, concatenate_videoclips
import librosa
import soundfile as sf
import os

def detect_silence(audio_data, sr, threshold=0.01, min_silence_len=0.4):
    """
    Detect silent intervals in audio.
    Returns list of (start, end) times for non-silent segments.
    """
    # Normalize audio
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

def trim_video_gaps(input_path, output_path, max_gap=0.4, silence_threshold=0.01):
    """
    Trim video to ensure audio gaps are no longer than max_gap seconds.
    """
    # Load video
    video = VideoFileClip(input_path)
    audio_path = "temp_audio.wav"
    
    # Extract audio
    video.audio.write_audiofile(audio_path)
    
    # Load audio for analysis
    audio_data, sr = librosa.load(audio_path, sr=None)
    
    # Detect non-silent segments
    segments = detect_silence(audio_data, sr, threshold=silence_threshold, min_silence_len=max_gap)
    
    if not segments:
        print("No non-silent segments detected.")
        video.close()
        os.remove(audio_path)
        return
    
    # Create video clips for non-silent segments
    clips = []
    prev_end = segments[0][1]
    clips.append(video.subclip(0, prev_end))
    
    for i, (start, end) in enumerate(segments[1:], 1):
        gap = start - prev_end
        if gap > max_gap:
            # Trim gap to max_gap
            new_start = prev_end + max_gap
            clips.append(video.subclip(new_start, end))
        else:
            clips.append(video.subclip(start, end))
        prev_end = end
    
    # Concatenate clips
    final_video = concatenate_videoclips(clips, method="compose")
    
    # Write output
    final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")
    
    # Clean up
    video.close()
    final_video.close()
    os.remove(audio_path)

if __name__ == "__main__":
    input_video = "input_video.mp4"  # Replace with your input video path
    output_video = "output_video.mp4"  # Output video path
    trim_video_gaps(input_video, output_video, max_gap=0.4, silence_threshold=0.01)