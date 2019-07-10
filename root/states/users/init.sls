#!stateconf yaml . jinja

.sudoers:
    file.managed:
        - name: /etc/sudoers
        - source: salt://users/files/sudoers
        - check_cmd: /usr/sbin/visudo -c -f

.remove_ubuntu_user:
    user.absent:
        - name: ubuntu

{%- for username, conf in salt['pillar.get']('users', {})items() %}
.user-{{ username }}:
    user.present:
        - name: {{ username }}
        - password: {{ conf.get('password', None) }}
        - shell: {{ conf.get('shell', '/bin/bash') }}
        - optional_groups: {{ conf.get('optional_groups', []) }}
    {% if 'public_keys' in conf -%}
    ssh_auth.present:
        - user: {{ username }}
        - names: {{ conf['public_keys'] }}
    {%- endif %}
    file.managed:
        - names:
            {% if 'sudoers' in conf -%}
            - /etc/sudoers.d/{{ username }}:
                - source: salt://users/files/user_sudoer
                - template: jinja
                - mode: 440
                - check_cmd: /usr/sbin/visudo -c -f
                - context:
                    username: {{ username }}
                    specs: {{ conf['sudoers'] }}
            {% endif -%}
            {%- for filename in conf.get('files', {}) %}
            - /home/{{ username }}/{{ filename }}:
                - user: {{ username }}
                - group: {{ username }}
                - contents_pillar: users:{{ username }}:files:{{ filename }}
            {%- endfor %}
{%- endfor %}
