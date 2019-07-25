#!stateconf yaml . jinja

{% from "consul/map.jinja" import config, services, checks, version with context %}

.extract_and_install:
    archive.extracted:
        - name: /tmp
        - source: https://releases.hashicorp.com/consul/{{ version }}/consul_{{ version }}_linux_amd64.zip
        - source_hash: https://releases.hashicorp.com/consul/{{ version }}/consul_{{ version }}_SHA256SUMS
        - enforce_toplevel: false
        - if_missing: /usr/local/bin/consul-{{ version }}
    file.rename:
        - name: /usr/local/bin/consul-{{ version }}
        - source: /tmp/consul
        - watch:
            - archive: .extract_and_install

.set_current:
    file.symlink:
        - name: /usr/local/bin/consul
        - source: /usr/local/bin/consul-{{ version }}

.config_dir:
    file.directory:
        - name: /etc/consul.d
        - user: root
        - group: root

.config:
    file.serialize:
        - mode: 600
        - formatter: json
        - names:
            - /etc/consul.json:
                - dataset: {{ config }}
            {%- for name, service in services.items() %}
                {%- set data = {"service": service} %}
            - /etc/consul.d/service-{{ name }}.json:
                - dataset: {{ data }}
            {%- endfor %}
            {%- for name, check in checks.items() %}
                {%- set data = {"check": service} %}
            - /etc/consul.d/check-{{ name }}.json:
                - dataset: {{ data }}
            {%- endfor %}