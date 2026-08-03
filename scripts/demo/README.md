# Demo video narration

`docs/media/ui-demo.mp4` has a spoken narration track generated offline with
[Piper](https://github.com/OHF-voice/piper1-gpl). The video's captions were
already burned in by the original recording tool (mirrored in
`docs/media/ui-demo.srt`), so this tooling only adds audio — it does not
touch subtitles.

## Regenerating

```
pip install -r scripts/demo/requirements.txt
python -m piper.download_voices --download-dir scripts/demo/voices en_US-lessac-medium
python scripts/demo/build_video.py
```

To change the wording, edit `SCRIPT` in [narration.py](narration.py) — each
entry's `(start, end)` must match `docs/media/ui-demo.srt` — then re-run
`build_video.py`. Each line is auto-fitted to its window: if the synthesized
speech would run past the cut, it's re-rendered slightly faster (down to a
floor so it stays natural). If the whole narration still runs longer than
the source video, the final frame is frozen for the difference so nothing
gets clipped.

`--voice <name>` switches voices (any Piper voice name); it's downloaded
into `scripts/demo/voices/` the same way as above. That directory is
gitignored — it's ~60 MB per voice and reproducible in one command.
