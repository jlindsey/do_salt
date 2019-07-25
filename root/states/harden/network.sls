#!stateconf yaml . jinja

.set_ipv4_params:
    sysctl.present:
        - names:
            - net.ipv4.icmp_ratelimit:
                - value: 100
            - net.ipv4.icmp_ratemask:
                - value: 88089
            - net.ipv4.tcp_rfc1337:
                - value: 1
            - net.ipv4.conf.all.log_martians:
                - value: 1
            - net.ipv4.conf.default.log_martians:
                - value: 1
