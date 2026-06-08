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
        os.makedirs(cli_convos_dir)
    if not os.path.exists(gui_convos_dir):
        os.makedirs(gui_convos_dir)

    # 1. Bidirectional copy of conversation logs
    print("[*] Performing bidirectional synchronization...")
    synced_to_gui = 0
    synced_to_cli = 0

    cli_files = {f for f in os.listdir(cli_convos_dir) if f.endswith(".db") or f.endswith(".pb")}
    gui_files = {f for f in os.listdir(gui_convos_dir) if f.endswith(".db") or f.endswith(".pb")}
    all_files = cli_files.union(gui_files)

    for file_name in all_files:
        cli_path = os.path.join(cli_convos_dir, file_name)
        gui_path = os.path.join(gui_convos_dir, file_name)

        exists_in_cli = os.path.exists(cli_path)
        exists_in_gui = os.path.exists(gui_path)

        if exists_in_cli and not exists_in_gui:
            try:
                shutil.copy2(cli_path, gui_path)
                synced_to_gui += 1
            except Exception:
                pass
        elif exists_in_gui and not exists_in_cli:
            try:
                shutil.copy2(gui_path, cli_path)
                synced_to_cli += 1
            except Exception:
                pass
        else:
            try:
                cli_mtime = os.path.getmtime(cli_path)
                gui_mtime = os.path.getmtime(gui_path)

                if cli_mtime > gui_mtime + 1:
                    shutil.copy2(cli_path, gui_path)
                    synced_to_gui += 1
                elif gui_mtime > cli_mtime + 1:
                    shutil.copy2(gui_path, cli_path)
                    synced_to_cli += 1
            except Exception:
                pass

    print(f"[+] Synced {synced_to_gui} files to GUI, {synced_to_cli} files to CLI.")

    # 2. Reset migration flags in state file (if files synced to GUI)
    if synced_to_gui > 0 and os.path.exists(state_file):
        print("[*] Resetting migration flags in state file to trigger re-import in GUI...")
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
        print("[+] Sync complete. No GUI state updates required.")

if __name__ == "__main__":
    sync_history()
