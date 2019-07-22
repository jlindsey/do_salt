"""
Deployment tasks for salt
"""

from __future__ import absolute_import

import io
import os
import tarfile
import time

import fabric
from invoke import task
from patchwork import files

SALT_MASTER = os.getenv("SALT_MASTER")
SALT_REPO = os.getenv("SALT_REPO")
SALT_USER = os.getenv("SALT_USER", "salt")
SALT_DEPLOY_PATH = os.getenv("SALT_DEPLOY_PATH", "/srv/salt")
SALT_BRANCH = os.getenv("SALT_BRANCH", "master")

conn = fabric.Connection(host=SALT_MASTER, user=SALT_USER)
conn.config.run.echo = True
conn.config.run.hide = "out"
conn.config.run.warn = False


def _make_release(in_repo_path, release_path, strip_components=1):
    files.directory(conn, release_path)
    with conn.cd(f"{SALT_DEPLOY_PATH}/repo"):
        conn.run(
            f"""git archive {SALT_BRANCH} {in_repo_path} | \\
                tar -x --strip-components {strip_components} -f - -C {release_path}"""
        )
        conn.run(f"git rev-list --max-count=1 {SALT_BRANCH} > {release_path}/REVISION")


@task
def setup(c):
    """
    Prepare the server for deployments
    """
    files.directory(conn, f"{SALT_DEPLOY_PATH}/repo")
    files.directory(conn, f"{SALT_DEPLOY_PATH}/releases")

    with conn.cd(f"{SALT_DEPLOY_PATH}/repo"):
        if not files.exists(conn, "HEAD"):
            conn.run(f"git clone --mirror --depth 1 --no-single-branch {SALT_REPO} .")

        conn.run(f"git remote set-url origin {SALT_REPO}")
        conn.run(f"git fetch --depth 1 origin {SALT_BRANCH}")


@task(setup)
def states(c):
    """
    Deploy salt states and modules into /srv/salt
    """
    release_ts = int(time.time() * 1000.0)
    release_dir = f"{SALT_DEPLOY_PATH}/releases/{release_ts}"

    tmp_dir = conn.run("mktemp -d").stdout.strip()
    try:
        _make_release("root", release_dir)

        conn.run(f"ln -s {release_dir} {tmp_dir}/current")
        conn.run(f"mv {tmp_dir}/current {SALT_DEPLOY_PATH}")
    finally:
        conn.run(f"rm -rf {tmp_dir}")


@task(setup)
def etc(c):
    """
    Deploy /etc/salt configs and restart daemon
    """
    _make_release("etc", "/etc/salt")
    conn.sudo("systemctl restart salt-master", pty=True)



@task
def gpg(c):
    """
    Deploy gpgkeys dir to /etc/salt
    """
    buf = io.BytesIO()
    tf = tarfile.TarFile(fileobj=buf, mode="w")
    tf.add("etc/gpgkeys", arcname="gpgkeys", recursive=True)
    tf.close()
    buf.seek(0)

    try:
        remote_tmp_dir = conn.run("mktemp -d").stdout.strip()
        upload_path = f"{remote_tmp_dir}/gpgkeys.tar"

        with conn.sftp() as sftp:
            sftp.putfo(buf, upload_path)

        conn.run(f"tar -xf {upload_path} -C /etc/salt")
    finally:
        buf.close()
        conn.run(f"rm -rf {remote_tmp_dir}")


@task(setup, default=True)
def all(c):
    """
    Deploy all salt master files except the gpg keys dir
    """
    states(c)
    etc(c)
