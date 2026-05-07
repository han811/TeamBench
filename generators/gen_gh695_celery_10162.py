"""
Parameterized generator for GH695_celery_10162.

Source PR:    https://github.com/celery/celery/pull/10162
Source Issue: N/A

Seed varies: renames 'build' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH695_celery_10162'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH695_celery_10162'
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
                files[fpath] = files[fpath].replace('build', 'build' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH695_celery_10162',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'celery/celery',
                "pr_number": 10162,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/celery/celery/pull/10162",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'requirements/extras/pytest.txt': 'pytest-celery[all]>=1.2.0,<1.3.0\n',
            'requirements/test.txt': 'pytest==9.0.2\npytest-celery[all]>=1.2.0,<1.3.0\npytest-rerunfailures>=15.0; python_version >= "3.9"\npytest-subtests>=0.14.1; python_version >= "3.9"\npytest-timeout==2.4.0\npytest-click==1.1.0\npytest-order==1.3.0\nboto3>=1.26.143\nmoto>=4.1.11,<5.1.0\n# type checking\nmypy==1.19.1; platform_python_implementation=="CPython"\npre-commit>=4.0.1; python_version >= \'3.9\'\n-r extras/yaml.txt\n-r extras/msgpack.txt\n-r extras/mongodb.txt\n-r extras/gcs.txt\n-r extras/pydantic.txt\n-r extras/azureblockblob.txt\n-r extras/gevent.txt\n',
            't/smoke/workers/docker/dev': 'FROM python:3.13-bookworm\n\n# Create a user to run the worker\nRUN adduser --disabled-password --gecos "" test_user\n\n# Install system dependencies\nRUN apt-get update && apt-get install -y build-essential \\\n    git \\\n    wget \\\n    make \\\n    curl \\\n    apt-utils \\\n    debconf \\\n    lsb-release \\\n    libmemcached-dev \\\n    libffi-dev \\\n    ca-certificates \\\n    pypy3 \\\n    pypy3-lib \\\n    sudo\n\n# Set arguments\nARG CELERY_LOG_LEVEL=INFO\nARG CELERY_WORKER_NAME=celery_dev_worker\nARG CELERY_WORKER_QUEUE=celery\nENV LOG_LEVEL=$CELERY_LOG_LEVEL\nENV WORKER_NAME=$CELERY_WORKER_NAME\nENV WORKER_QUEUE=$CELERY_WORKER_QUEUE\n\nENV PYTHONUNBUFFERED=1\nENV PYTHONDONTWRITEBYTECODE=1\n\nEXPOSE 5678\n\n# Install celery from source\nWORKDIR /celery\n\nCOPY --chown=test_user:test_user . /celery\nRUN pip install --no-cache-dir --upgrade \\\n    pip \\\n    -e /celery[redis,pymemcache,pydantic,sqs] \\\n    pytest-celery>=1.1.3\n\n# The workdir must be /app\nWORKDIR /app\n\n# Switch to the test_user\nUSER test_user\n\n# Start the celery worker\nCMD celery -A app worker --loglevel=$LOG_LEVEL -n $WORKER_NAME@%h -Q $WORKER_QUEUE\n',
            't/smoke/workers/docker/pypi': 'FROM python:3.10-bookworm\n\n# Create a user to run the worker\nRUN adduser --disabled-password --gecos "" test_user\n\n# Install system dependencies\nRUN apt-get update && apt-get install -y build-essential \\\n    git \\\n    wget \\\n    make \\\n    curl \\\n    apt-utils \\\n    debconf \\\n    lsb-release \\\n    libmemcached-dev \\\n    libffi-dev \\\n    ca-certificates \\\n    pypy3 \\\n    pypy3-lib \\\n    sudo\n\n# Set arguments\nARG CELERY_VERSION=""\nARG CELERY_LOG_LEVEL=INFO\nARG CELERY_WORKER_NAME=celery_tests_worker\nARG CELERY_WORKER_QUEUE=celery\nENV PIP_VERSION=$CELERY_VERSION\nENV LOG_LEVEL=$CELERY_LOG_LEVEL\nENV WORKER_NAME=$CELERY_WORKER_NAME\nENV WORKER_QUEUE=$CELERY_WORKER_QUEUE\n\nENV PYTHONUNBUFFERED=1\nENV PYTHONDONTWRITEBYTECODE=1\n\nEXPOSE 5678\n\n# Install Python dependencies\nRUN pip install --no-cache-dir --upgrade \\\n    pip \\\n    celery[redis,pymemcache]${CELERY_VERSION:+==$CELERY_VERSION} \\\n    pytest-celery[sqs]>=1.1.3 \\\n    pydantic>=2.4\n\n# The workdir must be /app\nWORKDIR /app\n\n# Switch to the test_user\nUSER test_user\n\n# Start the celery worker\nCMD celery -A app worker --loglevel=$LOG_LEVEL -n $WORKER_NAME@%h -Q $WORKER_QUEUE\n',
        }
