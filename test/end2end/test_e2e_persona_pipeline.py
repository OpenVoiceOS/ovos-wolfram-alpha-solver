"""Full-pipeline end-to-end test for ovos-wolfram-alpha-plugin using ovoscope.

Proves:
  1. An utterance flows through the real OVOS intent pipeline, hits the
     persona pipeline plugin, and produces a ``speak`` message with the
     stubbed Wolfram answer.
  2. Per-session memory is recorded: the live PersonaService accumulates
     USER + ASSISTANT turns keyed by session_id.

NO network access and NO real API key required.
``WolframAlphaRetrievalEngine.get_spoken_answer`` is monkeypatched to return a
fixed string.  This is the solver boundary the persona pipeline calls
(``RetrievalEngine.query`` -> ``get_spoken_answer``); it wraps the single
``WolframAlphaApi.spoken`` HTTP GET to api.wolframalpha.com/v1/spoken *and* the
optional translation step, so stubbing it guarantees no socket is opened
(neither Wolfram nor the translate server) while the persona, the OVOS
pipeline, and all memory logic run live.
"""
import json
import os
import tempfile
from unittest.mock import patch

import pytest

import ovoscope
import ovos_persona

from ovos_bus_client.message import Message
from ovos_bus_client.session import Session, SessionManager

from ovoscope import (
    PERSONA_PIPELINE,
    CaptureSession,
    get_minicroft,
    is_pipeline_available,
)

from ovos_wolfram_alpha_plugin import WolframAlphaRetrievalEngine

# ---------------------------------------------------------------------------
# Stub boundary: WolframAlphaRetrievalEngine.get_spoken_answer -> fixed answer.
# This is the method the persona's RetrievalEngine.query() delegates to; it
# wraps both the Wolfram HTTP call and the optional translate step, so no
# network is ever touched and no API key is needed.
# ---------------------------------------------------------------------------

STUB_ANSWER = "The speed of light in vacuum is approximately 3 times 10 to the 8 meters per second."

# Where the stub is applied (single source of truth for every test/fixture).
STUB_TARGET = "ovos_wolfram_alpha_plugin.WolframAlphaRetrievalEngine.get_spoken_answer"

PERSONA_NAME = "WolframBot"


def _make_personas_dir() -> str:
    """Write a minimal Wolfram persona JSON into a temp directory and return the path."""
    tmpdir = tempfile.mkdtemp()
    persona = {
        "name": PERSONA_NAME,
        "handlers": ["ovos-wolfram-alpha-plugin"],
        "ovos-wolfram-alpha-plugin": {
            "appid": "test-appid",
        },
    }
    with open(os.path.join(tmpdir, f"{PERSONA_NAME}.json"), "w") as fh:
        json.dump(persona, fh)
    return tmpdir


PERSONAS_PATH = _make_personas_dir()

PIPELINE_CONFIG = {
    "persona": {
        "personas_path": PERSONAS_PATH,
        "default_persona": PERSONA_NAME,
        "short-term-memory": True,
        "handle_fallback": True,
        "ignore_plugin_personas": True,
    }
}

TEST_PIPELINE = [
    "ovos-persona-pipeline-plugin-high",
    "ovos-persona-pipeline-plugin-low",
]


@pytest.fixture(scope="module")
def mc():
    """Shared MiniCroft with the Wolfram persona; the solver answer is stubbed."""
    # Patch at module level so the WolframAlphaRetrievalEngine instance created
    # by the PersonaService during MiniCroft startup already uses the stub, and
    # no socket is opened for the duration of the test module.
    with patch(STUB_TARGET, return_value=STUB_ANSWER):
        croft = get_minicroft(
            skill_ids=[],
            default_pipeline=TEST_PIPELINE,
            pipeline_config=PIPELINE_CONFIG,
        )
        yield croft
        croft.stop()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utterance_msg(utterance: str, sess: Session) -> Message:
    return Message(
        "recognizer_loop:utterance",
        {"utterances": [utterance], "lang": sess.lang},
        {"session": sess.serialize()},
    )


def _drive_utterance(croft, sess: Session, utterance: str, timeout: int = 30):
    with patch(STUB_TARGET, return_value=STUB_ANSWER):
        cap = CaptureSession(
            croft,
            eof_msgs=["ovos.utterance.handled", "ovos.utterance.cancelled"],
        )
        cap.capture(_utterance_msg(utterance, sess), timeout=timeout)
        return cap.finish()


def _get_persona_service(croft):
    return croft.intents.pipeline_plugins["ovos-persona-pipeline-plugin"]


# ---------------------------------------------------------------------------
# Test 1: speak flows through the full pipeline
# ---------------------------------------------------------------------------

class TestWolframPersonaSpeaksThroughPipeline:
    """An utterance must traverse the full OVOS intent pipeline, hit the
    persona plugin, delegate to the (stubbed) WolframAlphaRetrievalEngine,
    and produce a non-empty ``speak`` message."""

    def test_pipeline_produces_speak(self, mc):
        sess = Session(session_id="wolfram-e2e-speak")
        SessionManager.sessions[sess.session_id] = sess

        messages = _drive_utterance(mc, sess, "what is the speed of light", timeout=30)

        msg_types = [m.msg_type for m in messages]
        speak_msgs = [m for m in messages if m.msg_type == "speak"]

        assert speak_msgs, (
            f"Expected at least one 'speak' message; got msg_types: {msg_types}"
        )
        spoken = speak_msgs[0].data.get("utterance", "")
        assert spoken.strip(), (
            f"'speak' message had an empty utterance; data={speak_msgs[0].data}"
        )

    def test_speak_contains_stub_answer(self, mc):
        """The stubbed API answer must be what the persona speaks."""
        sess = Session(session_id="wolfram-e2e-stub-content")
        SessionManager.sessions[sess.session_id] = sess

        messages = _drive_utterance(mc, sess, "what is the speed of light", timeout=30)

        speak_msgs = [m for m in messages if m.msg_type == "speak"]
        assert speak_msgs, "Expected at least one 'speak' message"
        spoken_text = " ".join(
            m.data.get("utterance", "") for m in speak_msgs
        )
        assert STUB_ANSWER in spoken_text, (
            f"Stubbed answer not found in spoken text: {spoken_text!r}"
        )

    def test_different_utterance_also_speaks(self, mc):
        sess = Session(session_id="wolfram-e2e-speak-2")
        SessionManager.sessions[sess.session_id] = sess

        messages = _drive_utterance(mc, sess, "how old is the universe", timeout=30)

        for msg in messages:
            if msg.msg_type == "speak":
                assert msg.data.get("utterance", "").strip(), (
                    f"speak message has empty utterance: {msg.data}"
                )
                return

        pytest.fail(
            f"No 'speak' message found. Message types received: "
            f"{[m.msg_type for m in messages]}"
        )


# ---------------------------------------------------------------------------
# Test 2: per-session memory is recorded
# ---------------------------------------------------------------------------

class TestWolframPerSessionMemory:
    """PersonaService records USER+ASSISTANT turns per session_id.

    The live PersonaService is obtained from the MiniCroft pipeline registry
    via mc.intents.pipeline_plugins["ovos-persona-pipeline-plugin"].
    """

    def test_user_turn_recorded_in_memory(self, mc):
        svc = _get_persona_service(mc)
        sess = Session(session_id="wolfram-e2e-mem-user")
        SessionManager.sessions[sess.session_id] = sess

        persona = svc.personas.get(PERSONA_NAME)
        assert persona is not None, f"Persona '{PERSONA_NAME}' not loaded"
        assert persona.memory is not None, (
            "Persona must have short-term memory enabled"
        )

        _drive_utterance(mc, sess, "what is the boiling point of water", timeout=30)

        history = persona.memory.get_history(sess.session_id)
        contents = [m.content for m in history]
        assert any("boiling point" in c for c in contents), (
            f"User utterance not found in memory for session {sess.session_id}. "
            f"History contents: {contents}"
        )

    def test_assistant_response_recorded_in_memory(self, mc):
        from ovos_plugin_manager.templates.agents import MessageRole

        svc = _get_persona_service(mc)
        sess = Session(session_id="wolfram-e2e-mem-assistant")
        SessionManager.sessions[sess.session_id] = sess

        persona = svc.personas.get(PERSONA_NAME)
        assert persona is not None
        assert persona.memory is not None

        _drive_utterance(mc, sess, "what is pi", timeout=30)

        history = persona.memory.get_history(sess.session_id)
        roles = [m.role for m in history]
        assert MessageRole.ASSISTANT in roles, (
            f"No ASSISTANT turn recorded in memory. History roles: {roles}"
        )

    def test_unknown_session_has_empty_history(self, mc):
        svc = _get_persona_service(mc)
        persona = svc.personas.get(PERSONA_NAME)
        assert persona is not None
        assert persona.memory is not None

        # Drive a known session so the persona is active
        sess = Session(session_id="wolfram-e2e-mem-known-session")
        SessionManager.sessions[sess.session_id] = sess
        _drive_utterance(mc, sess, "hello wolfram", timeout=30)

        unknown_history = persona.memory.get_history("session-that-never-existed-wolfram")
        assert unknown_history == [], (
            f"Expected empty history for unknown session, got: {unknown_history}"
        )

    def test_same_session_accumulates_turns(self, mc):
        svc = _get_persona_service(mc)
        sess = Session(session_id="wolfram-e2e-mem-accumulate")
        SessionManager.sessions[sess.session_id] = sess

        persona = svc.personas.get(PERSONA_NAME)
        assert persona is not None
        assert persona.memory is not None
        # Reset so we count only turns from this test
        persona.memory.session2history.pop(sess.session_id, None)

        _drive_utterance(mc, sess, "what is the mass of the earth", timeout=30)
        _drive_utterance(mc, sess, "what is the mass of the moon", timeout=30)

        history = persona.memory.get_history(sess.session_id)
        assert len(history) >= 2, (
            f"Expected at least 2 history entries after two turns, got {len(history)}: "
            f"{[m.content for m in history]}"
        )
