"""
Exec module for various consul operations
"""

import os
import uuid
from functools import partial

import requests
from salt import exceptions


CONSUL_DEFAULT_HOST = "http://127.0.0.1:8500"
CONSUL_DEFAULT_TOKEN = None


NAMESPACE_CONSUL = uuid.uuid5(
    uuid.UUID("00000000-0000-0000-0000-000000000000"), "consul"
)


def _get_connection_params(host, token):
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


def get_session(host, token):
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


def all_policies(consul_host, consul_token):
    """
    Returns a list of all policies from consul.

    See: https://www.consul.io/api/acl/policies.html#list-policies
    """

    resp = get_session(consul_host, consul_token).get("acl/policies")
    resp.raise_for_status()
    json = resp.json()
    return json


def policy_from_name(name, consul_host, consul_token):
    """
    Fetches a policy detail object of the given name.

    Returns:
        The policy details dict or `None` if no policy exists with that name

    See: https://www.consul.io/api/acl/policies.html#read-a-policy
    """

    policy = [p for p in all_policies(consul_host, consul_token) if p["Name"] == name]
    if not policy:
        return None

    policy = policy.pop()
    policy_id = policy["ID"]
    resp = get_session(consul_host, consul_token).get(f"acl/policy/{policy_id}")
    resp.raise_for_status()
    return resp.json()


def create_update_policy(name, rules, description, consul_host, consul_token):
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
        if existing["Rules"] == rules and existing["Description"] == description:
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


def delete_policy(name, consul_host, consul_token):
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


def token_accessor_from_name(name):
    """
    Creates a deterministic token accessor based on a token name. Consul does not have
    any concept of a token "name": this is a purely for better integration with salt.

    Args:
        name: the salt name for this token

    Returns:
        A UUIDv5 namespaced to consul
    """

    return uuid.uuid5(NAMESPACE_CONSUL, name)


def token_link_names(token):
    """
    Extracts the list of policy names and role names from the Consul token link objects.

    Args:
        token: a dict representation of the json return of a consul token

    Returns:
        A tuple of (policy_names, role_names), where each element is a sorted list
        of strings
    """

    return (
        [policy["Name"] for policy in token["Policies"]],
        [role["Name"] for role in token["Roles"]],
    )


def token_by_name_or_accessor(consul_host, consul_token, name=None, accessor=None):
    """
    Convenience function to fetch a token object from Consul either from a salt-internal
    name or the Consul accessor UUID.

    Either ``name`` or ``accessor`` must be provided; if neither are, an exception is
    raised.

    Args:
        name: the salt name for this token
        accessor: the consul token accessor UUID

    Returns:
        A dict representing the token return from Consul, or None if no token exists
    """

    if name is None and accessor is None:
        raise exceptions.ArgumentValueError("Name or accessor must be provided")

    if name is not None:
        accessor = token_accessor_from_name(name)

    session = get_session(consul_host, consul_token)

    resp = session.get(f"acl/token/{accessor}")
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def create_update_token(
    name, secret, consul_host, consul_token, description=None, policies=[], roles=[]
):
    """
    Creates or updates a Consul ACL token.

    Name and Secret are immutable fields. Changing the secret for an existing token
    will result in an error. Changing the name will result in a new accessor being
    generated, which will create a new token. This may generate an error if the
    previous token was not deleted first, since secrets must be globally unique.

    Args:
        secret: The token secret ID
        description: Human-readable token description
        policies: Array of policy names to associate with this token
        roles: Array of role names to associate with this token

    Returns:
        A tuple where the first element is a bool indicating whether the token was
        created (True) or updated (False), and the second is a changes dict suitable
        for salt state returns
    """

    accessor = token_accessor_from_name(name)
    existing = token_by_name_or_accessor(
        accessor=accessor, consul_host=consul_host, consul_token=consul_token
    )

    params = {"AccessorID": accessor, "SecretID": secret, "Description": description}
    if policies:
        params["Policies"] = {"Name": policy for policy in policies}
    if roles:
        params["Roles"] = {"Name": role for role in roles}

    session = get_session(consul_host, consul_token)

    if existing is not None:
        if existing["SecretID"] != secret:
            raise exceptions.CheckError(
                "attempting to change a secretID on an existing consul token"
            )

        endpoint = f"acl/token/{accessor}"
        created = False

        existing_policy_names, existing_role_names = token_link_names(existing)

        ret = {}
        if existing["Description"] != description:
            ret["description"] = {"old": existing["Description"], "new": description}
        if sorted(existing_policy_names) != sorted(policies):
            ret["policies"] = {"old": existing_policy_names, "new": policies}
        if sorted(existing_role_names) != sorted(roles):
            ret["roles"] = {"old": existing_role_names, "new": roles}
    else:
        endpoint = "acl/token"
        created = True
        ret = {
            "accessor": {"old": "", "new": accessor},
            "secret": {"old": "", "new": secret},
            "description": {"old": "", "new": description},
            "policies": {"old": [], "new": policies},
            "roles": {"old": [], "new": roles},
        }

    resp = session.put(endpoint, json=params)
    resp.raise_for_status()
    return (created, ret)
