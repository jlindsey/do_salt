from __future__ import absolute_import

from invoke import Collection

from . import deploy, gpg

ns = Collection(deploy, gpg)
