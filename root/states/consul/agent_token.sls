#!stateconf yaml . jinja

{% from "consul/map.jinja" import host, tokens with context %}

{% if tokens['agent'] %}
.agent_policy:
    consul_policy.manage:
        - name: consul-agent-{{ host }}
        - description: Node agent token policy for {{ host }}
        - rules: |
            node "{{ host }}" {
                policy = "write"
            }
        - consul_host: http://127.0.0.1:8500
        - consul_token: {{ tokens['salt'] }}
        - require:
            - consul.install::goal
    consul_token.manage:
        - name: consul-agent-{{ host }}
        - description: Node agent token for {{ host }}
        - secret: {{ tokens['agent'] }}
        - policies:
            - consul-agent-{{ host }}
        - consul_host: http://127.0.0.1:8500
        - consul_token: {{ tokens['salt'] }}
        - require:
            - consul_policy: .agent_policy
{% endif %}
