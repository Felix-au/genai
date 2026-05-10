"""
CodeMate — Build Script
Packages the app as a standalone single-file EXE using PyInstaller.
All Python dependencies and libraries are bundled inside the executable.
The model (~3GB) is NOT bundled — it downloads from HuggingFace on first run.
"""

import os
import sys
import subprocess
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DIST_DIR = APP_DIR / "dist"


def build():
    print("╔══════════════════════════════════════════╗")
    print("║        CodeMate — Build Pipeline         ║")
    print("╚══════════════════════════════════════════╝")

    # Step 1: Verify PyInstaller is installed
    print("\n🔍 Step 1: Checking PyInstaller …")
    try:
        import PyInstaller
        print(f"  ✅ PyInstaller {PyInstaller.__version__} found")
    except ImportError:
        print("  ❌ PyInstaller not found. Install with: pip install pyinstaller")
        sys.exit(1)

    # Step 2: Verify spec file exists
    spec = APP_DIR / "build.spec"
    if not spec.exists():
        print(f"  ❌ {spec} not found — run from codemate_app/ directory")
        sys.exit(1)

    # Step 3: Run PyInstaller (single-file mode)
    print("\n🔧 Step 2: Building single-file EXE …")
    print("  This may take several minutes …\n")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(spec), "--noconfirm"],
        cwd=str(APP_DIR),
    )
    if result.returncode != 0:
        print("\n  ❌ PyInstaller build failed — check output above")
        sys.exit(1)

    print("\n  ✅ PyInstaller build complete")

    # Step 4: Summary
    exe = DIST_DIR / "CodeMate.exe"
    print(f"\n{'='*50}")
    print(f"  🎉 Build complete!")
    print(f"{'='*50}")
    print(f"  EXE:   {exe}")
    if exe.exists():
        size_mb = exe.stat().st_size / (1024 * 1024)
        print(f"  Size:  {size_mb:.1f} MB")
    print(f"\n  To run:")
    print(f"    {exe}")
    print(f"\n  Notes:")
    print(f"    • All Python dependencies are bundled inside the EXE")
    print(f"    • The AI model (~3GB) downloads from HuggingFace on first launch")
    print(f"    • Model is cached at: %LOCALAPPDATA%/CodeMate/CodeMate/model_cache")
    print(f"    • Settings stored at:  %LOCALAPPDATA%/CodeMate/CodeMate/settings.json")
    print(f"{'='*50}")


if __name__ == "__main__":
    build()
