"""
Minecraft Mod language file translator.
Uses DeepSeek API directly (bypassing harness) to translate JSON language files.

Usage:
    python translate.py <source_json> <glossary_md> <output_json> [--model MODEL] [--batch-size N]

The script reads source and glossary files itself — no content is passed from the harness.
"""
import urllib.request
import json
import os
import sys
import time
import argparse

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

# --- Config ---
BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic")
AUTH_TOKEN = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
DEFAULT_MODEL = os.environ.get("CLAUDE_CODE_SUBAGENT_MODEL", "deepseek-v4-flash")

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "anthropic-version": "2023-06-01",
}

TRANSLATION_SYSTEM_PROMPT = """You are a Minecraft Mod translator. Translate English language file entries to Simplified Chinese (zh_cn).

## Rules (MUST follow):
1. Only translate the VALUE, keep the JSON key unchanged
2. Preserve all format placeholders exactly: %s, %d, %1$s, %2$s, etc.
3. Preserve Minecraft color codes exactly: §0-§9, §a-§f, §k-§r, §l, §m, §n, §o
4. Preserve escape sequences: \\n, \\", %%
5. Keep technical terms and mod names in English (e.g. "XRay", "RF", "EU", "CFG")
6. Use natural, fluent Chinese suitable for game UI
7. For tooltips/help text (keys ending in .help, .tooltip, .desc), keep information accurate
8. For error/exception messages, make sure players can understand the problem
9. Follow the provided glossary for term consistency

## Style:
- Friendly, concise game UI tone
- Prefer Minecraft community standard translations when available
- Keep the original structure (line breaks at same positions)

## Output format:
Return ONLY the translated JSON object, with the same keys as the input. No extra text."""


def load_json(path):
    """Load and return JSON file content."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_glossary(path):
    """Load glossary markdown, extract term mappings as a string for the prompt."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        # Extract only the table portions (simple approach: return relevant sections)
        return content
    except FileNotFoundError:
        return "(No glossary file found — use Minecraft community standard translations)"


def build_glossary_section(glossary_text):
    """Build a concise glossary prompt section from glossary markdown."""
    if not glossary_text or glossary_text.startswith("(No glossary"):
        return ""
    return f"\n## Glossary (MUST follow these fixed translations):\n```\n{glossary_text}\n```\n"


def build_custom_glossary_section(custom_glossary, batch_entries):
    """Extract custom glossary entries relevant to this batch (matched by English value)."""
    if not custom_glossary:
        return ""
    relevant = {}
    for en_val in batch_entries.values():
        if en_val in custom_glossary:
            relevant[en_val] = custom_glossary[en_val]
    if not relevant:
        return ""
    lines = ["\n## Confirmed translations — MUST use EXACTLY (manually verified):"]
    for en, zh in relevant.items():
        lines.append(f'- "{en}" → "{zh}"')
    return "\n".join(lines) + "\n"


def translate_batch(model, entries, glossary_text, target_lang="zh_cn", custom_glossary=None):
    """Call DeepSeek API to translate a batch of key-value pairs."""
    entries_json = json.dumps(entries, ensure_ascii=False, indent=2)
    glossary_section = build_glossary_section(glossary_text)
    custom_section = build_custom_glossary_section(custom_glossary, entries)

    user_message = f"""Translate the following Minecraft Mod language entries from English to {target_lang}.

{glossary_section}{custom_section}
## Entries to translate:
```json
{entries_json}
```

Return ONLY the translated JSON object. Keep all keys, placeholders (%s, %d, etc.), and color codes (§) exactly as-is."""

    body = {
        "model": model,
        "max_tokens": 64000,
        "system": TRANSLATION_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_message}],
    }

    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/v1/messages",
        data=data,
        headers=HEADERS,
        method="POST",
    )

    max_retries = 3
    for attempt in range(max_retries):
        if attempt > 0:
            print(f"  Retrying (attempt {attempt + 1}/{max_retries})...")
        print("  Sending request...", end="", flush=True)
        t_start = time.time()
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                elapsed = time.time() - t_start
                print(f"\r  Response received in {elapsed:.1f}s")
                result = json.loads(resp.read().decode("utf-8"))
                # Extract text from response
                for block in result.get("content", []):
                    if block.get("type") == "text":
                        text = block["text"]
                        # Try to extract JSON from the response
                        return extract_json(text)
                return None
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            print(f"  API error ({e.code}): {body_text[:300]}")
            if e.code == 429 and attempt < max_retries - 1:
                wait = 2 ** attempt * 5
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return None
        except Exception as e:
            print(f"  Request failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return None
    return None


def extract_json(text):
    """Extract JSON object from model response text."""
    text = text.strip()
    # Try to find JSON within markdown code blocks
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        text = text[start:end].strip()

    # Try parsing directly
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object boundaries
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start >= 0 and brace_end > brace_start:
        try:
            return json.loads(text[brace_start:brace_end + 1])
        except json.JSONDecodeError:
            pass

    print(f"  WARNING: Could not parse JSON from response. Raw: {text[:200]}...")
    return None


def merge_translations(original, translated_batches):
    """Merge all translated batches back into the original key order."""
    result = {}
    for batch_dict in translated_batches:
        if batch_dict:
            result.update(batch_dict)

    # Preserve original key order, filling in translations where available
    ordered = {}
    for key in original:
        if key in result:
            ordered[key] = result[key]
        else:
            ordered[key] = original[key]  # Fallback to original
            print(f"  WARNING: Key '{key}' not translated, using original")

    return ordered


def main():
    parser = argparse.ArgumentParser(description="Minecraft Mod language file translator")
    parser.add_argument("source", help="Path to source JSON (e.g. en_us.json)")
    parser.add_argument("glossary", help="Path to glossary markdown")
    parser.add_argument("output", help="Path for output translated JSON")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model to use for translation")
    parser.add_argument("--batch-size", type=int, default=80, help="Entries per API call")
    parser.add_argument("--target-lang", default="zh_cn", help="Target language code")
    parser.add_argument("--custom-glossary", default=None,
                        help="Path to custom glossary JSON (English→Chinese mappings from manual corrections)")
    parser.add_argument("--previous-zh", default=None,
                        help="Path to previous zh_cn.json for version iteration (reuses existing translations)")
    args = parser.parse_args()

    if not AUTH_TOKEN:
        print("ERROR: ANTHROPIC_AUTH_TOKEN not set in environment")
        sys.exit(1)

    print(f"Source: {args.source}")
    print(f"Glossary: {args.glossary}")
    print(f"Output: {args.output}")
    print(f"Model: {args.model}")
    print(f"Batch size: {args.batch_size}")
    print()

    # Load files
    print("Loading source file...")
    source = load_json(args.source)
    print(f"  {len(source)} entries loaded")

    print("Loading glossary...")
    glossary_text = load_glossary(args.glossary)
    print(f"  {len(glossary_text)} chars")

    # Load custom glossary (English→Chinese confirmed translations)
    custom_glossary = None
    if args.custom_glossary:
        print("Loading custom glossary...")
        custom_glossary = load_json(args.custom_glossary)
        print(f"  {len(custom_glossary)} confirmed terms")

    # Load previous translation for version iteration
    reused_translations = {}
    if args.previous_zh:
        print("Loading previous translation...")
        previous_zh = load_json(args.previous_zh)
        for k in source:
            if k in previous_zh:
                reused_translations[k] = previous_zh[k]
        print(f"  {len(reused_translations)} entries reused from previous translation")

    # Determine what needs translating
    to_translate = {k: v for k, v in source.items() if k not in reused_translations}
    new_count = len(to_translate)
    reused_count = len(reused_translations)

    if reused_count > 0:
        print(f"\nReusing {reused_count} entries | Translating {new_count} new entries")
    else:
        print(f"\nTranslating all {new_count} entries")

    # Prepare batches from only the new/changed entries
    items = list(to_translate.items())
    batches = []
    for i in range(0, len(items), args.batch_size):
        batch = dict(items[i:i + args.batch_size])
        batches.append(batch)

    if batches:
        print(f"{len(batches)} batch(es) to process\n")
    else:
        print("No new entries to translate — all reused.\n")

    # Translate
    translated = []
    for idx, batch in enumerate(batches):
        batch_keys = list(batch.keys())
        first_key = batch_keys[0]
        last_key = batch_keys[-1]
        print(f"Batch {idx + 1}/{len(batches)}: keys {first_key[:50]}... → ...{last_key[-50:]}")

        t0 = time.time()
        result = translate_batch(args.model, batch, glossary_text, args.target_lang, custom_glossary)
        elapsed = time.time() - t0
        if result:
            translated.append(result)
            print(f"  OK: {len(result)} entries translated ({elapsed:.1f}s)")
        else:
            print(f"  FAILED: batch {idx + 1} could not be translated ({elapsed:.1f}s)")
            translated.append({})

    # Merge: start with reused translations, then overlay newly translated
    print("\nMerging translations...")
    final = dict(reused_translations)
    for batch_dict in translated:
        if batch_dict:
            final.update(batch_dict)

    # Preserve original key order, filling gaps with source as fallback
    ordered = {}
    for key in source:
        if key in final:
            ordered[key] = final[key]
        else:
            ordered[key] = source[key]  # Fallback to original English
            print(f"  WARNING: Key '{key}' not translated, using original")
    final = ordered

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    translated_count = sum(1 for k, v in final.items() if v != source.get(k, ""))
    print(f"\nDone! {translated_count}/{len(source)} entries translated → {args.output}")


if __name__ == "__main__":
    main()
