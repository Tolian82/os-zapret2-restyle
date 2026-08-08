"""Structured finite subprocess execution and DNS/TLS/HTTP/UDP parsing for Strategy Lab."""

from __future__ import annotations

import ipaddress
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

EX_OK = 0
EX_USAGE = 64
EX_SOFTWARE = 70
EX_TIMEOUT = 124
DNS_TIMEOUT_SECONDS = 15

DEFAULT_BINARIES = {
    "curl": "/usr/local/bin/curl",
    "drill": "/usr/bin/drill",
    "openssl": "/usr/bin/openssl",
    "netstat": "/usr/bin/netstat",
    "nc": "/usr/bin/nc",
}
BINARY_ENV = {
    "curl": "STRATEGY_LAB_CURL_BIN",
    "drill": "STRATEGY_LAB_DRILL_BIN",
    "openssl": "STRATEGY_LAB_OPENSSL_BIN",
    "netstat": "STRATEGY_LAB_NETSTAT_BIN",
    "nc": "STRATEGY_LAB_NC_BIN",
}
SECTION_RE = re.compile(r"^;;\s+([A-Z]+)\s+SECTION:\s*$")
CURL_EXIT_RE = re.compile(r"(?:^|\s)exit=(\d+)(?:\s|$)", re.MULTILINE)


class RequestError(RuntimeError):
    pass


class UsageError(RequestError):
    pass


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool
    termination: str
    signal: int | None
    duration_ms: int

    @property
    def ok(self) -> bool:
        return not self.timed_out and self.returncode == 0

    def evidence(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DnsResult:
    classification: str
    answers: list[str]
    execution: CommandResult

    @property
    def ok(self) -> bool:
        return self.classification == "pass"

    def evidence(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "answers": self.answers,
            "execution": self.execution.evidence(),
        }


def _text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value


def binary(name: str) -> str:
    value = os.environ.get(BINARY_ENV[name], DEFAULT_BINARIES[name])
    if not os.path.isfile(value) or not os.access(value, os.X_OK):
        raise RequestError(f"required Strategy Lab executable is unavailable: {value}")
    return value


def run_command(
    command: Sequence[str],
    *,
    timeout: float,
    stdin_devnull: bool = False,
    stdin_path: Path | None = None,
) -> CommandResult:
    if timeout <= 0:
        raise UsageError("Strategy Lab subprocess timeout must be positive")
    if stdin_devnull and stdin_path is not None:
        raise UsageError("Strategy Lab subprocess stdin source is ambiguous")
    argv = [str(item) for item in command]
    started = time.monotonic()
    stdin_handle = None
    try:
        if stdin_path is not None:
            stdin_handle = stdin_path.open("rb")
        completed = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=stdin_handle if stdin_handle is not None else (subprocess.DEVNULL if stdin_devnull else None),
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        duration = max(0, round((time.monotonic() - started) * 1000))
        return CommandResult(
            command=argv,
            returncode=None,
            stdout=_text(exc.stdout),
            stderr=_text(exc.stderr),
            timed_out=True,
            termination="timeout",
            signal=None,
            duration_ms=duration,
        )
    except OSError as exc:
        raise RequestError(f"Strategy Lab subprocess could not start: {argv[0]}: {exc}") from exc
    finally:
        if stdin_handle is not None:
            stdin_handle.close()

    duration = max(0, round((time.monotonic() - started) * 1000))
    signal_number = -completed.returncode if completed.returncode < 0 else None
    return CommandResult(
        command=argv,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        timed_out=False,
        termination="signal" if signal_number is not None else "completed",
        signal=signal_number,
        duration_ms=duration,
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


def combined_log(result: CommandResult) -> str:
    text = result.stdout + result.stderr
    if result.timed_out:
        text += "Strategy Lab subprocess timeout\n"
    return text


def tail20(text: str) -> str:
    lines = text.splitlines()
    return "" if not lines else "\n".join(lines[-20:]) + "\n"


def parse_drill_answers(output: str, record_type: str) -> list[str]:
    qtype = record_type.upper()
    if qtype not in {"A", "AAAA"}:
        raise UsageError("unsupported DNS record type")
    in_answer = False
    answers: list[str] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        section = SECTION_RE.match(line)
        if section:
            in_answer = section.group(1) == "ANSWER"
            continue
        if not in_answer or not line or line.startswith(";"):
            continue
        fields = line.split()
        try:
            in_index = fields.index("IN")
        except ValueError:
            continue
        if in_index + 2 >= len(fields) or fields[in_index + 1].upper() != qtype:
            continue
        candidate = fields[in_index + 2].rstrip(".")
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if qtype == "A" and address.version != 4:
            continue
        if qtype == "AAAA" and address.version != 6:
            continue
        normalized = str(address)
        if normalized not in answers:
            answers.append(normalized)
    return answers


def classify_dns(result: CommandResult, record_type: str) -> DnsResult:
    if result.timed_out:
        return DnsResult("timeout", [], result)
    if result.returncode != 0:
        return DnsResult("command_error", [], result)
    answers = parse_drill_answers(result.stdout, record_type)
    if not answers:
        return DnsResult("parser_rejected", [], result)
    return DnsResult("pass", answers, result)


def dns_request(host: str, record_type: str) -> DnsResult:
    return classify_dns(
        run_command([binary("drill"), host, record_type], timeout=DNS_TIMEOUT_SECONDS),
        record_type,
    )


def _curl_command(
    host: str,
    *,
    scheme: str,
    family: str = "ipv4",
    tls_version: str | None = None,
    bound_ip: str | None = None,
) -> list[str]:
    if family not in {"ipv4", "ipv6"}:
        raise UsageError("invalid curl address family")
    if scheme not in {"http", "https"}:
        raise UsageError("invalid curl scheme")
    command = [binary("curl"), f"--{family}", "--proto", f"={scheme}"]
    if tls_version is not None:
        if tls_version not in {"1.2", "1.3"}:
            raise UsageError("invalid TLS version")
        command.extend([f"--tlsv{tls_version}", "--tls-max", tls_version])
    command.extend(["--http1.1", "--request", "GET"])
    if bound_ip is None:
        command.extend(["--location", "--max-redirs", "2"])
    else:
        port = 443 if scheme == "https" else 80
        command.extend(["--max-redirs", "0", "--resolve", f"{host}:{port}:{bound_ip}"])
    command.extend([
        "--connect-timeout", "2",
        "--max-time", "3",
        "--retry", "0",
        "--silent",
        "--show-error",
        "--header", "Connection: close",
        "--range", "0-65535",
        "--output", "/dev/null",
        "--write-out", "exit=%{exitcode} remote_ip=%{remote_ip} http=%{http_version} code=%{response_code} bytes=%{size_download}\\n",
        f"{scheme}://{host}/",
    ])
    return command


def curl_request(
    host: str,
    *,
    scheme: str,
    family: str = "ipv4",
    tls_version: str | None = None,
    bound_ip: str | None = None,
) -> CommandResult:
    return run_command(
        _curl_command(host, scheme=scheme, family=family, tls_version=tls_version, bound_ip=bound_ip),
        timeout=4,
    )


def curl_exit(result: CommandResult) -> int:
    match = None
    for match in CURL_EXIT_RE.finditer(result.stdout):
        pass
    if match is not None:
        return int(match.group(1), 10)
    if result.returncode is not None and result.returncode >= 0:
        return result.returncode
    return 1


def ipv6_default_route() -> tuple[bool, CommandResult]:
    result = run_command([binary("netstat"), "-rn", "-f", "inet6"], timeout=2)
    available = result.ok and any(
        line.split()[:1] == ["default"] for line in result.stdout.splitlines() if line.strip()
    )
    return available, result


def quic_ipv4_request() -> CommandResult:
    return run_command([
        binary("openssl"), "s_client", "-4", "-quic",
        "-connect", "yandex.ru:443", "-servername", "yandex.ru",
        "-alpn", "h3", "-verify_hostname", "yandex.ru",
        "-verify_return_error", "-brief", "-no-interactive",
    ], timeout=2, stdin_devnull=True)


def quic_target_request(host: str, address: str) -> CommandResult:
    try:
        normalized = str(ipaddress.IPv4Address(address))
    except ipaddress.AddressValueError as exc:
        raise UsageError("invalid QUIC IPv4 endpoint") from exc
    return run_command([
        binary("openssl"), "s_client", "-4", "-quic",
        "-connect", f"{normalized}:443", "-servername", host,
        "-alpn", "h3", "-verify_hostname", host,
        "-verify_return_error", "-brief", "-no-interactive",
    ], timeout=3, stdin_devnull=True)


def tcp_request(host: str, port: int) -> CommandResult:
    return run_command([binary("nc"), "-z", "-w", "2", host, str(port)], timeout=3)


def udp_response_request(host: str, port: int, payload_path: Path) -> CommandResult:
    if port < 1 or port > 65535:
        raise UsageError("invalid UDP port")
    if not payload_path.is_file() or payload_path.stat().st_size <= 0:
        raise UsageError("UDP payload is unavailable")
    return run_command(
        [binary("nc"), "-u", "-w", "2", host, str(port)],
        timeout=4,
        stdin_path=payload_path,
    )


def _status(result: CommandResult) -> int:
    if result.timed_out:
        return EX_TIMEOUT
    if result.returncode is None or result.returncode < 0:
        return 1
    return result.returncode


def _write_result(path: str, result: CommandResult) -> int:
    write_text(Path(path), combined_log(result))
    return _status(result)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        raise UsageError("request operation is required")
    op = args[0]
    if op == "dns":
        if len(args) != 4:
            raise UsageError("request dns requires HOST TYPE OUTPUT")
        result = run_command(
            [binary("drill"), args[1], args[2]], timeout=DNS_TIMEOUT_SECONDS
        )
        return _write_result(args[3], result)
    if op == "parse-dns":
        if len(args) != 3:
            raise UsageError("request parse-dns requires TYPE OUTPUT")
        try:
            raw = Path(args[2]).read_text(encoding="utf-8")
        except OSError as exc:
            raise RequestError(f"DNS output is unreadable: {args[2]}") from exc
        answers = parse_drill_answers(raw, args[1])
        if not answers:
            return 1
        print(answers[0])
        return EX_OK
    if op in {"tls13", "tls12", "http"}:
        if len(args) != 4:
            raise UsageError(f"request {op} requires FAMILY HOST OUTPUT")
        family, host, output = args[1], args[2], args[3]
        if op == "http":
            result = curl_request(host, scheme="http", family=family)
        else:
            result = curl_request(host, scheme="https", family=family, tls_version="1.3" if op == "tls13" else "1.2")
        return _write_result(output, result)
    if op in {"tls13-bound", "tls12-bound", "http-bound"}:
        if len(args) != 4:
            raise UsageError(f"request {op} requires HOST IP OUTPUT")
        host, address, output = args[1], args[2], args[3]
        if op == "http-bound":
            result = curl_request(host, scheme="http", bound_ip=address)
        else:
            result = curl_request(host, scheme="https", tls_version="1.3" if op == "tls13-bound" else "1.2", bound_ip=address)
        return _write_result(output, result)
    if op == "ipv6-route":
        if len(args) != 1:
            raise UsageError("request ipv6-route takes no arguments")
        available, _result = ipv6_default_route()
        return EX_OK if available else 1
    if op == "quic-ipv4":
        if len(args) != 2:
            raise UsageError("request quic-ipv4 requires OUTPUT")
        return _write_result(args[1], quic_ipv4_request())
    if op == "quic-bound":
        if len(args) != 4:
            raise UsageError("request quic-bound requires HOST IP OUTPUT")
        return _write_result(args[3], quic_target_request(args[1], args[2]))
    if op == "tcp":
        if len(args) != 4:
            raise UsageError("request tcp requires HOST PORT OUTPUT")
        try:
            port = int(args[2], 10)
        except ValueError as exc:
            raise UsageError("invalid TCP port") from exc
        if port < 1 or port > 65535:
            raise UsageError("invalid TCP port")
        return _write_result(args[3], tcp_request(args[1], port))
    if op == "udp":
        if len(args) != 5:
            raise UsageError("request udp requires HOST PORT PAYLOAD OUTPUT")
        try:
            port = int(args[2], 10)
        except ValueError as exc:
            raise UsageError("invalid UDP port") from exc
        result = udp_response_request(args[1], port, Path(args[3]))
        status = _write_result(args[4], result)
        if status == 0 and not result.stdout:
            return 1
        return status
    raise UsageError(f"unsupported Strategy Lab request operation: {op}")
