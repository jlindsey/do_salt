#!stateconf yaml . jinja

.auto_updates:
    pkg.installed:
        - pkgs:
            - unattended-upgrades
            - bsd-mailx
    file.managed:
        - names:
            - /etc/apt/apt.conf.d/20auto-upgrades:
                source: salt://common/files/20auto-upgrades
            - /etc/apt/apt.conf.d/50unattended-upgrades:
                source: salt://common/files/50unattended-upgrades
        - require:
            - pkg: .auto_updates
