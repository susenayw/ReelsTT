# 0.0.100 release verification

Validated on Windows 11 x64 with Python 3.14.7, PyInstaller 6.22.3 and Velopack 1.2.161.

- 15 unit tests pass, including installed data persistence across version directories, existing portable settings and explicit data-directory overrides.
- Python requirements audit reports no known vulnerabilities. This does not audit code statically embedded in native libraries.
- GitHub Windows checks pass: https://github.com/susenayw/ReelsTT/actions/runs/39032642222 .
- Frozen core/UI module bytecode matches release source.
- Final Velopack setup installs successfully, invokes the fast startup hook, and installs an executable identical to the staged build.
- Installed app opens the library, plays local H.264 video with D3D11VA and displays the prerelease version in Preferences.
- Uninstall succeeds and preserves data outside the installation directory.
- Package inspection finds no user library/configuration/log files; third-party license/source index is included.
- Release downloads include SHA-256 checksums. This release has no Authenticode signature.

Playback of portrait H.264, HEVC 10-bit, VP9 and 4K HEVC was also checked during app verification. The earlier five-format session reached 451.3 MB resident RAM, 452.4 MB OS resident high-water, and 547 MB private commit. Memory below 500 MB is a resident-memory target, not a guaranteed cap.
