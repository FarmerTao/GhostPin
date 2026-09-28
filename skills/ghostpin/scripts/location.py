"""macOS USB iPhone location workflow. Run with the skill's virtualenv Python."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.metadata
import json
from pathlib import Path
import signal
import subprocess
import sys

from coordinates import to_wgs84

SKILL = Path(__file__).resolve().parent.parent
VERSION = "11.19.4"


class WorkflowError(RuntimeError):
    pass


def run_pmd(args, timeout=90):
    try:
        result = subprocess.run([sys.executable, "-m", "pymobiledevice3", *args],
                                capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise WorkflowError("Command timed out and was stopped. Check unlock, trust, or networking before retrying.") from e
    if result.returncode or " ERROR " in result.stderr:
        raise WorkflowError((result.stderr or result.stdout or "Upstream command failed").strip())
    return result.stdout.strip()


def json_pmd(args):
    try:
        return json.loads(run_pmd(args))
    except json.JSONDecodeError as e:
        raise WorkflowError("Upstream returned non-JSON data; check the CLI version and output, do not infer state.") from e


def select_device(requested):
    devices = json_pmd(["usbmux", "list", "--usb", "--simple"])
    if not isinstance(devices, list) or any(not isinstance(d, str) for d in devices):
        raise WorkflowError("Unsupported device-list format")
    devices = list(dict.fromkeys(devices))
    if requested:
        if requested not in devices:
            raise WorkflowError("Selected device is absent from USB. Reconnect the original phone; no automatic switch.")
        return requested
    if len(devices) != 1:
        raise WorkflowError("Exactly one USB device is required, or run devices and select explicitly with --udid.")
    return devices[0]


def target(args, udid):
    return [*args, "--udid", udid]


def device_version(udid):
    version = json_pmd(target(["lockdown", "get", "--key", "ProductVersion"], udid))
    try:
        major = int(version.split(".")[0])
    except (AttributeError, ValueError) as e:
        raise WorkflowError("Unrecognized device version") from e
    if not 17 <= major <= 26:
        raise WorkflowError(f"This helper implements iOS 17-26, detected {version}; consult upstream before adapting.")
    return version


def developer_mode(udid):
    value = json_pmd(target(["amfi", "developer-mode-status"], udid))
    if not isinstance(value, bool):
        raise WorkflowError("Unrecognized Developer Mode state")
    return value


def ensure_ready(udid):
    device_version(udid)
    if not developer_mode(udid):
        raise WorkflowError("Developer Mode is off. Use reveal if needed; the user enables, restarts, and confirms on the phone.")


def mounted(udid):
    images = json_pmd(target(["mounter", "list"], udid))
    if not isinstance(images, list):
        raise WorkflowError("Unrecognized mount state")
    return any(item.get("DiskImageType") == "Personalized" for item in images)


def verify_ddi(directory):
    try:
        manifest = json.loads((directory / "download-manifest.json").read_text())
        names = ("Image.dmg", "Image.dmg.trustcache", "BuildManifest.plist")
        for name in names:
            data = (directory / name).read_bytes()
            record = manifest["files"][name]
            if len(data) != record["size"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
                raise WorkflowError(f"Support-file verification failed: {name}")
    except (OSError, KeyError, ValueError, TypeError) as e:
        raise WorkflowError("Incomplete support files; download and verify again with fetch_ddi.py.") from e


def prepare(udid, directory):
    ensure_ready(udid)
    if mounted(udid):
        print("Developer support image is already mounted.")
        return
    if directory:
        directory = directory.resolve()
        verify_ddi(directory)
        command = ["mounter", "mount-personalized", str(directory / "Image.dmg"),
                   str(directory / "Image.dmg.trustcache"), str(directory / "BuildManifest.plist")]
    else:
        command = ["mounter", "auto-mount"]
    run_pmd(target(command, udid), timeout=180)
    if not mounted(udid):
        raise WorkflowError("Command returned but Personalized mount is unconfirmed. Stopping without setting location.")
    print("Developer support mount confirmed.")


def clear(udid):
    run_pmd(target(["developer", "dvt", "simulate-location", "clear"], udid))
    print("Clear command succeeded; confirm current location in Maps on the phone.", flush=True)


@contextmanager
def device_lock(udid):
    directory = SKILL / ".state"
    directory.mkdir(exist_ok=True)
    # No raw UDID or location history in local lock filenames.
    path = directory / (hashlib.sha256(udid.encode()).hexdigest()[:24] + ".lock")
    with path.open("a") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as e:
            raise WorkflowError("This device already has a skill session; stop it before starting another.") from e
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def simulate(udid, lat, lon):
    command = target(["developer", "dvt", "simulate-location", "set"], udid)
    command += ["--", str(lat), str(lon)]
    # Keep the upstream session alive. A subprocess handle, rather than a saved PID,
    # prevents signaling an unrelated process after PID reuse.
    with device_lock(udid):
        child = None
        old_handler = signal.getsignal(signal.SIGTERM)

        def terminate(_signum, _frame):
            raise KeyboardInterrupt

        signal.signal(signal.SIGTERM, terminate)
        failure = None
        try:
            print(f"Requesting WGS84 latitude {lat:.7f}, longitude {lon:.7f}.", flush=True)
            print("Keep this session running. Upstream waiting does not verify app acceptance; check Maps. Ctrl+C stops and attempts restoration.", flush=True)
            child = subprocess.Popen([sys.executable, "-m", "pymobiledevice3", *command],
                                     start_new_session=True)
            code = child.wait()
            if code:
                failure = WorkflowError(f"Set command exited {code}; setting location is not confirmed.")
        except KeyboardInterrupt:
            print("\nStopping location session and restoring...", flush=True)
        finally:
            # Avoid interruption halfway through cleanup; restore the caller's handlers.
            old_int = signal.signal(signal.SIGINT, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            try:
                if child is not None:
                    if child.poll() is None:
                        child.terminate()
                        try:
                            child.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            child.kill()
                            child.wait()
                    try:
                        clear(udid)
                    except WorkflowError as e:
                        failure = WorkflowError(f"Automatic restoration unconfirmed: {e}\nReconnect and unlock the original phone, then run clear. Unplugging is not proof of restoration.")
            finally:
                signal.signal(signal.SIGINT, old_int)
                signal.signal(signal.SIGTERM, old_handler)
        if failure:
            raise failure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("devices", help="List USB device IDs (do not commit IDs)")
    for name in ("doctor", "reveal", "prepare", "set", "clear"):
        p = sub.add_parser(name)
        p.add_argument("--udid", help="Required with multiple phones; reuse the same ID throughout")
        if name == "prepare":
            p.add_argument("--ddi-dir", type=Path, help="fetch_ddi.py output directory; omit for upstream automatic download")
        if name == "set":
            p.add_argument("--lat", type=float, required=True)
            p.add_argument("--lon", type=float, required=True)
            p.add_argument("--source", choices=["wgs84", "gcj02"], required=True)
    args = parser.parse_args()
    try:
        if sys.platform != "darwin":
            raise WorkflowError("This wrapper supports macOS only; Windows/Linux need separate upstream setup and validation.")
        if importlib.metadata.version("pymobiledevice3") != VERSION:
            raise WorkflowError(f"Use the pymobiledevice3 {VERSION} environment installed by bootstrap.sh.")
        coords = to_wgs84(args.lat, args.lon, args.source) if args.command == "set" else None
        if args.command == "devices":
            print(run_pmd(["usbmux", "list", "--usb", "--simple"]))
            return
        udid = select_device(args.udid)
        if args.command == "doctor":
            print(json.dumps({"ios_version": device_version(udid), "developer_mode": developer_mode(udid)}, indent=2))
        elif args.command == "reveal":
            run_pmd(target(["amfi", "reveal-developer-mode"], udid))
            print("Reveal request sent. Reopen Settings > Privacy & Security; enable, restart, and confirm on the phone.")
        elif args.command == "prepare":
            prepare(udid, args.ddi_dir)
        elif args.command == "set":
            ensure_ready(udid)
            if not mounted(udid):
                raise WorkflowError("Run prepare first and confirm the support image is mounted.")
            simulate(udid, *coords)
        elif args.command == "clear":
            # Restoration should still be attempted without preflight/version gates.
            clear(udid)
    except (WorkflowError, ValueError, OSError, importlib.metadata.PackageNotFoundError) as e:
        parser.exit(1, f"Not completed: {e}\n")


if __name__ == "__main__":
    main()
