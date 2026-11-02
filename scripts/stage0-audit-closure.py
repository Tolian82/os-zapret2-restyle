#!/usr/bin/env python3
"""Source-only Stage 0 audit closure record guard, never an appliance test."""
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
RECORD=Path("docs/verification/evidence/2026-11-02-v0.6.2_66-stage0-audit-closure.md")
STEPS=[f"0.{i:02d}" for i in range(1,17)]
OLD="1e21fbcac847529b94fea940241b4da7f86a42d33c129b7003ad04a72f4e5a0f"
KEY="9f3b76ffef38fb6405595038b324b61043c9a2c375ae5c151d628508e9a845ce"

class Refusal(Exception):
    pass

def need(value, reason):
    if not value:
        raise Refusal(reason)

def read(root,p):
    p=root/p
    need(p.is_file() and not p.is_symlink(),"MISSING_RECORD:"+str(p))
    return p.read_text(encoding="utf-8")

def verify(root):
    e=read(root,RECORD)
    make=read(root,Path("Makefile"))
    start=read(root,Path("docs/START_HERE.md"))
    state=read(root,Path("docs/PROJECT_STATE.md"))
    plan=read(root,Path("docs/architecture/OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_PLAN.md"))
    need(read(root,Path("VERSION")).strip()=="0.6.2" and
         re.search(r"(?m)^PLUGIN_REVISION=\s*66\s*$",make),"WRONG_VERSION")
    need("**Current handoff identity:** `v0.6.2_66`." in start and
         "`PLUGIN_REVISION=66`" in start,"WRONG_HANDOFF")
    need("Текущий этап — **`v0.6.2_66`**" in state and
         "package candidate: `os-zapret2-restyle-0.6.2_66.pkg`" in state,"WRONG_STATE")
    need("**Stage 0 audit status: CLOSED**" in plan and
         "Stage 1 READY FOR IMPLEMENTATION" in plan,"WRONG_PLAN_STATE")
    need("**Решение:** `CLOSED_AUDIT_ONLY`" in e and
         "Stage 0 AUDIT CLOSED" in e,"NOT_AUDIT_ONLY")
    rows=re.findall(r"(?m)^\| (0\.\d{2}) \| (AUDITED|NEGATIVE_CLASSIFIED) \|",e)
    need([row[0] for row in rows]==STEPS,"STAGE0_MISSING_OR_REORDERED")
    need(dict(rows)["0.12"]=="NEGATIVE_CLASSIFIED","FOREIGN_FILE_OWNERSHIP_MISCLASSIFIED")
    links=re.findall(r"\]\(([^)]+)\)",e)
    paths=[x.split("#")[0] for x in links if not x.startswith(("http://","https://","#"))]
    need(len(paths)>=16,"PROOF_LINKS_MISSING")
    for link in paths:
        q=(root/RECORD.parent/link).resolve()
        need(q.is_relative_to(root.resolve()) and q.is_file() and not q.is_symlink(),
             "INVALID_EVIDENCE_LINK:"+link)
    owner=read(root,Path("docs/verification/evidence/2026-11-01-v0.6.2_20-stage0-owner-opnsense-target-witness.md"))
    trusted=read(root,Path("docs/verification/evidence/2026-11-01-v0.6.2_26-stage0-owner-official-26.7-signing-key-pass.md"))
    catalog=read(root,Path("docs/verification/evidence/2026-11-01-v0.6.2_24-stage0-owner-target-trust-and-elf-acceptance.md"))
    native=read(root,Path("docs/verification/evidence/2026-11-02-v0.6.2_65-real-native-force-reinstall.md"))
    need(OLD in owner and "NO_PAIR" in owner and "FOREIGN" in owner,
         "ORIGINAL_BASELINE_OR_FOREIGN_REFUSAL_MISSING")
    need(KEY in trusted and "PASS_OFFICIAL_26_7_KEY_MATCH" in trusted,"OFFICIAL_SIGNING_PROOF_MISSING")
    need("PASS_CONFIGURED_TRUST_AND_LOCAL_RUNTIME" in catalog and
         "catalog_checked_with_configured_fingerprints=true" in catalog,"CATALOG_PROOF_MISSING")
    need("290" in native and "pkg add" in native,"NATIVE_PKG_PROOF_MISSING")
    for term in ("root pkg atomic admission","failed-hook compensation/rollback",
                 "safe configd worker PID reuse","NOT VERIFIED","NOT IMPLEMENTED"):
        need(term in e,"PRODUCT_SAFETY_BOUNDARY_MISSING:"+term)
    return {"schema":1,"status":"PASS_STAGE0_AUDIT_RECORD_ONLY",
            "step_count":len(STEPS),"stage0_audit_closed":True,
            "stage1_implemented":False,"full_product_acceptance":False,
            "foreign_repository_cleanup_permitted":False,
            "root_pkg_atomicity_proven":False,"owner_appliance_modified":False,
            "package_published":False}

def main():
    try: output=verify(ROOT)
    except (Refusal,OSError,ValueError) as exc:
        print("STAGE0_AUDIT_CLOSURE=REFUSED:"+str(exc),file=sys.stderr)
        return 2
    print("STAGE0_AUDIT_CLOSURE="+json.dumps(output,sort_keys=True))
    return 0

if __name__=="__main__":
    sys.exit(main())
