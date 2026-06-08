import os
import sys
import tempfile
import subprocess

def create_windows_shortcut(target_path, shortcut_path, icon_path):
    # Use VBScript to create the shortcut (native on all Windows, no external dependencies)
    vbs_content = f'''Set oWS = WScript.CreateObject("WScript.Shell")
Set oLink = oWS.CreateShortcut("{shortcut_path}")
oLink.TargetPath = "{target_path}"
oLink.IconLocation = "{icon_path}"
oLink.Save
'''
    with tempfile.NamedTemporaryFile("w", suffix=".vbs", delete=False) as f:
        f.write(vbs_content)
        temp_vbs = f.name

    try:
        subprocess.run(["cscript", "//nologo", temp_vbs], capture_output=True)
    finally:
        if os.path.exists(temp_vbs):
            os.remove(temp_vbs)

def main():
    if sys.platform != "win32":
        print("[-] Error: Shortcuts can only be created on Windows.")
        return

    gemini_dir = os.path.join(os.path.expanduser("~"), ".gemini")
    launch_bat = os.path.join(gemini_dir, "launch.bat")
    app_exe = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Programs", "antigravity", "Antigravity.exe")

    if not os.path.exists(launch_bat):
        print(f"[-] Error: launch.bat not found at '{launch_bat}'")
        return

    # Determine Start Menu Programs path
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
        programs_dir, _ = winreg.QueryValueEx(key, "Programs")
    except Exception:
        programs_dir = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs")

    shortcut_path = os.path.join(programs_dir, "Antigravity.lnk")
    
    print(f"[*] Creating Start Menu shortcut pointing to: {launch_bat}")
    create_windows_shortcut(launch_bat, shortcut_path, app_exe)
    print(f"[+] Successfully created Start Menu shortcut at: {shortcut_path}")

if __name__ == "__main__":
    main()
