"""
Exec module for various consul operations
"""

import logging
import os
from functools import partial
from typing import Any, Dict, List, Optional, Tuple

import requests

log = logging.getLogger(__name__)

CONSUL_DEFAULT_HOST = "http://127.0.0.1:8500"
CONSUL_DEFAULT_TOKEN = None


def _get_connection_params(
    host: Optional[str] = None, token: Optional[str] = None
) -> Tuple[str, str]:
    """
    Fetches the Consul connection string and API token to use.

    If the host and/or token param are passed in, they are used as-is.

    If not, check to see if the `consul:host` (for host) and/or `consul:token`
    (for token) configs are set. If so, use them.

    If not, check the env vars `CONSUL_HTTP_ADDR`, `CONSUL_HTTP_SSL`
    (for host) and `CONSUL_HTTP_TOKEN` (for token).

    Finally, fall back to the defaults: `http://127.0.0.1:8500` for host,
    and `None` for token.

    See:
        https://www.consul.io/docs/commands/index.html#environment-variables

    Args:
        host: optional connection string for consul agent
        token: optional token string

    Returns:
        A tuple of the form (host, token)
    """

    if host is None:
        host = __salt__["config.get"]("consul:host", None)
    if host is None:
        host = os.getenv("CONSUL_HTTP_ADDR", None)
        if host is not None and "://" not in host:
            ssl = os.getenv("CONSUL_HTTP_SSL", False)
            schema = (
                "https" if ssl and ssl.lower() not in ("0", "false", "f") else "http"
            )
            host = f"{schema}://{host}"
    if host is None:
        host = CONSUL_DEFAULT_HOST

    if token is None:
        token = __salt__["config.get"]("consul:token", None)
    if token is None:
        token = os.getenv("CONSUL_HTTP_TOKEN", None)
    if token is None:
        token = CONSUL_DEFAULT_TOKEN

    return (host, token)


def get_session(host: Optional[str], token: Optional[str]) -> requests.Session:
    """
    Instantiates a new requests Session object from the host and token.

    This Session behaves like BaseUrlSession from requests_toolbelt, so
    only the path is required to be given to request methods. It also
    appends "/v1/" to the end of the host, if absent, so that path portion
    is not required.

    Args:
        host: consul connection string
        token: consul token

    Returns:
        A `requests.Session` object
    """

    host, token = _get_connection_params(host, token)

    # Ensure the URL ends with a single / so urljoin doesn't
    # eat part of the pathname, and append the api path if missing
    host = host.rstrip("/") + "/"
    if "/v1/" not in host:
        host = host + "v1/"

    def new_req(host, f, method, url, *args, **kwargs):
        return f(method, host + url, *args, **kwargs)

    s = requests.Session()
    if token:
        s.headers.update({"X-Consul-Token": token})
    s.request = partial(new_req, host, s.request)

    return s


def all_policies(consul_host: str, consul_token: str) -> List[Dict[str, Any]]:
    """
    Returns a list of all policies from consul.

    See: https://www.consul.io/api/acl/policies.html#list-policies
    """

    resp = get_session(consul_host, consul_token).get("acl/policies")
    resp.raise_for_status()
    json = resp.json()
    log.debug("Got policies: {}", json)
    return json


def policy_from_name(
    name: str, consul_host: str, consul_token: str
) -> Optional[Dict[str, Any]]:
    """
    Fetches a policy detail object of the given name.

    Returns:
        The policy details dict or `None` if no policy exists with that name

    See: https://www.consul.io/api/acl/policies.html#read-a-policy
    """

    policy = [p for p in all_policies(consul_host, consul_token) if p["Name"] == name]
    log.debug("Got policies matching name {}: {}", name, policy)
    return policy.pop() if policy else None


def create_update_policy(
    name: str,
    rules: str,
    description: Optional[str] = None,
    consul_host: Optional[str] = None,
    consul_token: Optional[str] = None,
) -> Tuple[bool, Dict[str, str]]:
    """
    Creates or updates a Consul ACL policy.

    If the policy does not exist with the given name, it is created.

    If it does exist, and the given policy string matches the existing record,
    no changes are made.

    Otherwise, the policy is updated with the new policy string.

    Args:
        name: The policy name
        rules: The policy rules string
        description: The human-readable description string for this policy

    Returns:
        A tuple where the first element is a bool indicating whether the policy was
        created (true) or updated (false), and the second is a changes dict suitable
        for salt state returns.
    """
    session = get_session(consul_host, consul_token)

    existing = policy_from_name(name, consul_host, consul_token)

    if existing:
        # Update
        log.debug("consul policy {}: existing policy", name)
        if existing["Rules"] == rules and existing["Description"] == description:
            log.debug("consul policy {}: no update needed", name)
            return (False, {})  # No changes

        resp = session.put(
            f'acl/policy/{existing["ID"]}',
            json={"Name": name, "Description": description, "Rules": rules},
        )
        resp.raise_for_status()

        changes = {"rules": {"old": existing["Rules"], "new": rules}}
        if name != existing["Name"]:
            changes["name"] = {"old": existing["Name"], "new": name}
        if description != existing["Description"]:
            changes["description"] = {
                "old": existing["Description"],
                "new": description,
            }
        return (False, changes)

    # Create
    resp = session.put(
        "acl/policy", json={"Name": name, "Description": description, "Rules": rules}
    )
    resp.raise_for_status()
    changes = {
        "name": {"old": "", "new": name},
        "rules": {"old": "", "new": rules},
        "description": {"old": "", "new": description},
    }
    return (True, changes)


def delete_policy(
    name: str, consul_host: Optional[str] = None, consul_token: Optional[str] = None
) -> Dict[str, str]:
    """
    Ensures a policy does not exist with a given name.

    Args:
        name: The policy name

    Returns:
        A changes dict suitable for salt state returns
    """
    policy = policy_from_name(name, consul_host, consul_token)
    if policy is None:
        return {}

    resp = get_session(consul_host, consul_token).delete(f"acl/policy/{policy['ID']}")
    resp.raise_for_status()
    return {
        "id": {"old": policy["ID"], "new": ""},
        "name": {"old": policy["Name"], "new": ""},
        "description": {"old": policy["Description"], "new": ""},
        "rules": {"old": policy["Rules"], "new": ""},
    }
