"""
FileProcessorService: Claims and processes files from a work directory.

RACE CONDITION (TOCTOU): Checks if file exists, then opens it.
Between os.path.exists() and open(), another worker can claim and
delete the same file — causing FileNotFoundError or double-processing.

Inspiration: Distributed work queue TOCTOU bugs in file-based systems.
"""
import os
import fcntl
import threading
import time

WORK_DIR = "work_files"


def setup_work_dir(n_files: int = 10):
    os.makedirs(WORK_DIR, exist_ok=True)
    for i in range(n_files):
        path = os.path.join(WORK_DIR, f"task_{i:04d}.json")
        if not os.path.exists(path):
            with open(path, "w") as f:
                f.write(f'{"task_id": {i}, "status": "pending"}')


def claim_and_process(worker_id: str) -> dict:
    """Find an unclaimed file, mark it as in-progress, and process it.

    RACE CONDITION: os.path.exists() check + rename is not atomic.
    Two workers can both see the same file, both pass the exists check,
    then both try to rename/process it.

    Fix: use os.rename() atomically (POSIX atomic) or open with O_EXCL flag.
    """
    files = sorted(os.listdir(WORK_DIR)) if os.path.isdir(WORK_DIR) else []
    for fname in files:
        if not fname.endswith(".json"):
            continue
        src = os.path.join(WORK_DIR, fname)
        dst = os.path.join(WORK_DIR, fname.replace(".json", f".{worker_id}.processing"))

        # RACE CONDITION: another worker may claim src between exists() and rename()
        if os.path.exists(src):
            time.sleep(0.001)  # simulate delay — amplifies race
            try:
                os.rename(src, dst)
                # Successfully claimed — process it
                with open(dst) as f:
                    content = f.read()
                os.remove(dst)
                return {"worker": worker_id, "claimed": fname, "content": content}
            except (FileNotFoundError, OSError):
                continue  # already claimed by another worker
    return {"worker": worker_id, "claimed": None}


def count_remaining_files() -> int:
    if not os.path.isdir(WORK_DIR):
        return 0
    return len([f for f in os.listdir(WORK_DIR) if f.endswith(".json")])


def count_processing_files() -> int:
    if not os.path.isdir(WORK_DIR):
        return 0
    return len([f for f in os.listdir(WORK_DIR) if ".processing" in f])
