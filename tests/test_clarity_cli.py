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
