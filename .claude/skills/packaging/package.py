"""
Package translated language files into a Minecraft resource pack ZIP.

Usage:
    python package.py <assets_dir> <output_zip> [--mod-name NAME] [--description DESC]
"""
import zipfile
import json
import os
import sys
import argparse
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')


# Standard pack.mcmeta template
PACK_MCMETA = {
    "pack": {
        "pack_format": 34,  # Minecraft 1.21+
        "description": "{description}"
    }
}


def create_resource_pack(assets_dir, output_zip, description="Mod Translation Pack"):
    """Create a Minecraft resource pack ZIP from translated language files."""
    # Find all language files in assets dir
    lang_files = {}
    for root, dirs, files in os.walk(assets_dir):
        for f in files:
            if f.endswith(".json"):
                full_path = os.path.join(root, f)
                # Determine relative path structure
                rel = os.path.relpath(full_path, assets_dir)
                lang_files[rel] = full_path

    if not lang_files:
        print("ERROR: No JSON files found in assets directory")
        return False

    # Determine mod structure from first file
    first_rel = next(iter(lang_files))
    # Expected: <modname>/<lang_code>.json

    os.makedirs(os.path.dirname(output_zip) or ".", exist_ok=True)

    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        # Write pack.mcmeta
        mcmeta = PACK_MCMETA.copy()
        mcmeta["pack"]["description"] = description
        zf.writestr("pack.mcmeta", json.dumps(mcmeta, indent=2, ensure_ascii=False))

        # Determine modname from assets_dir basename (for 1-level deep case)
        assets_basename = os.path.basename(os.path.normpath(assets_dir.rstrip("/\\")))

        # Write each language file with correct resource pack path structure
        for rel_path, full_path in lang_files.items():
            parts = rel_path.replace("\\", "/").split("/")
            if len(parts) == 2:
                modname = parts[0]
                filename = parts[1]
            elif len(parts) == 1:
                # assets_dir is already the mod directory (e.g. assets/xaeroworldmap/)
                modname = assets_basename
                filename = parts[0]
            else:
                # Nested deeper — use first dir as modname
                modname = parts[0]
                filename = parts[-1]
            # Resource pack format: assets/<modname>/lang/<lang_code>.json
            archive_path = f"assets/{modname}/lang/{filename}"
            zf.write(full_path, archive_path)
            print(f"  + {archive_path}")

    size = os.path.getsize(output_zip)
    print(f"\nPack created: {output_zip} ({size} bytes)")

    # List contents
    with zipfile.ZipFile(output_zip, "r") as zf:
        print(f"  Contents: {len(zf.namelist())} files")
        for name in zf.namelist():
            print(f"    {name}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Package language files into Minecraft resource pack")
    parser.add_argument("assets_dir", help="Directory containing translated JSON files")
    parser.add_argument("output_zip", help="Output ZIP path (e.g. packages/<mod>/<mod>-trans.zip)")
    parser.add_argument("--description", default="Mod Translation Pack",
                        help="Resource pack description (default: 'Mod Translation Pack')")
    args = parser.parse_args()

    if not os.path.isdir(args.assets_dir):
        print(f"ERROR: Assets directory not found: {args.assets_dir}")
        sys.exit(1)

    print(f"Packaging: {args.assets_dir} -> {args.output_zip}")
    success = create_resource_pack(args.assets_dir, args.output_zip, args.description)

    if success:
        print("Done!")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
