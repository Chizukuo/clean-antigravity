import os
import sys
import subprocess
import shutil
import re
import argparse

# Dynamic determination of default app.asar path
if sys.platform == "darwin":
    DEFAULT_ASAR_PATH = "/Applications/Antigravity.app/Contents/Resources/app.asar"
elif sys.platform == "win32":
    DEFAULT_ASAR_PATH = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Programs", "antigravity", "resources", "app.asar")
else:
    DEFAULT_ASAR_PATH = ""

def run_command(cmd, shell=True):
    print(f"Running: {cmd}")
    res = subprocess.run(cmd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(f"Error: Command failed with exit code {res.returncode}")
        print(f"Stdout: {res.stdout}")
        print(f"Stderr: {res.stderr}")
        return False, res.stdout, res.stderr
    return True, res.stdout, res.stderr

def kill_processes():
    print("Stopping Antigravity and language_server processes...")
    if os.name == 'nt':  # Windows
        kill_cmd = 'powershell -Command "Stop-Process -Name Antigravity, language_server -Force -ErrorAction SilentlyContinue"'
        run_command(kill_cmd)
    else:  # macOS/Linux
        subprocess.run(["pkill", "-f", "Antigravity"], capture_output=True)
        subprocess.run(["pkill", "-f", "language_server"], capture_output=True)

def patch_asar(asar_path, no_kill):
    if not asar_path:
        print("Error: Default app.asar path could not be determined for this OS. Please specify via --asar-path.")
        return False

    if not os.path.exists(asar_path):
        print(f"Error: app.asar not found at '{asar_path}'")
        return False
        
    # Check if npx asar is available
    ok, stdout, stderr = run_command("npx asar --version")
    if not ok:
        print("Error: 'npx asar' is not available. Please install it or make sure npm/npx is in PATH.")
        return False

    # Create backup
    backup_path = asar_path + ".bak"
    if not os.path.exists(backup_path):
        print(f"Creating backup at '{backup_path}'...")
        shutil.copyfile(asar_path, backup_path)
    else:
        print(f"Backup already exists at '{backup_path}'.")

    # Temp directory for extraction
    tmp_dir = os.path.join(os.environ.get("TEMP", os.environ.get("TMPDIR", "/tmp")), "antigravity_asar_extracted")
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir, ignore_errors=True)

    try:
        print(f"Extracting app.asar to '{tmp_dir}'...")
        ok, _, _ = run_command(f'npx asar extract "{asar_path}" "{tmp_dir}"')
        if not ok:
            print("Failed to extract app.asar.")
            return False

        # 1. Patch utils.js
        utils_path = os.path.join(tmp_dir, "dist", "utils.js")
        if not os.path.exists(utils_path):
            print(f"Error: utils.js not found at '{utils_path}'")
            return False

        with open(utils_path, "r", encoding="utf-8") as f:
            utils_content = f.read()

        # Check if already patched
        if "did-fail-load" in utils_content:
            print("utils.js is already patched with did-fail-load handler.")
        else:
            target_str = "(0, loadingOverlay_1.attachLoadingOverlay)(win, foregroundColor, backgroundColor);"
            patch_str = """    (0, loadingOverlay_1.attachLoadingOverlay)(win, foregroundColor, backgroundColor);
    win.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL, isMainFrame) => {
        console.error(`Failed to load URL: ${validatedURL} with error code ${errorCode} (${errorDescription})`);
        if (errorCode === -3) {
            return;
        }
        if (isMainFrame === false) {
            return;
        }
        if (validatedURL && (validatedURL.startsWith('http:') || validatedURL.startsWith('https:'))) {
            console.log(`Retrying to load URL in 1000ms: ${validatedURL}`);
            setTimeout(() => {
                if (!win.isDestroyed()) {
                    void win.loadURL(validatedURL);
                }
            }, 1000);
        }
    });"""
            if target_str in utils_content:
                utils_content = utils_content.replace(target_str, patch_str, 1)
                with open(utils_path, "w", encoding="utf-8") as f:
                    f.write(utils_content)
                print("Successfully patched utils.js.")
            else:
                print("Error: Could not find target insertion point in utils.js.")
                return False

        # 2. Patch languageServer.js
        ls_path = os.path.join(tmp_dir, "dist", "languageServer.js")
        if not os.path.exists(ls_path):
            print(f"Error: languageServer.js not found at '{ls_path}'")
            return False

        with open(ls_path, "r", encoding="utf-8") as f:
            ls_content = f.read()

        if "request.certificate.fingerprint === constants_1.LS_CERT_FINGERPRINT" not in ls_content:
            if "request.hostname === '127.0.0.1'" in ls_content:
                print("languageServer.js is already patched to bypass certificate fingerprint check.")
            else:
                print("Error: Could not find setupLocalCertTrust pattern in languageServer.js.")
                return False
        else:
            target_pattern = r"if\s*\(\(request\.hostname\s*===\s*'127\.0\.0\.1'\s*\|\|\s*request\.hostname\s*===\s*'localhost'\)\s*&&\s*request\.certificate\.fingerprint\s*===\s*constants_1\.LS_CERT_FINGERPRINT\)"
            replacement = "if (request.hostname === '127.0.0.1' || request.hostname === 'localhost')"
            
            new_content, count = re.subn(target_pattern, replacement, ls_content)
            if count > 0:
                with open(ls_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print("Successfully patched languageServer.js.")
            else:
                print("Error: Regex replacement failed in languageServer.js.")
                return False

        # Kill running processes if needed
        if not no_kill:
            kill_processes()

        # Repack asar
        print(f"Repacking to '{asar_path}'...")
        ok, _, _ = run_command(f'npx asar pack "{tmp_dir}" "{asar_path}"')
        if not ok:
            print("Failed to repack app.asar. The application might still be running and locking the file.")
            print("Please make sure Antigravity is fully closed, then run this patch again.")
            return False

        print("Patch successfully applied! Antigravity blackscreen issue resolved.")
        return True

    finally:
        # Clean up
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)

def restore_asar(asar_path):
    if not asar_path:
        print("Error: Default app.asar path could not be determined. Please specify via --asar-path.")
        return False

    backup_path = asar_path + ".bak"
    if not os.path.exists(backup_path):
        print(f"Error: Backup file '{backup_path}' does not exist. Cannot restore.")
        return False
    
    kill_processes()
    print(f"Restoring '{asar_path}' from backup...")
    try:
        shutil.copyfile(backup_path, asar_path)
        print("Restore completed successfully.")
        return True
    except Exception as e:
        print(f"Failed to restore file: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Patch Antigravity desktop client to fix the loading/blackscreen issues.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    patch_parser = subparsers.add_parser("patch", help="Apply the blackscreen patches to app.asar.")
    patch_parser.add_argument("--asar-path", default=DEFAULT_ASAR_PATH, help="Path to app.asar.")
    patch_parser.add_argument("--no-kill", action="store_true", help="Do not kill running Antigravity processes before repacking.")
    
    restore_parser = subparsers.add_parser("restore", help="Restore app.asar from backup.")
    restore_parser.add_argument("--asar-path", default=DEFAULT_ASAR_PATH, help="Path to app.asar.")
    
    args = parser.parse_args()
    
    if args.command == "patch":
        success = patch_asar(args.asar_path, args.no_kill)
        sys.exit(0 if success else 1)
    elif args.command == "restore":
        success = restore_asar(args.asar_path)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
