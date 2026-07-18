# Repository-local tools

Bootstrap keeps downloaded executables and managed runtimes inside this
directory. The binaries themselves are ignored; this record is tracked.

| Tool | Version | Source | Verification |
|---|---|---|---|
| uv | 0.11.15 | Official Astral standalone installer | `uv.exe` SHA-256 `d4ffe0b73cbb1fa3d11242567d55c6e9058c4e885fae9272764409583a4e8640` |
| CPython | 3.12.13 | uv-managed python-build-standalone distribution | Installed and selected explicitly by `scripts/bootstrap.ps1` |

The installer is constrained with `UV_UNMANAGED_INSTALL`, and all uv, Python,
package, model, and browser caches are redirected into this repository.
