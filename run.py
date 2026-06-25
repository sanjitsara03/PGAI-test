"""PGAI patient voice-bot — CLI entry point.

Usage:
  python run.py setup            # create the Retell agent (free)
  python run.py call             # place ONE test call to the PGAI line (costs money)
  python run.py call --index 2   # save as call #2
"""
import argparse
import sys
import time

from src import config, recorder, retell_client

# Phase 1 uses a single scenario to prove the voice loop works end to end.
# Phase 2 generalizes this into config/scenarios.yaml.
PHASE1_SCENARIO = {
    "id": "new_patient",
    "brief": (
        "You're a NEW patient. A few days ago you hurt your right knee playing basketball — "
        "it's swollen and sore. You want to book the soonest new-patient appointment to get it "
        "looked at. If asked, your insurance is Blue Cross Blue Shield PPO."
    ),
}


def cmd_setup(args):
    state = config.load_agent_state()
    if state.get("agent_id") and not args.force:
        print(f"Agent already exists: {state['agent_id']} (use --force to recreate)")
        return
    state = retell_client.create_agent()
    print("Created Retell LLM :", state["llm_id"])
    print("Created agent      :", state["agent_id"])
    print("Model / voice      :", state["model"], "/", state["voice_id"])


def cmd_call(args):
    state = config.load_agent_state()
    if not state.get("agent_id"):
        sys.exit("No agent yet — run `python run.py setup` first.")

    ident = config.patient_identity()
    dynamic = {
        "patient_name": ident["name"],
        "patient_dob": ident["dob"],
        "patient_phone": ident["callback_phone"],
        "scenario_brief": PHASE1_SCENARIO["brief"],
    }
    print(f"Placing call {config.FROM_NUMBER} -> {config.TARGET_NUMBER} "
          f"(scenario: {PHASE1_SCENARIO['id']})")
    call_id = retell_client.place_call(
        state["agent_id"], dynamic, metadata={"scenario": PHASE1_SCENARIO["id"]}
    )
    print("call_id:", call_id, "\nWaiting for the call to complete...")

    call = _wait_for_call(call_id)
    print("Final status:", call.get("call_status"), "| duration:",
          (call.get("duration_ms") or 0) // 1000, "s")

    tpath, rpath = recorder.save_call(call, index=args.index, scenario=PHASE1_SCENARIO["id"])
    print("Transcript:", tpath)
    print("Recording :", rpath)
    print("\n--- transcript ---")
    print(recorder.build_transcript(call) or "(no transcript captured)")


def _wait_for_call(call_id, timeout=420, interval=5):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = retell_client.get_call(call_id)
        status = last.get("call_status")
        if status == "error":
            return last
        if status == "ended" and last.get("recording_url"):
            return last
        time.sleep(interval)
    return last or retell_client.get_call(call_id)


def main():
    p = argparse.ArgumentParser(description="PGAI patient voice-bot")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("setup", help="create the Retell agent (free)")
    s.add_argument("--force", action="store_true", help="recreate even if one exists")
    s.set_defaults(func=cmd_setup)

    c = sub.add_parser("call", help="place one test call (costs money)")
    c.add_argument("--index", type=int, default=1, help="call number for file naming")
    c.set_defaults(func=cmd_call)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
