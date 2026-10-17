# Native playback dependency

`libmpv-2.dll` is downloaded during a build; it is not committed to Git.
Run `python tools/bootstrap_native.py` to obtain the pinned x86-64 build and
verify its archive and DLL hashes. See `provenance.json` for the upstream build.

This is a GPL-enabled MPV/FFmpeg build. The MIT license at the repository root
applies to original ReelsTT source, not to the bundled playback library.
Redistribution of the combined binary package must preserve the upstream
GPL/LGPL requirements, license texts, and corresponding source access.
