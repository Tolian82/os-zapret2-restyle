#!/usr/bin/env python3
"""Stage 1 source-only OPNsense compatibility policy and explicit target-tuple checks.

NOT an installer admission gate. Never probes, installs or mutates the host.
The supported tuple is limited to the scope of its recorded qualification:
actual native Mk/pkg on disposable OPNsense, not final lifecycle acceptance.
"""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "compatibility.json"
TOP = {"schema_version", "target_product", "supported_platforms",
       "required_capabilities", "exceptions", "private_curl_impersonate"}
PLATFORM = {"opnsense_product_abi", "freebsd_pkg_abi", "architecture",
            "python", "qualification"}
PYTHON = {"policy", "entrypoint", "supported"}
QUALIFICATION = {"scope", "evidence"}
PRIVATE_CURL = {"selection", "repository", "repository_url", "abi",
                "version", "source_pkg_sha256", "elf_sha256", "chrome_profile"}


def validate_private_curl_source(lock):
    """Validate exact signed-source/ELF identity; no implicit fallback."""
    exact(lock, PRIVATE_CURL, "INVALID_PRIVATE_CURL_FIELDS")
    require(lock["repository"] == "FreeBSD" and
            lock["repository_url"] == "pkg+https://pkg.FreeBSD.org/${ABI}/latest" and
            lock["abi"] == "FreeBSD:15:amd64",
            "UNQUALIFIED_PRIVATE_CURL_SOURCE_REPOSITORY_OR_ABI")
    require(lock["selection"] in ("exploratory", "pinned"),
            "UNQUALIFIED_PRIVATE_CURL_SELECTION")
    names = ("version", "source_pkg_sha256", "elf_sha256", "chrome_profile")
    if lock["selection"] == "exploratory":
        require(all(lock[k] is None for k in names),
                "FLOATING_PRIVATE_CURL_CANNOT_CLAIM_A_PIN")
    else:
        require(isinstance(lock["version"], str) and
                re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z._,+~-]{0,127}",
                             lock["version"]) is not None,
                "PRIVATE_CURL_PIN_VERSION_INVALID")
        for key in ("source_pkg_sha256", "elf_sha256"):
            require(isinstance(lock[key], str) and
                    re.fullmatch(r"[a-f0-9]{64}", lock[key]) is not None,
                    "PRIVATE_CURL_PIN_HASH_INVALID:" + key)
        require(isinstance(lock["chrome_profile"], str) and
                re.fullmatch(r"chrome[0-9]+", lock["chrome_profile"]) is not None,
                "PRIVATE_CURL_PIN_CHROME_PROFILE_INVALID")
    return lock



class Refusal(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise Refusal(reason)


def exact(obj, fields, reason):
    require(isinstance(obj, dict) and set(obj) == fields, reason)


def unique_pairs(pairs):
    out = {}
    for k, v in pairs:
        require(k not in out, "DUPLICATE_JSON_KEY:" + k)
        out[k] = v
    return out


def load(path):
    require(path.is_file() and not path.is_symlink(), "POLICY_FILE_MISSING")
    try:
        return json.loads(path.read_text(encoding="utf-8"),
                          object_pairs_hook=unique_pairs,
                          parse_constant=lambda x: (_ for _ in ()).throw(
                              Refusal("NONFINITE_JSON_VALUE")))
    except (UnicodeError, json.JSONDecodeError):
        raise Refusal("INVALID_JSON") from None


def validate(policy, root=ROOT):
    exact(policy, TOP, "INVALID_TOP_LEVEL_FIELDS")
    require(type(policy["schema_version"]) is int and
            policy["schema_version"] == 1, "UNSUPPORTED_SCHEMA")
    require(policy["target_product"] == "OPNsense",
            "UNSUPPORTED_TARGET_PRODUCT")
    platforms = policy["supported_platforms"]
    require(isinstance(platforms, list) and platforms, "EMPTY_PLATFORM_MATRIX")
    for k in ("required_capabilities", "exceptions"):
        require(isinstance(policy[k], list), "INVALID_" + k.upper())
    required = policy["required_capabilities"]
    require(len(required) == len(set(str(x) for x in required)) and
            all(isinstance(x, str) and
                re.fullmatch(r"[a-z][a-z0-9-]{1,63}", x) for x in required),
            "INVALID_REQUIRED_CAPABILITIES")
    validate_private_curl_source(policy["private_curl_impersonate"])
    # Stage 1 does not define scoped exception semantics; do not admit an
    # arbitrary exception or silently let one widen compatibility.
    require(policy["exceptions"] == [], "UNQUALIFIED_EXCEPTION_POLICY")
    seen = set()
    for p in platforms:
        exact(p, PLATFORM, "INVALID_PLATFORM_FIELDS")
        product, abi, arch = (p["opnsense_product_abi"],
                              p["freebsd_pkg_abi"], p["architecture"])
        require(isinstance(product, str) and
                re.fullmatch(r"[0-9]{2}\.[0-9]{1,2}", product),
                "INVALID_OPNSENSE_ABI")
        require(isinstance(abi, str) and
                re.fullmatch(r"FreeBSD:[1-9][0-9]*:amd64", abi),
                "INVALID_FREEBSD_PACKAGE_ABI")
        require(arch == "amd64" and abi.endswith(":" + arch),
                "ABI_ARCHITECTURE_MISMATCH")
        combo = (product, abi, arch)
        require(combo not in seen, "DUPLICATE_PLATFORM_TUPLE")
        seen.add(combo)
        python = p["python"]
        exact(python, PYTHON, "INVALID_PYTHON_POLICY_FIELDS")
        require(python["policy"] == "opnsense-PLUGIN_PYTHON" and
                python["entrypoint"] == "/usr/local/bin/python3",
                "UNQUALIFIED_PYTHON_ENTRYPOINT")
        branches = python["supported"]
        require(isinstance(branches, list) and branches and
                all(isinstance(x, str) and
                    re.fullmatch(r"3\.[0-9]{1,2}", x) for x in branches) and
                len(branches) == len(set(branches)),
                "INVALID_PYTHON_BRANCHES")
        q = p["qualification"]
        exact(q, QUALIFICATION, "INVALID_QUALIFICATION_FIELDS")
        require(q["scope"] == "isolated-native-build-and-pkg-install-only",
                "UNQUALIFIED_ACCEPTANCE_SCOPE")
        name = q["evidence"]
        require(isinstance(name, str) and
                re.fullmatch(r"docs/verification/evidence/[A-Za-z0-9_.-]+\.md", name),
                "INVALID_QUALIFICATION_EVIDENCE_PATH")
        evidence = (root / name)
        require(evidence.is_file() and not evidence.is_symlink(),
                "QUALIFICATION_EVIDENCE_NOT_FOUND")
        body = evidence.read_text(encoding="utf-8")
        major = abi.split(":")[1]
        require("OPNsense " + product + " / FreeBSD " + major in body,
                "QUALIFICATION_EVIDENCE_PLATFORM_MISMATCH")
    return platforms


def check_target(policy, product, abi, arch, python_version, capabilities=()):
    platforms = policy["supported_platforms"]
    require(any(p["opnsense_product_abi"] == product for p in platforms),
            "UNSUPPORTED_OPNSENSE_PRODUCT_ABI")
    require(any(p["freebsd_pkg_abi"] == abi for p in platforms),
            "UNSUPPORTED_FREEBSD_ABI")
    require(any(p["architecture"] == arch for p in platforms),
            "UNSUPPORTED_ARCHITECTURE")
    matched = [p for p in platforms if
               (p["opnsense_product_abi"], p["freebsd_pkg_abi"],
                p["architecture"]) == (product, abi, arch)]
    require(len(matched) == 1, "UNQUALIFIED_PLATFORM_TUPLE")
    require(isinstance(python_version, str) and
            re.fullmatch(r"3\.[0-9]{1,2}(?:\.[0-9]+)?", python_version),
            "INVALID_PYTHON_RUNTIME_VERSION")
    branch = ".".join(python_version.split(".")[:2])
    require(branch in matched[0]["python"]["supported"],
            "UNSUPPORTED_PYTHON_BRANCH")
    missing = set(policy["required_capabilities"]) - set(capabilities)
    require(not missing, "MISSING_REQUIRED_CAPABILITY:" + ",".join(sorted(missing)))
    return {"status": "PASS_QUALIFIED_POLICY_TUPLE_ONLY",
            "opnsense_product_abi": product,
            "freebsd_pkg_abi": abi,
            "architecture": arch,
            "python_branch": branch,
            "qualification_scope": matched[0]["qualification"]["scope"],
            "native_lifecycle_acceptance": False,
            "owner_device_acceptance": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT)
    parser.add_argument("--opnsense-abi")
    parser.add_argument("--freebsd-pkg-abi")
    parser.add_argument("--architecture")
    parser.add_argument("--python-version")
    parser.add_argument("--capability", action="append", default=[])
    args = parser.parse_args(argv)
    supplied = (args.opnsense_abi, args.freebsd_pkg_abi,
                args.architecture, args.python_version)
    try:
        policy = load(args.policy)
        platforms = validate(policy, ROOT)
        require(all(x is not None for x in supplied) or
                all(x is None for x in supplied), "INCOMPLETE_TARGET_PROBE")
        result = (check_target(policy, *supplied, args.capability)
                  if supplied[0] is not None else
                  {"status": "PASS_POLICY_SCHEMA_ONLY",
                   "qualified_tuple_count": len(platforms),
                   "native_lifecycle_acceptance": False,
                   "owner_device_acceptance": False})
    except (Refusal, OSError) as error:
        print("COMPATIBILITY=REFUSED:" + str(error), file=sys.stderr)
        return 2
    print("COMPATIBILITY=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
