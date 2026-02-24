# Custom BLE Macro Pad

An end-to-end customizable Bluetooth macro pad built with an ESP32 and a Python desktop application.

It allows physical buttons to trigger configurable shortcuts on a PC via BLE, with local configuration and optional cloud sync.

---

## Features

- ESP32 BLE communication
- Desktop app built with Python (CustomTkinter)
- Configurable button mappings
- Local JSON configuration storage
- Firebase Real-Time Database integration
- Asynchronous BLE handling
- Multi-threaded desktop architecture
- Automated tests (pytest)
- CI/CD with GitHub Actions
- Packaged executable via PyInstaller

---

## Architecture Overview

### Input Layer
User presses a physical button connected to the ESP32.

### Communication Layer
ESP32 sends button event over Bluetooth Low Energy (BLE).

### Processing Layer
Python desktop app receives BLE notification asynchronously.

### Mapping Layer
Button ID is mapped to shortcut action from JSON config.

### Execution Layer
The application executes the mapped keyboard shortcut.

---

## Design Decisions

- **Desktop-side processing** keeps firmware lightweight and flexible.
- **BLE over classic Bluetooth** for lower energy and simplicity.
- **JSON-based configuration** for dynamic updates.
- **Asynchronous BLE handling** to prevent UI blocking.
- **CI/CD integration** ensures stable builds and test validation.
- **Separation of concerns** between BLE, UI, and config modules.

---

## Tech Stack

### Firmware
- ESP32
- Arduino framework
- BLE

### Desktop Application
- Python
- CustomTkinter
- Bleak (BLE client)
- PyAutoGUI

### Cloud & DevOps
- Firebase RTDB
- GitHub Actions
- pytest
- PyInstaller

---

## Setup

### Requirements
- ESP32 flashed with firmware

### Steps
1. Download the repository
2. Build the hardware based on design in doc folder
3. Flash ESP32 on Arduino using the ino file in custom_keyboard folder
4. Go to dist folder and run the executable
