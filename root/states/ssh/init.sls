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
    cmd.run:
        # Disable DH moduli of less than 3072 bits
        - name: awk '$5 >= 3071' /etc/ssh/moduli > /etc/ssh/moduli.tmp && mv /etc/ssh/moduli.tmp /etc/ssh/moduli
        - unless: "[ -z \"$(awk '$5 < 3071' /etc/ssh/moduli)\" ]"
    service.running:
        - name: sshd
        - enable: true
        - watch:
            - file: .sshd
            - cmd: .sshd
