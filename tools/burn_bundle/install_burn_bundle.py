from __future__ import annotations

import argparse
import shutil
from pathlib import Path


SKIP_NAMES = {"app.bin", "burn.log", "burn_tool.log"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install the repo-local burn bundle into a target burn directory."
    )
    parser.add_argument("--target-burn-dir", required=True, help="Target burn directory in this repo")
    parser.add_argument(
        "--platform",
        choices=("windows", "linux", "all"),
        default="all",
        help="Which platform bundle payload to install",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing bundle files")
    return parser.parse_args()


def iter_payload_files(bundle_root: Path, platform: str) -> list[tuple[Path, Path]]:
    selected = ["windows", "linux"] if platform == "all" else [platform]
    payloads: list[tuple[Path, Path]] = []
    for name in selected:
        platform_root = bundle_root / name
        if not platform_root.exists():
            continue
        for src in sorted(path for path in platform_root.rglob("*") if path.is_file()):
            if src.name in SKIP_NAMES:
                continue
            payloads.append((platform_root, src))
    return payloads


def main() -> int:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    bundle_root = script_dir
    target_dir = Path(args.target_burn_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    if not bundle_root.exists():
        raise SystemExit(f"Missing local burn bundle: {bundle_root}")

    payload_files = iter_payload_files(bundle_root, args.platform)
    if not payload_files:
        raise SystemExit(f"No bundle files found under: {bundle_root}")

    copied: list[str] = []
    skipped: list[str] = []
    for platform_root, src in payload_files:
        relative_path = src.relative_to(platform_root)
        dst = target_dir / relative_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and not args.force:
            skipped.append(str(dst))
            continue
        shutil.copy2(src, dst)
        copied.append(str(dst))

    if copied:
        print("Copied:")
        for item in copied:
            print(f"  {item}")
    if skipped:
        print("Skipped existing files:")
        for item in skipped:
            print(f"  {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
