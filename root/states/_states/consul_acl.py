"""
Manages Consul ACL objects: policies, roles, and tokens
"""


def manage_policy(name, description, rules, consul_host=None, consul_token=None):
    session = __salt__["consul.get_session"](consul_host, consul_token)

    ret = {"name": name, "result": True, "changes": {}, "comment": ""}

    if __opts__["test"]:
        existing = __salt__["consul.policy_from_name"](name, consul_host, consul_token)
        if existing:
            if existing["Rules"] == rules and existing["Description"] == description:
                ret["result"] = True
                return ret

            ret["result"] = None
            ret["comment"] = f"Policy {name} would be updated"
            return ret

    try:
        created, ret["changes"] = __salt__["consul.create_update_policy"](
            name=name,
            description=description,
            rules=rules,
            consul_host=consul_host,
            consul_token=consul_token,
        )
        if created:
            ret["comment"] = f"Policy {name} created"
        else:
            ret["comment"] = f"Policy {name} updated"
    except Exception as e:
        ret["result"] = False
        ret["comment"] = f"Error updating or creating policy: {e.__repr__()}"

    return ret
