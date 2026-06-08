---
name: diff-glossary
description: 对比原始翻译与人工修正后的语言文件，提取差异生成专有词汇表
---

# diff-glossary — 提取人工修正词汇表

## 概述

当用户对 `zh_cn.json` 进行人工修正后，本 skill 对比修正前后的差异，结合 `en_us.json` 英文源文件，生成专有词汇表（custom glossary）。该词汇表可在后续翻译中作为硬约束，确保已修正的术语不再翻偏。

## 工作流位置

本 skill 是翻译工作流的**辅助步骤**，在 `trans-json` 之后按需使用：

```
② trans-json                      ②.5 diff-glossary (本 skill)         ② trans-json (下次迭代)
assets/<mod>/zh_cn.json  ──人工修正──→  zh_cn-modified.json  ──对比──→  custom_glossary.json  ──喂入──→  新版本翻译
```

## 前置条件

- `sourse/<mod>/en_us.json` — 英文源文件
- `assets/<mod>/zh_cn.json` — 原始机器翻译（未经人工修正）
- `assets/<mod>/zh_cn-modified.json` — 用户手工修正后的版本

## 工作流程

### 1. 确认文件

检查三个文件是否存在：
```
sourse/<mod>/en_us.json          ← 英文源
assets/<mod>/zh_cn.json          ← 原始翻译（改前）
assets/<mod>/zh_cn-modified.json ← 人工修正（改后）
```

如果用户直接在 `zh_cn.json` 上修改、没有保留改前副本，需先通过 `trans-json` 重新生成一份原始翻译作对比基准。

### 2. 执行对比

```bash
python .claude/skills/diff-glossary/diff_glossary.py \
    "sourse/<mod>/en_us.json" \
    "assets/<mod>/zh_cn.json" \
    "assets/<mod>/zh_cn-modified.json" \
    --output-dict "assets/<mod>/custom_glossary.json" \
    --output-md  "assets/<mod>/custom_glossary.md"
```

**工作原理**：
- 逐 key 比较 `zh_cn.json` 和 `zh_cn-modified.json` 的 value
- 对每个不一致的 key，从 `en_us.json` 取对应的英文原文
- 以 `{英文原文: 修正后中文}` 格式输出

**参数说明**：
| 参数 | 说明 |
|---|---|
| 位置参数 1 | 英文源文件路径 |
| 位置参数 2 | 原始翻译路径（改前） |
| 位置参数 3 | 人工修正路径（改后） |
| `--output-dict` | 输出 JSON 词典（供 translate.py `--custom-glossary` 使用） |
| `--output-md` | 输出 Markdown 表格（供查阅或追加到 glossary.md） |

### 3. 后续使用

生成的 `custom_glossary.json` 可在下次翻译时通过 `--custom-glossary` 参数喂给 `translate.py`：

```bash
python .claude/skills/trans-json/translate.py \
    "sourse/<mod>/en_us.json" \
    ".claude/skills/trans-json/glossary.md" \
    "assets/<mod>/zh_cn.json" \
    --custom-glossary "assets/<mod>/custom_glossary.json"
```

此时译文中匹配到 custom glossary 的条目会被强制使用已确认的翻译。

版本迭代时配合 `--previous-zh` 使用：

```bash
python .claude/skills/trans-json/translate.py \
    "sourse/<mod>/en_us.json" \
    ".claude/skills/trans-json/glossary.md" \
    "assets/<mod>/zh_cn.json" \
    --previous-zh "assets/<mod>/zh_cn.json" \
    --custom-glossary "assets/<mod>/custom_glossary.json"
```

- `--previous-zh`：复用旧版已翻译的 key，只翻译新增条目
- `--custom-glossary`：新增条目翻译时强制遵循人工修正过的术语

### 4. 告知用户

报告差异条目数量、输出文件路径。建议用户审阅生成的词汇表，将通用性强的条目手动合并到 `glossary.md`。

## 注意事项

- 三个源文件均**只读**，脚本不会修改它们
- 输出到 `assets/<mod>/` 目录，不应打包进资源包（package.py 会将其打包，需注意清理）
- 仅对比 value 差异，不关心 key 顺序或 JSON 格式变化
- 空值条目自动跳过
- 若差异条目数为 0，说明没有人工修正或输入文件错误
