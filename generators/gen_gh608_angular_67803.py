"""
Parameterized generator for GH608_angular_67803.

Source PR:    https://github.com/angular/angular/pull/67803
Source Issue: N/A

Seed varies: renames 'angular' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH608_angular_67803'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH608_angular_67803'
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
                files[fpath] = files[fpath].replace('angular', 'angular' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH608_angular_67803',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'angular/angular',
                "pr_number": 67803,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/angular/angular/pull/67803",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'scripts/ci/publish-snapshot-build-artifacts.sh': '#!/usr/bin/env bash\n\nset -x -u -e -o pipefail\n\n# Setup environment\nreadonly thisDir=$(cd $(dirname $0); pwd)\n\nfunction getBuildVersion {\n  # Example of `STABLE_PROJECT_VERSION` for snapshots is: `21.0.0-next.7+sha-7134dfe`\n  local buildVersion=$(\n    pnpm --silent ng-dev release build-env-stamp --mode=snapshot |\n      grep STABLE_PROJECT_VERSION |\n      sed \'s/STABLE_PROJECT_VERSION //\'\n  )\n\n  if [[ -z "${buildVersion}" ]]; then\n    echo "Error: Unable to find the build version." 1>&2\n    exit 1;\n  fi\n\n  echo $buildVersion;\n}\n\nfunction publishRepo {\n  COMPONENT=$1\n  ARTIFACTS_DIR=$2\n\n  BUILD_REPO="${COMPONENT}-builds"\n  REPO_DIR="$(pwd)/tmp/${BUILD_REPO}"\n  REPO_URL="https://github.com/${ORG}/${BUILD_REPO}.git"\n\n  if [ -n "${CREATE_REPOS:-}" ]; then\n    curl -u "$ORG:$TOKEN" https://api.github.com/user/repos \\\n         -d \'{"name":"\'$BUILD_REPO\'", "auto_init": true}\'\n  fi\n\n  echo "Pushing build artifacts to ${ORG}/${BUILD_REPO}"\n\n  # create local repo folder and clone build repo into it\n  rm -rf $REPO_DIR\n  mkdir -p ${REPO_DIR}\n\n  echo "Starting cloning process of ${REPO_URL} into ${REPO_DIR}.."\n\n  (\n    if [[ $(git ls-remote --heads ${REPO_URL} ${BRANCH}) ]]; then\n      echo "Branch ${BRANCH} already exists. Cloning that branch."\n      git clone ${REPO_URL} ${REPO_DIR} --depth 100 --branch ${BRANCH}\n\n      cd ${REPO_DIR}\n      echo "Cloned repository and switched into the repository directory (${REPO_DIR})."\n    else\n      echo "Branch ${BRANCH} does not exist on ${BUILD_REPO} yet."\n      echo "Cloning default branch and creating branch \'${BRANCH}\' on top of it."\n\n       git clone ${REPO_URL} ${REPO_DIR} --depth 100\n      cd ${REPO_DIR}\n\n      echo "Cloned repository and switched into directory. Creating new branch now.."\n\n      git checkout -b ${BRANCH}\n    fi\n  )\n\n  # copy over build artifacts into the repo directory\n  rm -rf $REPO_DIR/*\n  cp -R $ARTIFACTS_DIR/* $REPO_DIR/\n\n  if [[ ${CI} ]]; then\n    (\n      cd $REPO_DIR && \\\n      git config credential.helper "store --file=$HOME/.git_credentials"\n    )\n  fi\n  echo `date` > $REPO_DIR/BUILD_INFO\n  echo $SHA >> $REPO_DIR/BUILD_INFO\n\n  (\n    cd $REPO_DIR && \\\n    git config user.name "${COMMITTER_USER_NAME}" && \\\n    git config user.email "${COMMITTER_USER_EMAIL}" && \\\n    git add --all && \\\n    git commit -m "${COMMIT_MSG}" --quiet && \\\n    git tag "${BUILD_VER}" --force && \\\n    git push origin "${BRANCH}" --tags --force\n  )\n}\n\n# Publish all individual packages from packages-dist.\nfunction publishPackages {\n  GIT_SCHEME=$1\n  PKGS_DIST=$2\n  BRANCH=$3\n  BUILD_VER=$4\n\n  for dir in $PKGS_DIST/*/\n  do\n    if [[ ! -f "$dir/package.json" ]]; then\n      # Only publish directories that contain a `package.json` file.\n      echo "Skipping $dir, it does not contain a package to be published."\n      continue\n    fi\n\n    COMPONENT="$(basename ${dir})"\n\n    # Replace _ with - in component name.\n    COMPONENT="${COMPONENT//_/-}"\n    JS_BUILD_ARTIFACTS_DIR="${dir}"\n\n    if [[ "$GIT_SCHEME" == "ssh" ]]; then\n      REPO_URL="git@github.com:${ORG}/${COMPONENT}-builds.git"\n    elif [[ "$GIT_SCHEME" == "http" ]]; then\n      REPO_URL="https://github.com/${ORG}/${COMPONENT}-builds.git"\n    else\n      die "Don\'t have a way to publish to scheme $GIT_SCHEME"\n    fi\n\n    publishRepo "${COMPONENT}" "${JS_BUILD_ARTIFACTS_DIR}"\n  done\n\n  echo "Finished publishing build artifacts"\n}\n\nfunction publishAllBuilds() {\n  GIT_SCHEME="$1"\n\n  SHA=`git rev-parse HEAD`\n  COMMIT_MSG=`git log --oneline -1`\n  COMMITTER_USER_NAME=`git --no-pager show -s --format=\'%cN\' HEAD`\n  COMMITTER_USER_EMAIL=`git --no-pager show -s --format=\'%cE\' HEAD`\n  PACKAGES_DIST="$(pwd)/dist/packages-dist"\n\n  local buildVersion=`getBuildVersion`\n\n  publishPackages $GIT_SCHEME $PACKAGES_DIST $CUR_BRANCH $buildVersion\n}\n\n# See docs/DEVELOPER.md for help\nCUR_BRANCH=$(git symbolic-ref --short HEAD)\nif [ $# -gt 0 ]; then\n  ORG=$1\n  publishAllBuilds "ssh"\nelse\n  ORG="angular"\n  publishAllBuilds "http"\nfi\n',
        }
