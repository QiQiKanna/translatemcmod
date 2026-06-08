## 简介

### 概述

该工作区用于 Minecraft Mod 语言文件的翻译工作。完整工作流为：**从 JAR 提取源文件 → 翻译 → 打包为资源包**，三步均由对应 skill 驱动。

### 架构原则

**Agent 负责判断，Python 脚本负责执行。** Agent 识别模组、确认选项、调度流程；脚本完成确定性的提取/翻译/打包工作。Agent 不读取源文件内容——只向脚本传递文件路径。

**子代理不可用。** 当前环境（DeepSeek provider）下 Agent/Workflow 工具均不可用（harness 参数冲突），翻译通过 Python 脚本直调 API 完成。

### 工作流

```
mods/<mod>.jar                    ← 用户放入的模组 JAR 包
       │ ① extract-json（提取）
       ▼
sourse/<mod>/en_us.json           ← 英文源语言文件（只读）
       │ ② trans-json（翻译）
       ▼
assets/<mod>/zh_cn.json           ← 翻译后的语言文件
assets/<mod>/zh_hk.json           ← （繁体中文等可选）
       │ ③ packaging（打包）
       ▼
packages/<mod>/<mod>-trans.zip    ← 可直接使用的资源包
```

| 顺序 | Skill | 调度脚本 | 功能 |
|---|---|---|---|
| ① | `extract-json` | `extract.py` | 从 JAR 提取语言文件 |
| ② | `trans-json` | `translate.py` | 分批调 API 翻译 |
| ③ | `packaging` | `package.py` | 打包为资源包 ZIP |

### 工作区结构

```
translatemcmod/
    .claude/
        skills/
            extract-json/
                SKILL.md              ← ① 提取 skill（Agent 读取）
                extract.py            ← 提取脚本
            trans-json/
                SKILL.md              ← ② 翻译 skill（Agent 读取）
                translate.py          ← 翻译脚本（直调 API）
                glossary.md           ← 术语对照表（脚本 Read）
            packaging/
                SKILL.md              ← ③ 打包 skill（Agent 读取）
                package.py            ← 打包脚本
    assets/                           ← 翻译后的文件
        <mod>/
            zh_cn.json                ← 简体中文
            zh_hk.json                ← 繁体中文（香港）
            ...
    mods/                             ← 模组 JAR 包（只读）
        <mod>.jar
    packages/                         ← 打包后的资源包
        examplemod/
            examplemod-trans.zip      ← 示例包（只读）
        <mod>/
            <mod>-trans.zip
    sourse/                           ← 从 JAR 提取的源文件（只读）
        <mod>/
            en_us.json
    CLAUDE.md
    issue.md                          ← 已知问题记录
```

### 注意事项

- `mods/` — 存放模组 JAR 包，**只读**，绝不修改
- `sourse/` — 存放从 JAR 提取的源语言文件，**只读**，绝不修改
- `assets/` — 翻译后的文件存放目录，子目录 `<mod>/` 可能需要创建
- `packages/` — 打包后的资源包输出目录
- `packages/examplemod/` — 示例翻译包，**只读**，仅作格式参考
- **Agent 不得读取源文件内容到上下文**——翻译时只向脚本传递文件路径
- **翻译不得降级为纯规则替换**——translate.py 通过 API 调 LLM 完成翻译
