# CodeMate Desktop App — Task Tracker

## Foundation
- [/] `config.py` — Central configuration
- [ ] `requirements.txt` — Dependencies
- [ ] `assets/icon.png` — Generate app icon

## Core Modules
- [ ] `core/__init__.py`
- [ ] `core/gpu_detector.py` — GPU vendor detection
- [ ] `core/model_engine.py` — Inference engine
- [ ] `core/clipboard_monitor.py` — Win32 clipboard listener
- [ ] `core/context_enricher.py` — Wikipedia/SO context
- [ ] `core/system_monitor.py` — GPU/CPU stats
- [ ] `core/startup_manager.py` — Windows startup registry

## UI Modules
- [ ] `ui/__init__.py`
- [ ] `ui/theme.py` — Design system / QSS
- [ ] `ui/widgets/gauge_widget.py` — Animated circular gauge
- [ ] `ui/widgets/stat_card.py` — Glassmorphism stat card
- [ ] `ui/floating_bubble.py` — Floating action circle
- [ ] `ui/response_popup.py` — Inference result popup
- [ ] `ui/dashboard.py` — Main dashboard window
- [ ] `ui/tray_icon.py` — System tray icon

## Entry Point & Build
- [ ] `main.py` — Application entry point
- [ ] `build.spec` — PyInstaller spec
- [ ] `build.py` — Build helper script

## Verification
- [ ] GPU detection test
- [ ] Model loading test
- [ ] Full app launch test
