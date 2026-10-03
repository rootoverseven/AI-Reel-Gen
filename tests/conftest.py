import pytest
from fastapi.testclient import TestClient

import core_engine as ce
import main

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 64
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 32
WEBM = b"\x1a\x45\xdf\xa3" + b"\x00" * 64


@pytest.fixture(autouse=True)
def no_elevenlabs(monkeypatch):
    def boom(*a, **kw):
        raise AssertionError("ElevenLabs must not be called")

    monkeypatch.setattr(ce, "generate_audio", boom)
    monkeypatch.setattr(main, "_ffmpeg_available", lambda: True)
    yield
    assert not main._generation_lock.locked()


@pytest.fixture
def lib(tmp_path, monkeypatch):
    bg = tmp_path / "bg"
    chars = tmp_path / "chars"
    out = tmp_path / "out"
    for d in (bg, chars, out):
        d.mkdir()
    (bg / "tech_bg.mp4").write_bytes(MP4)
    (chars / "savita.png").write_bytes(PNG)
    (chars / "suraj.png").write_bytes(PNG)
    monkeypatch.setitem(main.LIBRARY_DIRS, "backgrounds", bg)
    monkeypatch.setitem(main.LIBRARY_DIRS, "characters", chars)
    monkeypatch.setattr(main, "OUTPUT_DIR", out)
    return {"root": tmp_path, "bg": bg, "chars": chars, "out": out}


@pytest.fixture
def client(lib):
    return TestClient(main.app)
