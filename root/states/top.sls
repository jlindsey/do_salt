base:
    '*':
        - common
        - users
        - ssh
    'not P@roles:consul_master':
        - consul
    G@roles:consul_master:
        - consul.master
    G@roles:wireguard:
        - wireguard
    G@roles:nomad_agent:
        - consul.link_local
