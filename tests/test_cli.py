import json
from pathlib import Path
from unittest.mock import patch

import openpyxl
from typer.testing import CliRunner

from anki_builder.cli import app

runner = CliRunner()


def _create_xlsx(path: Path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["word", "translation"])
    ws.append(["dog", "Hund"])
    ws.append(["cat", "Katze"])
    wb.save(path)


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ankids" in result.output.lower()


def test_ingest_command(tmp_path):
    xlsx = tmp_path / "vocab.xlsx"
    _create_xlsx(xlsx)
    out = tmp_path / "myout"
    result = runner.invoke(app, ["ingest", "--input", str(xlsx), "--lang-target", "en", "--output", str(out)])
    assert result.exit_code == 0, result.output
    assert (out / "cards.json").exists()


def test_ingest_creates_workspace_uuid_folder(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "workspace").mkdir()
    xlsx = tmp_path / "vocab.xlsx"
    _create_xlsx(xlsx)
    result = runner.invoke(app, ["ingest", "--input", str(xlsx), "--lang-target", "en"])
    assert result.exit_code == 0, result.output
    workspace_dirs = list((tmp_path / "workspace").iterdir())
    assert len(workspace_dirs) == 1
    assert (workspace_dirs[0] / "cards.json").exists()


@patch("anki_builder.cli.enrich_cards")
def test_enrich_command(mock_enrich, tmp_path):
    mock_enrich.return_value = []
    out = tmp_path / "myout"
    out.mkdir()
    (out / "cards.json").write_text("[]")
    result = runner.invoke(
        app,
        ["enrich", "--output", str(out)],
        env={"MINIMAX_API_KEY": "test-key"},
    )
    assert result.exit_code == 0, result.output


def test_export_command(tmp_path):
    out = tmp_path / "myout"
    out.mkdir()
    (out / "cards.json").write_text("[]")
    result = runner.invoke(app, ["export", "--output", str(out), "--deck", "Test"])
    assert result.exit_code == 0, result.output
    assert (out / "Test.apkg").exists()


def test_ingest_with_typing_flag(tmp_path):
    xlsx = tmp_path / "vocab.xlsx"
    _create_xlsx(xlsx)
    out = tmp_path / "myout"
    result = runner.invoke(
        app, ["ingest", "--input", str(xlsx), "--lang-target", "en", "--typing", "--output", str(out)]
    )
    assert result.exit_code == 0, result.output
    cards_data = json.loads((out / "cards.json").read_text())
    assert all(c["typing"] for c in cards_data)


def test_ingest_without_typing_flag(tmp_path):
    xlsx = tmp_path / "vocab.xlsx"
    _create_xlsx(xlsx)
    out = tmp_path / "myout"
    result = runner.invoke(
        app, ["ingest", "--input", str(xlsx), "--lang-target", "en", "--output", str(out)]
    )
    assert result.exit_code == 0, result.output
    cards_data = json.loads((out / "cards.json").read_text())
    assert not any(c["typing"] for c in cards_data)
