from bulk_video_download.cli import main


def test_offline_demo_can_run_twice(tmp_path, capsys):
    args = ["demo", "--run", str(tmp_path / "demo")]
    assert main(args) == 0
    assert main(args) == 0
    assert "OFFLINE DEMO" in capsys.readouterr().out


def test_live_run_requires_python_configuration(tmp_path):
    assert main(["status", "--run", str(tmp_path), "--config", str(tmp_path / "missing.py")]) == 1
