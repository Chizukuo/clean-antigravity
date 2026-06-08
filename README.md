# Clean Antigravity

[English](#english) | [中文说明](#中文说明)

---

## English

A suite of safe, offline utility scripts to maintain and fix Google DeepMind's **Antigravity** desktop coding assistant.

### Features

1. **One-Click Startup Launcher (`launch.bat` / `launch_antigravity.py`)**:
   **Recommended daily usage**. Automatically runs the workspace deduplicator (to clean up configurations from your last session), checks for new terminal CLI chats, copies them into your GUI client directory, resets data migration flags to trigger imports, and then opens the Antigravity GUI application. 

2. **Workspace Deduplicator (`clean_antigravity.py`)**:
   Resolves the issue where version upgrades split old conversations into standalone projects (e.g. `project 2`, `project 3`). Safely consolidates duplicate configurations and maps conversation history to their primary project ID in the database (`agyhub_summaries_proto.pb`) without loss of history.
   
3. **Black Screen Patcher (`patch_blackscreen.py`)**:
   Diagnoses and patches the application when stuck on a black/loading screen due to transient network changes (`ERR_NETWORK_CHANGED`) or local loopback self-signed SSL/TLS verification issues (`ERR_CERT_AUTHORITY_INVALID`). It extracts `app.asar`, injects retry and cert bypass logic, and repackages it.

4. **CLI/GUI History Syncer (`sync_history.py`)**:
   Manual tool. Copies conversation history logs from your terminal-based CLI configuration (`antigravity-cli`) into your GUI app directory and resets migration flags in `antigravity_state.pbtxt` to force the GUI to register and import CLI chats.

5. **Start Menu Shortcut Creator (`create_shortcut.py`)**:
   Windows-only utility. Automatically creates or updates the Windows Start Menu Programs shortcut to point to `launch.bat` (our launcher), making it easy to start the automated sync flow.

### Usage

#### Daily Launching (Automated Synchronization)
Instead of launching the GUI application directly, double-click `launch.bat` (Windows) or run the Python launcher:
```bash
python launch_antigravity.py
```
This automatically handles database cleanup, stages any new CLI files for importing, and starts the GUI client.

#### Fixing the Black/Loading Screen
Close the Antigravity desktop app, then:
```bash
# Patch the client (requires node/npx installed)
python patch_blackscreen.py patch

# Revert to original backed-up state if needed
python patch_blackscreen.py restore
```

#### Generating Start Menu Shortcut (Windows)
```bash
python create_shortcut.py
```

#### Manual Consolidation & Deduplication
```bash
python clean_antigravity.py
```

---

## 中文说明

用于维护和修复 Google DeepMind **Antigravity** 桌面端编程助手的一系列安全、离线的实用脚本工具包。

### 功能介绍

1. **一键智能启动器 (`launch.bat` / `launch_antigravity.py`)**:
   **推荐日常使用**。启动时自动运行重复项目清理脚本（解决上一次运行产生的文件碎片），检测并同步来自终端 CLI 的最新对话，重置迁移标志以引导客户端自动导入，随后拉起桌面端 GUI 客户端。

2. **重复项目清理与合并 (`clean_antigravity.py`)**:
   解决版本升级后，旧对话被拆分为独立项目（例如产生 `my-project 2`、`my-project 3`）的问题。在二进制层面对数据库（`agyhub_summaries_proto.pb`）重新映射，把所有对话关联到唯一主项目下，并删除冗余的 JSON 文件，确保不丢失历史记录。

3. **黑屏/加载卡死修复 (`patch_blackscreen.py`)**:
   解决客户端由于网络状态变动（`ERR_NETWORK_CHANGED`）或本地环回自签名证书 SSL 校验失败（`ERR_CERT_AUTHORITY_INVALID`）导致启动卡在黑屏或加载界面的问题。通过解包 `app.asar` 并向 `utils.js` / `languageServer.js` 注入重试及证书信任逻辑后重新打包。

4. **CLI/GUI 历史对话同步 (`sync_history.py`)**:
   手动同步工具。将终端 CLI 版（`antigravity-cli`）的聊天历史记录同步复制到桌面端（`antigravity`）中，并重置 `antigravity_state.pbtxt` 中的数据迁移状态，强制桌面客户端在下次启动时对这部分 CLI 对话进行读取和导入。

5. **开始菜单快捷方式生成器 (`create_shortcut.py`)**:
   Windows 专用小工具。自动在 Windows 「开始菜单」的程序列表中创建或更新指向 `launch.bat` 的快捷方式，便于直接搜索启动。

### 使用方法

#### 日常自动化启动与同步
日常使用时，无需直接运行 Antigravity，只需双击运行目录下的 `launch.bat` (Windows) 或通过终端运行启动器：
```bash
python launch_antigravity.py
```
它会在后台完成项目去重、CLI 对话的复制与预准备工作，并安全地拉起 GUI 桌面客户端。

#### 修复黑屏/加载卡死
确保完全关闭客户端后，执行：
```bash
# 运行补丁（需要系统已安装 Node.js/npx）
python patch_blackscreen.py patch

# 如需从备份还原：
python patch_blackscreen.py restore
```

#### 生成开始菜单快捷方式 (Windows)
```bash
python create_shortcut.py
```

#### 手动重复项目合并
```bash
python clean_antigravity.py
```

## License
MIT License
