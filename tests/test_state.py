import json
import pytest
from studio.state import EpisodeState, Stage, GateError


def test_load_and_stage(state_file):
    st = EpisodeState.load(state_file.parent)
    assert st.stage == Stage.PROPOSED


def test_approve_topic_records_timestamp(state_file):
    st = EpisodeState.load(state_file.parent)
    st.approve("topic")
    assert "topic" in st.data["approvals"]


def test_advance_to_script_draft(state_file):
    st = EpisodeState.load(state_file.parent)
    st.set_stage(Stage.SCRIPT_DRAFT)
    reloaded = EpisodeState.load(state_file.parent)
    assert reloaded.stage == Stage.SCRIPT_DRAFT


def test_require_gate_blocks_without_approval(state_file):
    st = EpisodeState.load(state_file.parent)
    with pytest.raises(GateError, match="script"):
        st.require("script")


def test_require_gate_passes_after_approval(state_file):
    st = EpisodeState.load(state_file.parent)
    st.approve("script")
    st.require("script")  # no raise


def test_record_usage_appends(state_file):
    st = EpisodeState.load(state_file.parent)
    st.record_usage("tts", {"characters": 500})
    assert st.data["usage"][0]["stage"] == "tts"
    assert st.data["usage"][0]["characters"] == 500
