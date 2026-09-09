#!/usr/bin/env python3
"""ipconfig - Windows-style network configuration display for Linux.

Mimics the output of the Windows ``ipconfig`` command using data from
iproute2 (``ip -j``) and the system resolver configuration. Read-only:
it inspects and prints network state, it never modifies it.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import shutil
import socket
import subprocess
import sys
from typing import Any

# Version scheme requested by the user:
#   MAJOR.MEDIUM.MINOR
#     MAJOR  -> large / breaking changes
#     MEDIUM -> medium-sized feature changes
#     MINOR  -> small changes and fixes
__version__ = "1.0.0"

# Field label width used to align the dotted leaders like Windows does.
_LABEL_WIDTH = 38

# Map of Windows-style switches to their POSIX long-option equivalents so
# that both ``ipconfig /all`` and ``ipconfig --all`` behave identically.
_WINDOWS_SWITCHES = {
    "/all": "--all",
    "/?": "--help",
    "/help": "--help",
    "/version": "--version",
}


class IpconfigError(Exception):
    """Raised for unrecoverable runtime errors (reported to stderr)."""


def normalize_args(argv: list[str]) -> list[str]:
    """Translate Windows-style ``/switch`` arguments to POSIX long options."""
    return [_WINDOWS_SWITCHES.get(arg.lower(), arg) for arg in argv]


def run_ip_json(args: list[str]) -> Any:
    """Run ``ip -j <args>`` and return the parsed JSON payload.

    Raises IpconfigError if the ``ip`` binary is missing, the command
    fails, or the output is not valid JSON.
    """
    ip_path = shutil.which("ip")
    if ip_path is None:
        raise IpconfigError(
            "the 'ip' command (iproute2) was not found in PATH; "
            "install iproute2 to use this tool"
        )

    cmd = [ip_path, "-j", *args]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired as exc:
        raise IpconfigError(f"'{' '.join(cmd)}' timed out") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else "unknown error"
        raise IpconfigError(f"'{' '.join(cmd)}' failed: {stderr}") from exc

    output = result.stdout.strip()
    if not output:
        return []
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise IpconfigError(
            f"could not parse JSON from '{' '.join(cmd)}': {exc}"
        ) from exc


def prefix_to_netmask(prefixlen: int) -> str:
    """Convert an IPv4 prefix length (0-32) to a dotted-decimal netmask."""
    network = ipaddress.IPv4Network(f"0.0.0.0/{prefixlen}")
    return str(network.netmask)


def get_hostname() -> str:
    """Return the local host name (short form, like Windows)."""
    return socket.gethostname().split(".")[0]


def get_dns_config() -> tuple[list[str], str]:
    """Parse /etc/resolv.conf.

    Returns a tuple of (nameservers, primary search/domain suffix).
    Missing or unreadable files yield empty defaults rather than errors.
    """
    nameservers: list[str] = []
    search_suffix = ""
    try:
        with open("/etc/resolv.conf", encoding="utf-8", errors="replace") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or line.startswith(";"):
                    continue
                parts = line.split()
                if len(parts) < 2:
                    continue
                keyword, value = parts[0].lower(), parts[1]
                if keyword == "nameserver":
                    nameservers.append(value)
                elif keyword in ("search", "domain") and not search_suffix:
                    search_suffix = value
    except FileNotFoundError:
        pass
    except OSError as exc:
        print(f"warning: could not read /etc/resolv.conf: {exc}", file=sys.stderr)
    return nameservers, search_suffix


def get_default_gateways() -> dict[str, list[str]]:
    """Return a mapping of interface name -> list of default gateway IPs."""
    gateways: dict[str, list[str]] = {}
    for family in ("-4", "-6"):
        routes = run_ip_json([family, "route", "show", "default"])
        for route in routes:
            dev = route.get("dev")
            gateway = route.get("gateway")
            if dev and gateway:
                gateways.setdefault(dev, []).append(gateway)
    return gateways


def emit_field(label: str, value: str) -> None:
    """Print a single aligned ``Label . . . . : value`` line."""
    # Windows pads the label with " ." leaders up to a fixed column and
    # always keeps a single space directly before the colon.
    dotted = label + " "
    while len(dotted) < _LABEL_WIDTH:
        dotted += ". "
    dotted = dotted[:_LABEL_WIDTH]
    if dotted[-1] != " ":
        dotted = dotted[:-1] + " "
    print(f"   {dotted}: {value}")


def classify_adapter(iface: dict[str, Any]) -> str:
    """Return a human-friendly adapter type prefix based on link type/name."""
    name = iface.get("ifname", "")
    link_type = iface.get("link_type", "")
    if link_type == "loopback":
        return "Loopback adapter"
    if name.startswith(("wl", "wlan", "wlp")):
        return "Wireless LAN adapter"
    if name.startswith(("en", "eth", "eno", "enp", "ens")):
        return "Ethernet adapter"
    if name.startswith(("tun", "tap", "wg", "ppp")):
        return "Tunnel adapter"
    if name.startswith(("docker", "br", "virbr", "veth")):
        return "Virtual adapter"
    return "Adapter"


def print_general_header(hostname: str, primary_suffix: str) -> None:
    """Print the top-level host information block."""
    print()
    print("Linux IP Configuration")
    print()
    emit_field("Host Name", hostname)
    emit_field("Primary Dns Suffix", primary_suffix)
    print()


def print_adapter(
    iface: dict[str, Any],
    gateways: dict[str, list[str]],
    nameservers: list[str],
    search_suffix: str,
    show_all: bool,
) -> None:
    """Print one adapter block in Windows ipconfig style."""
    name = iface.get("ifname", "?")
    prefix = classify_adapter(iface)
    print(f"{prefix} {name}:")
    print()

    is_up = "UP" in iface.get("flags", []) and iface.get("operstate") != "DOWN"
    addr_info = iface.get("addr_info", [])
    has_global = any(
        a.get("scope") == "global" for a in addr_info
    )

    # Media-disconnected adapters mirror the Windows short block.
    if not has_global and iface.get("link_type") != "loopback":
        emit_field("Media State", "Media disconnected" if not is_up else "connected")
        emit_field("Connection-specific DNS Suffix", search_suffix)
        if show_all:
            emit_field("Description", name)
            mac = iface.get("address", "")
            if mac:
                emit_field("Physical Address", mac.upper().replace(":", "-"))
        print()
        return

    emit_field("Connection-specific DNS Suffix", search_suffix)

    if show_all:
        emit_field("Description", name)
        mac = iface.get("address", "")
        if mac and iface.get("link_type") != "loopback":
            emit_field("Physical Address", mac.upper().replace(":", "-"))
        dhcp_enabled = any(a.get("dynamic") for a in addr_info)
        emit_field("DHCP Enabled", "Yes" if dhcp_enabled else "No")

    # IPv4 addresses first (Windows convention), then IPv6.
    for addr in sorted(addr_info, key=lambda a: a.get("family") != "inet"):
        family = addr.get("family")
        local = addr.get("local")
        prefixlen = addr.get("prefixlen")
        if not local or prefixlen is None:
            continue
        if family == "inet":
            emit_field("IPv4 Address", f"{local}(Preferred)")
            emit_field("Subnet Mask", prefix_to_netmask(prefixlen))
        elif family == "inet6":
            scope = addr.get("scope", "")
            if scope == "link":
                label = "Link-local IPv6 Address"
                value = f"{local}%{name}(Preferred)"
            else:
                label = "IPv6 Address"
                value = f"{local}(Preferred)"
            emit_field(label, value)

    for gateway in gateways.get(name, []):
        emit_field("Default Gateway", gateway)

    if show_all and nameservers:
        emit_field("DNS Servers", nameservers[0])
        for extra in nameservers[1:]:
            # Continuation lines align under the first DNS server value.
            print(f"   {' ' * _LABEL_WIDTH}: {extra}")

    print()


def build_report(show_all: bool) -> None:
    """Gather all network state and print the full ipconfig report."""
    interfaces = run_ip_json(["addr", "show"])
    gateways = get_default_gateways()
    nameservers, search_suffix = get_dns_config()
    hostname = get_hostname()

    print_general_header(hostname, search_suffix)

    for iface in interfaces:
        print_adapter(iface, gateways, nameservers, search_suffix, show_all)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ipconfig",
        description="Display network configuration (Windows ipconfig style) on Linux.",
        epilog="Windows-style switches are also accepted: /all, /version, /?",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="show the full configuration (MAC, DHCP status, DNS servers)",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"ipconfig {__version__}",
        help="show the program version and exit",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    args = parser.parse_args(normalize_args(raw))

    try:
        build_report(show_all=args.all)
    except IpconfigError as exc:
        print(f"ipconfig: error: {exc}", file=sys.stderr)
        return 1
    except BrokenPipeError:
        # Consumer closed the pipe (e.g. `ipconfig | head`); exit quietly.
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
