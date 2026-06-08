"""
Compare an automatically translated language file with a manually corrected version,
extracting the corrections into a glossary (English → corrected Chinese).

Usage:
    python diff_glossary.py <en_us.json> <zh_cn.json> <zh_cn-modified.json> [--output-dict <file>] [--output-md <file>]

The script:
  - Loads the three JSON files
  - For every key where zh_cn.json and zh_cn-modified.json differ:
      records { en_us[key] : zh_cn_modified[key] }
  - Outputs a JSON dict and/or a markdown table section
"""
import json
import sys
import os
import argparse


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def diff_translations(en_us, zh_cn, zh_cn_modified):
    """
    Compare zh_cn vs zh_cn_modified, return a dict of:
        { english_value : modified_chinese_value }
    for entries that were changed manually.
    """
    glossary = {}

    all_keys = set(zh_cn_modified.keys())

    for key in sorted(all_keys):
        original = zh_cn.get(key, "")
        modified = zh_cn_modified.get(key, "")
        english = en_us.get(key)

        # Skip keys not in the English source
        if english is None:
            continue

        # Skip if values are identical (no manual change)
        if original == modified:
            continue

        # Skip empty values
        if not modified or not english:
            continue

        glossary[english] = modified

    return glossary


def write_json_dict(glossary, path):
    """Write the glossary as a JSON dict file."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(glossary, f, ensure_ascii=False, indent=2)
    print(f"Glossary dict written: {path} ({len(glossary)} entries)")


def write_markdown(glossary, path):
    """Write the glossary as a markdown table section."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("## 人工修正词汇表\n\n")
        f.write("> 自动生成，基于 zh_cn.json 与 zh_cn-modified.json 的差异。\n\n")
        f.write("| 英文 | 修正后中文 |\n")
        f.write("|---|---|\n")
        for english, chinese in glossary.items():
            # Escape pipe characters in table cells
            en_escaped = english.replace("|", "\\|").replace("\n", "\\n")
            zh_escaped = chinese.replace("|", "\\|").replace("\n", "\\n")
            f.write(f"| {en_escaped} | {zh_escaped} |\n")
    print(f"Glossary markdown written: {path} ({len(glossary)} entries)")


def main():
    parser = argparse.ArgumentParser(
        description="Diff translated JSONs to extract manual corrections as a glossary"
    )
    parser.add_argument("en_us", help="Path to English source JSON")
    parser.add_argument("zh_cn", help="Path to auto-translated zh_cn.json")
    parser.add_argument("zh_cn_modified", help="Path to manually corrected zh_cn.json")
    parser.add_argument("--output-dict", default=None,
                        help="Output path for JSON dict (e.g. assets/<mod>/custom_glossary.json)")
    parser.add_argument("--output-md", default=None,
                        help="Output path for markdown table (e.g. assets/<mod>/custom_glossary.md)")
    args = parser.parse_args()

    print(f"Loading files...")
    en_us = load_json(args.en_us)
    zh_cn = load_json(args.zh_cn)
    zh_cn_modified = load_json(args.zh_cn_modified)
    print(f"  en_us: {len(en_us)} entries")
    print(f"  zh_cn: {len(zh_cn)} entries")
    print(f"  zh_cn_modified: {len(zh_cn_modified)} entries")

    glossary = diff_translations(en_us, zh_cn, zh_cn_modified)
    print(f"\nManual corrections found: {len(glossary)} entries\n")

    if args.output_dict:
        write_json_dict(glossary, args.output_dict)
    if args.output_md:
        write_markdown(glossary, args.output_md)

    # If no output paths given, print summary to stdout
    if not args.output_dict and not args.output_md:
        print("No output path specified (use --output-dict and/or --output-md)")
        if glossary:
            print("\nPreview (first 10):")
            for i, (en, zh) in enumerate(glossary.items()):
                if i >= 10:
                    break
                print(f"  {en[:80]} → {zh[:80]}")


if __name__ == "__main__":
    main()
