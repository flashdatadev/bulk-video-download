# Import YouTube URLs and CSV files

Use an existing list of video links without editing every line by hand:

```bash
flashdata-bulk import video-urls.txt video-ids.txt
flashdata-bulk run video-ids.txt --run runs/collection-01
```

`import` runs locally and does not need an API key. `run` uses your private Python configuration. The importer converts links to the Bulk API's **ID-only** input format, removes duplicates in first-seen order, and reports counts. It does not submit URLs to FlashData.

## Accepted text input

One URL or 11-character video ID per line. You can mix:

```text
https://www.youtube.com/watch?v=jNQXAC9IVRw
https://youtu.be/aqz-KE-bpKQ
M7lc1UVf-VE
```

Supported paths: `watch?v=...`, `youtu.be/...`, `/shorts/...`, `/live/...`, `/embed/...`. Mobile and YouTube Music watch links are accepted too. Timestamps, share parameters and a playlist parameter on a **video** link do not change the selected video. This does not import the entire playlist.

For example, a watch link and a shortened link for the same video become one ID. Blank lines are counted and skipped. A malformed or unsupported nonblank line stops the import with its line number; no partial output is published. An existing output file is never overwritten.

## CSV with a named column

```csv
title,url
Me at the zoo,https://www.youtube.com/watch?v=jNQXAC9IVRw
Big Buck Bunny,https://youtu.be/aqz-KE-bpKQ
```

```bash
flashdata-bulk import videos.csv video-ids.txt --column url
```

Other columns are ignored. Quoted commas and multiline cells are supported. Choose the exact column header; the importer does not guess a URL column. [Sample text](../sample-data/video-urls.txt) · [Sample CSV](../sample-data/video-urls.csv)

## Python

```python
from bulk_video_download import import_urls

counts = import_urls("video-urls.txt", "video-ids.txt")
print(counts["unique"], "videos ready")
# CSV: import_urls("videos.csv", "video-ids.txt", column="url")
```

Channel and playlist-only URLs require a separate discovery step. The importer never follows redirects or downloads web pages. Use the [YouTube Data API toolkit](https://github.com/flashdatadev/youtube-data-api) for discovery. If you already have an ID file, `flashdata-bulk prepare` validates it without accepting URLs.
