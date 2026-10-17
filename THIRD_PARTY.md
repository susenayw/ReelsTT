# Third-party software and source access

The MIT license in the repository covers original ReelsTT code. It does not relicense the following components. The bundled GPL-enabled libmpv/FFmpeg and the Python wrapper are used together; recipients retain the applicable GPL/LGPL rights. ReelsTT's MIT source is compatible with those terms. No warranty is provided.

Full available license notices from the installed distributions are in `licenses/` and in `_runtime/licenses/` inside the app. They are also provided as an independent release download. Please retain these notices when redistributing. Modified compatible Qt/libmpv libraries can replace the DLLs in `_runtime/`; rebuild the Python app with `tools/build.py` if needed. There is no signature lock or prohibition on reverse engineering for debugging modifications.

| Component | License / source |
| --- | --- |
| CPython 3.14.7 | PSF and included third-party licenses; https://github.com/python/cpython/tree/v3.14.7 |
| PySide6 Essentials / Shiboken / Qt 6.12.0 | LGPL-3.0 and bundled notices; https://code.qt.io/cgit/pyside/pyside-setup.git/tag/?h=v6.12.0 ; https://download.qt.io/archive/qt/6.12/6.12.0/submodules/ |
| python-mpv 1.0.8 | LGPL-2.1-or-later; https://github.com/jaseg/python-mpv |
| libmpv, 20261017 | GPL build; https://github.com/mpv-player/mpv/tree/dde0671072 ; https://github.com/mpv-player/mpv/archive/dde0671072.tar.gz |
| FFmpeg linked into libmpv | GPL-3.0-or-later enabled; https://github.com/FFmpeg/FFmpeg/tree/2d49d0e62 ; https://github.com/FFmpeg/FFmpeg/archive/2d49d0e62.tar.gz |
| Native build and dependencies | Exact build recipe, patch files and upstream source repositories: https://github.com/shinchiro/mpv-winbuild-cmake/tree/20261017 ; local copy `licenses/native-build/` |
| Send2Trash 2.1.0 | BSD-3-Clause; https://github.com/arsenetar/send2trash |
| pywin32 312 | PSF and included notices; https://github.com/mhammond/pywin32/tree/b312 |
| psutil 7.2.2 | BSD-3-Clause; https://github.com/giampaolo/psutil |
| imageio-ffmpeg 0.6.0 | BSD-2-Clause wrapper; https://github.com/imageio/imageio-ffmpeg/tree/v0.6.0 |
| imageio's FFmpeg 7.1 executable | Separately executed GPL-enabled thumbnail tool; source/build: https://github.com/imageio/imageio-binaries/tree/master/ffmpeg ; https://ffmpeg.org/releases/ffmpeg-7.1.tar.xz |
| Velopack 1.2.161 | MIT plus third-party notices; https://github.com/velopack/velopack/tree/1.2.161 |
| PyInstaller 6.22.3 bootloader | GPL with bootloader distribution exception; https://github.com/pyinstaller/pyinstaller |

## Native provenance

`native/provenance.json` records the exact original download and SHA-256 hashes. The unmodified DLL reports mpv `v0.41.0-1200-gdde067107` and FFmpeg `N-127602-g2d49d0e62`. This is an upstream development snapshot, not a stable mpv release. Its statically linked dependencies have their own terms; source locations and build switches are in `licenses/native-build/packages/`. Upstream build logs: https://github.com/shinchiro/mpv-winbuild-cmake/actions/runs/38984269935 .

The dependency source locations above are provided alongside the binary downloads. The ReelsTT application source, modifications, build scripts and installation configuration are available under the release tag. The installer bundles Python and native libraries; it does not require a separate .NET runtime on the user's computer.
