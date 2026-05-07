"""
Parameterized generator for GH568_dateutil_1467.

Source PR:    https://github.com/dateutil/dateutil/pull/1467
Source Issue: N/A

Seed varies: renames 'been' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH568_dateutil_1467'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH568_dateutil_1467'
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
                files[fpath] = files[fpath].replace('been', 'been' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH568_dateutil_1467',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'dateutil/dateutil',
                "pr_number": 1467,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/dateutil/dateutil/pull/1467",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'ci_tools/run_tz_master_env.sh': '#!/usr/bin/env bash\n\n###\n# Runs the \'tz\' tox test environment, which builds the repo against the master\n# branch of the upstream tz database project.\n\nset -e\n\nTMP_DIR=${1}\nREPO_DIR=${2}\nORIG_DIR=$(pwd)\nCITOOLS_DIR=$REPO_DIR/ci_tools\n\nREPO_TARBALL=${REPO_DIR}/src/dateutil/zoneinfo/dateutil-zoneinfo.tar.gz\nTMP_TARBALL=${TMP_DIR}/dateutil-zoneinfo.tar.gz\n\nUPSTREAM_URL="https://github.com/eggert/tz.git"\n\nif [ -n "$TF_BUILD" ]; then\n    EXTRA_TEST_ARGS=--junitxml=../unittests/TEST-tz.xml\nfi\n\nfunction cleanup {\n    # Since this script modifies the original repo, whether or not\n    # it fails we need to restore the original file so as to not\n    # overwrite the user\'s local changes.\n    echo "Cleaning up."\n    if [ -f $TMP_TARBALL ]; then\n        cp -p $TMP_TARBALL $REPO_TARBALL\n    fi\n}\n\ntrap cleanup EXIT\n\n# Work in a temporary directory\ncd $TMP_DIR\n\n# Clone or update the repo\nDIR_EXISTS=false\nif [ -d tz ]; then\n    cd tz\n    if [[ $(git remote get-url origin) == ${UPSTREAM_URL} ]]; then\n        git fetch origin master\n        git reset --hard origin/master\n        DIR_EXISTS=true\n    else\n        cd ..\n        rm -rf tz\n    fi\nfi\n\nif [ "$DIR_EXISTS" = false ]; then\n    git clone ${UPSTREAM_URL}\n    cd tz\nfi\n\n# Get the version\nmake version\nVERSION=$(cat version)\nTARBALL_NAME=tzdata${VERSION}.tar.gz\n\n# Make the tzdata tarball - deactivate errors because\n# I don\'t know how to make just the .tar.gz and I don\'t\n# care if the others fail\nset +e\nmake traditional_tarballs\nset -e\n\nmv $TARBALL_NAME $ORIG_DIR\n\n# Install everything else\nmake ZFLAGS=\'-b fat\' TOPDIR="$TMP_DIR/tzdir" install\n\n#\n# Make the zoneinfo tarball\n#\ncd $ORIG_DIR\n\n# Put the latest version of zic on the path\nPATH=$TMP_DIR/tzdir/usr/sbin:${PATH}\n\n# Stash the old zoneinfo file in the temporary directory\nmv $REPO_TARBALL $TMP_TARBALL\n\n\n# Make the metadata file\nZONEFILE_METADATA_NAME=zonefile_metadata_master.json\n${CITOOLS_DIR}/make_zonefile_metadata.py \\\n    $TARBALL_NAME \\\n    $VERSION \\\n    $ZONEFILE_METADATA_NAME\n\npython ${REPO_DIR}/updatezinfo.py $ZONEFILE_METADATA_NAME\n\n# Run the tests\npython -m pytest ${REPO_DIR}/tests $EXTRA_TEST_ARGS\n\n',
        }
