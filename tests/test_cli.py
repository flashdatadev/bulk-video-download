from bulk_video_download.cli import main


def test_offline_demo_can_run_twice(tmp_path, capsys):
    args = ["demo", "--run", str(tmp_path / "demo")]
    assert main(args) == 0
    assert main(args) == 0
    assert "OFFLINE DEMO" in capsys.readouterr().out


def test_live_run_requires_python_configuration(tmp_path):
    assert main(["status", "--run", str(tmp_path), "--config", str(tmp_path / "missing.py")]) == 1


def test_init_works_without_clone_and_never_overwrites_config(tmp_path):
    config = tmp_path / "config.py"
    assert main(["init", "--config", str(config)]) == 0
    assert 'API_KEY = "your-flashdata-api-key"' in config.read_text()
    config.write_text("# Keep my settings", encoding="utf-8")
    assert main(["init", "--config", str(config)]) == 1
    assert config.read_text() == "# Keep my settings"


def test_live_demo_rejects_placeholder_key_before_network(tmp_path):
    config = tmp_path / "config.py"
    assert main(["init", "--config", str(config)]) == 0
    assert main(["live-demo", "--config", str(config), "--run", str(tmp_path / "run")]) == 1
    assert not (tmp_path / "run").exists()
