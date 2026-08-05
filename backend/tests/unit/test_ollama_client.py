import pytest
from unittest.mock import MagicMock, patch

from src.ollama_client import build_prompt, parse_report, generate_report


class TestBuildPrompt:
    def test_includes_system_directive(self):
        prompt = build_prompt({"magnitude": 4.8})
        assert "Do not invent data" in prompt
        assert "SUMMARY:" in prompt
        assert "RECOMMENDATIONS:" in prompt

    def test_only_serializes_known_telemetry_keys(self):
        prompt = build_prompt({"magnitude": 4.8, "secret_field": "leak"})
        assert "secret_field" not in prompt
        assert "magnitude" in prompt

    def test_missing_keys_omitted(self):
        prompt = build_prompt({"zone_id": 3})
        assert '"magnitude"' not in prompt
        assert '"zone_id": 3' in prompt


class TestParseReport:
    def test_parses_structured_output(self):
        raw = (
            "SUMMARY: A magnitude 4.8 event was recorded.\n"
            "RECOMMENDATIONS:\n"
            "- Drop, cover, hold on.\n"
            "- Stay away from windows.\n"
        )
        parsed = parse_report(raw, model="test-model")
        assert parsed["summary"] == "A magnitude 4.8 event was recorded."
        assert parsed["recommendations"] == ["Drop, cover, hold on.", "Stay away from windows."]
        assert parsed["model"] == "test-model"

    def test_tolerates_format_drift(self):
        raw = "Just a raw sentence."
        parsed = parse_report(raw, model="test-model")
        assert parsed["summary"] == "Just a raw sentence."


class TestGenerateReport:
    def test_success_path_forces_deterministic_options(self):
        fake_response = MagicMock()
        fake_response.raise_for_status = MagicMock()
        fake_response.json.return_value = {"response": "SUMMARY: OK\nRECOMMENDATIONS:\n- Stay safe."}

        with patch("src.ollama_client.requests.post", return_value=fake_response) as mock_post:
            with patch("src.ollama_client.OLLAMA_MODEL", "test-model"):
                result = generate_report({"magnitude": 5.0})

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs["json"]
        assert payload["options"]["temperature"] == 0.0
        assert payload["options"]["top_k"] == 1
        assert payload["stream"] is False
        assert result["summary"] == "OK"
        assert "error" not in result

    def test_failure_returns_explicit_unavailable(self):
        with patch("src.ollama_client.requests.post", side_effect=Exception("boom")):
            with patch("src.ollama_client.OLLAMA_MODEL", "test-model"):
                result = generate_report({"magnitude": 5.0})

        assert result["error"] == "boom"
        assert "unavailable" in result["summary"].lower()
        assert result["recommendations"]  # always at least one safe fallback bullet
