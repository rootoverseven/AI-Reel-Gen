from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import core_engine as ce
import os
import uvicorn

app = FastAPI(title="AI Reel Gen API")

class ScriptRequest(BaseModel):
    topic: str = "APIs"

class Dialog(BaseModel):
    speaker: str
    text: str

class GenerateRequest(BaseModel):
    script: str
    savita_voice_id: str
    suraj_voice_id: str
    savita_img: Optional[str] = "savita.png"
    suraj_img: Optional[str] = "suraj.png"

@app.get("/")
def read_root():
    return {"message": "Welcome to AI Reel Gen API"}

@app.post("/generate-script")
def api_generate_script(request: ScriptRequest):
    # In a real app, this would call an LLM (Gemini/OpenAI)
    # For now, it returns the mock script from core_engine
    script_content = ce.generate_script(request.topic)
    return {"script": script_content}

@app.get("/voices")
def api_get_voices():
    voices = ce.get_available_voices()
    return [{"name": name, "id": vid} for name, vid in voices]

@app.post("/generate-video")
def api_generate_video(request: GenerateRequest):
    try:
        # 1. Parse Dialogues
        dialogues = ce.parse_dialogues(request.script)
        if not dialogues:
            raise HTTPException(status_code=400, detail="Invalid script format")

        # 2. Map Voices
        voice_map = {
            "Savita": request.savita_voice_id,
            "Suraj": request.suraj_voice_id
        }

        # 3. Generate Audio
        # We use a unique job ID folder to avoid collisions in a real server?
        # For MVP, we stick to 'audio' folder but maybe clean it?
        # Ideally, use temp dirs. sticking to 'audio' for now.
        audio_files = ce.generate_audio(dialogues, voice_map)
        
        # 4. Arrange Audio
        final_audio, duration = ce.arrange_audio(audio_files)
        if not final_audio:
            raise HTTPException(status_code=500, detail="Failed to arrange audio")

        # 5. Create Video
        # Ensure images exist
        if not os.path.exists(request.savita_img):
             raise HTTPException(status_code=400, detail=f"Image not found: {request.savita_img}")
        if not os.path.exists(request.suraj_img):
             raise HTTPException(status_code=400, detail=f"Image not found: {request.suraj_img}")

        video_path = ce.create_video(
            audio_files, 
            final_audio, 
            request.savita_img, 
            request.suraj_img
        )
        
        if not video_path:
             raise HTTPException(status_code=500, detail="Video generation failed")

        return {
            "status": "success", 
            "video_path": video_path,
            "duration": duration
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
