# ReelsTT

A native Windows video player for browsing local folders as a scrolling video feed. Built with Python, PySide6 / Qt and libmpv. No account, browser engine, telemetry or media upload.

## Install the preview

Download **SUWS.ReelsTT-win-preview-Setup.exe** from the [0.0.100 prerelease](https://github.com/susenayw/ReelsTT/releases/tag/v0.0.100).
Windows 10/11 x64 is required. The Velopack installer uses a compact progress splash, installs for the current user, and creates a Start menu shortcut. No old-style Next/Next wizard and no separate Python installation. The portable ZIP is also available.

This experimental release is **unsigned**. Windows may show an unknown-publisher warning. SHA256SUMS.txt verifies download integrity; it does not replace a digital signature.

## Use

Add a local folder with **Ctrl+O** or drag a folder onto the window. Search, sort, switch grid/list view, and save favorites. Double-click a video to enter the feed.

| Input | Action |
| --- | --- |
| Wheel / Up / Down / W / S | Previous / next video |
| Click / Space | Pause / resume |
| Left / Right | Seek five seconds |
| M / L / F | Mute / loop / favorite |
| E | Reveal file in Explorer |
| Delete | Confirm moving the original file to Recycle Bin |
| Esc / Backspace | Return to library |
| F11 | Fullscreen |
| Ctrl+R | Refresh folders |

Deletion has no permanent-delete fallback. Formats depend on the bundled codecs; DRM and corrupt files may fail.

## Memory and local data

Hardware decoding, bounded buffers, one thumbnail worker and adaptive neighbor preloading aim for **under 500 MB resident RAM**. This is a target, not a guaranteed hard limit. A five-format local verification measured 451.3 MB resident RAM (452.4 MB OS high-water); private committed memory reached 547 MB. Drivers, resolution and codecs change memory use; GPU memory is separate.

New packaged installations save preferences, thumbnails and bounded logs in `%LOCALAPPDATA%\ReelsTT`, outside versioned installation files. Existing portable copies with `data/config.json` keep that directory. Source runs use `data/`. `REELSTT_DATA_DIR` overrides the location. Updates do not delete the library settings or original media. Uninstall leaves user data for deliberate manual removal.

The app does not automatically download updates. **View releases** in Preferences opens GitHub. Install a newer Velopack setup to update.

## Develop

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe tools\bootstrap_native.py
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Build on Windows x64 with Python 3.14 and the .NET 8 runtime (build tool only):

```powershell
.\.venv\Scripts\python.exe tools\release.py
```

Outputs are in `Releases/`. Native downloads and the Velopack CLI are pinned by SHA-256. Builds do not copy personal data or overwrite a running development app. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## Licensing

Original ReelsTT source is [MIT licensed](LICENSE). The distributed player also includes GPL/LGPL components, including a GPL-enabled libmpv/FFmpeg build, so **the installer is not MIT-only**. Their terms, license texts and source locations are supplied in [THIRD_PARTY.md](THIRD_PARTY.md), `licenses/`, and the release source materials. Qt is dynamically linked; its DLLs can be replaced with compatible modified builds.
