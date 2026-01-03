# Custom-Keyboard

This is a custom keyboard built using an ESP32, buttons and a breadboard with a Python script to perform keyboard shortcuts.

- Demo coming soon

# Why This Was Made

The goal of this project was to be a customizable keyboard that can be used for various cases such as daily office work, gaming, or video editing.

# Tech Stack:

- Language: Python and Arduino 
- Arduino: To program the ESP32
- Python: To perform automation and connect to Firebase real-time database

# How It Was Made

- The hardware was made by connecting an ESP32 to buttons through a breadboard
- The ESP32 sends messages on which button is pressed through Bluetooth Low Energy (BLE) and a desktop Python script detects it to perform the keyboard shortcut.

# Architecture Overview:

**Input Layer**
  - User presses a button and the ESP32 sends a message through BLE to the Python script

**Processing Layer**
- The Python script receives the BLE message and reads it to determine which button was pressed

**Command Layer**
- The script maps buttons to keyboard shortcuts in a JSON file.

**Execution Layer**
- The script executes the respective keyboard shortcut

# Design Decisions

- Using a Python script instead of implementing everything in Arduino allows more customization and keeps the firmware simple
- Event-driven input was used instead of polling to reduce unnecessary CPU usage
- Macro mappings are stored in JSON to allow easy updates without code changes
- Asynchronous BLE handling and separate threads are used to keep the application responsive.

# Limitations

- Can only do keyboard shortcuts
- Adding a new profile and adding buttons requires modifying the JSON file directly
- BLE connectivity can be affected by environmental factors such as distance

# Future Improvements

- Create a GUI to allow users to modify profiles and buttons
- Expand on automation actions the script can perform