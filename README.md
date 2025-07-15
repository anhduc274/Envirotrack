# 📡 Airmeter – Firmware & App Guide for LILYGO T-A7670G ESP32 with ThingSpeak Integration

## 🔧 1. Uploading Firmware to LILYGO TTGO T-A7670G ESP32

### Requirements:
- Thonny (latest version)
- ESP32 board package installed (via Boards Manager)
- USB cable (data cable)
- Nano SIM with active **4G data plan**
- All firmware files (in `Mainboard code/` folder)

### Steps:
1. Connect the **LILYGO T-A7670G ESP32** board to your computer using a USB cable.
2. Open **Thonny**.
3. Upload all code files in the Mainboard Code File to the mainboard
## 📲 2. Installing and Running the Airmeter App

### Requirements:
- Android Studio
- Android phone or emulator

### Steps:
1. Open **Android Studio**.
2. Select **"Open an Existing Project"**, and open the folder `AndroidApp/`.
3. Let Gradle sync finish.
4. Connect your Android phone with USB debugging enabled.
5. Click the green **Run** (▶️) button to build and install the app.
6. The app is named **Airmeter** and will launch after installation.

---

## ☁️ 3. Viewing Sensor Data on ThingSpeak

This project uses **ThingSpeak** to upload and display sensor data (e.g. temperature, humidity).

### Steps:
1. Go to [https://thingspeak.com](https://thingspeak.com) and sign in or create an account.
2. Create a **New Channel** and:
   - Name it (e.g. `Airmeter ESP32`)
   - Add Fields (e.g. Field1: Temperature, Field2: Humidity, etc.)
   - Save the channel.
3. Go to **API Keys** tab → Copy your **Write API Key**.

4. In the firmware (`main.py`), find the line like this:
   ```cpp
   String apiKey = "YOUR_API_KEY_HERE";
Replace "YOUR_API_KEY_HERE" with your actual Write API Key from ThingSpeak.

Re-upload the code to your board using Arduino IDE.

After boot, your ESP32 will connect via 4G and send data to ThingSpeak automatically every few seconds.

Go to your ThingSpeak Channel → Click Private View / Public View to see real-time graphs.

🛠 4. Changing the API Key in the App
If your app needs to display data from ThingSpeak, it may require a Read API Key.

To change it in the Android app:
Open the Android project in Android Studio.

Look for a file sensor_dashboard.dart
Find lines 109 and 110
Replace it with your actual Read API Key from ThingSpeak.

Rebuild and reinstall the app using the Run button.

💡 Alternatively, you can pass the API key via settings in the app if it's supported.

✅ Summary
Task	Done From
Upload firmware to ESP32	Arduino IDE
Run Airmeter app	Android Studio
View sensor data	ThingSpeak
Update Write API Key	In main.py
Update Read API Key	In Android app source
