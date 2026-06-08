---
name: extract-json
description: 从 mods/ 下的 JAR 包中提取 en_us.json 语言文件，输出到 sourse/<mod>/en_us.json
---

# extract-json — 从 JAR 包提取语言文件

## 概述

从 `mods/` 目录下的 Minecraft Mod JAR 包中提取语言文件到 `sourse/`，为后续翻译工作做准备。

采用**两步流程**：扫描发现 → 确认后提取。避免 Agent 猜测 modid 导致选错。

## 工作流程

### 1. 选择 JAR

列出 `mods/` 下 JAR 文件让用户选择（若只有一个则直接确认）。

### 2. 扫描发现（Step 1）

```bash
python .claude/skills/extract-json/extract.py "mods/<JAR>" --scan
```

脚本输出示例：

```
JAR: axiom.jar
Found 2 modid(s):

  [1] modid: axiom
      primary: en_us (1234 entries)
      all: en_us (1234 entries), zh_cn (567 entries)

  [2] modid: axiombase
      primary: en_us (12 entries)
      all: en_us (12 entries)

MODIDS=axiom axiombase
RECOMMENDED_MODID=axiom     ← 仅单一 modid 时输出
```

### 3. Agent 确认 modid

- **只有一个 modid** 且用户未指定 → 使用推荐值，直接进入提取
- **多个 modid** → 展示给用户选择（通常是条目数最多的那个）
- **用户指定了目录名** → 用 `--output-dir` 覆盖

### 4. 执行提取（Step 2）

```bash
python .claude/skills/extract-json/extract.py "mods/<JAR>" --modid <确认的modid>
```

可选参数：

| 场景 | 命令 |
|---|---|
| 自定义输出目录 | `... --modid axiom --output-dir sourse/my-name/` |
| 额外提取其他语言 | `... --modid axiom --extra-lang zh_hk` |

脚本输出：
```
MODID=axiom
OUTPUT_DIR=sourse/axiom/
ENTRIES=1234
```

### 5. 告知用户

报告提取结果：modid、条目数、输出路径。记录 `MODID` 供后续 `trans-json` 和 `packaging` 使用。

## 注意事项

- `mods/` 目录中的 JAR 文件仅**读取提取**，绝不修改
- 若输出目录已有文件，用 `--output-dir` 指定不同路径或先询问用户
- 扫描步骤的 `RECOMMENDED_MODID` 仅作参考，Agent 应结合目录结构判断
