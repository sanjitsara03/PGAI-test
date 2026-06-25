"""Thin wrappers over the Retell SDK: create the patient agent, place a call, fetch it."""
from retell import Retell

from . import config

# The patient persona. Per-call specifics arrive via Retell dynamic variables ({{...}}),
# so one agent can play every scenario.
PERSONA_TEMPLATE = """You are a patient calling a medical practice's front desk to get something done. \
You are a real person on a phone call — never say or imply you are an AI, a bot, or a test.

Your identity (share details only when asked, and keep them consistent):
- Name: {{patient_name}}
- Date of birth: {{patient_dob}}
- Callback number: {{patient_phone}}

Your situation and goal for THIS call:
{{scenario_brief}}

How to sound on the phone:
- Talk like a normal person: short, natural turns; everyday wording; a little hesitation is fine.
- Actively pursue your goal and steer toward it, but react naturally to what the agent says.
- Share one thing at a time — don't dump every detail at once.
- If asked for something you haven't decided, improvise something plausible and stay consistent.
- When your goal is handled (or clearly can't be), thank them and end the call.
- Keep most replies to one or two sentences."""


def client():
    return Retell(api_key=config.RETELL_API_KEY)


def create_agent():
    """Create the Retell LLM (Claude brain) + agent (voice). Returns saved state."""
    c = client()
    llm = c.llm.create(
        model=config.BRAIN_MODEL,
        general_prompt=PERSONA_TEMPLATE,
        general_tools=[{
            "type": "end_call",
            "name": "end_call",
            "description": "End the phone call once your goal is resolved or the conversation "
                           "has naturally wrapped up.",
        }],
    )
    agent = c.agent.create(
        response_engine={"type": "retell-llm", "llm_id": llm.llm_id},
        voice_id=config.VOICE_ID,
        agent_name="PGAI Patient Simulator",
        language="en-US",
    )
    state = {
        "llm_id": llm.llm_id,
        "agent_id": agent.agent_id,
        "model": config.BRAIN_MODEL,
        "voice_id": config.VOICE_ID,
    }
    config.save_agent_state(state)
    return state


def place_call(agent_id, dynamic_vars, metadata=None):
    resp = client().call.create_phone_call(
        from_number=config.FROM_NUMBER,
        to_number=config.TARGET_NUMBER,
        override_agent_id=agent_id,
        retell_llm_dynamic_variables=dynamic_vars,
        metadata=metadata or {},
    )
    return resp.call_id


def get_call(call_id):
    call = client().call.retrieve(call_id)
    return call.model_dump() if hasattr(call, "model_dump") else dict(call)
