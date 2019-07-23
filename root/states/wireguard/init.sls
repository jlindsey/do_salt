#!stateconf yaml . jinja

.wireguard:
    pkgrepo.managed:
        - ppa: wireguard/wireguard
    pkg.installed:
        - pkgs:
            - wireguard-dkms
            - wireguard-tools
        - require:
            - pkgrepo: .wireguard
    file.managed:
        - user: root
        - group: root
        - mode: 600
        - template: jinja
        - source: salt://wireguard/files/interface.conf.j2
        - names:
        {%- for dev, config in salt['pillar.get']('wireguard:interfaces', {}).items() %}
            - /etc/wireguard/{{ dev }}.conf:
                {%- set ctx = {**salt['pillar.get']('wireguard:defaults'), **config} %}
                - context: {{ ctx }}
        {%- endfor %}
    service.running:
        - enable: true
        - names:
        {%- for dev in salt['pillar.get']('wireguard:interfaces', {}).keys() %}
            - wg-quick@{{ dev }}
        {%- endfor %}
