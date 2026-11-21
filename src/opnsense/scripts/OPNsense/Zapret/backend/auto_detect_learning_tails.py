#!/usr/bin/env python3
"""Pure projection of independently attested original P2b N-inode cuts.

Not an owner/ACK authority: callers must acquire original FD9/P2a/GUI/FD4,
verify existing second-slot source+destination progress and physically re-read
both frozen and current original P2b native/debug evidence.
"""


def qualify_learning_forward_late_delta(frozen: dict, current: dict,
                                        learning: tuple) -> dict:
    """Compute ONLY the N-specific unread tail after the committed second cut.

    A domain and HOSTLIST alone do not identify the native clone. Keep the
    native_number for both equal-hostname YouTube TCP/QUIC observations.
    No P1, Found, managed, filesystem modification, cursor write, or ACK.
    """
    if (type(frozen) is not dict or type(current) is not dict or
            type(learning) is not tuple or not learning or
            type(frozen.get("native")) is not list or
            type(current.get("native")) is not list or
            len(frozen["native"]) != len(learning) or
            len(current["native"]) != len(learning) or
            type(frozen.get("debug")) is not dict or
            type(current.get("debug")) is not dict or
            frozen.get("p2b_drained") is not True or
            current.get("p2b_drained") is not True or
            frozen.get("commit_authorized") is not False or
            current.get("commit_authorized") is not False or
            frozen.get("ack_authorized") is not False or
            current.get("ack_authorized") is not False):
        raise ValueError("unqualified_original_forward_tail_sources")

    allowed = {(n, h) for n, h, _ in learning}
    if (len(allowed) != len(learning) or
            any(type(n) is not int or not 1 <= n <= 255 or
                h not in ("youtube", "user") or
                type(path) is not str or not path.startswith("/")
                for n, h, path in learning)):
        raise ValueError("invalid_original_learning_profile_map")

    def native_events(snapshot):
        rows = snapshot.get("native_observations")
        if type(rows) is not list:
            raise ValueError("missing_native_profile_provenance")
        normalized = []
        for row in rows:
            if (type(row) is not dict or
                    set(row) != {"native_number", "hostlist", "hostname"} or
                    type(row["native_number"]) is not int or
                    type(row["hostlist"]) is not str or
                    type(row["hostname"]) is not str or
                    not row["hostname"] or
                    (row["native_number"], row["hostlist"]) not in allowed):
                raise ValueError("foreign_native_profile_observation")
            normalized.append((row["native_number"], row["hostlist"],
                               row["hostname"]))
        if (normalized != sorted(set(normalized)) or
                snapshot.get("observations") != [
                    {"hostname": host, "hostlist": name}
                    for _, name, host in normalized]):
            raise ValueError("unqualified_native_observation_order")
        return normalized

    previous = native_events(frozen)
    after = native_events(current)
    if not set(previous).issubset(after):
        raise ValueError("original_second_observations_not_preserved")
    late = sorted(set(after) - set(previous))

    older, newer = frozen["debug"], current["debug"]
    if (any(older.get(key) != newer.get(key)
            for key in ("device", "inode", "start", "start_sha256")) or
            type(older.get("end")) is not int or
            type(newer.get("end")) is not int or
            newer["end"] < older["end"] or
            type(older.get("end_sha256")) is not str or
            type(newer.get("end_sha256")) is not str or
            (late and newer["end"] == older["end"])):
        raise ValueError("original_forward_debug_cursor_regressed")

    cursors = []
    total_tail = 0
    for index, (number, name, pathname) in enumerate(learning):
        prior, now = frozen["native"][index], current["native"][index]
        if (type(prior) is not dict or type(now) is not dict or
                prior.get("native_number") != number or
                now.get("native_number") != number or
                prior.get("hostlist") != name or
                now.get("hostlist") != name or
                prior.get("old_path") != now.get("old_path") or
                prior.get("old_device") != now.get("old_device") or
                prior.get("old_inode") != now.get("old_inode") or
                prior.get("old_start") != now.get("old_start") or
                prior.get("new_path") != now.get("new_path") or
                prior.get("new_device") != now.get("new_device") or
                prior.get("new_inode") != now.get("new_inode") or
                prior.get("new_start") != now.get("new_start") or
                (prior.get("new_path") is not None and
                 prior.get("new_path") != pathname) or
                (prior.get("new_path") is None and
                 prior.get("old_path") != pathname)):
            raise ValueError("original_forward_native_inode_or_order_changed")
        cursor = {"native_number": number, "hostlist": name}
        for side in ("old", "new"):
            path = prior.get(f"{side}_path")
            start = prior.get(f"{side}_end")
            end = now.get(f"{side}_end")
            if path is None:
                if (side != "new" or start is not None or end is not None or
                        prior.get(f"{side}_end_sha256") is not None or
                        now.get(f"{side}_end_sha256") is not None):
                    raise ValueError("original_forward_partial_new_inode")
                cursor[side] = None
                continue
            if (type(start) is not int or type(end) is not int or
                    start < 0 or end < start or
                    type(prior.get(f"{side}_end_sha256")) is not str or
                    type(now.get(f"{side}_end_sha256")) is not str):
                raise ValueError("original_forward_native_cursor_regressed")
            cursor[side] = {
                "path": path, "device": prior[f"{side}_device"],
                "inode": prior[f"{side}_inode"],
                "start": start, "start_sha256": prior[f"{side}_end_sha256"],
                "end": end, "end_sha256": now[f"{side}_end_sha256"],
                "unread_bytes": end - start,
            }
            total_tail += end - start
        cursors.append(cursor)
    return {
        "native": cursors,
        "debug": {
            "device": older["device"], "inode": older["inode"],
            "start": older["end"], "start_sha256": older["end_sha256"],
            "end": newer["end"], "end_sha256": newer["end_sha256"],
        },
        "native_observations": [
            {"native_number": number, "hostlist": name, "hostname": host}
            for number, name, host in late],
        "observations": [
            {"hostname": host, "hostlist": name}
            for _, name, host in late],
        "unread_native_bytes": total_tail,
        "p2b_drained": True,
        "cursor_advanced": False,
        "native_pending_ack_authorized": False,
        "native_cleanup_authorized": False,
        "generation_retired": False,
    }
