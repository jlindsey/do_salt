#!stateconf yaml . jinja

include:
    - consul

.policies:
    consul_acl.manage_policy:
        - consul_host: http://127.0.0.1:8500
        - consul_token: {{ salt['pillar.get']('consul:config:acl:tokens:master') }}
        - require:
            - consul::goal
        - names:
            - consul-agent-salt:
                - description: Salt master node agent token policy
                - rules: |
                    node "master" {
                        policy = "write"
                    }