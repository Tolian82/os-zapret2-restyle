# Contributing

Thank you for contributing to `os-zapret2-restyle`.

## Canonical rules

General contributor rules are not duplicated here. Read:

- [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md) — `DOC-*`;
- [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md) — `DEV-*`;
- [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md) — `GH-*`.

Current work scope is defined by `START_HERE.md` and current facts by `PROJECT_STATE.md`.

## Required local checks

Run checks relevant to the changed files/behavior before submitting a PR. Common checks include:

```sh
find src pkg scripts -type f -name '*.sh' -exec sh -n {} \;
find src -type f -name '*.php' -exec php -l {} \;
find src -type f -name '*.xml' -exec xmllint --noout {} \;
git diff --check
```

Repository CI remains authoritative for the complete current automated matrix. Live OPNsense verification is selected by the current risk/evidence gate (`DEV-041`–`DEV-044`), not by a blanket rule that every change must repeat every appliance scenario.

## Repository-specific exclusions

In addition to `GH-031`–`GH-033`, do not commit runtime state or private installation data such as:

- generated `runtime-v2` contents;
- installed upstream zapret2 engine files/binaries;
- `/conf/config.xml`;
- PID files or runtime logs;
- credentials, tokens, private keys, or other secrets/private configuration.

Technical source changes must follow the platform/safety rules in `DEV-020`–`DEV-026`.
