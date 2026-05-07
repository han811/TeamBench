"""
Parameterized generator for GH1208_pytorch_178062.

Source PR:    https://github.com/pytorch/pytorch/pull/178062
Source Issue: N/A

Seed varies: renames 'aarch64' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH1208_pytorch_178062'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH1208_pytorch_178062'
        )
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        files = self._base_workspace()
        # Apply seed-based renaming to prevent direct memorization
        suffixes = ["", "_alt", "_impl"]
        suffix = suffixes[seed % len(suffixes)]
        if suffix:
            for fpath in list(files.keys()):
                files[fpath] = files[fpath].replace('aarch64', 'aarch64' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH1208_pytorch_178062',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'pytorch/pytorch',
                "pr_number": 178062,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/pytorch/pytorch/pull/178062",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            '.ci/pytorch/smoke_test/check_wheel_tags.py': '"""Validate wheel platform tags and macOS dylib minos.\nSupports two modes:\n1. Pre-install: reads .whl files from PYTORCH_FINAL_PACKAGE_DIR\n2. Post-install: reads metadata from installed torch package (soft warnings)\n- (macOS only) dylib minos matches the wheel platform tag\n"""\n\nimport os\nimport platform\nimport re\nimport subprocess\nimport sys\nimport tempfile\nimport zipfile\nfrom pathlib import Path\n\n\nEXPECTED_PLATFORM_TAGS: dict[str, str] = {\n    "linux": r"_x86_64$",\n    "linux-aarch64": r"_aarch64$",\n    "windows": r"^win_amd64$",\n    "win32": r"^win_amd64$",\n    "macos-arm64": r"^macosx_\\d+_\\d+_arm64$",\n    "darwin": r"^macosx_\\d+_\\d+_(arm64|x86_64)$",\n}\n\n\ndef _extract_wheel_tags(whl_path: Path) -> list[str]:\n    """Extract Tag values from the WHEEL metadata file inside a .whl archive."""\n    tags = []\n    with zipfile.ZipFile(whl_path, "r") as zf:\n        wheel_files = [n for n in zf.namelist() if n.endswith("/WHEEL")]\n        if not wheel_files:\n            return tags\n        content = zf.read(wheel_files[0]).decode("utf-8")\n        for line in content.splitlines():\n            if line.startswith("Tag:"):\n                tags.append(line.split(":", 1)[1].strip())\n    return tags\n\n\ndef _extract_installed_wheel_tags(package: str = "torch") -> list[str]:\n    """Extract Tag values from an installed package\'s WHEEL metadata."""\n    from importlib.metadata import distribution\n\n    dist = distribution(package)\n    wheel_text = dist.read_text("WHEEL")\n    if not wheel_text:\n        return []\n    tags = []\n    for line in wheel_text.splitlines():\n        if line.startswith("Tag:"):\n            tags.append(line.split(":", 1)[1].strip())\n    return tags\n\n\ndef check_wheel_platform_tag() -> None:\n    """Validate that wheel Tags in WHEEL metadata match the expected platform.\n\n    Mode 1: PYTORCH_FINAL_PACKAGE_DIR set → read .whl file (strict, raises on mismatch)\n    Mode 2: No wheel dir → read from installed torch package (soft, prints warnings)\n    """\n    wheel_dir = os.getenv("PYTORCH_FINAL_PACKAGE_DIR", "")\n\n    target_os = os.getenv("TARGET_OS", sys.platform)\n    if target_os == "linux" and platform.machine() == "aarch64":\n        target_os = "linux-aarch64"\n    expected_python = f"cp{sys.version_info.major}{sys.version_info.minor}"\n    abiflags = getattr(sys, "abiflags", "")\n    # free-threaded Python uses \'t\' suffix, detectable via sys._is_gil_enabled()\n    if not abiflags and not getattr(sys, "_is_gil_enabled", lambda: True)():\n        abiflags = "t"\n    expected_abi = f"cp{sys.version_info.major}{sys.version_info.minor}{abiflags}"\n\n    platform_pattern = EXPECTED_PLATFORM_TAGS.get(target_os)\n    if not platform_pattern:\n        print(\n            f"No expected platform pattern for TARGET_OS={target_os}, "\n            "skipping wheel tag check"\n        )\n        return\n\n    # Mode 1: Read from .whl file\n    if wheel_dir and os.path.isdir(wheel_dir):\n        whls = list(Path(wheel_dir).glob("torch-*.whl"))\n        if not whls:\n            print(f"No torch wheel found in {wheel_dir}, skipping wheel tag check")\n            return\n        if len(whls) > 1:\n            raise RuntimeError(\n                f"Expected exactly one torch wheel in {wheel_dir}, "\n                f"found {len(whls)}: {[w.name for w in whls]}"\n            )\n        whl = whls[0]\n        print(f"Checking wheel platform tag for: {whl.name}")\n        tags = _extract_wheel_tags(whl)\n        source = whl.name\n    else:\n        # Mode 2: Read from installed package (soft)\n        print("PYTORCH_FINAL_PACKAGE_DIR not set, reading from installed torch package")\n        try:\n            tags = _extract_installed_wheel_tags("torch")\n            source = "installed torch"\n        except Exception as e:\n            print(f"Could not read installed torch metadata: {e}, skipping")\n            return\n\n    if not tags:\n        raise RuntimeError(f"No Tag found in WHEEL metadata of {source}")\n\n    for tag_str in tags:\n        parts = tag_str.split("-")\n        if len(parts) != 3:\n            msg = (\n                f"Malformed wheel tag \'{tag_str}\' in {source}, "\n                f"expected format: <python>-<abi>-<platform>"\n            )\n            raise RuntimeError(msg)\n\n        python_tag, abi_tag, platform_tag = parts\n\n        print(f"Checking tag: {tag_str} (from {source})")\n        if python_tag != expected_python:\n            msg: str = (\n                f"Python tag mismatch in {source}: "\n                f"got \'{python_tag}\', expected \'{expected_python}\'"\n            )\n            raise RuntimeError(msg)\n\n        if abi_tag != expected_abi:\n            msg = (\n                f"ABI tag mismatch in {source}: "\n                f"got \'{abi_tag}\', expected \'{expected_abi}\'"\n            )\n            raise RuntimeError(msg)\n\n        if not re.search(platform_pattern, platform_tag):\n            msg = (\n                f"Platform tag mismatch in {source}: "\n                f"got \'{platform_tag}\', expected pattern matching "\n                f"\'{platform_pattern}\' for TARGET_OS={target_os}"\n            )\n            raise RuntimeError(msg)\n\n    print(f"OK: Wheel tag(s) valid for {source}: {\', \'.join(tags)}")\n\n\ndef _check_dylibs_minos(dylibs: list, expected_minos: str, source: str) -> None:\n    mismatches = []\n    for dylib in dylibs:\n        try:\n            result = subprocess.run(\n                ["otool", "-l", str(dylib)],\n                capture_output=True,\n                text=True,\n                timeout=30,\n            )\n        except Exception:\n            continue\n\n        minos = None\n        lines = result.stdout.splitlines()\n        for i, line in enumerate(lines):\n            s = line.strip()\n            if "LC_BUILD_VERSION" in s:\n                for j in range(i + 1, min(i + 6, len(lines))):\n                    if lines[j].strip().startswith("minos"):\n                        minos = lines[j].strip().split()[1]\n                        break\n                break\n            if "LC_VERSION_MIN_MACOSX" in s:\n                for j in range(i + 1, min(i + 4, len(lines))):\n                    if lines[j].strip().startswith("version"):\n                        minos = lines[j].strip().split()[1]\n                        break\n                break\n\n        if minos and minos != expected_minos:\n            mismatches.append(f"{dylib.name}: minos={minos}, expected={expected_minos}")\n\n    if mismatches:\n        raise RuntimeError(\n            f"minos/platform tag mismatch in {len(mismatches)} dylib(s):\\n"\n            + "\\n".join(f"  {m}" for m in mismatches)\n        )\n    print(\n        f"OK: All {len(dylibs)} dylib(s) have minos matching "\n        f"platform tag ({expected_minos}) for {source}"\n    )\n\n\ndef check_mac_wheel_minos() -> None:\n    if sys.platform != "darwin":\n        return\n\n    wheel_dir = os.getenv("PYTORCH_FINAL_PACKAGE_DIR", "")\n\n    if wheel_dir and os.path.isdir(wheel_dir):\n        # Mode 1: extract dylibs from .whl file\n        whls = list(Path(wheel_dir).glob("*.whl"))\n        if not whls:\n            print(f"No .whl files in {wheel_dir}, skipping wheel minos check")\n            return\n\n        macos_whl_re = re.compile(r"macosx_(\\d+)_(\\d+)_(\\w+)\\.whl$")\n        for whl in whls:\n            print(f"Checking wheel tag minos for: {whl.name}")\n            m = macos_whl_re.search(whl.name)\n            if not m:\n                print(f"No macOS platform tag in {whl.name}, skipping")\n                continue\n            expected_minos = f"{m.group(1)}.{m.group(2)}"\n\n            with tempfile.TemporaryDirectory() as tmpdir:\n                with zipfile.ZipFile(whl, "r") as zf:\n                    dylib_names = [n for n in zf.namelist() if n.endswith(".dylib")]\n                    if not dylib_names:\n                        print("No .dylib files in wheel, skipping minos check")\n                        continue\n                    for name in dylib_names:\n                        zf.extract(name, tmpdir)\n                dylibs = list(Path(tmpdir).rglob("*.dylib"))\n                _check_dylibs_minos(dylibs, expected_minos, whl.name)\n    else:\n        # Mode 2: read from installed torch package\n        print("PYTORCH_FINAL_PACKAGE_DIR not set, checking installed torch dylibs")\n        try:\n            tags = _extract_installed_wheel_tags("torch")\n        except Exception as e:\n            print(f"Could not read installed torch metadata: {e}, skipping")\n            return\n\n        expected_minos = None\n        for tag_str in tags:\n            m = re.search(r"macosx_(\\d+)_(\\d+)_\\w+", tag_str)\n            if m:\n                expected_minos = f"{m.group(1)}.{m.group(2)}"\n                break\n\n        if not expected_minos:\n            print("No macOS platform tag found in installed torch metadata, skipping")\n            return\n\n        print(f"Expected minos from installed wheel tag: {expected_minos}")\n\n        import torch\n\n        torch_dir = Path(torch.__file__).parent\n        dylibs = list(torch_dir.rglob("*.dylib"))\n        if not dylibs:\n            raise RuntimeError("No .dylib files found in installed torch")\n        _check_dylibs_minos(dylibs, expected_minos, "installed torch")\n\n\nif __name__ == "__main__":\n    check_wheel_platform_tag()\n    check_mac_wheel_minos()\n',
        }
