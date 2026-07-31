#!/usr/bin/env python3
"""
Release Manifest & Checksum Generator for PC Optimizer (Phase 12)
Generates release_manifest.json and SHA256SUMS.txt containing version info, file hashes, and security metadata.
"""

import os
import sys
import json
import hashlib
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

VERSION = "2.0.1"
FILES_TO_HASH = [
    "optimizer.exe",
    "optimizer-auto.exe",
    "optimizer.py",
    "install.ps1",
    "index.html",
    "emergency_fix.ps1",
    "find_hog.ps1",
    "diag.ps1"
]

def calculate_sha256(filepath: str) -> str:
    if not os.path.exists(filepath):
        return "N/A (File not found)"
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def generate_manifest():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    artifacts = {}
    sums_lines = []

    for fname in FILES_TO_HASH:
        fpath = os.path.join(root_dir, fname)
        if os.path.exists(fpath):
            sha = calculate_sha256(fpath)
            size = os.path.getsize(fpath)
            artifacts[fname] = {
                "size_bytes": size,
                "sha256": sha
            }
            sums_lines.append(f"{sha}  {fname}")

    manifest = {
        "project": "PC Optimizer",
        "version": VERSION,
        "release_date": datetime.now().strftime("%Y-%m-%d"),
        "license": "MIT",
        "signature_status": "Unsigned (Independent Open-Source)",
        "virustotal_report": "https://www.virustotal.com/gui/file/aff8e3fea11ec763970f6055fa90cc58ef6a10f5c92baca422a6e27183a82c9f",
        "security_notes": "Static ML heuristic flags (e.g. Wacatac.B!ml) are common false positives for unsigned PyInstaller single-file executables that request admin privileges. Source code is published on GitHub for complete auditability.",
        "artifacts": artifacts
    }

    manifest_path = os.path.join(root_dir, "release_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    sums_path = os.path.join(root_dir, "SHA256SUMS.txt")
    with open(sums_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sums_lines) + "\n")

    print(f"[OK] Release manifest generated successfully: {manifest_path}")
    print(f"[OK] SHA256SUMS.txt generated successfully: {sums_path}")

if __name__ == "__main__":
    generate_manifest()
