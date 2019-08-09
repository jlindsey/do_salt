"""
Manages Consul ACL policies
"""

# Do some nonsense so jedi stops complaining about salt injected vars
__opts__ = __opts__ or {}
__salt__ = __salt__ or {}


def manage(name, description, rules, consul_host=None, consul_token=None):
    ret = {"name": name, "result": True, "changes": {}, "comment": ""}

    if __opts__["test"]:
        existing = __salt__["consul.policy_from_name"](name, consul_host, consul_token)
        if (
            existing
            and existing["Rules"] == rules
            and existing["Description"] == description
        ):
            ret["result"] = True  # No changes
            return ret

        ret["result"] = None
        ret[
            "comment"
        ] = f"Policy {name} would be {'updated' if existing else 'created'}"
        return ret

    try:
        created, ret["changes"] = __salt__["consul.create_update_policy"](
            name=name,
            description=description,
            rules=rules,
            consul_host=consul_host,
            consul_token=consul_token,
        )
        ret["comment"] = f"Policy {name} was {'created' if created else 'updated'}"
    except Exception as e:
        ret["result"] = False
        ret["comment"] = f"Error updating or creating policy: {e.__repr__()}"

    return ret
