# DEC-2026-08-02 — Package post-install reloads actions without restarting the Web GUI

Status: Approved and implemented
Date: 2026-08-02

## Decision

When package contents replace files under
`/usr/local/opnsense/service/conf/actions.d`, `+POST_INSTALL` reloads those actions
through the canonical OPNsense plugin-framework operation:

`/usr/local/etc/rc.d/configd restart`

After the rc script returns, the hook must prove that configd accepts a real request
before invoking any further `configctl` action. The readiness probe is retried for a
bounded period and package installation fails visibly when configd never becomes ready.

The post-install order is:

1. register the plugin in OPNsense firmware state;
2. restart configd through the canonical rc script;
3. wait until `configctl system status` succeeds;
4. run `rc.configure_plugins POST_INSTALL` to flush plugin caches and configure shared
   plugin state;
5. render the `OPNsense/Zapret` template;
6. during package upgrade only, restore and verify a runtime that was running before
   replacement;
7. print the installation message.

The plugin package must not run `configctl webgui restart`,
`/usr/local/etc/rc.restart_webgui`, or an equivalent global Web GUI restart from any
package lifecycle hook. OPNsense cache flushing remains owned by
`rc.configure_plugins POST_INSTALL`; replacement browser assets are observed after the
normal request/cache lifecycle rather than by stopping global lighttpd/php-cgi workers.

## Reason

The upstream OPNsense plugin framework automatically adds the exact configd rc restart
when a plugin installs an `actions.d` directory. The project must mirror that canonical
operation because its custom package builder supplies manual lifecycle scripts.

Live installation of package candidate `0.2.8_7` on OPNsense 26.7.1_1 demonstrated the
failure of the previous expanded sequence. The hook restarted global configd, then
scheduled a global Web GUI restart. Configd accepted the request and generated WebGui
templates, but the operation never returned `OK`; both configd and lighttpd were left
unavailable with stale pid/socket files. Manually restoring configd and then issuing
the same Web GUI restart in a stable system succeeded. Therefore the defect was the
package-owned combined restart sequence, not ordinary Web GUI restart functionality.

The former focused test only searched for required command strings and ordering. It
therefore enforced the unsafe Web GUI restart instead of executing the hook contract.

## Consequences

- Package candidate advances to `0.2.8_8`.
- New configd actions are available immediately after package installation.
- Configd readiness is verified by an actual request, not socket-file presence alone.
- Package installation no longer stops or restarts global OPNsense Web GUI workers.
- A running Zapret runtime is still restored only after template rendering; stopped or
  absent runtime state remains unchanged.
- The lifecycle regression test executes `+POST_INSTALL` with behavioral mocks,
  exercises a failed then successful configd readiness probe, verifies the complete
  call order, and rejects every Web GUI restart path.
- Static checks remain only as supplemental guards for the canonical upstream rc path
  and prohibited global restart commands.

## Affected files and documentation

- `Makefile`
- `pkg/+POST_INSTALL`
- `scripts/test-package-lifecycle-restart.sh`
- `docs/decisions/DEC-2026-08-02-runtime-absent-lifecycle.md`
- this decision record
