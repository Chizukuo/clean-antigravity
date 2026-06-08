import os
import shutil
import re

def get_gemini_dir():
    return os.path.join(os.path.expanduser("~"), ".gemini")

def sync_history():
    gemini_dir = get_gemini_dir()
    cli_convos_dir = os.path.join(gemini_dir, "antigravity-cli", "conversations")
    gui_convos_dir = os.path.join(gemini_dir, "antigravity", "conversations")
    state_file = os.path.join(gemini_dir, "antigravity", "antigravity_state.pbtxt")

    print("==================================================")
    print("      Antigravity CLI/GUI History Syncer          ")
    print("==================================================")
    print(f"[*] Base directory: {gemini_dir}")

    if not os.path.exists(cli_convos_dir):
        print(f"[-] Error: CLI conversations directory not found at {cli_convos_dir}")
        return

    if not os.path.exists(gui_convos_dir):
        os.makedirs(gui_convos_dir)

    # 1. Copy conversation logs
    print("[*] Copying conversation files from CLI to GUI...")
    copied_count = 0
    for file_name in os.listdir(cli_convos_dir):
        if not (file_name.endswith(".db") or file_name.endswith(".pb")):
            continue
        src = os.path.join(cli_convos_dir, file_name)
        dst = os.path.join(gui_convos_dir, file_name)
        if not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst):
            shutil.copy2(src, dst)
            copied_count += 1

    print(f"[+] Copied {copied_count} new conversation files.")

    # 2. Reset migration flags in state file
    if os.path.exists(state_file):
        print("[*] Resetting migration flags in state file to trigger re-import...")
        # Backup
        shutil.copy2(state_file, state_file + ".bak")
        
        with open(state_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Reset migrate_convos_into_projects
        content = re.sub(
            r"migrate_convos_into_projects:\s*\w+",
            "migrate_convos_into_projects:  MIGRATION_STATUS_NOT_STARTED",
            content
        )
        # Reset migrate_retroactive_projects
        content = re.sub(
            r"migrate_retroactive_projects:\s*\w+",
            "migrate_retroactive_projects:  RETROACTIVE_MIGRATION_STATUS_NOT_STARTED",
            content
        )

        with open(state_file, "w", encoding="utf-8") as f:
            f.write(content)

        print("[+] Migration flags reset successfully.")
        print("\nNext Steps:")
        print("1. Start the Antigravity desktop app once so it can import the newly copied conversations.")
        print("2. Close the app again and run `clean_antigravity.py` to clean up any duplicate project entries that the import process may have created.")
    else:
        print("[-] Warning: antigravity_state.pbtxt not found. Direct import trigger skipped.")

if __name__ == "__main__":
    sync_history()
