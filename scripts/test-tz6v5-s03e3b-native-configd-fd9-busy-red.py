#!/usr/bin/env python3
"""S03e3b old native configd stop/restart FD9 BUSY RED, disposable CI ONLY."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

S = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
A = Path("/usr/local/opnsense/service/conf/actions.d/actions_zapret.conf")
P = Path("/usr/local/opnsense/mvc/app/controllers/OPNsense/Base/ApiMutableServiceControllerBase.php")
G = Path("/usr/local/opnsense/mvc/app/views/OPNsense/Zapret/general.volt")
C = Path("/conf/config.xml")
L = Path("/var/run/zapret2-lifecycle.lock")
K = Path("stage5-browser-wan-ci.pub")

class Refuse(Exception): pass

def need(ok, why):
    if not ok: raise Refuse(why)

def query(argv, timeout=15):
    try:
        return subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              check=False, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        raise Refuse("S03E3B_QUERY_UNAVAILABLE_OR_TIMEOUT") from None

def digest(data):
    return hashlib.sha256(data).hexdigest()

def preflight():
    need(sys.platform.startswith("freebsd") and os.geteuid() == 0 and
         os.getenv("GITHUB_ACTIONS") == "true" and
         os.getenv("ZAPRET2_STAGE5_BROWSER_WAN") == "1",
         "S03E3B_DISPOSABLE_CI_FREEBSD_ONLY")
    auth = Path("/root/.ssh/authorized_keys")
    need(K.is_file() and not K.is_symlink() and auth.is_file() and
         K.read_bytes().strip() in auth.read_bytes().splitlines(),
         "S03E3B_EXACT_GUEST_ATTESTATION_MISSING")
    need(all(p.is_file() and not p.is_symlink() for p in (S,A,P,G,C)),
         "S03E3B_INSTALLED_SOURCE_MISSING")
    need(query(["pkg","info","-e","os-zapret2-restyle"]).returncode == 0 and
         query(["opnsense-version","-a"]).stdout.strip() == b"26.7",
         "S03E3B_NOT_INSTALLED_OPNSENSE_26_7")
    need(not Path("/usr/local/etc/zapret2/binaries/my/dvtws2").exists() and
         not Path("/var/db/zapret2/pkg-update/operation.json").exists() and
         not Path("/var/run/zapret2-restyle/pkg-replacement.restart").exists(),
         "S03E3B_ENGINE_OR_PENDING_UPDATE")
    shell, actions, parent, gui = (p.read_text(encoding="utf-8") for p in (S,A,P,G))
    need("LIFECYCLE_LOCK_FILE=" in shell and
         "/var/run/zapret2-lifecycle.lock" in shell and
         "LOCKF_BIN" in shell and "service_with_lifecycle_lock" in shell,
         "S03E3B_ACTUAL_ORIGINAL_FD9_CHANGED")
    for verb in ("stop","restart"):
        need("[" + verb + "]\ncommand:" + str(S) + " " + verb + "\n" in actions,
             "S03E3B_CONFIGD_ACTION_CHANGED_" + verb)
        segments=parent.split("public function "+verb+"Action()",1)
        need(len(segments) == 2 and
             ("' "+verb+"'") in segments[1].split("public function",1)[0] and
             "return ['response' => $response];" in segments[1].split("public function",1)[0],
             "S03E3B_INHERITED_API_CHANGED_" + verb)
    need("url: '/api/zapret/service/' + action" in gui and
         "}).done(function() {" in gui, "S03E3B_GUI_HANDLER_CHANGED")
    need(not L.is_symlink(),"S03E3B_FD9_SYMLINK_REFUSED")
    if L.exists():
        st=L.stat()
        need(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and not st.st_mode & 0o022,
             "S03E3B_FD9_OWNER_UNEXPECTED")

def witness():
    ip=query(["/sbin/ipfw","-q","list"])
    ps=query(["ps","-axo","command="])
    need(ps.returncode == 0 and b"dvtws2" not in ps.stdout and
         b"supervisor_loop.sh" not in ps.stdout, "S03E3B_ENGINE_OR_SUPERVISOR_RUNNING")
    return (digest(C.read_bytes()),
            digest(str(ip.returncode).encode()+b"\0"+ip.stdout+b"\0"+ip.stderr))

def probe():
    return query(["/bin/sh","-c",
        'exec 9>"$1"; /usr/bin/lockf -s -t 0 9',"s03e3b-check",str(L)],5).returncode

def summary(raw):
    raw=raw.strip()
    return "OK" if raw==b"OK" else ("EMPTY" if not raw else
           ("EXECUTE_ERROR" if raw.startswith(b"Execute error") else "OTHER_REDACTED"))

def native():
    preflight()
    before=witness()
    need(probe()==0,"S03E3B_ORIGINAL_FD9_NOT_FREE")
    owner=subprocess.Popen(["/bin/sh","-c",
        'exec 9>"$1"; /usr/bin/lockf -s -t 0 9 || exit 75; exec /bin/sleep 180',
        "s03e3b-test-owned-only",str(L)],
        stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    children=[]
    started=time.monotonic()
    try:
        busy=False
        for _ in range(60):
            need(owner.poll() is None,"S03E3B_TEST_OWNER_EXITED")
            if probe()!=0: busy=True;break
            time.sleep(.1)
        need(busy,"S03E3B_FD9_BUSY_NOT_CONFIRMED")
        for verb in ("stop","restart"):
            for kind,argv in (("shell",["/bin/sh",str(S),verb]),
                              ("configd",["/usr/local/sbin/configctl","zapret",verb])):
                children.append((kind,verb,subprocess.Popen(argv,stdout=subprocess.PIPE,
                                                              stderr=subprocess.PIPE)))
        receipts=[]
        for kind,verb,child in children:
            try: out,err=child.communicate(timeout=110)
            except subprocess.TimeoutExpired:
                raise Refuse("S03E3B_NATIVE_ACTION_TIMEOUT_"+kind+"_"+verb)
            if kind=="shell":
                need(child.returncode==75 and not out.strip() and
                     b"another zapret lifecycle operation is already running" in err,
                     "S03E3B_NATIVE_SHELL_RC75_CHANGED_"+verb)
            else:
                receipts.append({"action":verb,"rc":child.returncode,
                                 "stdout_class":summary(out),"stderr_present":bool(err.strip())})
        need(owner.poll() is None and probe()!=0 and witness()==before,
             "S03E3B_LOCK_OR_CONFIG_IPFW_CHANGED")
        remaining=75-(time.monotonic()-started)
        if remaining>0: time.sleep(remaining)
        ps=query(["ps","-axo","command="])
        need(ps.returncode==0 and
             not re.search(rb"/zapret_service\.sh (?:stop|restart)(?:\s|$)",ps.stdout) and
             witness()==before,"S03E3B_PENDING_CONFIGD_CHILD_OR_STATE_CHANGED")
        print("S03E3B_NATIVE_STOP_RESTART_RED="+json.dumps({
            "original_fd9_busy":True,"shell_rc75":2,
            "configd_observed":receipts,"config_ipfw_engine_unchanged":True,
            "physical_transition_executed":False,"gui_native_producer_not_tested":True,
            "owner_appliance_unchanged":True},sort_keys=True))
    finally:
        for _,_,child in children:
            if child.poll() is None:
                child.terminate()
                try:child.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill();child.communicate(timeout=3)
        if owner.poll() is None:
            owner.terminate()
            try:owner.wait(timeout=4)
            except subprocess.TimeoutExpired:
                owner.kill();owner.wait(timeout=3)
    need(witness()==before,"S03E3B_POST_FD9_NATIVE_STATE_CHANGED")
    print("S03E3B_REAL_CONFIGD_STOP_RESTART_FD9_BUSY_RED_PASS")

def main():
    try:
        if sys.argv[1:]==["--self-test"]:
            need(summary(b"OK\n")=="OK" and summary(b"")=="EMPTY" and
                 summary(b"secret")=="OTHER_REDACTED","S03E3B_REDACTION_FAILED")
            print("S03E3B_INERT_SELF_TEST_PASS")
        elif sys.argv[1:]==["--native"]:native()
        else:raise Refuse("S03E3B_USAGE")
    except (Refuse,OSError,ValueError) as e:
        print("S03E3B_FAIL="+str(e)[:170],file=sys.stderr)
        return 2
    return 0

if __name__=="__main__":raise SystemExit(main())
