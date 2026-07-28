# Contributing

Thank you for contributing to `os-zapret2-restyle`.

## Engineering principles

- Correctness over speed.
- No hidden magic or silent data loss.
- Prefer generic mechanisms over service-specific special cases.
- Keep backend modules focused on one responsibility.
- Validate candidate configuration before disturbing an active service.
- Preserve native zapret2 strategy syntax where possible.
- Use FreeBSD-compatible `/bin/sh`; do not introduce Bash-only syntax.
- Do not assume OPNsense framework, HTML, shell, or command behavior without verification.
- Discuss requirement or architecture changes before implementation.

## Required checks

Run the relevant checks before submitting a pull request:

```sh
find src pkg scripts -type f -name '*.sh' -exec sh -n {} \;
find src -type f -name '*.php' -exec php -l {} \;
find src -type f -name '*.xml' -exec xmllint --noout {} \;
git diff --check
```

Live OPNsense testing is required for changes affecting service lifecycle,
configuration generation, ipfw, dvtws2 startup, or the GUI Apply flow.

## Repository hygiene

Do not commit:

- runtime-v2 files;
- installed zapret2 engine files or binaries;
- `/conf/config.xml`;
- PID files or logs;
- `.orig`, `.rej`, editor backups, or temporary archives;
- credentials, tokens, private keys, public IP details, or other secrets.
