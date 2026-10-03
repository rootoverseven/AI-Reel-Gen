from pathlib import Path

import pytest

import core_engine as ce
import main

SCRIPT = "Savita: hello\nSuraj: hi there"
BASE = {"script": SCRIPT, "savita_voice_id": "v1", "suraj_voice_id": "v2"}


def post(client, **over):
    body = {**BASE, **over}
    return client.post("/generate-video", json=body)


@pytest.fixture
def stubs(monkeypatch, lib):
    captured = {}

    def gen(dialogues, voice_map, output_dir="audio", start_idx=0):
        captured["voice_map"] = voice_map
        return [
            {"path": f"{output_dir}/d{i}.mp3", "speaker": d["speaker"], "duration": 1.0, "text": d["text"]}
            for i, d in enumerate(dialogues)
        ]

    def arrange(audio_files, output_dir="audio"):
        return f"{output_dir}/final.mp3", 2.0

    def create(audio_files, final_audio, savita, suraj, output_dir="output", bg_video=None):
        captured.update(savita=savita, suraj=suraj, bg=bg_video, output_dir=output_dir)
        return str(Path(output_dir) / "reel_test.mp4")

    monkeypatch.setattr(ce, "generate_audio", gen)
    monkeypatch.setattr(ce, "arrange_audio", arrange)
    monkeypatch.setattr(ce, "create_video", create)
    return captured


BAD_BG = ["../main.py", "..\\core_engine.py", "C:\\Windows\\win.ini", "/etc/passwd", "missing.mp4", "savita.png"]


@pytest.mark.parametrize("bg", BAD_BG)
def test_bad_background(client, bg):
    # generate_audio is stubbed to raise AssertionError by the autouse fixture
    r = post(client, background=bg)
    assert r.status_code == 400
    assert r.json()["detail"] == f"Background not found in library: {bg}"


@pytest.mark.parametrize("img", ["../.env", "tech_bg.mp4"])
def test_bad_images(client, img):
    r = post(client, savita_img=img)
    assert r.status_code == 400
    assert r.json()["detail"] == f"Savita image not found in library: {img}"
    r = post(client, suraj_img=img)
    assert r.status_code == 400
    assert r.json()["detail"] == f"Suraj image not found in library: {img}"


def test_script_without_colon(client):
    r = post(client, script="no colons here")
    assert r.status_code == 400
    assert r.json()["detail"] == "Invalid script format"


@pytest.mark.parametrize("field", ["script", "savita_voice_id", "suraj_voice_id"])
@pytest.mark.parametrize("mode", ["missing", "empty"])
def test_required_fields(client, field, mode):
    body = dict(BASE)
    if mode == "missing":
        del body[field]
    else:
        body[field] = ""
    assert client.post("/generate-video", json=body).status_code == 422


def test_happy_path(client, lib, stubs):
    r = post(client)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["status"] == "success"
    assert j["video_url"] == "/output/reel_test.mp4"
    assert j["duration"] == 2.0
    assert j["video_path"].endswith("reel_test.mp4")
    assert stubs["bg"] == str((lib["bg"] / "tech_bg.mp4").resolve())
    for key, nm in (("savita", "savita.png"), ("suraj", "suraj.png")):
        p = Path(stubs[key])
        assert p.is_absolute() and p == (lib["chars"] / nm).resolve()
    assert stubs["voice_map"] == {"Savita": "v1", "Suraj": "v2"}


def test_explicit_selection(client, lib, stubs):
    (lib["bg"] / "other.mp4").write_bytes(b"x")
    (lib["chars"] / "me.png").write_bytes(b"x")
    r = post(client, background="other.mp4", savita_img="me.png", suraj_img="suraj.png")
    assert r.status_code == 200
    assert Path(stubs["bg"]).name == "other.mp4"
    assert Path(stubs["savita"]).name == "me.png"


def test_null_fields_default(client, lib, stubs):
    r = post(client, background=None, savita_img=None, suraj_img=None)
    assert r.status_code == 200
    assert Path(stubs["bg"]).name == "tech_bg.mp4"
    assert Path(stubs["savita"]).name == "savita.png"
    assert Path(stubs["suraj"]).name == "suraj.png"


def test_partial_audio_502(client, stubs, monkeypatch):
    def gen(dialogues, voice_map, output_dir="audio", start_idx=0):
        return [{"path": "x", "speaker": "Savita", "duration": 1.0, "text": "t"}]

    monkeypatch.setattr(ce, "generate_audio", gen)
    r = post(client)
    assert r.status_code == 502
    assert r.json()["detail"] == (
        "Audio generation failed for 1 of 2 lines (check voice IDs / ElevenLabs quota)."
    )


def test_arrange_failure_500(client, stubs, monkeypatch):
    monkeypatch.setattr(ce, "arrange_audio", lambda *a, **k: (None, 0))
    r = post(client)
    assert r.status_code == 500
    assert r.json()["detail"] == "Failed to arrange audio"


def test_render_failure_500(client, stubs, monkeypatch):
    monkeypatch.setattr(ce, "create_video", lambda *a, **k: None)
    r = post(client)
    assert r.status_code == 500
    assert r.json()["detail"] == "Video rendering failed (see server log)"


def test_unexpected_error_500(client, stubs, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(ce, "create_video", boom)
    r = post(client)
    assert r.status_code == 500
    assert r.json()["detail"] == "kaboom"


def test_lock_held_409(client, stubs):
    assert main._generation_lock.acquire(blocking=False)
    try:
        r = post(client)
        assert r.status_code == 409
        assert r.json()["detail"] == "Another reel is being generated. Try again when it finishes."
    finally:
        main._generation_lock.release()


def test_validation_before_lock(client):
    assert main._generation_lock.acquire(blocking=False)
    try:
        assert post(client, background="nope.mp4").status_code == 400
    finally:
        main._generation_lock.release()


def test_missing_ffmpeg_fails_before_audio(client, monkeypatch):
    monkeypatch.setattr(main, "_ffmpeg_available", lambda: False)
    r = client.post("/generate-video", json={
        "script": "Savita: hi", "savita_voice_id": "a", "suraj_voice_id": "b"})
    assert r.status_code == 500
    assert "ffmpeg" in r.json()["detail"]
