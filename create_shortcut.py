import os
import sys
import tempfile
import subprocess

def create_windows_shortcut(target_path, shortcut_path, icon_path, working_dir=None):
    # Use VBScript to create the shortcut (native on all Windows, no external dependencies)
    vbs_content = f'''Set oWS = WScript.CreateObject("WScript.Shell")
Set oLink = oWS.CreateShortcut("{shortcut_path}")
oLink.TargetPath = "{target_path}"
oLink.IconLocation = "{icon_path}"
'''
    if working_dir:
        # Escape backslashes for VBScript string literal (just in case)
        escaped_working_dir = working_dir.replace('"', '""')
        vbs_content += f'oLink.WorkingDirectory = "{escaped_working_dir}"\n'
    
    vbs_content += 'oLink.Save\n'

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
    launch_vbs = os.path.join(gemini_dir, "launch.vbs")
    launch_bat = os.path.join(gemini_dir, "launch.bat")
    app_exe = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Programs", "antigravity", "Antigravity.exe")

    if not os.path.exists(launch_vbs):
        print(f"[-] Error: launch.vbs not found at '{launch_vbs}'")
        return
    if not os.path.exists(launch_bat):
        print(f"[-] Error: launch.bat not found at '{launch_bat}'")
        return

    # Determine Start Menu Programs and Desktop path
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
        programs_dir, _ = winreg.QueryValueEx(key, "Programs")
        desktop_dir, _ = winreg.QueryValueEx(key, "Desktop")
    except Exception:
        programs_dir = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs")
        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")

    # Create Start Menu Shortcuts
    print(f"[*] Creating Start Menu shortcuts...")
    sm_silent = os.path.join(programs_dir, "Antigravity.lnk")
    sm_console = os.path.join(programs_dir, "Antigravity (Console).lnk")
    
    create_windows_shortcut(launch_vbs, sm_silent, app_exe, gemini_dir)
    create_windows_shortcut(launch_bat, sm_console, app_exe, gemini_dir)
    print(f"[+] Created Start Menu (Silent): {sm_silent}")
    print(f"[+] Created Start Menu (Console): {sm_console}")

    # Create Desktop Shortcuts
    print(f"[*] Creating Desktop shortcuts...")
    dt_silent = os.path.join(desktop_dir, "Antigravity.lnk")
    dt_console = os.path.join(desktop_dir, "Antigravity (Console).lnk")

    create_windows_shortcut(launch_vbs, dt_silent, app_exe, gemini_dir)
    create_windows_shortcut(launch_bat, dt_console, app_exe, gemini_dir)
    print(f"[+] Created Desktop (Silent): {dt_silent}")
    print(f"[+] Created Desktop (Console): {dt_console}")

if __name__ == "__main__":
    main()
