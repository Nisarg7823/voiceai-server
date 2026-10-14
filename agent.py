from dotenv import load_dotenv
load_dotenv(".env")

import asyncio
import json
from datetime import datetime, timezone

from livekit import agents, rtc
from livekit.agents import AgentSession, Agent, function_tool
from livekit.plugins import silero, deepgram, groq, sarvam

import db
from prompts import AGENT_INSTRUCTION, COMPANY_NAME


# Shared transcript buffer — populated by speech events, read by register_complaint
_transcript_turns: list[dict] = []


@function_tool
async def register_complaint(
    complaint_number: str,
    caller_name: str,
    mobile: str,
    city: str,
    area: str,
    category: str,
    description: str,
) -> str:
    """Register a customer support ticket in the database. Call this after
    collecting all required details (name, mobile, city, vehicle model,
    registration number, category, description) and before saying the ticket
    number aloud. category must be one of: Vehicle Complaint, Service & Repair,
    Warranty, Roadside Assistance, Test Drive, Sales Inquiry, Billing, Other."""

    # Duplicate check
    duplicate = await db.check_duplicate(mobile, category)
    if duplicate:
        return (
            f"Duplicate found: complaint {duplicate['complaint_number']} was already "
            f"filed for {category} on {duplicate['timestamp']}. "
            f"Status: {duplicate['status']}."
        )

    timestamp = datetime.now(timezone.utc).isoformat()
    data = {
        "complaint_number": complaint_number,
        "caller_name": caller_name,
        "mobile": mobile,
        "city": city,
        "area": area,
        "category": category,
        "description": description,
        "timestamp": timestamp,
    }

    await db.save_complaint(data)

    # Cluster check
    count = await db.check_and_flag_cluster(area, category)
    if count >= 3:
        print(f"[CLUSTER ALERT] {count} complaints for {category} in {area}")

    # Save transcript
    if _transcript_turns:
        await db.save_transcript(complaint_number, list(_transcript_turns))

    return f"Ticket {complaint_number} registered successfully with {COMPANY_NAME} Support."


@function_tool
async def lookup_caller(mobile: str) -> str:
    """Look up a caller's history by mobile number. Call this as soon as the
    caller provides their mobile number."""
    history = await db.get_caller_history(mobile)
    if not history:
        return "New caller."
    name = history[0].get("caller_name", "")
    summary = "; ".join(
        f"{h['complaint_number']} ({h['category']}, {h['status']})"
        for h in history
    )
    return json.dumps({"name": name, "past_complaints": summary})


@function_tool
async def check_status(complaint_number: str) -> str:
    """Look up the status of a complaint by its complaint number. Call this
    when the caller asks to check their complaint status."""
    record = await db.get_complaint_status(complaint_number)
    if not record:
        return "No complaint found with that number."
    return (
        f"Complaint {record['complaint_number']} "
        f"({record['category']}, {record['area']}, {record['city']}) — "
        f"Status: {record['status']}. Filed on {record['timestamp']}."
    )

@function_tool
async def update_compaint_status(complaint_number: str, status: str) -> str:
    """Update the status of a complaint by its complaint number. Call this
    when the agent wants to update the status of a complaint. Always take user confirmation before calling this function."""
    record = await db.get_complaint_status(complaint_number)
    if not record:
        return "No complaint found with that number."
    await db.update_complaint_status(complaint_number, status)
    return (
        f"Complaint {record['complaint_number']} "
        f"({record['category']}, {record['area']}, {record['city']}) — "
        f"Status updated to: {status}."
    )


class Assistant(Agent):
    def __init__(self):
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            tools=[register_complaint, lookup_caller, check_status],
        )


async def entrypoint(ctx: agents.JobContext):
    global _transcript_turns
    _transcript_turns = []

    await db.init_db()

    session = AgentSession(
        stt=deepgram.STT(model="nova-2", language="en"),
        llm=groq.LLM(model="openai/gpt-oss-120b", temperature=0),
        tts=sarvam.TTS(
            target_language_code="en-IN",
            speaker="ritu",
            model="bulbul:v3",
            pitch=0.0,
            pace=1,
            enable_preprocessing=True,
        ),
        vad=silero.VAD.load(
            activation_threshold=0.6,
            min_speech_duration=0.12,
            min_silence_duration=0.18,
            prefix_padding_duration=0.2,
        ),
        turn_detection="vad",
        min_endpointing_delay=0.1,
        max_endpointing_delay=2.0,
        allow_interruptions=True,
    )

    # Capture transcript turns
    @session.on("user_speech_committed")
    def on_user_speech(event):
        text = getattr(event, "transcript", None) or getattr(event, "text", "")
        if text:
            _transcript_turns.append({
                "role": "caller",
                "content": text,
                "index": len(_transcript_turns),
            })

    @session.on("agent_speech_committed")
    def on_agent_speech(event):
        text = getattr(event, "transcript", None) or getattr(event, "text", "")
        if text:
            _transcript_turns.append({
                "role": "agent",
                "content": text,
                "index": len(_transcript_turns),
            })

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_options=agents.room_io.RoomOptions(
            close_on_disconnect=False,
            audio_input=agents.room_io.AudioInputOptions(),
        ),
    )

    # 🔊 FIRST AUDIO MUST BE AUDIBLE
    await session.say(
        f"Hello, thank you for calling {COMPANY_NAME} Customer Support. "
        "How may I assist you today?",
        allow_interruptions=False,
    )

    await asyncio.sleep(1)


if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(
            agent_name="VoiceAIAgentInbound",
            entrypoint_fnc=entrypoint)
    )
