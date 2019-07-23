#!stateconf yaml . jinja

{% from "wireguard/map.jinja" import vars, interfaces, defaults with context %}

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
        {%- for interface in interfaces %}
            - /etc/wireguard/{{ interface }}.conf:
                {%- set config = salt['pillar.get']('wireguard:interfaces:%s'%interface, defaults, merge=true) %}
                {%- if config['gateway'] %}
                    {%- set vars.ip_forward = true %}
                {%- endif %}
                - context: {{ config }}
        {%- endfor %}
    {%- if vars.ip_forward %}
    sysctl.present:
        - name: net.ipv4.ip_forward
        - value: 1
    {% endif %}
    service.running:
        - enable: true
        - watch:
            - file: .wireguard
        - names:
        {%- for dev in salt['pillar.get']('wireguard:interfaces', {}).keys() %}
            - wg-quick@{{ dev }}
        {%- endfor %}
