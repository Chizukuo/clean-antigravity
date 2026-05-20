# Clean Antigravity

[English](#english) | [中文说明](#中文说明)

---

## English

A safe, offline utility to resolve the duplicated project files issue in Google DeepMind's **Antigravity** desktop coding assistant.

### The Problem
During version upgrades, Antigravity's migration helper converts each old conversation into a standalone project (e.g. `my-project 2`, `my-project 3`), spawning dozens of duplicate project configuration JSON files in your config directory.

If you delete these JSON files manually, the running `language_server` will notice their absence and silently hide/delete the corresponding conversations from the database (`agyhub_summaries_proto.pb`), causing you to lose your chat history in the UI.

### The Solution
This script solves the issue in one click by operating **offline** (while the Language Server is safely stopped):
1. Detects all unique workspace folders and identifies which project configuration is the primary one.
2. Gracefully stops the Antigravity Language Server process.
3. Automatically creates a backup of your conversation database.
4. Performs a binary search-and-replace to map all conversations from duplicate projects to their primary project ID.
5. Deletes all redundant duplicate project JSON configuration files.

### Usage
1. Close the Antigravity desktop app.
2. Clone this repository and run the script:
   ```bash
   python clean_antigravity.py
   ```
3. Restart Antigravity. All your conversation history will be safely consolidated under their corresponding main projects.

---

## 中文说明

一个安全、一键式的离线实用工具，用于解决 Google DeepMind **Antigravity** 桌面编程助手中“对话被拆分成单独项目”以及“项目列表重复混乱”的问题。

### 根本原因
在版本升级过程中，Antigravity 的迁移工具会将旧对话单独转换为一个独立项目（例如产生 `my-project 2`、`my-project 3` 等重复项目），并在配置目录中生成大量的重复 JSON 文件。

如果您直接在磁盘上手动删除这些 JSON 文件，后台运行的 `language_server` 会感知到文件丢失，并自动从其数据库（`agyhub_summaries_proto.pb`）中隐藏/删除对应的对话记录，导致您在界面上丢失历史聊天记录。

### 解决方案
本脚本通过**离线状态下**的一步到位操作彻底解决此问题：
1. 扫描所有项目配置文件，按物理路径归类，确定每个工作区的唯一主项目和冗余重复项目。
2. 强制终止后台的 Antigravity 语言服务器进程，防止其用内存缓存覆盖我们的修改。
3. 自动对您的对话数据库文件进行安全备份。
4. 在二进制层面对数据库进行映射重构，把重复项目下的所有历史对话重新关联到唯一的主项目下。
5. 清理磁盘上所有冗余的重复项目 JSON 配置文件。

### 使用方法
1. 关闭 Antigravity 客户端。
2. 克隆本仓库并运行脚本：
   ```bash
   python clean_antigravity.py
   ```
3. 重新启动 Antigravity 客户端，您的所有历史对话将完美合并并分类归属到唯一的主项目下。

## License
MIT License
