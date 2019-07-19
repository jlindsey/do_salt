#!stateconf yaml . jinja

include:
    - users

.sshd:
    file.managed:
        - name: /etc/ssh/sshd_config
        - source: salt://ssh/files/sshd_config
        - mode: 644
        # Our sshd_config disables root logins, so make sure the users state passed first and
        # we have a user to log in as afterwards.
        - require:
            - users::goal
    service.running:
        - name: sshd
        - enable: true
        - watch:
            - file: .sshd
