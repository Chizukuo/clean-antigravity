import os
import sys
import subprocess
import shutil
import re
import time
from collections import defaultdict

# ----------------------------------------------------
# Configuration Paths
# ----------------------------------------------------
def get_gemini_dir():
    return os.path.join(os.path.expanduser("~"), ".gemini")

GEMINI_DIR = get_gemini_dir()
PROJECTS_DIR = os.path.join(GEMINI_DIR, "config", "projects")
PB_PATH = os.path.join(GEMINI_DIR, "antigravity", "agyhub_summaries_proto.pb")
STATE_FILE = os.path.join(GEMINI_DIR, "antigravity", "antigravity_state.pbtxt")
CLI_CONVOS_DIR = os.path.join(GEMINI_DIR, "antigravity-cli", "conversations")
GUI_CONVOS_DIR = os.path.join(GEMINI_DIR, "antigravity", "conversations")

if sys.platform == "win32":
    APP_EXE = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Programs", "antigravity", "Antigravity.exe")
elif sys.platform == "darwin":
    APP_EXE = "/Applications/Antigravity.app"
else:
    APP_EXE = ""

# ----------------------------------------------------
# Step 1: Run Deduplicator (Safe Offline Clean)
# ----------------------------------------------------
def run_deduplicator():
    print("[*] Running workspace deduplication...")
    if not os.path.exists(PROJECTS_DIR):
        return

    # Scan and group project files by folderUri
    uri_to_projects = defaultdict(list)
    for file_name in os.listdir(PROJECTS_DIR):
        if not file_name.endswith(".json"):
            continue
        file_path = os.path.join(PROJECTS_DIR, file_name)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            project_id = data.get("id")
            project_name = data.get("name")
            resources = data.get("projectResources", {}).get("resources", [])
            if not resources:
                continue
            
            res = resources[0]
            folder_uri = ""
            if "folderUri" in res:
                folder_uri = res["folderUri"]
            elif "gitFolder" in res and "folderUri" in res["gitFolder"]:
                folder_uri = res["gitFolder"]["folderUri"]
                
            if folder_uri:
                import urllib.parse
                normalized_uri = urllib.parse.unquote(folder_uri).lower()
                uri_to_projects[normalized_uri].append({
                    "id": project_id,
                    "name": project_name,
                    "file": file_name,
                    "is_git": "gitFolder" in res
                })
        except Exception as e:
            pass

    # Determine primary and duplicate projects
    primaries = {}
    mappings = {}
    all_duplicates = []

    for uri, projs in uri_to_projects.items():
        def sort_key(x):
            name = x["name"]
            is_path = 1 if ("\\" in name or "/" in name) else 0
            return (is_path, len(name), x["id"])
            
        projs.sort(key=sort_key)
        primary = projs[0]
        primaries[uri] = primary
        
        for dup in projs[1:]:
            mappings[dup["id"]] = primary["id"]
            all_duplicates.append(dup)

    if not all_duplicates:
        print("[+] Workspace configurations are already clean.")
        return

    # Update database
    if os.path.exists(PB_PATH):
        try:
            with open(PB_PATH, "rb") as f:
                content = f.read()
            
            replaced_count = 0
            orig_size = len(content)
            for dup_id, primary_id in mappings.items():
                if len(dup_id) == 36 and len(primary_id) == 36:
                    dup_bytes = dup_id.encode("utf-8")
                    primary_bytes = primary_id.encode("utf-8")
                    occurrences = content.count(dup_bytes)
                    if occurrences > 0:
                        content = content.replace(dup_bytes, primary_bytes)
                        replaced_count += occurrences
            
            if len(content) == orig_size:
                with open(PB_PATH, "wb") as f:
                    f.write(content)
                print(f"[+] Database updated. Re-mapped {replaced_count} conversation references.")
        except Exception as e:
            print(f"[-] Database update skipped: {e}")

    # Delete duplicate JSON files
    for dup in all_duplicates:
        file_path = os.path.join(PROJECTS_DIR, dup["file"])
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
    print(f"[+] Removed {len(all_duplicates)} duplicate project configurations.")

# ----------------------------------------------------
# Step 2: Sync CLI history
# ----------------------------------------------------
def run_sync():
    print("[*] Checking for CLI history updates to sync...")
    if not os.path.exists(CLI_CONVOS_DIR):
        return

    if not os.path.exists(GUI_CONVOS_DIR):
        os.makedirs(GUI_CONVOS_DIR)

    copied_count = 0
    for file_name in os.listdir(CLI_CONVOS_DIR):
        if not (file_name.endswith(".db") or file_name.endswith(".pb")):
            continue
        src = os.path.join(CLI_CONVOS_DIR, file_name)
        dst = os.path.join(GUI_CONVOS_DIR, file_name)
        if not os.path.exists(dst):
            try:
                shutil.copy2(src, dst)
                copied_count += 1
            except Exception:
                pass

    if copied_count > 0:
        print(f"[+] Synced {copied_count} new conversation files from CLI.")
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    content = f.read()
                
                content = re.sub(r"migrate_convos_into_projects:\s*\w+", "migrate_convos_into_projects:  MIGRATION_STATUS_NOT_STARTED", content)
                content = re.sub(r"migrate_retroactive_projects:\s*\w+", "migrate_retroactive_projects:  RETROACTIVE_MIGRATION_STATUS_NOT_STARTED", content)
                
                with open(STATE_FILE, "w", encoding="utf-8") as f:
                    f.write(content)
                print("[+] Reset migration state to trigger import on startup.")
            except Exception as e:
                print(f"[-] Failed to update migration state: {e}")
    else:
        print("[+] No new CLI conversations to sync.")

# ----------------------------------------------------
# Step 3: Launch Antigravity
# ----------------------------------------------------
def launch_app():
    if not APP_EXE or not os.path.exists(APP_EXE):
        print(f"[-] Error: Antigravity executable not found at '{APP_EXE}'")
        return

    print(f"[*] Launching Antigravity GUI...")
    if sys.platform == "win32":
        subprocess.Popen([APP_EXE], creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", APP_EXE])
    else:
        subprocess.Popen([APP_EXE])
    print("[+] Antigravity has been started.")

if __name__ == "__main__":
    import json
    # Run offline deduplication first (to clean up from last GUI session)
    run_deduplicator()
    # Run sync history (to stage any new CLI conversations for import)
    run_sync()
    # Launch GUI
    launch_app()
