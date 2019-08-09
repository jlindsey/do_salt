#!stateconf yaml . jinja

{% from "consul/map.jinja" import tokens, managed_tokens, managed_policies with context %}

.salt_token:
    consul_policy.manage:
        - name: salt-acl
        - description: Salt ACL management permissions
        - rules: acl = "write"
        - consul_host: http://127.0.0.1:8500
        - consul_token: {{ tokens['bootstrap'] }}
    consul_token.manage:
        - name: salt-acl
        - description: Salt ACL management token
        - secret: {{ salt['pillar.get']('consul:salt_acl_token') }}
        - policies:
            - salt-acl
        - consul_host: http://127.0.0.1:8500
        - consul_token: {{ tokens['bootstrap'] }}
        - require:
            - consul_policy: .salt_token

{% if managed_policies %}
.managed_policies:
    consul_policy.manage:
        - consul_host: http://127.0.0.1:8500
        - consul_token: {{ tokens['salt'] }}
        - names:
            {% for name, policy in salt['pillar.get']('consul:policies', {}).items() %}
            - {{ name }}:
                - rules: {{ policy['rules'] }}
                - description: {{ policy.get('description', none) }}
            {% endfor %}
{% endif %}

{% if managed_tokens %}
.managed_tokens:
    consul_token.manage:
        - consul_host: http://127.0.0.1:8500
        - consul_token: {{ tokens['salt'] }}
        - names:
            {% for name, token in salt['pillar.get']('consul:tokens', {}).items() %}
            - {{ name }}:
                - description: {{ token['description'] }}
                - secret: {{ token['secret'] }}
                - policies: {{ token.get('policies', []) }}
                - roles: {{ token.get('roles', []) }}
            {% endfor %}
{% endif %}