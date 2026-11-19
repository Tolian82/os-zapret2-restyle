#!/usr/bin/env python3
"""One installed five-HOSTLIST F5 after the existing G03 authenticated Apply.

No new VM or separate source of truth: G03 already persists and restarts all
five editors using the original FD9. This host-side Chromium probe reads the
SAME installed guest after those writes and performs one genuine F5. It never
submits an Apply, starts/stops a service or logs Config/domain values.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import runpy
import sys


class Refusal(RuntimeError):
    pass


# Exact expected content comes from the already-executed G03 native mutation,
# NOT a fabricated API fixture or a fallback to a source-only DOM.
EXPECTED = {
    "youtube_manual": "!blocked.example.com\nmanual-youtube.example.org",
    "youtube_found": "zapret-youtube.org\n",
    "user_manual": "^exact.example.org\nmanual-user.example.com",
    "user_found": "zapret-user.com\n",
    "shared_found": "",
}
INPUTS = {
    "youtube_manual": "zapret.hostlist.youtubedomains",
    "youtube_found": "zapretYoutubeFound",
    "user_manual": "zapret.hostlist.userdomains",
    "user_found": "zapretUserFound",
    "shared_found": "zapretSharedFound",
}


def demand(value: bool, reason: str) -> None:
    if not value:
        raise Refusal(reason)


def run() -> None:
    demand(os.environ.get("GITHUB_ACTIONS") == "true" and
           os.environ.get("ZAPRET2_G03_FIVE_F5") == "1" and
           os.environ.get("STAGE5_LOCAL_CHROMIUM"),
           "G03_F5_DISPOSABLE_HOST_OPTIN_REQUIRED")
    # Reuse the previous native P3 browser's real login, read API, and
    # GET/F5 waiters. No duplicate mock of OPNsense rendering.
    p3 = runpy.run_path(str(Path(__file__).with_name("p3-browser-i18n.py")))
    from playwright.sync_api import sync_playwright

    def observe(page) -> dict:
        page.wait_for_function(
            """expected => Object.entries(expected).every(([key, spec]) => {
                const field = document.getElementById(spec.id);
                return field && field.value === spec.content;
            })""",
            arg={key: {"id": INPUTS[key], "content": EXPECTED[key]}
                 for key in EXPECTED},
            timeout=30000,
        )
        snapshot = p3["check_tz6v3_five_source_read"](page)
        demand(snapshot["auto_owned_complete"] is True,
               "G03_F5_FOUND_SOURCE_NOT_INITIALIZED")
        # The native OPNsense textarea supplies manual bytes, while the
        # root-locked API returns only length/revision, never an echoed manual
        # content field. Verify the fixture against the *saved* SHA proof.
        def source_matches(key: str) -> bool:
            row = snapshot["editors"][key]
            expected = EXPECTED[key]
            if key.endswith("_manual"):
                raw = expected.encode("utf-8")
                return (row.get("owner") == "config" and
                        "content" not in row and
                        row.get("length_bytes") == len(raw) and
                        row.get("revision") ==
                        hashlib.sha256(b"present\0" + raw).hexdigest())
            return row.get("content") == expected

        demand(all(source_matches(key) for key in EXPECTED),
               "G03_F5_SAVED_CONTENT_NOT_PERSISTED")
        demand(all(page.locator('[id="' + INPUTS[key] + '"]').input_value() ==
                   EXPECTED[key] for key in EXPECTED),
               "G03_F5_NATIVE_RENDER_MISMATCH")
        demand(page.locator("#reconfigureAct").count() == 1 and
               page.locator("#zapretAutoHostlistSave").count() == 0 and
               page.locator("#zapretAutoHostlistReload").count() == 0,
               "G03_F5_LEGACY_OR_MULTIPLE_APPLY_CONTROLS")
        return snapshot

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=os.environ["STAGE5_LOCAL_CHROMIUM"])
        try:
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()
            p3["login"](page)
            p3["wait_native_load"](
                page, "/api/zapret/settings/get",
                "/ui/zapret", "frm_GeneralSettings")
            before = observe(page)
            p3["f5_and_wait"](page, "/api/zapret/settings/get")
            after = observe(page)
            demand(after == before, "G03_F5_NATIVE_SOURCE_REVISIONS_CHANGED")
            context.close()
        finally:
            browser.close()
    print("G03_CHROMIUM_FIVE_HOSTLIST_F5=PASS_REAL_INSTALLED_POST_WRITE_RELOAD")


if __name__ == "__main__":
    try:
        run()
    except (Refusal, KeyError, ValueError, OSError) as error:
        # G03 test content is private fixture data: print only stable code.
        print("G03_CHROMIUM_FIVE_HOSTLIST_F5=REFUSED:" + str(error),
              file=sys.stderr)
        raise SystemExit(1)
