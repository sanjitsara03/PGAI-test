# Architecture

## Overview

The bot is a thin Python orchestrator around a managed voice platform (Retell AI) plus two Claude
roles. `run.py` is the CLI; `src/` holds the pieces — `retell_client.py` (create the agent, place
calls, fetch results), `recorder.py` (save the recording and build the dual‑side transcript),
`judge.py` (offline bug analysis), and `config.py` (env, pinned models, paths). **One** Retell agent
plays every scenario: per‑call specifics — the patient's goal and identity — are injected as Retell
**dynamic variables** into a single persona prompt, so adding a test case is a YAML edit in `config/scenarios.yaml`, not new code.

## Key design choices and why

**Managed voice over a hand‑built pipeline.** 
Retell supplies the hardest, most reject‑prone parts — real‑time STT, endpointing/turn‑taking, barge‑in, and TTS — so we clear the voice gate with almost no glue code and no hosted webhook. Retell's built‑in LLM exposes Claude (`claude-4.6-sonnet`) as the conversational brain, so the patient is driven by Claude without us hosting an inference loop; the pre‑wired contingency, had early calls shown talk‑over or lag, was to swap **only** the live loop to a speech‑to‑speech model and keep everything else. Recording and a dual‑channel, timestamped transcript come straight from Retell's `get-call` API — exactly what the transcript deliverable needs, with no DIY audio plumbing.

**Claude Opus 4.8 for the offline judge — a two‑pass design.** 
The judge first reads each transcript independently (with that scenario's intent in context) and emits structured findings, each grounded in a verbatim agent quote and a timestamp. A second Opus pass then **de‑duplicates** those findings into distinct issues — collapsing, for example, the same identity‑verification behavior seen across eight calls into one issue with its recurrence noted, and
labelling plausibly‑intended demo behavior as such while still flagging the real‑deployment risk. This is what turns 33 raw observations into 9 high‑signal issues. Structured outputs (JSON schema) make the
judge's output directly machine‑checkable, and the rubric is prompt‑cached across transcripts. Opus is used here, not in the live loop, because the analysis is latency‑insensitive and careful bug recall is where it wins most.

**Simplicity.** No database, no server, no queue — a CLI, two YAML config files, and flat output
files. The only persistent state (the created agent's ids) lives in one generated JSON file. 