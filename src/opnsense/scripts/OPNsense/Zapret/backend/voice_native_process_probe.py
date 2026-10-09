#!/usr/bin/env python3
"""Read-only, adapter-injected FreeBSD Voice process probe (NOT production wired).

No CLI, kill, daemon or IPFW calls; only bounded /bin/ps reads and fixed
pidfile descriptors. Linux CI injects a fake ps reader. A caller must hold
Config and lifecycle locks and explicitly verify the native ps output format
before considering these observations authoritative for any live restore.
"""
from __future__ import annotations
import datetime
import os
from pathlib import Path
import platform
import re
import stat
import subprocess

from voice_cutover_backup import inspect_previous
from voice_process_recovery_evidence import (
    ProcessEvidenceError, _expected_paths, _runtime_args_digest,
)

MAX_PS = 2 * 1024 * 1024
MONTHS = {name: i for i,name in enumerate(
    ("Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"),1)}
START = re.compile(
    r"^\s*([0-9]+)\s+([A-Z][a-z]{2})\s+([A-Z][a-z]{2})\s+([0-9]{1,2})\s+"
    r"([0-9]{2}):([0-9]{2}):([0-9]{2})\s+([0-9]{4})\s+(.+?)\s*$"
)
PID = re.compile(r"^[1-9][0-9]{0,6}\n?$")


def _safe_paths(values):
    _expected_paths(values)
    if any(any(ch.isspace() for ch in value) for value in values.values()):
        raise ProcessEvidenceError("Voice command identity contains whitespace")
    return values


class FreeBSDVoiceProcessProbe:
    """Read-only source for capture_process_evidence; never authoritative alone."""

    def __init__(self, expected_paths: dict, pidfiles: dict,
                 previous_backup: Path, *, ps_reader=None):
        self.expected = dict(_safe_paths(expected_paths))
        if not isinstance(pidfiles,dict) or set(pidfiles) != set(self.expected):
            raise ProcessEvidenceError("incomplete Voice native pidfile map")
        self.pidfiles = dict(pidfiles)
        for path in self.pidfiles.values():
            if not isinstance(path,str) or not path.startswith("/var/run/") or \
               ".." in Path(path).parts or "\x00" in path or \
               any(ch.isspace() for ch in path):
                raise ProcessEvidenceError("untrusted Voice native pidfile path")
        if len(set(self.pidfiles.values())) != 3:
            raise ProcessEvidenceError("duplicate native Voice pidfile")
        self.previous_backup = Path(previous_backup)
        self.reader = ps_reader

    def _query(self, *arguments):
        argv=("/bin/ps",*arguments)
        if self.reader is not None:
            output=self.reader(argv)
        else:
            if platform.system() != "FreeBSD":
                raise ProcessEvidenceError("native Voice process probe requires FreeBSD")
            result=subprocess.run(argv,check=False,stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,text=True,timeout=5,
                                  env={"LC_ALL":"C","PATH":"/bin:/usr/bin"})
            if result.returncode != 0:
                raise ProcessEvidenceError("native FreeBSD process query failed")
            output=result.stdout
        if not isinstance(output,str) or len(output.encode("utf-8")) > MAX_PS:
            raise ProcessEvidenceError("invalid or oversized FreeBSD process listing")
        return output

    def _read_pid(self, path):
        flags=os.O_RDONLY | getattr(os,"O_NOFOLLOW",0) | getattr(os,"O_NONBLOCK",0)
        try:
            fd=os.open(path,flags)
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise ProcessEvidenceError("unreadable or linked Voice pidfile") from exc
        try:
            before=os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or \
               before.st_uid != os.geteuid() or before.st_mode & 0o022 or \
               before.st_size > 32:
                raise ProcessEvidenceError("unsafe Voice pidfile ownership or type")
            raw=os.read(fd,33)
            after=os.fstat(fd)
            if before.st_ino != after.st_ino or before.st_dev != after.st_dev or \
               before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
                raise ProcessEvidenceError("Voice pidfile changed while reading")
        finally:
            os.close(fd)
        try:
            text=raw.decode("ascii")
        except UnicodeError as exc:
            raise ProcessEvidenceError("non-ASCII Voice pidfile") from exc
        if not PID.fullmatch(text):
            raise ProcessEvidenceError("malformed Voice pidfile")
        pid=int(text.strip())
        if pid <= 1 or pid > 4194304:
            raise ProcessEvidenceError("Voice pidfile outside safe PID range")
        return pid

    @staticmethod
    def _parse_global(output):
        rows={}
        for line in output.splitlines():
            fields=line.split(None,1)
            if len(fields) != 2 or not fields[0].isdigit():
                raise ProcessEvidenceError("unexpected global FreeBSD ps row")
            pid=int(fields[0])
            if pid in rows or pid <= 0:
                raise ProcessEvidenceError("duplicate or invalid global Voice ps PID")
            rows[pid]=fields[1].split()
        return rows

    @staticmethod
    def _started(line,pid):
        m=START.fullmatch(line.strip())
        if m is None or int(m.group(1)) != pid or m.group(3) not in MONTHS:
            raise ProcessEvidenceError("unrecognized native ps start identity")
        try:
            timestamp=datetime.datetime(int(m.group(8)),MONTHS[m.group(3)],
                int(m.group(4)),int(m.group(5)),int(m.group(6)),
                int(m.group(7))).timestamp()
        except (ValueError,OverflowError,OSError) as exc:
            raise ProcessEvidenceError("invalid native process start date") from exc
        if timestamp <= 0:
            raise ProcessEvidenceError("invalid process start timestamp")
        return int(timestamp)*1000000000, m.group(9).split()

    def probe(self):
        """Probe all three roles; require no orphan or duplicate matching process."""
        saved=inspect_previous(self.previous_backup)
        args_sha=_runtime_args_digest(saved)
        pidmap={role:self._read_pid(path) for role,path in self.pidfiles.items()}
        all_rows=self._parse_global(self._query("-A","-ww","-o","pid=","-o","command="))
        engine=self.expected["engine"]
        daemon=self.expected["daemon"]
        loop=self.expected["monitor"]
        engines={pid for pid,tokens in all_rows.items() if engine in tokens}
        daemons={pid for pid,tokens in all_rows.items()
                 if daemon in tokens and loop in tokens}
        monitors={pid for pid,tokens in all_rows.items()
                  if loop in tokens and daemon not in tokens}
        expected_sets=(engines,daemons,monitors)
        roles=("engine","daemon","monitor")
        if all(pid is None for pid in pidmap.values()):
            if any(expected_sets):
                raise ProcessEvidenceError("orphan Voice process without pidfile")
            state="stopped"
            processes={role:{"pid":None,"start_ns":None,
                             "executable":self.expected[role]} for role in roles}
        else:
            if any(pid is None for pid in pidmap.values()) or \
               len(set(pidmap.values())) != 3 or \
               any(matches != {pidmap[role]} for role,matches in zip(roles,expected_sets)):
                raise ProcessEvidenceError("partial, foreign or multiple Voice processes")
            processes={}
            state="running"
            for role in roles:
                pid=pidmap[role]
                output=self._query("-p",str(pid),"-o","pid=","-o","lstart=","-o","command=")
                lines=output.splitlines()
                if len(lines) != 1:
                    raise ProcessEvidenceError("missing or multiple native process details")
                start_ns,tokens=self._started(lines[0],pid)
                if tokens != all_rows[pid]:
                    raise ProcessEvidenceError("Voice process command changed during observation")
                processes[role]={"pid":pid,"start_ns":start_ns,
                                 "executable":self.expected[role]}
        return {"engine":{"state":state,"process":processes["engine"],
                          "runtime_args_sha256":args_sha},
                "supervisor":{"state":state,"daemon":processes["daemon"],
                              "monitor":processes["monitor"]}}
