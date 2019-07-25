#!stateconf yaml . jinja

.networking:
    file.managed:
        - mode: 644
        - user: root
        - group: root
        - names:
            - /etc/systemd/network/dummy0.netdev:
                - source: salt://consul/files/dummy0.netdev
            - /etc/systemd/network/dummy0.network:
                - source: salt://consul/files/dummy0.network
    service.running:
        - name: systemd-networkd
        - watch:
            - file: .networking
