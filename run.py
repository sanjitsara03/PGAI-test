"""PGAI patient voice-bot — CLI entry point.

Usage:
  python run.py setup                     # create the Retell agent (free)
  python run.py scenarios                 # list the test scenarios (free)
  python run.py call --scenario new_patient   # place ONE call (costs money)
  python run.py call --scenario all           # place all 10 calls, in order
"""
import argparse
import sys
import time

from src import config, recorder, retell_client


def _dynamic_vars(scenario):
    ident = config.patient_identity()
    return {
        "patient_name": ident["name"],
        "patient_dob": ident["dob"],
        "patient_phone": ident["callback_phone"],
        "scenario_brief": scenario["brief"].strip(),
    }


def _wait_for_call(call_id, timeout=480, interval=5):
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


def _run_one(scenario, index, agent_id):
    print(f"\n=== #{index:02d} {scenario['id']} — {scenario.get('title', '')} ===")
    print(f"Placing call {config.FROM_NUMBER} -> {config.TARGET_NUMBER}")
    call_id = retell_client.place_call(
        agent_id, _dynamic_vars(scenario),
        metadata={"scenario": scenario["id"], "index": index},
    )
    print("call_id:", call_id, "— waiting for completion...")
    call = _wait_for_call(call_id)
    print("status:", call.get("call_status"),
          "| duration:", (call.get("duration_ms") or 0) // 1000, "s")
    tpath, rpath = recorder.save_call(call, index=index, scenario=scenario["id"])
    print("saved:", tpath.name, "|", rpath.name if rpath else "(no recording yet)")
    return call


def cmd_setup(args):
    state = config.load_agent_state()
    if state.get("agent_id") and not args.force:
        print(f"Agent already exists: {state['agent_id']} (use --force to recreate)")
        return
    state = retell_client.create_agent()
    print("Created Retell LLM :", state["llm_id"])
    print("Created agent      :", state["agent_id"])
    print("Model / voice      :", state["model"], "/", state["voice_id"])


def cmd_scenarios(args):
    for i, s in enumerate(config.load_scenarios(), start=1):
        print(f"{i:2d}. {s['id']:<28} {s.get('title', '')}")


def cmd_analyze(args):
    from src import judge
    judge.run_all()


def cmd_call(args):
    agent_id = config.load_agent_state().get("agent_id")
    if not agent_id:
        sys.exit("No agent yet — run `python run.py setup` first.")

    scenarios = config.load_scenarios()
    by_id = {s["id"]: (i + 1, s) for i, s in enumerate(scenarios)}

    if args.scenario is None:
        sys.exit("Specify --scenario <id> or --scenario all. Options:\n  " +
                 "\n  ".join(by_id) + "\n  all")

    if args.scenario == "all":
        for i, s in enumerate(scenarios, start=1):
            try:
                _run_one(s, i, agent_id)
            except Exception as e:  # keep the unattended batch going if one call fails
                print(f"!! scenario #{i:02d} {s['id']} failed: {e}")
            if i < len(scenarios):
                time.sleep(args.gap)
        print("\nAll scenarios complete. See calls/manifest.json")
        return

    if args.scenario not in by_id:
        sys.exit(f"Unknown scenario '{args.scenario}'. Options: {', '.join(by_id)}, all")
    idx, scenario = by_id[args.scenario]
    call = _run_one(scenario, args.index or idx, agent_id)
    print("\n--- transcript ---")
    print(recorder.build_transcript(call) or "(no transcript captured)")


def cmd_regen(args):
    """Rebuild transcript(s) from already-completed calls — free, no new calls placed."""
    import json
    manifest_path = config.CALLS_DIR / "manifest.json"
    if not manifest_path.exists():
        sys.exit("No calls/manifest.json yet — place a call first.")
    manifest = json.loads(manifest_path.read_text())
    targets = manifest if args.index is None else [m for m in manifest if m["index"] == args.index]
    if not targets:
        sys.exit(f"No call with index {args.index} in the manifest.")
    for m in targets:
        call = retell_client.get_call(m["call_id"])
        tpath, _ = recorder.save_call(call, index=m["index"], scenario=m["scenario"])
        print(f"regenerated #{m['index']:02d} {m['scenario']}: {tpath.name}")


def main():
    p = argparse.ArgumentParser(description="PGAI patient voice-bot")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("setup", help="create the Retell agent (free)")
    s.add_argument("--force", action="store_true", help="recreate even if one exists")
    s.set_defaults(func=cmd_setup)

    ls = sub.add_parser("scenarios", help="list test scenarios (free)")
    ls.set_defaults(func=cmd_scenarios)

    c = sub.add_parser("call", help="place a call (costs money)")
    c.add_argument("--scenario", default=None, help="scenario id, or 'all'")
    c.add_argument("--index", type=int, default=None, help="override file index (single only)")
    c.add_argument("--gap", type=int, default=8, help="seconds between calls in --scenario all")
    c.set_defaults(func=cmd_call)

    r = sub.add_parser("regen", help="rebuild transcript(s) from saved calls (free)")
    r.add_argument("--index", type=int, default=None, help="single call index; default all")
    r.set_defaults(func=cmd_regen)

    a = sub.add_parser("analyze", help="run the Claude Opus 4.8 bug judge over all transcripts")
    a.set_defaults(func=cmd_analyze)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
