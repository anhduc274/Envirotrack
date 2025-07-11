# 📡 Airmeter – Android App & ESP32 Firmware Deployment Guide

## 📦 Table of Contents
- [1. Overview](#1-overview)
- [2. Requirements](#2-requirements)
- [3. Project Structure](#3-project-structure)
- [4. Running the Android App (Airmeter)](#4-running-the-android-app-airmeter)
- [5. Uploading Code to Lyligo A7670G ESP32](#5-uploading-code-to-lyligo-a7670g-esp32)
- [6. Notes](#6-notes)

---

## 1. 📌 Overview

This project includes:

- **Airmeter**: an Android application used to display and interact with sensor data.
- **Firmware**: a set of code files running on the **Lyligo A7670G ESP32 board**, using a 4G module for connectivity.

---

## 2. ⚙️ Requirements

### For Android App
- [Android Studio](https://developer.android.com/studio)
- Android smartphone or emulator

### For Firmware
- [Arduino IDE](https://www.arduino.cc/en/software)
- USB cable for ESP32
- Installed board package for **ESP32 (by Espressif Systems)**
- Libraries used (may be auto-included in the sketch folder)

---

## 3. 📁 Project Structure

```plaintext
IOT/
├── AndroidApp/             # Android Studio project (Airmeter)
│   └── app/                # Source code of the mobile app
│
├── Mainboard code/         # Firmware files for Lyligo A7670G ESP32
│   ├── main.ino            # Main firmware file
│   ├── A7670G.cpp/h        # Files for 4G module
│   └── ...                 # Additional required source files
│
└── README.md               # This guide
4. 📲 Running the Android App (Airmeter)
Open Android Studio.

Choose "Open an Existing Project".

Navigate to the AndroidApp/ folder and open it.

Let Gradle finish syncing.

Connect an Android phone via USB or launch an emulator.

Press Run (green ▶️ button) to install and start Airmeter.

5. 🚀 Uploading Code to Lyligo A7670G ESP32
Connect the Lyligo A7670G ESP32 board to your computer via USB.

Open the Arduino IDE.

Go to File → Open, and select the main.ino file inside the Mainboard code/ folder.

Ensure all .cpp, .h, and .ino files in Mainboard code/ are in the same folder.

In Arduino IDE:

Go to Tools → Board → Select ESP32 Dev Module or Lyligo A7670G if available.

Go to Tools → Port → Select the correct COM port.

Click the Upload button (right arrow).

Wait until upload completes.

✅ All files inside Mainboard code/ are required. Simply placing them in the same folder is enough — no additional setup needed.

⚠️ If upload fails, try holding the BOOT button when uploading.

6. 📝 Notes
The ESP32 communicates via 4G (A7670G module) — make sure your SIM card is inserted and activated.

Check APN settings in the firmware (.ino or .cpp files).

Data from the ESP32 is sent to the app (or server) via 4G.

If the app does not receive data:

Make sure the ESP32 successfully connects to the network.

Check serial output in Arduino IDE (baud rate 115200).
