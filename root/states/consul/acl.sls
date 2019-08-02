#!stateconf yaml . jinja

.policies:
    consul_acl.manage_policy:
        - host: http://127.0.0.1:8500
        - token: {{ salt['pillar.get']('consul:config:acl:tokens:master') }}
        - names:
            - consul-agent-salt:
                - description: Salt master node agent token policy
                - rules: |
                    node "master" {
                        policy = "write"
                    }