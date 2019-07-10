#!stateconf yaml . jinja

.schedule:
    schedule.present:
        - function: state.highstate
        - minutes: 5
        - splay: 30
