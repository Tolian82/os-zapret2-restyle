#!/usr/bin/env python3
"""Disposable-only native _102->published _104 bootstrap with +1s owner_start."""
import hashlib, importlib.util, json, os, re, stat, subprocess, sys, tempfile
from datetime import datetime, timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/"scripts"
SERVICE=Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
CONFIG=Path("/conf/config.xml")
JOURNAL=Path("/var/db/zapret2/shared-apply/operation.json")
EPOCHS=Path("/var/db/zapret2/auto-detect-epochs")
PID=Path("/var/run/dvtws2.pid")
ASSETS={
 "102":("https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.6.5_102/os-zapret2-restyle-0.6.5_102.pkg","17a0cfda2a966056372a66bd8ba1b7935a78016a8768a03e846538f8e74b1eda"),
 "104":("https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.6.5_104/os-zapret2-restyle-0.6.5_104.pkg","81b8e3b26d37de326c7233204fb954cd9bcdda7382ea04ce5679b50d0a4f75ee")
}
class Refused(RuntimeError): pass
def need(x,reason):
 if not x: raise Refused(reason)
def run(args,t=180):
 try: return subprocess.run(args,text=True,capture_output=True,timeout=t,check=False)
 except (OSError,subprocess.SubprocessError) as e: raise Refused("NATIVE_COMMAND_UNAVAILABLE") from e
def sha(path):
 h=hashlib.sha256()
 with path.open("rb") as src:
  for chunk in iter(lambda:src.read(1024*1024),b""):h.update(chunk)
 return h.hexdigest()
def module(name,identity):
 spec=importlib.util.spec_from_file_location(identity,HERE/name)
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 return mod
def version():
 x=run(["/usr/sbin/pkg","query","%v","os-zapret2-restyle"])
 need(x.returncode==0,"PKGDB_UNAVAILABLE");return x.stdout.strip()
def svc_status(expected):
 x=run([str(SERVICE),"status"],t=30)
 need(x.returncode==expected,"SERVICE_STATUS_UNEXPECTED")
def live_pid():
 need(PID.is_file() and not PID.is_symlink(),"PIDFILE_REFUSED")
 value=PID.read_text().strip()
 need(value.isdecimal() and int(value)>1,"ENGINE_PID_REFUSED")
 return int(value)
def journal():
 doc=json.loads(JOURNAL.read_bytes())
 need(doc.get("phase")=="committed","JOURNAL_NOT_COMMITTED")
 return doc
def get_pkg(n):
 url,digest=ASSETS[n];p=Path("/root")/("os-zapret2-restyle-0.6.5_"+n+".pkg")
 need(run(["/usr/bin/fetch","-o",str(p),url],t=130).returncode==0 and sha(p)==digest,"PUBLISHED_ARCHIVE_CHANGED_"+n)
 x=run(["/usr/bin/tar","-xOf",str(p),"+MANIFEST"])
 need(x.returncode==0,"MANIFEST_UNAVAILABLE")
 m=json.loads(x.stdout)
 need(m.get("name")=="os-zapret2-restyle" and m.get("version")=="0.6.5_"+n and m.get("abi")=="FreeBSD:15:amd64","PKG_IDENTITY_REFUSED_"+n)
 return p
def ipfw_owned():
 x=run(["/sbin/ipfw","-q","list"],t=20);need(x.returncode==0,"IPFW_UNAVAILABLE")
 return [l for l in x.stdout.splitlines() if l.split() and l.split()[0].isdigit() and 19000<=int(l.split()[0])<=19010]
def perturb_one_field(epoch):
 need(epoch.is_file() and not epoch.is_symlink() and stat.S_IMODE(epoch.stat().st_mode)==0o600,"EPOCH_UNTRUSTED")
 doc=json.loads(epoch.read_bytes());old=doc["owner_start"]
 fmt="%a %b %d %H:%M:%S %Y"
 doc["owner_start"]=(datetime.strptime(old,fmt)-timedelta(seconds=1)).strftime(fmt)
 need(doc["owner_start"]!=old,"CLOCK_DRIFT_NOT_PRODUCED")
 # ONLY disposable guest: reproduce a real kernel lstart drift without changing engine.
 epoch.write_bytes((json.dumps(doc,sort_keys=True,separators=(",",":"))+"\n").encode())
def main():
 need(os.geteuid()==0 and os.uname().sysname=="FreeBSD" and os.uname().machine=="amd64" and
      os.environ.get("GITHUB_ACTIONS")=="true" and
      os.environ.get("ZAPRET2_NATIVE_BUILD_CI")=="1" and
      os.environ.get("ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK")=="1" and
      os.environ.get("ZAPRET2_OWNER102_CLOCK_BOOTSTRAP")=="1" and
      os.environ.get("ZAPRET2_PROTECTED_PKG_NATIVE_TEST")=="1","DISPOSABLE_ONLY")
 need(run(["/usr/local/sbin/opnsense-version","-a"]).stdout.startswith("26.7"),"WRONG_OPNSENSE")
 need(run(["/usr/sbin/pkg","info","-e","os-zapret2-restyle"]).returncode==1,"GUEST_NOT_CLEAN")
 need(not Path("/var/db/zapret2-restyle/runtime-rollback").exists(),"ROLLBACK_PREEXISTS")
 old=get_pkg("102");new=get_pkg("104")
 need(run(["/usr/sbin/pkg","-o","REPO_AUTOUPDATE=false","add","-f",str(old)]).returncode==0 and version()=="0.6.5_102","NATIVE_102_INSTALL_FAILED")
 svc_status(1)
 bridge=module("test-own70-native-package-handoff.py","owner102_bridge")
 witness=module("p5b2b-native-witness.py","owner102_witness")
 protected=module("stage5-native-protected-update.py","owner102_cache")
 g03=module("stage2-opnsense-g03-first-install.py","owner102_g03")
 witness.set_guest_lo0();bridge.set_guest_list_mode()
 protected.seed_qualified_stable_tag_for_disposable_guest(g03)
 setup=g03.dispatch_and_poll();need(setup["installed"]=="1" and setup["service"]=="stopped","G03_SETUP_FAILED")
 for mode in ("list","auto"):
  out=run(["/usr/local/sbin/configctl","zapret","shared_apply","strategies",bridge.request(mode)],t=250)
  need(out.returncode==0 and "applied-id=" in out.stdout,"PREDECESSOR_APPLY_"+mode)
  svc_status(0)
 predecessor=journal();old_id=predecessor["detail"]["id"];old_pid=live_pid()
 epoch=EPOCHS/old_id/"epoch.json";cfg=sha(CONFIG)
 need(epoch.is_file() and ipfw_owned(),"AUTO_RUNNING_BASELINE_MISSING")
 perturb_one_field(epoch);corrupted_hash=sha(epoch)
 old_stop=run([str(SERVICE),"stop"],t=90)
 svc_status(0)
 need(old_stop.returncode!=0 and live_pid()==old_pid and sha(epoch)==corrupted_hash and sha(CONFIG)==cfg,"OLD_102_ONE_SECOND_STOP_REFUSAL_NOT_REPRODUCED")
 print("OWNER102_OLD_STOP=EXPECTED_REFUSAL",flush=True)
 with tempfile.TemporaryDirectory(prefix="owner102-stage-",dir="/root") as d:
  root=Path(d);root.chmod(0o700);stage=bridge.staged_source(new,root)
  installed_sha=sha(SERVICE)
  staged_status=bridge.recovered_status(stage,"status")
  # The _104 change is in the Python Auto-detect Stop modules; the
  # package-owned shell dispatcher itself is intentionally byte-identical.
  staged_differs=sha(stage/"backend"/"auto_detect_minute.py")!=sha(
      SERVICE.parent/"backend"/"auto_detect_minute.py")
  print("OWNER102_STAGED_STATUS="+json.dumps({
      "published_104_stop_module_differs_from_installed_102":staged_differs,
      "staged_status_rc":staged_status.returncode,
      "staged_reports_running":staged_status.stdout.strip()=="zapret is running",
      "native_status_rc":run([str(SERVICE),"status"],t=30).returncode,
  },sort_keys=True),flush=True)
  need(staged_differs,"STAGED_104_STOP_MODULE_NOT_DISTINCT")
  need(staged_status.returncode==0 and staged_status.stdout.strip()=="zapret is running","STAGED_104_RUNNING_OWNER_STATUS_REFUSED")
  stopped=bridge.recovered_status(stage,"stop",timeout=180)
  output={"staged_stop_rc":stopped.returncode,"config_unchanged":sha(CONFIG)==cfg,
          "old_retirement_receipt":(EPOCHS/old_id/"retired.json").is_file(),
          "remaining_plugin_rules":len(ipfw_owned()),"version":version(),
          "installed_script_unchanged":sha(SERVICE)==installed_sha}
  print("OWNER102_STAGED_STOP="+json.dumps(output,sort_keys=True),flush=True)
  need(stopped.returncode==0 and sha(CONFIG)==cfg and (EPOCHS/old_id/"retired.json").is_file() and
       not ipfw_owned() and version()=="0.6.5_102" and sha(SERVICE)==installed_sha,"STAGED_104_STOP_DID_NOT_COMMIT")
  svc_status(1)
 # Native old-package protected updater is used only AFTER verified STOPPED.
 updated=run([str(SERVICE),"pkg-update",str(new)],t=330)
 output=updated.stdout+"\n"+updated.stderr
 need(updated.returncode==0 and "pkg-update=verified-installed-and-restored" in output and
      not any(x in output for x in ("PRE-INSTALL script failed","PRE-DEINSTALL script failed","POST-INSTALL script failed","POST-DEINSTALL script failed")) and
      version()=="0.6.5_104" and not Path("/var/db/zapret2/pkg-update/operation.json").exists() and
      sha(CONFIG)==cfg,"STOPPED_PROTECTED_PACKAGE_UPGRADE_FAILED")
 svc_status(1)
 print("OWNER102_PROTECTED_PKG=PASS_VERIFIED_STOPPED_REPLACEMENT",flush=True)
 boot=run([str(SERVICE),"start"],t=180)
 svc_status(0);new_id=journal()["detail"]["id"]
 need(boot.returncode==0 and live_pid()!=old_pid and new_id!=old_id and
      (EPOCHS/new_id/"epoch.json").is_file() and sha(CONFIG)==cfg,"SUCCESSOR_NATIVE_START_FAILED")
 print("OWNER102_TO_104=PASS_STAGED_STOP_PROTECTED_PKG_AND_START",flush=True)
def test():
 fmt="%a %b %d %H:%M:%S %Y"
 x=(datetime.strptime("Thu Nov 19 14:28:00 2026",fmt)-timedelta(seconds=1)).strftime(fmt)
 need(x=="Thu Nov 19 14:27:59 2026" and len(ASSETS)==2 and
      all(len(item[1])==64 for item in ASSETS.values()),"DISPOSABLE_TEST_INVALID")
 print("OWNER102_TEST_SOURCE=PASS")
if __name__=="__main__":
 try:
  if sys.argv[1:]==["--self-test"]:test()
  elif sys.argv[1:]==["--native"]:main()
  else:raise Refused("EXPLICIT_TEST_MODE_REQUIRED")
 except (Refused,ValueError,KeyError,OSError,TypeError,subprocess.SubprocessError) as exc:
  print("OWNER102_TO_104=REFUSED:"+type(exc).__name__+":"+str(exc),file=sys.stderr);sys.exit(2)
