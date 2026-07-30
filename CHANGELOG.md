# Changelog

All notable changes to the **PC Optimizer** project are documented in this file.

## [2.0.0] - 2026-07-30

### Added
- **True State Management & Ownership Tracking**: Original system settings (Power plan GUID, Visual Effects registry keys, GameDVR settings, Telemetry start mode) are captured prior to modification and restored only if `modified_by_optimizer == true`.
- **Startup Entry Disable Strategy**: Startup entries are moved to `RunDisabled` registry subkeys rather than permanently deleted.
- **Detailed Cleanup Engine Metrics**: Cleanup engine calculates dry-run estimations, measures actual reclaimed bytes, and tracks locked file / permission-denied counters.
- **Explicit User Confirmation Prompts**: Added user confirmation dialogs before executing optimization or restoration steps in GUI and CLI modes.
- **PyInstaller Build Guard**: `build.py` gracefully checks PyInstaller availability without running automatic `pip install`.
- **Verified Installer**: `install.ps1` verifies SHA256 checksums and source URLs before execution.
- **Unit Test Suite**: Added 9 comprehensive unit tests in `tests/test_optimizer.py` using mocks with 0 system mutation.
- **Release Checksum Manifest**: Added `generate_manifest.py` generating `release_manifest.json`.

### Security & Reversibility
- Protected system-critical maintenance processes (`TrustedInstaller`, `TiWorker`, `vssvc`, `WmiPrvSE`, `msiexec`) in repair scripts.
- Safeguarded WSL containers from automatic shutdown unless `-ShutdownWSL` switch is explicitly supplied.
- Honestly documented Windows SmartScreen warnings for unsigned open-source binaries.
