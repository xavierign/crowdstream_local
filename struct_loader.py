"""Utility for loading DJ structure JSON files into a single mapping.

Each JSON file in the target directory is assumed to describe one track.
The returned mapping uses the JSON file name (without extension) as the key
and the parsed JSON document as the value.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def load_track_structs(struct_dir: str | Path) -> Dict[str, Any]:
    """Load all ``*.json`` files from ``struct_dir`` into a dictionary.

    Parameters
    ----------
    struct_dir:
        Directory containing JSON files for each track. The file's stem (file
        name without extension) is used as the dictionary key.

    Returns
    -------
    dict
        Mapping of ``{file_stem: json_contents}`` for every ``*.json`` file in
        the directory. Files are processed in sorted order to keep deterministic
        output.
    """

    base = Path(struct_dir).expanduser()
    if not base.is_dir():
        raise NotADirectoryError(f"Struct directory does not exist: {base}")

    tracks: Dict[str, Any] = {}
    for json_path in sorted(base.glob("*.json")):
        with json_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        key = json_path.stem
        if key in tracks:
            raise ValueError(f"Duplicate track key encountered: {key}")
        tracks[key] = data

    return tracks


def _main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Load all JSON track struct files from a directory and emit a single "
            "dictionary keyed by file name."
        )
    )
    parser.add_argument(
        "struct_dir",
        nargs="?",
        default="/Users/xaviergonzalez/Documents/repos/crowdstream/dj/struct",
        help="Directory containing track JSON files (default: user's DJ struct folder)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Optional path to write the aggregated JSON mapping; prints to stdout when omitted.",
    )
    args = parser.parse_args()

    tracks = load_track_structs(args.struct_dir)
    serialized = json.dumps(tracks, indent=2, ensure_ascii=False)

    if args.output:
        args.output.write_text(serialized + "\n", encoding="utf-8")
    else:
        print(serialized)


if __name__ == "__main__":
    _main()
