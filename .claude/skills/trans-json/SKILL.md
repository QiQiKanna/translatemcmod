---
name: trans-json
description: 将 sourse/ 下的 Minecraft Mod 给定语言文件翻译为指定语言，输出到 assets/
---

# trans-json — Minecraft Mod 语言文件翻译

## 概述

将 `sourse/` 目录下的 Minecraft Mod 给定语言文件（一般是 `en_us.json`）翻译为指定语言文件（未指定则默认为简体中文 `zh_cn.json`），输出到 `assets/` 目录。

## 工作流位置

本 skill 是整个翻译工作流的**第二步**：

```
① extract-json          ② trans-json (本 skill)       ③ packaging
mods/*.jar  ──提取──→  sourse/<mod>/en_us.json  ──翻译──→  assets/<mod>/zh_cn.json  ──打包──→  packages/<mod>/<mod>-trans.zip
```

| 步骤 | Skill | 说明 |
|---|---|---|
| 前置 | `extract-json` | 从 JAR 中提取 `en_us.json` → `sourse/<mod>/en_us.json` |
| **当前** | **`trans-json`** | 翻译 `sourse/<mod>/` → `assets/<mod>/` |
| 后续 | `packaging` | 将 `assets/<mod>/` 打包为资源包 ZIP |

## 前置条件

- `sourse/<mod>/en_us.json` 必须已存在（若不存在，请先使用 `extract-json` 提取）

## 工作流程

### 1. 确认翻译目标

首先询问用户需要翻译的mod名称  
 - 检查 `sourse/` 进行匹配：

```
sourse/
  <mod名称>/
    en_us.json    ← 英文源文件(可能是其他语言)
```

然后询问用户要翻译的目标语言  
 - 若未指定，默认只生成 **简体中文(`zh_cn`)**
 - 若未指定且源文件已经是简体中文,则默认只生成 **英文(`en_us.json`)**
 - 若用户指定的目标语言在sourse中已存在,就告知用户,询问并等待用户下一步指示


### 2. 执行翻译

**⚠️ 核心原则：主会话不得读取源文件内容。翻译由 Python 脚本通过 API 直调完成，主会话只负责调度。**

使用 `.claude/skills/trans-json/translate.py` 执行翻译：

```bash
python .claude/skills/trans-json/translate.py \
    "sourse/<mod>/<源语言>.json" \
    ".claude/skills/trans-json/glossary.md" \
    "assets/<mod>/<目标语言>.json" \
    --target-lang <目标语言代码>
```

**工作原理**：
- Python 脚本自行 Read 源文件和对照表（不经过主会话上下文）
- 脚本直接调用 DeepSeek API（deepseek-v4-flash 模型），绕过 harness 层
- 自动分批处理（默认每批 80 条），支持断点续传
- 翻译完成后脚本直接 Write 输出文件

**参数说明**：
| 参数 | 说明 |
|---|---|
| 位置参数 1 | 源文件路径（如 `sourse/axiom/en_us.json`） |
| 位置参数 2 | 对照表路径（固定为 `.claude/skills/trans-json/glossary.md`） |
| 位置参数 3 | 输出路径（如 `assets/axiom/zh_cn.json`） |
| `--target-lang` | 目标语言代码（默认 `zh_cn`） |
| `--batch-size` | 每批翻译条数（默认 80，可调小以避免超时） |
| `--model` | 模型（默认 `deepseek-v4-flash`） |

**主会话职责**：
1. 确认源文件存在（输出目录由脚本自动创建，无需 Agent 手动 mkdir）
2. 构造上述命令并执行
3. 等待脚本完成后，验证输出文件的条目数是否与源文件一致
4. 告知用户翻译结果


### 3. 输出文件

按以下结构写入 `assets/` 目录：

```
assets/
  <mod名称>/
    zh_cn.json    ← 简体中文翻译
    zh_hk.json    ← 繁体中文翻译
    ...(其他语言同理)
```

## 翻译规范

### 基本规则

1. **Key 不翻译,仅翻译 Value**：JSON 的 key 必须与源文件完全一致
2. **保留格式占位符**：`%s`、`%d`、`%1$s` 等 Java 格式化占位符必须原样保留
3. **保留 Minecraft 格式码**：
   - `§` + 数字/字母 是 Minecraft 的颜色/格式代码（如 `§6`=金色, `§r`=重置, `§c`=红色, `§a`=绿色）
   - **必须原样保留**这些格式码，不能删除或修改
4. **保留换行符**：`\n` 必须保留在翻译中
5. **保留特殊字符**：`%%` 等转义字符保持不变
6. **格式,顺序,空行等保持不变**

### 翻译风格

- **术语统一**：必须遵守 [glossary.md](glossary.md)（翻译对照表）中的固定搭配，不得自行发挥
- **语气**：保持游戏内提示的友好、简洁风格
- **专有名词**：Mod 名称、技术术语可保留英文不翻译
- 对照表中未覆盖的术语，优先采用 Minecraft 社区通用译法

### 需要特别注意的条目

- 以 `.help.` 或 `.tooltip.` 结尾的 key：通常是帮助/提示文本，需保持信息准确
- 包含 `\n` 的多行文本：翻译后仍需保持可读的换行位置
- `message.unknown` / `message.thats_odd` 类：是错误/异常提示，翻译需让玩家能理解问题

## 示例

**源文件** (`en_us.json`)：
```json
{
    "xray.mod_name": "Advanced XRay",
    "xray.message.added_block": "Successfully added %s.",
    "xray.toggle.activated": "XRay activated"
}
```

**简体中文** (`zh_cn.json`)：
```json
{
    "xray.mod_name": "Advanced XRay",
    "xray.message.added_block": "成功添加了 %s。",
    "xray.toggle.activated": "XRay 已激活"
}
```


## 后续步骤

翻译完成后，可使用 `packaging` skill 将 `assets/<mod>/` 下的翻译文件打包为 Minecraft 资源包 ZIP，即可直接放入游戏的 `resourcepacks/` 目录使用。

## 注意事项

- 源文件 (`sourse/`) 是 **只读** 的，永远不要修改
- 输出目录由脚本自动创建（`os.makedirs`），Agent 无需手动 mkdir
- 翻译完成后告知用户输出路径
