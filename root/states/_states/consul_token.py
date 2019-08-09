"""
Manages Consul ACL tokens
"""

# Do some nonsense so jedi stops complaining about salt injected vars
__opts__ = __opts__ or {}
__salt__ = __salt__ or {}


def manage(
    name, secret, consul_host, consul_token, description=None, policies=[], roles=[]
):
    ret = {"name": name, "result": True, "changes": {}, "comment": ""}

    if __opts__["test"]:
        existing = __salt__["consul.token_by_name_or_accessor"](
            consul_host=consul_host, consul_token=consul_token, name=name
        )

        if existing:
            existing_policy_names, existing_role_names = __salt__[
                "consul.token_link_names"
            ](existing)

            if (
                existing["Description"] == description
                and sorted(existing_policy_names) == sorted(policies)
                and sorted(existing_role_names) == sorted(roles)
            ):
                ret["result"] = True  # No changes
                return ret

            ret["result"] = None
            ret["comment"] = f"Token {name} would be updated"
        else:
            ret["result"] = None
            ret["comment"] = f"Token {name} would be created"

        return ret

    try:
        created, ret["changes"] = __salt__["consul.create_update_token"](
            name=name,
            secret=secret,
            description=description,
            policies=policies,
            roles=roles,
            consul_host=consul_host,
            consul_token=consul_token,
        )
        ret["comment"] = f"Token {name} was {'created' if created else 'updated'}"
    except Exception as e:
        ret["result"] = False
        ret["comment"] = f"Error updating or creating token: {e}"

    return ret
