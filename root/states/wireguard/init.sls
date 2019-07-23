#!stateconf yaml . jinja

{% set ip_forward = false %}

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
                {%- do config.update(salt['pillar.get']('wireguard:defaults', {})) %}
                {%- if config['gateway'] %}
                    {%- set ip_forward = true %}
                {%- endif %}
                - context: {{ config }}
        {%- endfor %}
    {%- if ip_forward %}
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
