"""
CodeMate — Build Script
Packages the app as a standalone exe using PyInstaller.
Model files are copied alongside (not bundled inside).
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DIST_DIR = APP_DIR / "dist"
MODEL_SRC = APP_DIR.parent / "codemate" / "final_adapter"
MODEL_DST = DIST_DIR / "CodeMate" / "model"


def build():
    print("╔══════════════════════════════════════════╗")
    print("║        CodeMate — Build Pipeline         ║")
    print("╚══════════════════════════════════════════╝")

    # Step 1: Run PyInstaller
    print("\n🔧 Step 1: Running PyInstaller …")
    spec = APP_DIR / "build.spec"
    if not spec.exists():
        print(f"  ❌ {spec} not found — run from codemate_app/ directory")
        sys.exit(1)

    subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(spec), "--noconfirm"],
        cwd=str(APP_DIR),
        check=True,
    )
    print("  ✅ PyInstaller build complete")

    # Step 2: Copy model files
    print("\n📦 Step 2: Copying model adapter …")
    if MODEL_SRC.exists():
        if MODEL_DST.exists():
            shutil.rmtree(MODEL_DST)
        shutil.copytree(MODEL_SRC, MODEL_DST)
        print(f"  ✅ Adapter copied to {MODEL_DST}")
    else:
        print(f"  ⚠ Adapter source not found: {MODEL_SRC}")
        print("     The base model will be downloaded on first run.")

    # Step 3: Summary
    exe = DIST_DIR / "CodeMate" / "CodeMate.exe"
    print(f"\n🎉 Build complete!")
    print(f"   EXE: {exe}")
    print(f"   Model: {MODEL_DST}")
    print(f"\n   To run: {exe}")
    print(f"   Note: Base model ({MODEL_SRC.name}) is auto-downloaded on first launch.")


if __name__ == "__main__":
    build()
