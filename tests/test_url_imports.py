import pytest

from bulk_video_download import import_urls, video_id_from_url
from bulk_video_download.cli import main


@pytest.mark.parametrize(
    "value",
    [
        "jNQXAC9IVRw",
        " https://www.youtube.com/watch?v=jNQXAC9IVRw&t=5 ",
        "https://youtu.be/jNQXAC9IVRw?si=share",
        "https://m.youtube.com/watch?v=jNQXAC9IVRw",
        "https://youtube.com/shorts/jNQXAC9IVRw",
        "https://www.youtube.com/live/jNQXAC9IVRw",
        "https://www.youtube.com/embed/jNQXAC9IVRw",
        "https://www.youtube-nocookie.com/embed/jNQXAC9IVRw",
        "https://music.youtube.com/watch?v=jNQXAC9IVRw&list=PL123",
    ],
)
def test_supported_video_links(value):
    assert video_id_from_url(value) == "jNQXAC9IVRw"


@pytest.mark.parametrize(
    "value",
    [
        "https://youtube.com.evil.example/watch?v=jNQXAC9IVRw",
        "https://youtube.com@evil.example/watch?v=jNQXAC9IVRw",
        "https://user:password@youtube.com/watch?v=jNQXAC9IVRw",
        "https://youtube.com:443/watch?v=jNQXAC9IVRw",
        "https://youtube.com/watch?v=jNQXAC9IVRw&v=dQw4w9WgXcQ",
        "https://youtube.com/playlist?list=PL123",
        "https://youtube.com/@channel",
        "https://youtu.be/jNQXAC9IVRw/other",
        "https://youtu.be/embed/jNQXAC9IVRw",
        "https://youtube.com/watch?v=short",
        "https://youtube.com/watch?v=jNQXAC9IVRw\nhttps://youtu.be/jNQXAC9IVRw",
        "https://www.youtube-nocookie.com/shorts/jNQXAC9IVRw",
        "file:///watch?v=jNQXAC9IVRw",
        "//youtube.com/watch?v=jNQXAC9IVRw",
        "https://youtube.com\\evil.example/watch?v=jNQXAC9IVRw",
    ],
)
def test_rejects_ambiguous_or_nonvideo_urls(value):
    with pytest.raises(ValueError):
        video_id_from_url(value)


def test_mixed_url_file_is_normalized_and_deduplicated(tmp_path):
    source, target = tmp_path / "urls.txt", tmp_path / "ids.txt"
    source.write_text(
        "\ufeffhttps://youtu.be/jNQXAC9IVRw?si=test\r\n"
        "jNQXAC9IVRw\n\nhttps://youtube.com/watch?v=aqz-KE-bpKQ\n",
        encoding="utf-8",
        newline="\n",
    )
    result = import_urls(source, target)
    assert target.read_bytes() == b"jNQXAC9IVRw\naqz-KE-bpKQ\n"
    assert result["unique"] == 2
    assert result["duplicates"] == result["blank"] == 1


def test_bad_late_url_does_not_leave_partial_import(tmp_path):
    source, target = tmp_path / "urls.txt", tmp_path / "ids.txt"
    source.write_text("jNQXAC9IVRw\nhttps://example.com/a", encoding="utf-8")
    with pytest.raises(ValueError, match="Line 2"):
        import_urls(source, target)
    assert not target.exists()


def test_csv_import_through_cli_uses_explicit_column(tmp_path):
    source, target = tmp_path / "videos.csv", tmp_path / "ids.txt"
    source.write_text(
        'title,url\n"Title, with comma",https://youtu.be/jNQXAC9IVRw\n'
        '"Multi\nline",https://youtube.com/watch?v=aqz-KE-bpKQ\n',
        encoding="utf-8",
    )
    assert main(["import", str(source), str(target), "--column", "url"]) == 0
    assert target.read_text().splitlines() == ["jNQXAC9IVRw", "aqz-KE-bpKQ"]
    assert main(["import", str(source), str(target), "--column", "url"]) == 1
    assert target.read_text().splitlines() == ["jNQXAC9IVRw", "aqz-KE-bpKQ"]


@pytest.mark.parametrize(
    "content",
    [
        "title,link\nvideo,jNQXAC9IVRw",
        "url,url\njNQXAC9IVRw,aqz-KE-bpKQ",
        "url\njNQXAC9IVRw,extra",
        'url\njNQXAC9IVRw\n"unterminated',
    ],
)
def test_invalid_csv_is_not_published(tmp_path, content):
    source, target = tmp_path / "input.csv", tmp_path / "ids.txt"
    source.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        import_urls(source, target, column="url")
    assert not target.exists()
