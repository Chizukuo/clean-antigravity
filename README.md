# Clean Antigravity

[English](#english) | [中文说明](#中文说明)

---

## English

A suite of safe, offline utility scripts to maintain and fix Google DeepMind's **Antigravity** desktop coding assistant.

### Features

1. **Workspace Deduplicator (`clean_antigravity.py`)**:
   Resolves the issue where version upgrades split old conversations into standalone projects (e.g. `project 2`, `project 3`). Safely consolidates duplicate configurations and maps conversation history to their primary project ID in the database (`agyhub_summaries_proto.pb`) without loss of history.
   
2. **Black Screen Patcher (`patch_blackscreen.py`)**:
   Diagnoses and patches the application when stuck on a black/loading screen due to transient network changes (`ERR_NETWORK_CHANGED`) or local loopback self-signed SSL/TLS verification issues (`ERR_CERT_AUTHORITY_INVALID`). It extracts `app.asar`, injects retry and cert bypass logic, and repackages it.

3. **CLI/GUI History Syncer (`sync_history.py`)**:
   Copies conversation history logs from your terminal-based CLI configuration (`antigravity-cli`) into your GUI app directory and resets migration flags in `antigravity_state.pbtxt` to force the GUI to register and import CLI chats.

### Usage

Before running any script, make sure to close the Antigravity desktop app.

#### 1. Consolidation & Deduplication
```bash
python clean_antigravity.py
```

#### 2. Fixing the Black/Loading Screen
```bash
# Patch the client (requires node/npx installed)
python patch_blackscreen.py patch

# Revert to original backed-up state if needed
python patch_blackscreen.py restore
```

#### 3. Synchronizing CLI and GUI Chats
```bash
# 1. Sync the files
python sync_history.py

# 2. Launch Antigravity ONCE to let the app import the new histories
# 3. Close the app and run the consolidator to merge duplicate projects that the import process may have created:
python clean_antigravity.py
```

---

## 中文说明

用于维护和修复 Google DeepMind **Antigravity** 桌面端编程助手的一系列安全、离线的实用脚本工具包。

### 功能介绍

1. **重复项目清理与合并 (`clean_antigravity.py`)**:
   解决版本升级后，旧对话被拆分为独立项目（例如产生 `my-project 2`、`my-project 3`）的问题。在二进制层面对数据库（`agyhub_summaries_proto.pb`）重新映射，把所有对话关联到唯一主项目下，并删除冗余的 JSON 文件，确保不丢失历史记录。

2. **黑屏/加载卡死修复 (`patch_blackscreen.py`)**:
   解决客户端由于网络状态变动（`ERR_NETWORK_CHANGED`）或本地环回自签名证书 SSL 校验失败（`ERR_CERT_AUTHORITY_INVALID`）导致启动卡在黑屏或加载界面的问题。通过解包 `app.asar` 并向 `utils.js` / `languageServer.js` 注入重试及证书信任逻辑后重新打包。

3. **CLI/GUI 历史对话同步 (`sync_history.py`)**:
   将终端 CLI 版（`antigravity-cli`）的聊天历史记录同步复制到桌面端（`antigravity`）中，并重置 `antigravity_state.pbtxt` 中的数据迁移状态，强制桌面客户端在下次启动时对这部分 CLI 对话进行读取和导入。

### 使用方法

运行任何脚本前，请确保已完全关闭 Antigravity 客户端。

#### 1. 重复项目合并
```bash
python clean_antigravity.py
```

#### 2. 修复黑屏/加载卡死
```bash
# 运行补丁（需要系统已安装 Node.js/npx）
python patch_blackscreen.py patch

# 如需从备份还原：
python patch_blackscreen.py restore
```

#### 3. 同步 CLI 与 GUI 对话记录
```bash
# 1. 执行同步
python sync_history.py

# 2. 启动一次 Antigravity 客户端，让其自动导入新同步的对话记录
# 3. 关闭客户端，运行清理合并脚本以解决导入过程中可能产生的重复项目：
python clean_antigravity.py
```

## License
MIT License
