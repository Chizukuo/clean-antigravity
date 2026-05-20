import os
import json
import shutil
import subprocess
import time
from collections import defaultdict

def get_gemini_dir():
    """Automatically locate the user's .gemini configuration directory."""
    return os.path.join(os.path.expanduser("~"), ".gemini")

def run_cleanup(auto_approve=False):
    gemini_dir = get_gemini_dir()
    projects_dir = os.path.join(gemini_dir, "config", "projects")
    pb_path = os.path.join(gemini_dir, "antigravity", "agyhub_summaries_proto.pb")
    bak_path = pb_path + ".bak"

    print("==================================================")
    print("     Antigravity Workspace Deduplicator v1.0      ")
    print("==================================================")
    print(f"[*] Base directory detected: {gemini_dir}")

    if not os.path.exists(projects_dir):
        print(f"[-] Error: Project configuration directory not found at {projects_dir}")
        return

    # 1. Scan and group project files by folderUri
    print("[*] Scanning project configurations...")
    uri_to_projects = defaultdict(list)
    
    for file_name in os.listdir(projects_dir):
        if not file_name.endswith(".json"):
            continue
        file_path = os.path.join(projects_dir, file_name)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            project_id = data.get("id")
            project_name = data.get("name")
            resources = data.get("projectResources", {}).get("resources", [])
            if not resources:
                continue
            
            folder_uri = resources[0].get("gitFolder", {}).get("folderUri")
            if folder_uri:
                uri_to_projects[folder_uri.lower()].append({
                    "id": project_id,
                    "name": project_name,
                    "file": file_name
                })
        except Exception as e:
            print(f"[-] Warning: Failed to parse {file_name}: {e}")

    # 2. Determine primary and duplicate projects
    primaries = {}
    mappings = {}  # duplicate_id -> primary_id
    all_duplicates = []

    for uri, projs in uri_to_projects.items():
        # Keep the shortest name/first ID as primary
        projs.sort(key=lambda x: (len(x["name"]), x["id"]))
        primary = projs[0]
        primaries[uri] = primary
        
        for dup in projs[1:]:
            mappings[dup["id"]] = primary["id"]
            all_duplicates.append(dup)

    print(f"[+] Scan complete. Found {len(primaries)} unique workspaces and {len(all_duplicates)} duplicate project configurations.")

    if not all_duplicates:
        print("[+] Your workspace configuration is already clean! No action required.")
        return

    # 3. Print mapping plan
    print("\nProposed cleanup actions:")
    for uri, primary in primaries.items():
        dups = [d for d in uri_to_projects[uri] if d["id"] != primary["id"]]
        if dups:
            print(f"\n  Workspace: {uri}")
            print(f"    [KEEP] Primary Project: '{primary['name']}' ({primary['id']})")
            for d in dups:
                print(f"    [REMOVE & MERGE] Duplicate: '{d['name']}' ({d['id']})")

    # 4. Confirmation
    if not auto_approve:
        confirm = input("\nDo you want to proceed with the cleanup? (y/N): ").strip().lower()
        if confirm != 'y':
            print("[-] Cleanup canceled by user.")
            return

    # 5. Shut down Language Server
    print("\n[*] Terminating Antigravity / Language Server processes...")
    if os.name == 'nt':  # Windows
        subprocess.run(["taskkill", "/F", "/IM", "language_server.exe"], capture_output=True)
    else:  # macOS/Linux
        subprocess.run(["pkill", "-f", "language_server"], capture_output=True)
    time.sleep(2.0)  # Wait for process shutdown

    # 6. Recreate missing primary configurations (just in case they were deleted)
    for uri, p in primaries.items():
        file_path = os.path.join(projects_dir, p["file"])
        if not os.path.exists(file_path):
            proj_config = {
                "id": p["id"],
                "name": p["name"],
                "projectResources": {
                    "resources": [
                        {
                            "gitFolder": {
                                "folderUri": uri,
                                "defaultBranch": "main",
                                "allowWrite": True
                            }
                        }
                    ]
                }
            }
            with open(file_path, "w", encoding="utf-8") as pf:
                json.dump(proj_config, pf, indent=2)
            print(f"[+] Recreated primary configuration file: {p['file']}")

    # 7. Backup and update database
    if os.path.exists(pb_path):
        # Create a timestamped backup for absolute safety, plus standard .bak
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        ts_bak_path = f"{pb_path}.bak_{timestamp}"
        
        try:
            shutil.copy2(pb_path, ts_bak_path)
            print(f"[+] Timestamped database backup created: {ts_bak_path}")
            if not os.path.exists(bak_path):
                shutil.copy2(pb_path, bak_path)
                print(f"[+] Standard database backup created: {bak_path}")
        except Exception as e:
            print(f"[-] Error creating database backup: {e}")
            return
        
        # Read the file with retry logic to handle file locking
        print("[*] Rebuilding database conversation mapping...")
        content = None
        for attempt in range(5):
            try:
                with open(pb_path, "rb") as f:
                    content = f.read()
                break
            except PermissionError:
                print(f"[!] Warning: Database file is locked. Retrying to read ({attempt + 1}/5)...")
                time.sleep(1.0)
        
        if content is None:
            print("[-] Error: Database file is locked by another process. Skipping remapping.")
            return

        replaced_count = 0
        orig_size = len(content)
        
        for dup_id, primary_id in mappings.items():
            # Validate UUID length to avoid corrupting protobuf serialization fields
            if len(dup_id) != 36 or len(primary_id) != 36:
                print(f"[-] Skip: Invalid UUID length for duplicate '{dup_id}' or primary '{primary_id}'")
                continue
                
            dup_bytes = dup_id.encode("utf-8")
            primary_bytes = primary_id.encode("utf-8")
            
            occurrences = content.count(dup_bytes)
            if occurrences > 0:
                content = content.replace(dup_bytes, primary_bytes)
                replaced_count += occurrences
        
        if len(content) == orig_size:
            # Write with retry logic to handle file locking
            success = False
            for attempt in range(5):
                try:
                    with open(pb_path, "wb") as f:
                        f.write(content)
                    success = True
                    break
                except PermissionError:
                    print(f"[!] Warning: Database file is locked. Retrying to write ({attempt + 1}/5)...")
                    time.sleep(1.0)
            
            if success:
                print(f"[+] Database updated successfully. Re-mapped {replaced_count} occurrences.")
            else:
                print("[-] Error: Failed to write to database file due to file lock.")
                print(f"[*] Restoring database from backup {ts_bak_path}...")
                shutil.copy2(ts_bak_path, pb_path)
                return
        else:
            print("[-] Error: Binary size mismatch after replacement. Restoring backup database...")
            shutil.copy2(ts_bak_path, pb_path)
            return
    else:
        print("[-] Warning: Database file not found. Skipping conversation remapping.")

    # 8. Clean up duplicate JSON files
    deleted_files = 0
    for dup in all_duplicates:
        file_path = os.path.join(projects_dir, dup["file"])
        if os.path.exists(file_path):
            os.remove(file_path)
            deleted_files += 1
            
    print(f"[+] Cleanup finished. Deleted {deleted_files} duplicate project configurations.")
    print("[*] You can now restart Antigravity. All your conversations will be neatly grouped under their primary projects.")

if __name__ == "__main__":
    import sys
    auto_approve = "-y" in sys.argv or "--yes" in sys.argv
    run_cleanup(auto_approve=auto_approve)
