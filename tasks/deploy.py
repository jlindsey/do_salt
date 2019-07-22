"""
Deployment tasks for salt
"""

from __future__ import absolute_import

import io
import os
import tarfile

import fabric
from invoke import task
from patchwork import files

from . import utils

SALT_MASTER = os.getenv("SALT_MASTER")
SALT_REPO = os.getenv("SALT_REPO")
SALT_USER = os.getenv("SALT_USER", "salt")
SALT_DEPLOY_PATH = os.getenv("SALT_DEPLOY_PATH", "/srv/salt")
SALT_BRANCH = os.getenv("SALT_BRANCH", "master")
SALT_KEEP_RELEASES = os.getenv("SALT_KEEP_RELEASES", 5)

conn = fabric.Connection(host=SALT_MASTER, user=SALT_USER)
conn.config.run.echo = True
conn.config.run.hide = "out"
conn.config.run.warn = False


@task
def setup(c):
    """
    Prepare the server for deployments
    """
    files.directory(conn, utils.join(SALT_DEPLOY_PATH, utils.DEPLOY_REPO_DIR))
    files.directory(conn, utils.join(SALT_DEPLOY_PATH, utils.DEPLOY_RELEASES_DIR))

    with conn.cd(utils.join(SALT_DEPLOY_PATH, utils.DEPLOY_REPO_DIR)):
        if not files.exists(conn, "HEAD"):
            conn.run(f"git clone --mirror --depth 1 --no-single-branch {SALT_REPO} .")

        conn.run(f"git remote set-url origin {SALT_REPO}")
        conn.run(f"git fetch --depth 1 origin {SALT_BRANCH}")


@task
def prune(c):
    """
    Clean up old releases, keeping the value of SALT_KEEP_RELEASES
    """
    with conn.cd(utils.join(SALT_DEPLOY_PATH, utils.DEPLOY_RELEASES_DIR)):
        releases = [
            d.replace("./", "").strip()
            for d in conn.run("find . -maxdepth 1 -mindepth 1 -type d", pty=True)
            .stdout.strip()
            .split("\n")
        ]
        releases.sort()

        diff = len(releases) - int(SALT_KEEP_RELEASES)
        print(
            f"Found {len(releases)} current releases; set to keep {SALT_KEEP_RELEASES}"
        )
        if diff > 0:
            to_delete = releases[:diff]
            print(f"Cleaning up {len(to_delete)} old release(s)")
            conn.run(f"rm -rf {' '.join(to_delete)}")
        else:
            print("Nothing to do")


@task(setup, post=[prune])
def states(c):
    """
    Deploy salt states and modules into /srv/salt
    """
    release_dir = utils.new_release(
        conn, deploy_root=SALT_DEPLOY_PATH, in_repo_path="root", branch=SALT_BRANCH
    )
    utils.promote_release_to_current(
        conn, deploy_root=SALT_DEPLOY_PATH, release_dir=release_dir
    )


@task(setup)
def etc(c):
    """
    Deploy /etc/salt configs and restart daemon
    """
    utils.new_release(
        conn,
        deploy_root=SALT_DEPLOY_PATH,
        in_repo_path="etc",
        release_path="/etc/salt",
        branch=SALT_BRANCH,
    )
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

    with utils.remote_tmp_dir(conn) as tmp_dir:
        upload_path = utils.join(tmp_dir, "gpgkeys.tar")

        with conn.sftp() as sftp:
            try:
                sftp.putfo(buf, upload_path)
            finally:
                buf.close()

        conn.run(f"tar -xf {upload_path} -C /etc/salt")


@task(setup, default=True)
def all(c):
    """
    Deploy all salt master files except the gpg keys dir
    """
    states(c)
    etc(c)
    prune(c)
