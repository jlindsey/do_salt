base:
    '*':
        - common
        - users
        - ssh
        - consul
    G@roles:consul_master:
        - consul.acl
    G@roles:wireguard:
        - wireguard
    G@roles:nomad_agent:
        - consul.link_local
