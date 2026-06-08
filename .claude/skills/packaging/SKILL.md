---
name: packaging
description: 将 assets/ 下的翻译文件打包为 Minecraft 资源包 ZIP，输出到 packages/
---

# packaging — 翻译文件打包

## 概述

将 `assets/<mod>/` 下已翻译的语言文件打包为 Minecraft 资源包（Resource Pack）格式的 ZIP 文件，输出到 `packages/<mod>/<mod>-trans.zip`。

## 资源包格式

Minecraft 资源包本质是 ZIP 文件，内部结构固定：

```
<mod>-trans.zip
├── pack.mcmeta                    ← 资源包元数据（必需）
├── pack.png                       ← 资源包封面图（可选，512×512）
└── assets/
    └── <modid>/                   ← 模组注册 ID
        └── lang/
            ├── zh_cn.json         ← 简体中文
            ├── zh_hk.json         ← 繁体中文（香港）
            └── ...                ← 其他语言
```

**参考示例**：`packages/examplemod/examplemod-trans.zip`（只读，仅作参考）

## pack.mcmeta 格式

```json
{
    "pack": {
        "description": "<描述文本>",
        "pack_format": 55,
        "supported_formats": [34, 64],
        "min_format": 34,
        "max_format": [69, 0]
    }
}
```

| 字段 | 说明 |
|---|---|
| `description` | 包描述，自由填写，建议注明翻译来源 |
| `pack_format` | 资源包格式版本，与 Minecraft 版本对应 |
| `supported_formats` | 支持的格式范围 |
| `min_format` / `max_format` | 最小/最大兼容格式 |

## 工作流程

### 1. 确认打包目标

检查 `assets/<mod>/` 下已有的翻译文件。若用户未指定语言，默认打包全部。

### 2. 确认 modid

资源包内路径 `assets/<modid>/lang/` 中的 `<modid>` 必须与模组原始注册 ID 一致。优先复用 extract-json 步骤输出的 modid，其次询问用户。

### 3. 执行打包

使用 `.claude/skills/packaging/package.py`：

```bash
python .claude/skills/packaging/package.py "assets/<mod>/" "packages/<mod>/<mod>-trans.zip" --description "<描述>"
```

脚本自动完成：创建输出目录 → 构建 pack.mcmeta → 组织目录结构 → 打包 ZIP。Agent 无需手动 mkdir。

### 4. 验证

脚本会打印包内文件列表。确认结构：`pack.mcmeta` + `assets/<modid>/lang/<语言>.json`。

## 注意事项

- `packages/examplemod/examplemod-trans.zip` 为示例包，**只读，绝不修改**
- 使用 `zipfile.ZIP_DEFLATED` 压缩以减小体积
- 打包前确认 `assets/<mod>/` 下翻译文件已是最新版本
- 若 `packages/<mod>/<mod>-trans.zip` 已存在，询问用户是否覆盖
