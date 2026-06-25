"""Central config: env keys, pinned models/voice, paths, and small state helpers."""
import json
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# --- Models / voice (pinned) ---
BRAIN_MODEL = "claude-4.6-sonnet"   # Retell's id for Claude Sonnet 4.6 (live patient brain)
FALLBACK_MODEL = "claude-4.5-haiku"  # lower-latency fallback if turn-taking lags
JUDGE_MODEL = "claude-opus-4-8"     # offline bug-analysis judge (Anthropic API, Phase 6)
VOICE_ID = "11labs-Lucas"           # patient voice: male, middle-aged

# --- Numbers ---
FROM_NUMBER = os.environ.get("RETELL_FROM_NUMBER")
TARGET_NUMBER = os.environ.get("TARGET_NUMBER", "+18054398008")

# --- Keys ---
RETELL_API_KEY = os.environ.get("RETELL_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# --- Paths ---
CALLS_DIR = ROOT / "calls"
REPORTS_DIR = ROOT / "reports"
IDENTITY_FILE = ROOT / "config" / "patient_identity.yaml"
AGENT_STATE = ROOT / ".retell_agent.json"   # generated; holds llm_id + agent_id


def patient_identity():
    with open(IDENTITY_FILE) as f:
        return yaml.safe_load(f)


def load_agent_state():
    return json.loads(AGENT_STATE.read_text()) if AGENT_STATE.exists() else {}


def save_agent_state(state):
    AGENT_STATE.write_text(json.dumps(state, indent=2))
