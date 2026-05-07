"""Race condition tests for FileProcessorService — file TOCTOU."""
import os
import shutil
import threading
import pytest
import service as svc

WORK_DIR = svc.WORK_DIR


@pytest.fixture(autouse=True)
def setup_and_teardown():
    if os.path.isdir(WORK_DIR):
        shutil.rmtree(WORK_DIR)
    svc.setup_work_dir(n_files=20)
    yield
    if os.path.isdir(WORK_DIR):
        shutil.rmtree(WORK_DIR)


def test_single_worker_claims_file():
    result = svc.claim_and_process("worker_0")
    assert result["claimed"] is not None


def test_concurrent_workers_no_double_processing():
    """Each file must be processed by exactly one worker."""
    claimed = []
    lock = threading.Lock()

    def work(worker_id):
        while True:
            result = svc.claim_and_process(worker_id)
            if result["claimed"] is None:
                break
            with lock:
                claimed.append(result["claimed"])

    threads = [threading.Thread(target=work, args=(f"w{i}",)) for i in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()

    # Each filename should appear at most once
    unique = set(claimed)
    assert len(claimed) == len(unique), (
        f"Double processing detected: {len(claimed)} claims, {len(unique)} unique files"
    )


def test_all_files_processed():
    """All files must eventually be claimed (no starvation)."""
    initial_count = svc.count_remaining_files()
    claimed = []
    lock = threading.Lock()

    def work(worker_id):
        while True:
            result = svc.claim_and_process(worker_id)
            if result["claimed"] is None:
                break
            with lock:
                claimed.append(result["claimed"])

    threads = [threading.Thread(target=work, args=(f"w{i}",)) for i in range(4)]
    for t in threads: t.start()
    for t in threads: t.join()

    assert len(claimed) == initial_count, (
        f"Not all files processed: {len(claimed)}/{initial_count}"
    )
    assert svc.count_remaining_files() == 0
    assert svc.count_processing_files() == 0
