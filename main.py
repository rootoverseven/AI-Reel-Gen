import logging
import os
import shutil
import threading
import unicodedata
import re
import uuid
import urllib.parse
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import core_engine as ce

logger = logging.getLogger("reeler")

app = FastAPI(title="AI Reel Gen API")

# --- Paths / library configuration -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
LIBRARY_DIRS = {
    "backgrounds": ASSETS_DIR / "backgrounds",
    "characters": ASSETS_DIR / "characters",
}
ALLOWED_EXTS = {
    "backgrounds": {"mp4", "mov", "webm"},
    "characters": {"png", "jpg", "jpeg", "webp"},
}
MAX_UPLOAD_BYTES = {
    "backgrounds": 200 * 1024 * 1024,
    "characters": 15 * 1024 * 1024,
}
OUTPUT_DIR = BASE_DIR / "output"
EXT_ORDER = ["mp4", "mov", "webm", "png", "jpg", "jpeg", "webp"]  # display order in error messages
DEFAULTS = {
    "background": "tech_bg.mp4",
    "savita_img": "savita.png",
    "suraj_img": "suraj.png",
}
WINDOWS_RESERVED = (
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)

_generation_lock = threading.Lock()
_upload_lock = threading.Lock()

CHUNK_SIZE = 1024 * 1024
BODY_OVERHEAD_BYTES = 64 * 1024

for _d in (*LIBRARY_DIRS.values(), OUTPUT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


if not _ffmpeg_available():
    logger.warning("ffmpeg/ffprobe not found on PATH; video generation will fail.")


# --- Models ------------------------------------------------------------------------
class ScriptRequest(BaseModel):
    topic: str = "APIs"


class Dialog(BaseModel):
    speaker: str
    text: str


class GenerateRequest(BaseModel):
    script: str = Field(min_length=1)
    savita_voice_id: str = Field(min_length=1)
    suraj_voice_id: str = Field(min_length=1)
    background: Optional[str] = None
    savita_img: Optional[str] = None
    suraj_img: Optional[str] = None


# --- Library helpers ---------------------------------------------------------------
def _kind_dir(kind: str) -> Path:
    if kind not in LIBRARY_DIRS:
        raise HTTPException(status_code=404, detail="Unknown library")
    return LIBRARY_DIRS[kind]


def list_library(kind: str) -> list[dict]:
    directory = _kind_dir(kind)
    allowed = ALLOWED_EXTS[kind]
    names = []
    if directory.is_dir():
        for entry in directory.iterdir():
            name = entry.name
            if name.startswith("."):
                continue
            if "." not in name or name.rpartition(".")[2].lower() not in allowed:
                continue
            if not entry.is_file():
                continue
            names.append(name)
    names.sort(key=lambda n: n.casefold())
    return [
        {"name": n, "url": f"/assets/{kind}/" + urllib.parse.quote(n)} for n in names
    ]


# Maps the error label to the default file name used when a field is omitted.
DEFAULTS_BY_KIND_LABEL = {
    "Background": DEFAULTS["background"],
    "Savita image": DEFAULTS["savita_img"],
    "Suraj image": DEFAULTS["suraj_img"],
}


def resolve_library_file(kind: str, name: Optional[str], label: str) -> Path:
    name = name or DEFAULTS_BY_KIND_LABEL.get(label)
    if not name or any(c in name for c in ("/", "\\", ":", "\x00")) or name in (".", ".."):
        raise HTTPException(status_code=400, detail=f"{label} not found in library: {name}")
    known = {item["name"] for item in list_library(kind)}
    if name not in known:
        raise HTTPException(status_code=400, detail=f"{label} not found in library: {name}")
    base = LIBRARY_DIRS[kind].resolve()
    path = (LIBRARY_DIRS[kind] / name).resolve()
    if path.parent != base:
        raise HTTPException(status_code=400, detail=f"{label} not found in library: {name}")
    return path


def sanitize_filename(raw: str, allowed: set) -> str:
    name = unicodedata.normalize("NFKC", raw or "")
    name = name.replace("\x00", "")
    name = re.split(r"[\\/]", name)[-1]
    stem, dot, ext = name.rpartition(".")
    if not dot:
        raise HTTPException(status_code=400, detail="File must have an extension")
    ext = ext.lower()
    if ext not in allowed:
        allowed_list = ", ".join(
            f".{e}" for e in sorted(allowed, key=lambda e: (EXT_ORDER.index(e) if e in EXT_ORDER else 99, e))
        )
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{ext}'. Allowed: {allowed_list}",
        )
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", stem)
    stem = re.sub(r"_+", "_", stem)
    stem = stem.strip("._- ")[:80]
    if not stem:
        stem = "upload"
    if stem.upper() in WINDOWS_RESERVED:
        stem = "file_" + stem
    return f"{stem}.{ext}"


def sniff_ok(head: bytes, ext: str) -> bool:
    ext = ext.lower()
    if ext == "png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in ("jpg", "jpeg"):
        return head.startswith(b"\xff\xd8\xff")
    if ext == "webp":
        return head[0:4] == b"RIFF" and head[8:12] == b"WEBP"
    if ext in ("mp4", "mov"):
        return head[4:8] in {b"ftyp", b"moov", b"mdat", b"wide", b"free", b"skip", b"pnot"}
    if ext == "webm":
        return head.startswith(b"\x1a\x45\xdf\xa3")
    return False


def unique_path(directory: Path, name: str) -> Path:
    candidate = directory / name
    if not candidate.exists():
        return candidate
    stem, _, ext = name.rpartition(".")
    for i in range(1, 10001):
        candidate = directory / f"{stem}-{i}.{ext}"
        if not candidate.exists():
            return candidate
    raise HTTPException(status_code=409, detail="Too many files with the same name")


def _too_large(kind: str) -> HTTPException:
    mb = MAX_UPLOAD_BYTES[kind] // (1024 * 1024)
    return HTTPException(
        status_code=413, detail=f"File too large. Maximum is {mb} MB for {kind}."
    )


def save_upload(upload: UploadFile, kind: str) -> str:
    directory = _kind_dir(kind)
    if not upload.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    name = sanitize_filename(upload.filename, ALLOWED_EXTS[kind])
    ext = name.rpartition(".")[2]
    limit = MAX_UPLOAD_BYTES[kind]
    tmp = directory / f".upload-{uuid.uuid4().hex}.part"
    try:
        total = 0
        head = b""
        with open(tmp, "xb") as out:
            while True:
                chunk = upload.file.read(CHUNK_SIZE)
                if not chunk:
                    break
                if len(head) < 16:
                    head = (head + chunk)[:16]
                total += len(chunk)
                if total > limit:
                    raise _too_large(kind)
                out.write(chunk)
        if total == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        if not sniff_ok(head, ext):
            raise HTTPException(status_code=400, detail=f"File content does not match .{ext}")
        with _upload_lock:
            final = unique_path(directory, name)
            os.replace(tmp, final)
        return final.name
    finally:
        tmp.unlink(missing_ok=True)


# --- Middleware --------------------------------------------------------------------
@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    if request.method == "POST":
        for kind in LIBRARY_DIRS:
            if request.url.path.rstrip("/") == f"/library/{kind}":
                length = request.headers.get("content-length", "")
                if length.isdigit() and int(length) > MAX_UPLOAD_BYTES[kind] + BODY_OVERHEAD_BYTES:
                    exc = _too_large(kind)
                    return JSONResponse({"detail": exc.detail}, status_code=413)
    return await call_next(request)


# --- Routes ------------------------------------------------------------------------
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


@app.get("/library/backgrounds")
def api_list_backgrounds():
    return list_library("backgrounds")


@app.get("/library/characters")
def api_list_characters():
    return list_library("characters")


@app.post("/library/backgrounds", status_code=201)
def api_upload_background(file: UploadFile = File(...)):
    name = save_upload(file, "backgrounds")
    return {"name": name, "url": "/assets/backgrounds/" + urllib.parse.quote(name)}


@app.post("/library/characters", status_code=201)
def api_upload_character(file: UploadFile = File(...)):
    name = save_upload(file, "characters")
    return {"name": name, "url": "/assets/characters/" + urllib.parse.quote(name)}


@app.post("/generate-video")
def api_generate_video(request: GenerateRequest):
    # 1. Parse dialogues
    dialogues = ce.parse_dialogues(request.script)
    if not dialogues:
        raise HTTPException(status_code=400, detail="Invalid script format")

    # 2. Validate library selections (before any paid API call)
    bg_path = resolve_library_file("backgrounds", request.background or DEFAULTS["background"], "Background")
    savita_path = resolve_library_file("characters", request.savita_img or DEFAULTS["savita_img"], "Savita image")
    suraj_path = resolve_library_file("characters", request.suraj_img or DEFAULTS["suraj_img"], "Suraj image")

    # Fail before spending ElevenLabs credits on a render that cannot finish
    if not _ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg/ffprobe not found on PATH; install ffmpeg and restart the server.")

    # 3. Only one render at a time (shared audio/ working directory)
    if not _generation_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="Another reel is being generated. Try again when it finishes.",
        )
    try:
        voice_map = {
            "Savita": request.savita_voice_id,
            "Suraj": request.suraj_voice_id,
        }
        audio_dir = str(BASE_DIR / "audio")

        audio_files = ce.generate_audio(dialogues, voice_map, output_dir=audio_dir)
        if len(audio_files) < len(dialogues):
            failed = len(dialogues) - len(audio_files)
            raise HTTPException(
                status_code=502,
                detail=(
                    f"Audio generation failed for {failed} of {len(dialogues)} lines "
                    "(check voice IDs / ElevenLabs quota)."
                ),
            )

        final_audio, duration = ce.arrange_audio(audio_files, output_dir=audio_dir)
        if not final_audio:
            raise HTTPException(status_code=500, detail="Failed to arrange audio")

        video_path = ce.create_video(
            audio_files,
            final_audio,
            str(savita_path),
            str(suraj_path),
            output_dir=str(OUTPUT_DIR),
            bg_video=str(bg_path),
        )
        if not video_path:
            raise HTTPException(
                status_code=500, detail="Video rendering failed (see server log)"
            )

        video_url = "/output/" + urllib.parse.quote(Path(video_path).name)
        try:
            rel_path = Path(video_path).resolve().relative_to(BASE_DIR).as_posix()
        except ValueError:
            rel_path = str(video_path)

        return {
            "status": "success",
            "video_path": rel_path,
            "video_url": video_url,
            "duration": round(duration, 2),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _generation_lock.release()


# --- Static mounts (must come after all routes) ------------------------------------
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
