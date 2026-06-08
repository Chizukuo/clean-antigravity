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
                
                # Also patch project IDs in SQLite .db conversation files in both GUI and CLI directories
                patched_dbs = 0
                import glob
                import sqlite3
                for base_dir in [GUI_CONVOS_DIR, CLI_CONVOS_DIR]:
                    if not os.path.exists(base_dir):
                        continue
                    for db_path in glob.glob(os.path.join(base_dir, "*.db")):
                        try:
                            conn = sqlite3.connect(db_path)
                            c = conn.cursor()
                            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trajectory_metadata_blob';")
                            if c.fetchone():
                                c.execute("SELECT id, data FROM trajectory_metadata_blob")
                                rows = c.fetchall()
                                db_updated = False
                                for row_id, data in rows:
                                    if isinstance(data, bytes):
                                        new_data = data
                                        for dup_id, primary_id in mappings.items():
                                            dup_bytes = dup_id.encode('utf-8')
                                            primary_bytes = primary_id.encode('utf-8')
                                            if dup_bytes in new_data:
                                                new_data = new_data.replace(dup_bytes, primary_bytes)
                                        if new_data != data:
                                            c.execute("UPDATE trajectory_metadata_blob SET data = ? WHERE id = ?", (new_data, row_id))
                                            db_updated = True
                                if db_updated:
                                    conn.commit()
                                    patched_dbs += 1
                            conn.close()
                        except Exception as e:
                            print(f"[-] Warning: Failed to patch {os.path.basename(db_path)}: {e}")
                if patched_dbs > 0:
                    print(f"[+] Patched project IDs in {patched_dbs} conversation databases.")
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
def is_app_running():
    if sys.platform != "win32":
        try:
            res = subprocess.run(["pgrep", "-f", "Antigravity"], capture_output=True)
            return res.returncode == 0
        except Exception:
            return False
    try:
        output = subprocess.check_output('tasklist /FI "IMAGENAME eq Antigravity.exe"', shell=True, text=True)
        return "Antigravity.exe" in output
    except Exception:
        return False

def run_sync():
    print("[*] Performing bidirectional synchronization between CLI and GUI...")
    if not os.path.exists(CLI_CONVOS_DIR):
        os.makedirs(CLI_CONVOS_DIR)
    if not os.path.exists(GUI_CONVOS_DIR):
        os.makedirs(GUI_CONVOS_DIR)

    synced_to_gui = 0
    synced_to_cli = 0

    cli_files = {f for f in os.listdir(CLI_CONVOS_DIR) if f.endswith(".db") or f.endswith(".pb")}
    gui_files = {f for f in os.listdir(GUI_CONVOS_DIR) if f.endswith(".db") or f.endswith(".pb")}
    all_files = cli_files.union(gui_files)

    for file_name in all_files:
        cli_path = os.path.join(CLI_CONVOS_DIR, file_name)
        gui_path = os.path.join(GUI_CONVOS_DIR, file_name)

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

    if synced_to_gui > 0 or synced_to_cli > 0:
        print(f"[+] Bidirectional sync complete. CLI -> GUI: {synced_to_gui} files, GUI -> CLI: {synced_to_cli} files.")
        if synced_to_gui > 0 and os.path.exists(STATE_FILE):
            if is_app_running():
                print("[*] Antigravity is already running. Skipping migration reset to avoid onboarding popup.")
            else:
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
        print("[+] Conversations are already fully synchronized.")

# ----------------------------------------------------
# Onboarding State Preservation & Restore (Prevents repeated onboarding guide)
# ----------------------------------------------------
SAVED_ONBOARDING_STATE = None

def capture_onboarding_state():
    global SAVED_ONBOARDING_STATE
    if not os.path.exists(STATE_FILE):
        return
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check if completed onboarding steps are present in the active file
        if "completed_steps" in content:
            post_onboarding_match = re.search(r"post_onboarding:\s*\{[^}]*\}", content)
            seen_nuxs_match = re.search(r"seen_nuxs:\s*\{[^}]*\}", content)
            
            post_onboarding = post_onboarding_match.group(0) if post_onboarding_match else None
            seen_nuxs = seen_nuxs_match.group(0) if seen_nuxs_match else None
            
            if post_onboarding and seen_nuxs:
                SAVED_ONBOARDING_STATE = (post_onboarding, seen_nuxs)
                print("[+] Captured onboarding state from active file.")
                return
                
        # If not found in the active file, check the backup file (.bak)
        bak_path = STATE_FILE + ".bak"
        if os.path.exists(bak_path):
            with open(bak_path, "r", encoding="utf-8") as f:
                bak_content = f.read()
            if "completed_steps" in bak_content:
                post_onboarding_match = re.search(r"post_onboarding:\s*\{[^}]*\}", bak_content)
                seen_nuxs_match = re.search(r"seen_nuxs:\s*\{[^}]*\}", bak_content)
                
                post_onboarding = post_onboarding_match.group(0) if post_onboarding_match else None
                seen_nuxs = seen_nuxs_match.group(0) if seen_nuxs_match else None
                
                if post_onboarding and seen_nuxs:
                    SAVED_ONBOARDING_STATE = (post_onboarding, seen_nuxs)
                    print("[+] Captured onboarding state from backup file.")
                    return
    except Exception as e:
        print(f"[-] Warning: Failed to capture onboarding state: {e}")

    # Fallback to default completed state if not found anywhere
    post_onboarding = """post_onboarding:  {
  completed_steps:  POST_ONBOARDING_STEP_TYPE_MANAGER_WELCOME
  completed_steps:  POST_ONBOARDING_STEP_TYPE_USAGE_MODE
  completed_steps:  POST_ONBOARDING_STEP_TYPE_AGENT_CONFIGURATION
  completed_steps:  POST_ONBOARDING_STEP_TYPE_ADD_WORKSPACE
}"""
    seen_nuxs = """seen_nuxs:  {
  uids:  23
  uids:  25
  uids:  24
  uids:  26
  uids:  27
}"""
    SAVED_ONBOARDING_STATE = (post_onboarding, seen_nuxs)
    print("[+] Used default fallback onboarding state.")

def watch_and_restore_onboarding():
    if not SAVED_ONBOARDING_STATE:
        return
        
    print("[*] Monitoring state file to restore onboarding status...")
    post_onboarding_str, seen_nuxs_str = SAVED_ONBOARDING_STATE
    start_time = time.time()
    restored = False
    
    while time.time() - start_time < 90:
        time.sleep(1.0)
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Check if Language Server has written MIGRATION_STATUS_COMPLETED
                if "migrate_convos_into_projects:  MIGRATION_STATUS_COMPLETED" in content:
                    # Check if post_onboarding is empty (wiped) or missing entirely
                    if "post_onboarding" not in content or "post_onboarding:  {}" in content or "post_onboarding: {}" in content:
                        new_content = content
                        
                        # Replace empty post_onboarding with saved block
                        if "post_onboarding:  {}" in new_content:
                            new_content = new_content.replace("post_onboarding:  {}", post_onboarding_str)
                        elif "post_onboarding: {}" in new_content:
                            new_content = new_content.replace("post_onboarding: {}", post_onboarding_str)
                        elif "post_onboarding" not in new_content:
                            # Append it to the file
                            new_content += "\n" + post_onboarding_str
                            
                        # Insert seen_nuxs if missing
                        if "seen_nuxs" not in new_content:
                            new_content += "\n" + seen_nuxs_str
                        
                        # Ensure agent_onboarding_completed is set to COMPLETED
                        if "agent_onboarding_completed:  AGENT_ONBOARDING_STATE_COMPLETED" not in new_content:
                            if "agent_onboarding_completed" not in new_content:
                                new_content += "\nagent_onboarding_completed:  AGENT_ONBOARDING_STATE_COMPLETED"
                            else:
                                new_content = re.sub(
                                    r"agent_onboarding_completed:\s*\w+",
                                    "agent_onboarding_completed:  AGENT_ONBOARDING_STATE_COMPLETED",
                                    new_content
                                )
                            
                        with open(STATE_FILE, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        print("[+] Onboarding status successfully restored!")
                        restored = True
                        break
            except Exception:
                pass
                
    if not restored:
        print("[*] Onboarding status monitor finished (no restore performed).")

# ----------------------------------------------------
# Step 4: Setup Clash Proxy
# ----------------------------------------------------
def setup_proxy():
    import socket
    # Check if proxy is already defined in environment
    for var in ["HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"]:
        if var in os.environ:
            val = os.environ[var]
            print(f"[+] Using existing proxy from environment variable {var}: {val}")
            return True, val

    # Auto-detect Clash on port 7890
    clash_port = 7890
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex(("127.0.0.1", clash_port)) == 0:
                proxy_url = f"http://127.0.0.1:{clash_port}"
                socks_url = f"socks5://127.0.0.1:{clash_port}"
                # Set both upper and lower case env variables for robust client compatibility
                os.environ["HTTP_PROXY"] = proxy_url
                os.environ["HTTPS_PROXY"] = proxy_url
                os.environ["ALL_PROXY"] = socks_url
                os.environ["http_proxy"] = proxy_url
                os.environ["https_proxy"] = proxy_url
                os.environ["all_proxy"] = socks_url
                print(f"[+] Clash proxy detected on port {clash_port}. Proxy env variables applied.")
                return True, proxy_url
    except Exception as e:
        print(f"[-] Error auto-detecting Clash proxy: {e}")
    
    print("[*] Clash proxy not detected on port 7890. Proceeding without proxy.")
    return False, None

# ----------------------------------------------------
# Step 5: Launch Antigravity
# ----------------------------------------------------
def launch_app(use_proxy=False, proxy_url=None):
    if not APP_EXE or not os.path.exists(APP_EXE):
        print(f"[-] Error: Antigravity executable not found at '{APP_EXE}'")
        return

    print(f"[*] Launching Antigravity GUI...")
    if sys.platform == "win32":
        if use_proxy and proxy_url:
            # On Windows, Chromium/Electron does not automatically respect proxy env variables,
            # so we pass the --proxy-server command-line argument.
            subprocess.Popen([APP_EXE, f"--proxy-server={proxy_url}"])
        else:
            os.startfile(APP_EXE)
    elif sys.platform == "darwin":
        if use_proxy and proxy_url:
            subprocess.Popen(["open", APP_EXE, "--args", f"--proxy-server={proxy_url}"])
        else:
            subprocess.Popen(["open", APP_EXE])
    else:
        if use_proxy and proxy_url:
            subprocess.Popen([APP_EXE, f"--proxy-server={proxy_url}"])
        else:
            subprocess.Popen([APP_EXE])
    print("[+] Antigravity has been started.")

if __name__ == "__main__":
    import json
    # Check if app is running
    app_was_running = is_app_running()
    
    # Detect and set up Clash proxy if active
    use_proxy, proxy_url = setup_proxy()
    
    # Only capture onboarding state if the app is NOT running (since we only reset flags then)
    if not app_was_running:
        capture_onboarding_state()
        
    # Run offline deduplication first
    run_deduplicator()
    # Run sync history
    run_sync()
    # Launch GUI
    launch_app(use_proxy, proxy_url)
    
    # Only monitor if the app was NOT running and we captured onboarding
    if not app_was_running and SAVED_ONBOARDING_STATE:
        watch_and_restore_onboarding()
