# Security policy

## Supported releases

ReelsTT 0.0.100 is an experimental prerelease. Security fixes will be released
as new versions; older prereleases are not maintained separately.

## Report a vulnerability

Use GitHub's **Security → Report a vulnerability** for this repository:
https://github.com/susenayw/ReelsTT/security/advisories/new

Please do not post exploit media, credentials, personal folder paths, or private
logs in a public issue. Include the application version, Windows version,
reproduction steps, and the affected component. If private reporting is not
available, open a public issue containing only a request for a private contact.

## Security boundaries

- The native app plays files you select locally. It does not upload your library,
  favorites, or logs, and does not contain a telemetry service.
- Local video files are parsed by MPV/FFmpeg. Keep Windows and this application
  updated; do not assume malformed media is harmless. This release does not
  sandbox native codecs.
- Deletion requires confirmation and uses the modern Windows Recycle Bin API.
  It has no application-level permanent-delete fallback.
- Installed application data lives under `%LOCALAPPDATA%\ReelsTT`, outside the
  versioned installer files. Existing portable copies keep their `data` folder.
- Release downloads are accompanied by SHA-256 checksums. A checksum verifies
  bytes against the published manifest; it is not an Authenticode signature.
- Release binaries are currently unsigned. No signing certificates or secrets
  are stored in this repository. No administrator access is requested by default.

Dependencies are pinned, pull requests run tests and a Python dependency audit,
and Dependabot monitors Python packages and GitHub Actions. Native codec
dependencies need separate review; Python package auditing does not cover all
code inside a DLL or bundled FFmpeg executable.
