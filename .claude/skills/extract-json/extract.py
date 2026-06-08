"""
Extract Minecraft language files from a mod JAR file.
Two-step workflow: scan (discover modids) → extract (with confirmed modid).

Usage:
    # Step 1: Discover what's inside
    python extract.py "mods/axiom.jar" --scan

    # Step 2: Extract with confirmed modid
    python extract.py "mods/axiom.jar" --modid axiom
    python extract.py "mods/axiom.jar" --modid axiom --output-dir sourse/custom/
"""
import zipfile
import json
import os
import sys
import argparse
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')


def scan_jar(jar_path):
    """Scan JAR for all language JSON files.
    Returns: {modid: {lang_code: (internal_path, entry_count), ...}, ...}"""
    result = defaultdict(dict)
    with zipfile.ZipFile(jar_path, "r") as zf:
        for name in zf.namelist():
            # Match: assets/<modid>/lang/<lang_code>.json
            if "/lang/" in name and name.endswith(".json"):
                parts = name.split("/")
                # Expected: ..., "assets", "<modid>", "lang", "<file>.json"
                try:
                    asset_idx = parts.index("assets")
                    if len(parts) >= asset_idx + 4:
                        modid = parts[asset_idx + 1]
                        lang_code = os.path.splitext(parts[-1])[0]
                        # Quick count entries without loading full JSON into memory
                        data = json.loads(zf.read(name).decode("utf-8"))
                        result[modid][lang_code] = (name, len(data))
                except (ValueError, json.JSONDecodeError):
                    continue
    return dict(result)


def print_scan_results(jar_path, found):
    """Print scan results in human-readable format."""
    jar_name = os.path.basename(jar_path)
    print(f"JAR: {jar_name}")
    print(f"Found {len(found)} modid(s):\n")

    for idx, (modid, langs) in enumerate(found.items(), 1):
        primary_lang = "en_us" if "en_us" in langs else next(iter(langs))
        primary_entries = langs[primary_lang][1]
        lang_list = ", ".join(
            f"{code} ({count} entries)" for code, (_, count) in sorted(langs.items())
        )
        print(f"  [{idx}] modid: {modid}")
        print(f"      primary: {primary_lang} ({primary_entries} entries)")
        print(f"      all: {lang_list}")
        print()

    if len(found) == 1:
        modid = next(iter(found))
        print(f"Only one modid found. Recommended: --modid {modid}")
    else:
        print("Multiple modids found. Agent/user must choose which to extract.")
        print("Typically the one with the most en_us entries is the main mod.")


def extract_lang(jar_path, modid, output_dir, primary_lang="en_us", extra_langs=None):
    """Extract language files for a specific modid."""
    with zipfile.ZipFile(jar_path, "r") as zf:
        # Find all lang files for this modid
        available = {}
        prefix = f"assets/{modid}/lang/"
        for name in zf.namelist():
            if name.startswith(prefix) and name.endswith(".json"):
                lang_code = os.path.splitext(name[len(prefix):])[0]
                available[lang_code] = name

    if not available:
        print(f"ERROR: No language files found for modid '{modid}'", file=sys.stderr)
        sys.exit(1)

    print(f"Extracting from modid: {modid}")
    print(f"  Available: {sorted(available.keys())}")
    print(f"  Output: {output_dir}/")

    # Determine output directory
    if output_dir is None:
        output_dir = os.path.join("sourse", modid)
    os.makedirs(output_dir, exist_ok=True)

    # Extract primary language
    if primary_lang not in available:
        print(f"ERROR: '{primary_lang}' not found. Available: {sorted(available.keys())}",
              file=sys.stderr)
        sys.exit(1)

    extracted = []
    with zipfile.ZipFile(jar_path, "r") as zf:
        # Primary
        data = zf.read(available[primary_lang])
        out_path = os.path.join(output_dir, f"{primary_lang}.json")
        with open(out_path, "wb") as f:
            f.write(data)
        entry_count = len(json.loads(data.decode("utf-8")))
        extracted.append((primary_lang, len(data), entry_count))
        print(f"  + {primary_lang}.json ({entry_count} entries, {len(data)} bytes)")

        # Extras
        for lang in (extra_langs or []):
            if lang in available and lang != primary_lang:
                data = zf.read(available[lang])
                out_path = os.path.join(output_dir, f"{lang}.json")
                with open(out_path, "wb") as f:
                    f.write(data)
                entry_count = len(json.loads(data.decode("utf-8")))
                extracted.append((lang, len(data), entry_count))
                print(f"  + {lang}.json ({entry_count} entries, {len(data)} bytes)")

    # Machine-parseable summary for agent
    print(f"\nMODID={modid}")
    print(f"OUTPUT_DIR={output_dir}")
    print(f"ENTRIES={extracted[0][2]}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract Minecraft mod language files. Two-step: --scan then --modid."
    )
    parser.add_argument("jar", help="Path to mod JAR file")
    parser.add_argument("--scan", action="store_true",
                        help="Step 1: scan JAR and list all found modids (no extraction)")
    parser.add_argument("--modid",
                        help="Step 2: modid to extract (from --scan results)")
    parser.add_argument("--output-dir", "-o",
                        help="Output directory (default: sourse/<modid>/)")
    parser.add_argument("--lang", default="en_us",
                        help="Primary language to extract (default: en_us)")
    parser.add_argument("--extra-lang", action="append",
                        help="Additional languages (zh_cn is auto-added if present)")
    args = parser.parse_args()

    if not os.path.exists(args.jar):
        print(f"ERROR: JAR not found: {args.jar}", file=sys.stderr)
        sys.exit(1)

    # Step 1: Scan mode
    if args.scan:
        found = scan_jar(args.jar)
        if not found:
            print("ERROR: No language files found in JAR", file=sys.stderr)
            sys.exit(1)
        print_scan_results(args.jar, found)
        # Output machine-parseable line
        modids = list(found.keys())
        print(f"MODIDS={' '.join(modids)}")
        if len(modids) == 1:
            print(f"RECOMMENDED_MODID={modids[0]}")
        sys.exit(0)

    # Step 2: Extract mode — modid is required
    if not args.modid:
        print("ERROR: --modid is required for extraction.", file=sys.stderr)
        print("  First run --scan to discover available modids.", file=sys.stderr)
        print(f"  Then run: python {sys.argv[0]} \"{args.jar}\" --modid <modid>", file=sys.stderr)
        sys.exit(1)

    extract_lang(
        args.jar,
        args.modid,
        args.output_dir,
        primary_lang=args.lang,
        extra_langs=args.extra_lang,
    )


if __name__ == "__main__":
    main()
