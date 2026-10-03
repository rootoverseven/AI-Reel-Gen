import io

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.datastructures import UploadFile

import main
from conftest import JPG, MP4, PNG, WEBM, WEBP


def names(resp):
    return [i["name"] for i in resp.json()]


def upload(client, kind, filename, data, field="file"):
    return client.post(f"/library/{kind}", files={field: (filename, data)})


def test_list_defaults_sorted_and_hidden(client, lib):
    (lib["chars"] / "Zed.png").write_bytes(PNG)
    (lib["chars"] / "alpha.png").write_bytes(PNG)
    (lib["chars"] / ".upload-x.part").write_bytes(b"x")
    (lib["chars"] / ".hidden.png").write_bytes(PNG)
    (lib["chars"] / "notes.txt").write_bytes(b"x")
    (lib["chars"] / "subdir.png").mkdir()
    r = client.get("/library/characters")
    assert r.status_code == 200
    assert names(r) == ["alpha.png", "savita.png", "suraj.png", "Zed.png"]
    assert r.json()[0]["url"] == "/assets/characters/alpha.png"
    r = client.get("/library/backgrounds")
    assert r.json() == [{"name": "tech_bg.mp4", "url": "/assets/backgrounds/tech_bg.mp4"}]


def test_list_empty(client, lib):
    (lib["bg"] / "tech_bg.mp4").unlink()
    assert client.get("/library/backgrounds").json() == []


def test_url_is_quoted(client, lib):
    (lib["chars"] / "a b.png").write_bytes(PNG)
    r = client.get("/library/characters")
    assert {"name": "a b.png", "url": "/assets/characters/a%20b.png"} in r.json()


def test_unknown_kind_404(client):
    assert client.get("/library/other").status_code == 404


def test_png_upload(client, lib):
    r = upload(client, "characters", "hero.png", PNG)
    assert r.status_code == 201
    assert r.json() == {"name": "hero.png", "url": "/assets/characters/hero.png"}
    assert (lib["chars"] / "hero.png").read_bytes() == PNG
    assert not list(lib["chars"].glob(".upload-*"))


def test_other_formats(client, lib):
    assert upload(client, "characters", "a.jpg", JPG).status_code == 201
    assert upload(client, "characters", "b.jpeg", JPG).status_code == 201
    assert upload(client, "characters", "c.webp", WEBP).status_code == 201
    assert upload(client, "backgrounds", "a.mov", MP4).status_code == 201
    assert upload(client, "backgrounds", "a.webm", WEBM).status_code == 201


def test_ext_lowercased(client, lib):
    r = upload(client, "characters", "x.PNG", PNG)
    assert r.status_code == 201 and r.json()["name"] == "x.png"


@pytest.mark.parametrize("fn", ["evil.exe", "x.png.exe", "noext"])
def test_bad_extension(client, fn):
    r = upload(client, "characters", fn, PNG)
    assert r.status_code == 400
    assert isinstance(r.json()["detail"], str)


def test_unsupported_message(client):
    r = upload(client, "backgrounds", "a.exe", MP4)
    assert r.json()["detail"] == "Unsupported file type '.exe'. Allowed: .mp4, .mov, .webm"


def test_content_mismatch(client, lib):
    r = upload(client, "backgrounds", "a.mp4", PNG)
    assert r.status_code == 400
    assert r.json()["detail"] == "File content does not match .mp4"
    r = upload(client, "characters", "a.png", b"hello")
    assert r.status_code == 400
    assert not list(lib["chars"].glob(".upload-*"))
    assert "a.png" not in [p.name for p in lib["chars"].iterdir()]


def test_empty_file(client):
    assert upload(client, "characters", "a.png", b"").status_code == 400


def test_missing_field(client):
    assert upload(client, "characters", "a.png", PNG, field="other").status_code == 422


def test_traversal_name(client, lib):
    r = upload(client, "characters", "../../evil name.png", PNG)
    assert r.status_code == 201
    assert r.json()["name"] == "evil_name.png"
    assert (lib["chars"] / "evil_name.png").exists()
    for p in lib["root"].rglob("*"):
        if p.is_file():
            assert lib["chars"] in p.parents or lib["bg"] in p.parents


def test_reserved_name(client):
    r = upload(client, "characters", "CON.png", PNG)
    assert r.status_code == 201 and r.json()["name"] == "file_CON.png"


def test_duplicate_names(client, lib):
    original = (lib["chars"] / "savita.png").read_bytes()
    r1 = upload(client, "characters", "savita.png", PNG + b"1")
    r2 = upload(client, "characters", "savita.png", PNG + b"2")
    assert r1.json()["name"] == "savita-1.png"
    assert r2.json()["name"] == "savita-2.png"
    assert (lib["chars"] / "savita.png").read_bytes() == original


def test_too_large_413(client, lib, monkeypatch):
    monkeypatch.setitem(main.MAX_UPLOAD_BYTES, "characters", 1024)
    before = sorted(p.name for p in lib["chars"].iterdir())
    r = upload(client, "characters", "big.png", PNG + b"\x00" * 200_000)
    assert r.status_code == 413
    assert r.json()["detail"].startswith("File too large. Maximum is")
    assert sorted(p.name for p in lib["chars"].iterdir()) == before


def test_too_large_streaming_path(client, lib, monkeypatch):
    # Within the Content-Length slack (64 KiB) so the streaming cap fires.
    monkeypatch.setitem(main.MAX_UPLOAD_BYTES, "characters", 1024)
    before = sorted(p.name for p in lib["chars"].iterdir())
    r = upload(client, "characters", "big.png", PNG + b"\x00" * 5000)
    assert r.status_code == 413
    assert r.json()["detail"].startswith("File too large. Maximum is")
    assert sorted(p.name for p in lib["chars"].iterdir()) == before


def test_too_large_message_format(client):
    r = upload(client, "backgrounds", "a.mp4", MP4)
    assert r.status_code == 201
    msg = main._too_large("backgrounds").detail
    assert msg == "File too large. Maximum is 200 MB for backgrounds."
    assert main._too_large("characters").detail == "File too large. Maximum is 15 MB for characters."


def test_save_upload_streaming_cap(lib, monkeypatch):
    monkeypatch.setitem(main.MAX_UPLOAD_BYTES, "characters", 1024)
    up = UploadFile(file=io.BytesIO(PNG + b"\x00" * 5000), filename="a.png")
    before = sorted(p.name for p in lib["chars"].iterdir())
    with pytest.raises(HTTPException) as ei:
        main.save_upload(up, "characters")
    assert ei.value.status_code == 413
    assert sorted(p.name for p in lib["chars"].iterdir()) == before


def test_save_upload_empty_filename(lib):
    up = UploadFile(file=io.BytesIO(PNG), filename="")
    with pytest.raises(HTTPException) as ei:
        main.save_upload(up, "characters")
    assert ei.value.status_code == 400


IMG = {"png", "jpg", "jpeg", "webp"}


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("a.png", "a.png"),
        ("A.PNG", "A.png"),
        ("my photo (1).jpg", "my_photo_1.jpg"),
        ("../../x.png", "x.png"),
        ("..\\..\\x.png", "x.png"),
        ("C:\\dir\\x.png", "x.png"),
        ("a\x00b.png", "ab.png"),
        ("CON.png", "file_CON.png"),
        ("con.png", "file_con.png"),
        ("LPT3.webp", "file_LPT3.webp"),
        ("...png", "upload.png"),
        (".png", "upload.png"),
        ("---.png", "upload.png"),
        ("a" * 200 + ".png", "a" * 80 + ".png"),
        ("a__b  c.png", "a_b_c.png"),
        ("-_x_-.png", "x.png"),
        ("\uff46\uff55\uff4c\uff4c.png", "full.png"),
        ("name.tar.png", "name_tar.png"),
    ],
)
def test_sanitize_filename(raw, expected):
    assert main.sanitize_filename(raw, IMG) == expected


@pytest.mark.parametrize("raw", ["noext", "x.exe", "x.png.exe", "x.", ""])
def test_sanitize_rejects(raw):
    with pytest.raises(HTTPException) as ei:
        main.sanitize_filename(raw, IMG)
    assert ei.value.status_code == 400


def test_real_static_mount():
    c = TestClient(main.app)
    assert c.get("/assets/characters/savita.png").status_code == 200
    assert c.get("/assets/..%2fmain.py").status_code == 404
    assert c.get("/output/..%2fmain.py").status_code == 404
