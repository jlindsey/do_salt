#!stateconf yaml . jinja

.base_packages:
    pkg.installed:
        - aggregate: true
        - pkgs:
        {%- for pkg in salt['pillar.get']('packages', []) %}
            - {{ pkg }}
        {%- endfor %}
