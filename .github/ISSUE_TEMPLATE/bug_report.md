---
name: Bug report
about: Report a reproducible os-zapret2-restyle problem
title: "[Bug] "
labels: bug
assignees: Tolian82
---

## Environment

- OPNsense version:
- os-zapret2-restyle version or commit:
- Installation type:
- WAN interface type:

## Problem

Describe what happened and what you expected.

## Reproduction

1.
2.
3.

## Diagnostics

Provide relevant output with secrets removed:

```text
configctl zapret status
cat /var/run/zapret2-execution.status
pgrep -laf 'dvtws2|supervisor_loop'
```

## Additional information

Do not include passwords, tokens, private keys, or unredacted private configuration.
