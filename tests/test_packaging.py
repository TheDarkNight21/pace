import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_marketplace_manifest_is_valid_json_and_lists_the_plugin():
    data = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
    assert data["name"]
    assert any(p["name"] == "pace" for p in data["plugins"])


def test_plugin_manifest_is_valid_json():
    data = json.loads((ROOT / "plugins" / "pace" / ".claude-plugin" / "plugin.json").read_text())
    assert data["name"] == "pace"
    assert data["description"]


def test_setup_command_exists_and_documents_the_settings_write():
    body = (ROOT / "plugins" / "pace" / "commands" / "pace.md").read_text()
    assert "statusLine" in body
    assert "pace-setup" in body


def test_readme_states_the_manual_settings_path():
    body = (ROOT / "README.md").read_text()
    assert "statusLine" in body
    assert "refreshInterval" in body
