# Contributing

Use Python 3.14 on Windows x64. Create an isolated virtual environment and install
`requirements-dev.txt`. Fetch the pinned MPV binary with `tools/bootstrap_native.py`
before trying playback. Run `python -m unittest discover -s tests -v` before a PR.

Keep library paths, media files, settings, logs, caches, tokens, certificates, and
generated packages out of commits. Never run build commands against user media.
Tests must use temporary or explicitly generated sample files.

The original ReelsTT source is MIT licensed. Contributions must be compatible
with MIT. Preserve all third-party notices and do not label bundled third-party
components as MIT. See `THIRD_PARTY.md` and `licenses/`.

Release packaging uses PyInstaller onedir output followed by Velopack, not MSI
or a legacy wizard. Installation hooks must execute before application startup,
and persistent user data must remain outside versioned application directories.
