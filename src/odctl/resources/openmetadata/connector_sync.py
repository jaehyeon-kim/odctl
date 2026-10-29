"""Copies custom OpenMetadata connectors from s3://openmetadata/connectors.

The `openmetadata-ingestion` container runs this twice. `--once` makes the first
copy before Airflow starts and tries for up to 60 seconds, because `storage`
starts at the same time and its bucket exists only after `seaweed-init` has run.
Without an option it lists the prefix every 15 seconds, keys and ETags. Its first
pass copies the files again, and every later pass copies only when the list
changed. It never stops Airflow: a failed first copy or listing is printed and
tried again.
"""

import argparse
import os
import shutil
import time
from typing import Any, Callable, Optional

BUCKET = "openmetadata"
PREFIX = "connectors/"
DEST = "/opt/airflow/connectors"
INTERVAL_SECONDS = 15
FIRST_COPY_SECONDS = 60
RETRY_SECONDS = 5

Objects = list[tuple[str, str]]


def _make_client() -> Any:
    """Create the S3 client for SeaweedFS, with short timeouts.

    Returns:
        Any: A boto3 S3 client that reads its keys from the environment.
    """
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url="http://seaweed:8333",
        config=Config(connect_timeout=5, read_timeout=15, retries={"max_attempts": 1}),
    )


def listing(s3: Any) -> Objects:
    """List the objects under the prefix, skipping folder markers.

    Args:
        s3 (Any): The S3 client.

    Returns:
        Objects: Sorted (key, ETag) pairs, so two listings compare equal when
        nothing changed.

    Raises:
        Exception: Whatever the S3 client raises when a page cannot be read.
    """
    objects = []
    pages = s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix=PREFIX)
    for page in pages:
        for obj in page.get("Contents", []):
            if obj["Key"].endswith("/"):
                continue
            objects.append((obj["Key"], obj["ETag"]))
    return sorted(objects)


def _copy(s3: Any, objects: Objects, dest: str = DEST) -> None:
    """Make the destination folder hold exactly the listed objects.

    Each file is replaced as a whole, so a process that imports a module while the
    copy runs reads either the old file or the new one. Files that are no longer
    listed are deleted, and so are the folders that no listed file is in. Python's
    `__pycache__` folders stay in the folders that are still used.

    Args:
        s3 (Any): The S3 client.
        objects (Objects): The listing to copy.
        dest (str): The folder to fill.

    Raises:
        Exception: Whatever the S3 client raises when a download fails.
    """
    wanted = set()
    used = {dest}
    for key, _ in objects:
        path = os.path.join(dest, key.removeprefix(PREFIX))
        wanted.add(path)
        folder = os.path.dirname(path)
        os.makedirs(folder, exist_ok=True)
        s3.download_file(BUCKET, key, path)
        while folder not in used:
            used.add(folder)
            folder = os.path.dirname(folder)
    for folder, _, names in os.walk(dest, topdown=False):
        if "__pycache__" in folder:
            continue
        for name in names:
            if os.path.join(folder, name) not in wanted:
                os.remove(os.path.join(folder, name))
        if folder not in used:
            shutil.rmtree(folder)
    print("Connectors:", [key for key, _ in objects], flush=True)


def first_copy(
    s3: Any,
    dest: str = DEST,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
) -> Optional[Objects]:
    """Copy the prefix, retrying until it works or 60 seconds have passed.

    Args:
        s3 (Any): The S3 client.
        dest (str): The folder to fill.
        sleep (Callable[[float], None]): Waits between tries.
        now (Callable[[], float]): The clock that measures the 60 seconds.

    Returns:
        Optional[Objects]: The listing that was copied, or None when no try worked.
    """
    deadline = now() + FIRST_COPY_SECONDS
    while now() < deadline:
        try:
            objects = listing(s3)
            _copy(s3, objects, dest)
            return objects
        except Exception as error:
            print("Copying s3://openmetadata/connectors failed:", error, flush=True)
            sleep(RETRY_SECONDS)
    return None


def sync_changes(
    s3: Any, objects: Optional[Objects], dest: str = DEST
) -> Optional[Objects]:
    """List the prefix once and copy it again when the listing changed.

    Args:
        s3 (Any): The S3 client.
        objects (Optional[Objects]): The listing last copied, or None before any copy.
        dest (str): The folder to fill.

    Returns:
        Optional[Objects]: The listing now in the folder. It is the old one when the
        listing or the copy failed, so the next pass tries again.
    """
    try:
        latest = listing(s3)
        if latest != objects:
            _copy(s3, latest, dest)
            return latest
    except Exception as error:
        print("Syncing s3://openmetadata/connectors failed:", error, flush=True)
    return objects


def main(argv: Optional[list[str]] = None) -> None:
    """Run the first copy with `--once`, or the loop that keeps copying.

    Args:
        argv (Optional[list[str]]): The command line, without the program name.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="copy once, then exit")
    args = parser.parse_args(argv)
    s3 = _make_client()
    if args.once:
        first_copy(s3)
        return
    objects = None
    while True:
        time.sleep(INTERVAL_SECONDS)
        objects = sync_changes(s3, objects)


if __name__ == "__main__":
    main()
