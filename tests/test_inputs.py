import pytest

from bulk_video_download import prepare_ids


def test_normalizes_bom_crlf_whitespace_and_duplicates(tmp_path):
    source = tmp_path / "source.txt"
    source.write_bytes(b"\xef\xbb\xbfjNQXAC9IVRw\r\n\r\n dQw4w9WgXcQ \r\njNQXAC9IVRw\n")
    output = tmp_path / "ready.txt"
    result = prepare_ids(source, output)
    assert output.read_bytes() == b"jNQXAC9IVRw\ndQw4w9WgXcQ\n"
    assert result["unique"] == 2
    assert result["duplicates"] == result["blank"] == 1


@pytest.mark.parametrize(
    "invalid",
    [
        "https://youtu.be/jNQXAC9IVRw",
        "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        "video_id",
        '["jNQXAC9IVRw"]',
        "short",
        "abcdefghij!",
        "",
        "\n  \n",
    ],
)
def test_rejects_bad_input_without_publishing_partial_file(tmp_path, invalid):
    source, output = tmp_path / "source.txt", tmp_path / "ready.txt"
    source.write_text(invalid, encoding="utf-8")
    with pytest.raises(ValueError):
        prepare_ids(source, output)
    assert not output.exists()


def test_late_invalid_line_does_not_publish_earlier_valid_ids(tmp_path):
    source, output = tmp_path / "source.txt", tmp_path / "ready.txt"
    source.write_text("jNQXAC9IVRw\nnot-an-id", encoding="utf-8")
    with pytest.raises(ValueError, match="Line 2"):
        prepare_ids(source, output)
    assert not output.exists()


def test_does_not_overwrite_existing_file(tmp_path):
    output = tmp_path / "existing.txt"
    output.write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError):
        prepare_ids(output, output)
    assert output.read_text() == "keep"
