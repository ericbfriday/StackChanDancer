"""Portable command line entry point. No firmware flashing or uploading."""

import argparse
import json
from pathlib import Path

from jsonschema.exceptions import ValidationError

from .contract import validate
from .mapping import map_dance


def write_json(path, value):
    path.write_text(json.dumps(value, separators=(",", ":"), allow_nan=False) + "\n",
                    encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="Analyze an audio file and map choreography")
    build.add_argument("audio", type=Path)
    build.add_argument("--out", type=Path, default=Path("build"))
    build.add_argument("--force", action="store_true", help="Replace generated output files")
    check = sub.add_parser("validate", help="Validate a dance file and optional PCM")
    check.add_argument("dance", type=Path)
    check.add_argument("--pcm", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "validate":
            validate(json.loads(args.dance.read_text(encoding="utf-8")), args.pcm)
            print("Valid Stack-chan Dance v1")
            return

        if not args.audio.is_file():
            raise ValueError(f"Audio file does not exist: {args.audio}")
        targets = [args.out / name for name in
                   ("features.json", "dance.json", "playback.pcm", "playback.wav")]
        if args.audio.resolve() in [p.resolve() for p in targets]:
            raise ValueError("Input audio cannot also be an output file")
        if not args.force and any(p.exists() for p in targets):
            raise ValueError("Output files already exist; choose another --out or use --force")
        args.out.mkdir(parents=True, exist_ok=True)
        from .analyze import analyze
        features = analyze(args.audio, args.out)
        dance = map_dance(features)
        validate(dance, args.out / "playback.pcm")
        write_json(args.out / "features.json", features)
        write_json(args.out / "dance.json", dance)
        print(f"Built {len(features['beats'])} beats, {features['bpm']:.2f} BPM; "
              f"{len(dance['motion'])} poses -> {args.out}")
    except (ValueError, OSError, ValidationError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
