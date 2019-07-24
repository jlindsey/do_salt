"""
Various utility functions, mostly for deploys
"""
from __future__ import absolute_import

import time
from contextlib import contextmanager
from pathlib import PurePosixPath as path

from patchwork import files


DEPLOY_RELEASES_DIR = "releases"
DEPLOY_CURRENT_LINK = "current"
DEPLOY_REPO_DIR = "repo"


def join(*parts):
    return str(path(*[str(p) for p in parts]))


@contextmanager
def remote_tmp_dir(conn):
    tmp_dir = conn.run("mktemp -d").stdout.strip()
    try:
        yield tmp_dir
    finally:
        conn.run(f"rm -rf {tmp_dir}")


def new_release(conn, deploy_root, branch, in_repo_path, release_path=None):
    if release_path is None:
        release_path = join(deploy_root, DEPLOY_RELEASES_DIR, int(time.time() * 1000.0))

    files.directory(conn, release_path)
    with conn.cd(join(deploy_root, DEPLOY_REPO_DIR)):
        conn.run(
            f"""git archive {branch} {in_repo_path} | \\
                tar -x --strip-components 1 -f - -C {release_path}"""
        )
        conn.run(
            f"git rev-list --max-count=1 {branch} > {join(release_path, 'REVISION')}"
        )

    return release_path


def promote_release_to_current(conn, deploy_root, release_dir):
    with remote_tmp_dir(conn) as tmp_dir:
        conn.run(f"ln -s {release_dir} {join(tmp_dir, 'current')}")
        conn.run(f"mv {join(tmp_dir, 'current')} {deploy_root}")
