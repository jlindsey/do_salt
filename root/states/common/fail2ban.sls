#!stateconf yaml . jinja

.fail2ban:
    pkg.installed:
        - name: fail2ban
    service.running:
        - name: fail2ban
        - enable: true
