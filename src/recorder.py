"""Save a finished call: recording-NN.wav + transcript-NN.txt (both sides, timestamps) + manifest."""
import json
import urllib.request

from . import config

# In Retell, role "agent" = OUR Retell bot (the patient simulator we built),
# and role "user" = the party we called (PGAI's front-desk agent).
ROLE = {"agent": "PATIENT", "user": "AGENT"}


def _ts(sec):
    sec = int(sec or 0)
    return f"{sec // 60:02d}:{sec % 60:02d}"


def build_transcript(call):
    lines = []
    for utt in (call.get("transcript_object") or [])[1:]:
        role = ROLE.get(utt.get("role"), (utt.get("role") or "?").upper())
        words = utt.get("words") or []
        start = words[0]["start"] if words else 0
        content = (utt.get("content") or "").strip()[:60]
        if content:
            lines.append(f"[{_ts(start)}] {role}: {content}")
    return "\n".join(lines)


def _download(url, dest):
    with urllib.request.urlopen(url, timeout=60) as r, open(dest, "wb") as f:
        f.write(r.read())


def save_call(call, index, scenario):
    config.CALLS_DIR.mkdir(exist_ok=True)
    nn = f"{index:02d}"

    header = (
        f"Scenario: {scenario}\n"
        f"Call ID:  {call.get('call_id')}\n"
        f"Duration: {(call.get('duration_ms') or 0)}s\n"
        f"From {call.get('from_number')} -> To {call.get('to_number')}\n"
        + "-" * 60 + "\n"
    )
    transcript_path = config.CALLS_DIR / f"transcript-{nn}.txt"
    transcript_path.write_text(header + build_transcript(call) + "\n")

    rec_path = None
    url = call.get("recording_url")
    if url:
        ext = ".mp3" if ".mp3" in url.lower() else ".wav"
        rec_path = config.CALLS_DIR / f"recording-{nn}{ext}"
        if not rec_path.exists():   # skip re-download when regenerating a transcript
            _download(url, rec_path)

    _update_manifest(index, scenario, call, transcript_path, rec_path)
    return transcript_path, rec_path


def _update_manifest(index, scenario, call, transcript_path, rec_path):
    path = config.CALLS_DIR / "manifest.json"
    manifest = json.loads(path.read_text()) if path.exists() else []
    manifest = [m for m in manifest if m.get("index") != index]
    manifest.append({
        "index": index,
        "scenario": scenario,
        "call_id": call.get("call_id"),
        "duration_s": (call.get("duration_ms") or 0) // 1000,
        "call_status": call.get("call_status"),
        "transcript": transcript_path.name,
        "recording": rec_path.name if rec_path else None,
    })
    manifest.sort(key=lambda m: m["index"])
    path.write_text(json.dumps(manifest, indent=2))
