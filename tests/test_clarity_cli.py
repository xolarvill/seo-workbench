import io
import json

from seo_workbench import cli, state


def test_cli_configure_reads_stdin_without_returning_secret(tmp_path, monkeypatch, capsys):
    state.init_state("shopify", "Store", "https://example.com", project_dir=tmp_path)
    monkeypatch.setattr("sys.stdin", io.StringIO("secret-token-123456\n"))
    assert cli.main(["--project-dir", str(tmp_path), "clarity", "configure", "--clarity-project", "abc123",
                     "--timezone", "UTC", "--token-stdin", "--skip-verify", "--json"]) == 0
    output = capsys.readouterr().out
    assert "secret-token" not in output
    assert json.loads(output)["configured"]
    assert cli.main(["--project-dir", str(tmp_path), "clarity", "disconnect", "--json"]) == 0


def test_cli_exposes_quality_and_rejects_wrong_scope(tmp_path, monkeypatch, capsys):
    from seo_workbench_tools import clarity_probe
    monkeypatch.setattr(clarity_probe, "collect", lambda *a, **k: {
        "collection_status": "partial", "reason_code": "scope_mismatch", "transport_status": "ok",
        "scope_status": "mismatch", "identity_status": "operator_declared", "capability_status": "available",
    })
    assert cli.main(["--project-dir", str(tmp_path), "clarity", "query", "--query", "Sessions", "--start", "2026-10-26", "--end", "2026-10-26", "--json"]) == 1
    response = json.loads(capsys.readouterr().out)
    assert response["transport_status"] == "ok" and response["scope_status"] == "mismatch"
