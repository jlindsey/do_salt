#!stateconf yaml . jinja

.wireguard:
    pkgrepo.managed:
        - ppa: wireguard/wireguard
    pkg.installed:
        - pkgs:
            - wireguard-dkms
            - wireguard-tools