"""Offline tests only: no network, usbmux, pairing, or phone mutation."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/ghostpin/scripts"
sys.path.insert(0, str(SCRIPTS))
import coordinates
import fetch_ddi
import location


class CoordinateTests(unittest.TestCase):
    def test_recorded_landmark_conversion(self):
        lat, lon = coordinates.to_wgs84(31.300023, 121.505283, "gcj02")
        self.assertAlmostEqual(lat, 31.3020138, places=6)
        self.assertAlmostEqual(lon, 121.5008487, places=6)

    def test_wgs84_is_not_converted_twice(self):
        point = (31.3020138, 121.5008487)
        self.assertEqual(coordinates.to_wgs84(*point, "wgs84"), point)

    def test_reject_unknown_reversed_or_nonfinite(self):
        for point in [(121.5, 31.3), (float("nan"), 1), (1, float("inf"))]:
            with self.assertRaises(ValueError):
                coordinates.to_wgs84(*point, "wgs84")
        with self.assertRaises(ValueError):
            coordinates.to_wgs84(31, 121, "bd09")
        with self.assertRaises(ValueError):
            coordinates.to_wgs84(40, -74, "gcj02")


class DeviceTests(unittest.TestCase):
    def test_multiple_devices_requires_selection(self):
        with patch.object(location, "json_pmd", return_value=["a", "b"]):
            with self.assertRaises(location.WorkflowError):
                location.select_device(None)
            self.assertEqual(location.select_device("b"), "b")

    def test_missing_original_never_switches(self):
        with patch.object(location, "json_pmd", return_value=["replacement"]):
            with self.assertRaises(location.WorkflowError):
                location.select_device("original")

    def test_empty_and_single_device(self):
        with patch.object(location, "json_pmd", return_value=[]):
            with self.assertRaises(location.WorkflowError):
                location.select_device(None)
        with patch.object(location, "json_pmd", return_value=["one"]):
            self.assertEqual(location.select_device(None), "one")

    def test_locked_mount_not_reported_as_success(self):
        with patch.object(location, "ensure_ready"), patch.object(location, "mounted", return_value=False), \
             patch.object(location, "run_pmd", side_effect=location.WorkflowError("DeviceLocked")):
            with self.assertRaisesRegex(location.WorkflowError, "DeviceLocked"):
                location.prepare("one", None)

    def test_mount_exit_zero_still_requires_mount_evidence(self):
        with patch.object(location, "ensure_ready"), patch.object(location, "mounted", return_value=False), \
             patch.object(location, "run_pmd", return_value=""):
            with self.assertRaisesRegex(location.WorkflowError, "unconfirmed"):
                location.prepare("one", None)

    def test_already_mounted_skips_download(self):
        with patch.object(location, "ensure_ready"), patch.object(location, "mounted", return_value=True), \
             patch.object(location, "run_pmd") as run, contextlib.redirect_stdout(io.StringIO()):
            location.prepare("one", None)
            run.assert_not_called()

    def test_timeout_is_failure(self):
        with patch.object(location.subprocess, "run", side_effect=subprocess.TimeoutExpired("pmd", 90)):
            with self.assertRaises(location.WorkflowError):
                location.run_pmd(["doctor"])

    def test_logged_error_even_with_exit_zero(self):
        result = subprocess.CompletedProcess([], 0, "", "time logger ERROR mount failed")
        with patch.object(location.subprocess, "run", return_value=result):
            with self.assertRaises(location.WorkflowError):
                location.run_pmd(["mounter", "auto-mount"])

    def test_clear_does_not_require_developer_preflight(self):
        with patch.object(location, "run_pmd", return_value="") as run, \
             patch.object(location, "ensure_ready") as ready, contextlib.redirect_stdout(io.StringIO()):
            location.clear("original")
            ready.assert_not_called()
            self.assertEqual(run.call_args.args[0][-2:], ["--udid", "original"])
            self.assertIn("clear", run.call_args.args[0])


class SessionTests(unittest.TestCase):
    def simulate_with(self, child, clear_error=None):
        with tempfile.TemporaryDirectory() as tmp, patch.object(location, "SKILL", Path(tmp)), \
             patch.object(location.subprocess, "Popen", return_value=child) as popen, \
             patch.object(location, "clear", side_effect=clear_error) as clear, \
             contextlib.redirect_stdout(io.StringIO()):
            location.simulate("original", 31.3, 121.5)
            return popen, clear

    def test_interrupt_terminates_own_child_and_clears_same_device(self):
        child = Mock()
        child.wait.side_effect = [KeyboardInterrupt(), 0]
        child.poll.return_value = None
        popen, clear = self.simulate_with(child)
        child.terminate.assert_called_once()
        clear.assert_called_once_with("original")
        command = popen.call_args.args[0]
        self.assertEqual(command[-5:], ["--udid", "original", "--", "31.3", "121.5"])

    def test_set_failure_still_attempts_recovery(self):
        child = Mock()
        child.wait.return_value = 1
        child.poll.return_value = 1
        with self.assertRaisesRegex(location.WorkflowError, "exited 1"):
            self.simulate_with(child)

    def test_clear_failure_is_not_hidden(self):
        child = Mock()
        child.wait.return_value = 0
        child.poll.return_value = 0
        with self.assertRaisesRegex(location.WorkflowError, "restoration unconfirmed"):
            self.simulate_with(child, location.WorkflowError("device disconnected"))

    def test_live_device_lock_blocks_second_set(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(location, "SKILL", Path(tmp)):
            with location.device_lock("same"):
                with self.assertRaises(location.WorkflowError):
                    with location.device_lock("same"):
                        self.fail("second session acquired lock")
                with location.device_lock("different"):
                    pass
            with location.device_lock("same"):
                pass


class DownloadTests(unittest.TestCase):
    def test_blob_rejects_size_and_content_tampering(self):
        data = b"valid"
        sha = hashlib.sha1(b"blob 5\0valid").hexdigest()
        fetch_ddi.verify_blob(data, 5, sha)
        for changed, size in [(b"other", 5), (data, 6)]:
            with self.assertRaises(ValueError):
                fetch_ddi.verify_blob(changed, size, sha)

    def test_download_pins_commit_and_manifest_is_checked(self):
        commit = "a" * 40
        payloads = {name: (name + " content").encode() for name in fetch_ddi.FILES}
        entries = [{"name": name, "size": len(data),
                    "sha": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()}
                   for name, data in payloads.items()]
        by_sha = {entry["sha"]: payloads[entry["name"]] for entry in entries}
        def fake_request(path, raw=False):
            self.assertTrue(raw)
            return io.BytesIO(by_sha[path.rsplit("/", 1)[-1]])
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(fetch_ddi, "get_json", side_effect=[{"sha": commit}, entries]) as metadata, \
             patch.object(fetch_ddi, "request", side_effect=fake_request), \
             contextlib.redirect_stdout(io.StringIO()):
            out = Path(tmp)
            fetch_ddi.download(out, "main")
            self.assertIn("ref=" + commit, metadata.call_args_list[1].args[0])
            location.verify_ddi(out)
            manifest = json.loads((out / "download-manifest.json").read_text())
            self.assertEqual(manifest["commit"], commit)
            (out / "Image.dmg").write_bytes(b"tampered")
            with self.assertRaises(location.WorkflowError):
                location.verify_ddi(out)

    def test_missing_completion_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(location.WorkflowError):
                location.verify_ddi(Path(tmp))


if __name__ == "__main__":
    unittest.main()
