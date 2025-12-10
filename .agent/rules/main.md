---
trigger: always_on
---

# Main Rules for AzerothForge

## Follow Design
Always read DESIGN.md before generating code to ensure architectural compliance.

## UI Framework
Use PySide6 (Qt) exclusively. Do not suggest Tkinter or PyQt5.

## Style 
Follow PEP8. Use type hints (def func(a: int) -> str:).

## OS
Assume Linux environment (use systemd logic).