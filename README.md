# PGAI Patient Voice Bot

An automated **"patient"** that places real outbound phone calls to Pretty Good AI's test line, holds a natural voice conversation with their AI medical front‑desk agent,
**records + transcribes both sides**, and **reports bugs / quality issues**.

## How it works (short)

- **Telephony + voice:** [Retell AI](https://retellai.com) places the outbound call and runs the
  real‑time voice loop (speech‑to‑text, turn‑taking / barge‑in, text‑to‑speech). One Retell agent
  plays every scenario.
- **Patient brain:** **Claude Sonnet 4.6** (Retell's built‑in `claude-4.6-sonnet`) drives the
  conversation from a persona prompt; per‑call specifics are injected as Retell **dynamic variables**.
- **Capture:** Retell returns a recording + a dual‑channel transcript with per‑utterance timestamps;
  we save `recording-NN.wav` + `transcript-NN.txt` (PATIENT / AGENT, `[mm:ss]`).
- **Bug analysis:** a **Claude Opus 4.8** judge reads each transcript and emits structured findings,
  then a second Opus pass **de‑duplicates** them into a tight bug report.

See [`docs/architecture.md`](docs/architecture.md) for the reasoning.

## Setup

Requires **Python 3.11+**, an **Anthropic API key**, and a **Retell** account with one phone number.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # then fill in the values (see below)
.venv/bin/python run.py setup # creates the Retell agent (Claude brain + voice)
```

Fill `.env`:
- `ANTHROPIC_API_KEY` — for the bug‑analysis judge
- `RETELL_API_KEY` — your Retell API key
- `RETELL_FROM_NUMBER` — your single caller‑ID number, E.164 (e.g. `+14155551234`)
- `TARGET_NUMBER` — preset to `+18054398008` (do not change)

Optional: edit the fake patient in `config/patient_identity.yaml` and the test cases in
`config/scenarios.yaml`.

## Run (after setup)

```bash
.venv/bin/python run.py call --scenario all   # place all 10 test calls
.venv/bin/python run.py analyze               # write reports/bug_report.md
```

Other commands:
- `run.py call --scenario <id>` — place a single call (`run.py scenarios` lists the ids)
- `run.py regen [--index N]` — rebuild transcript(s) from already‑completed calls, **free** (no new calls)
- `run.py scenarios` — list the 10 test scenarios

## Outputs

| Path | What |
|---|---|
| `calls/recording-NN.wav` | call audio (gitignored — large) |
| `calls/transcript-NN.txt` | both sides, `[mm:ss]` timestamps |
| `calls/manifest.json` | index of calls (scenario, duration, paths) |
| `reports/bug_report.md` | de‑duplicated issues (severity · call ref · timestamp · quote) |
| `reports/findings_raw.json` | raw per‑call findings |

## Notes

- Models are pinned in `src/config.py`: brain `claude-4.6-sonnet`, judge `claude-opus-4-8`.
- A full run costs roughly **$10–15** (telephony + Claude). 
