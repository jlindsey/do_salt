from __future__ import print_function

import os
from os import path
from tempfile import NamedTemporaryFile
from textwrap import dedent

from fabric import Connection
from invoke import Collection, task
from invoke.exceptions import Exit
from patchwork import transfers

root_dir = path.abspath(path.dirname(__file__))

conn = None

ns = Collection()


@task(name="etc")
def deploy_etc(c):
    """
    Deploy the salt master configs to /etc/salt, and restart master process
    """
    transfers.rsync(_conn(), path.join(root_dir, "etc/"), "/etc/salt")
    resp = _conn().run("systemctl restart salt-master")
    if resp.stderr:
        print(resp.stderr.strip())


@task(name="fs")
def deploy_fs(c):
    """
    Deploy the salt master filesystem to /srv/salt
    """
    _conn().run("mkdir -p /srv/salt")
    transfers.rsync(_conn(), path.join(root_dir, "root/"), "/srv/salt", delete=True)


@task(name="all", default=True, pre=[deploy_etc, deploy_fs])
def deploy_all(c):
    """
    Deploy all salt master files
    """
    pass


@task
def gen_keys(c):
    """
    Bootstrap the GPG keys for Salt encrypted pillars
    """
    c.config.run.echo = True

    if path.exists("etc/gpgkeys"):
        raise Exit("GPG key dir already exists, refusing to overwrite")

    with NamedTemporaryFile() as f:
        keyopts = """
            Key-Type: default
            Key-Length: 4096
            Subkey-Type: default
            Subkey-Length: 4096
            Name-Real: Salt
            Name-Comment: SaltStack encryption key
            Name-Email: salt@jlindsey.me
            Expire-Date: 0
            %no-protection
            %commit"""
        keyopts = dedent(keyopts).strip()
        print(keyopts)
        f.write(keyopts.encode())
        f.seek(0)

        with c.cd("etc"):
            c.run("mkdir -p gpgkeys")
            c.run("chmod 0700 gpgkeys")
            c.run(f"gpg --homedir gpgkeys --batch --gen-key {f.name}")


ns_deploy = Collection("deploy", deploy_all, deploy_etc, deploy_fs)
ns_crypt = Collection("gpg", gen_keys)
ns.add_collection(ns_crypt)
ns.add_collection(ns_deploy)
ns.default = "deploy.all"


def _conn():
    global conn

    if conn is None:
        master_addr = os.getenv("SALT_MASTER")
        if master_addr is None:
            raise Exception("SALT_MASTER env var not present")
        conn = Connection(master_addr)

    return conn
