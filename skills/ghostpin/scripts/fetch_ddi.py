"""Fetch upstream DDI via GitHub API at a resolved commit; verify each Git blob."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.request

REPOSITORY = "doronz88/DeveloperDiskImage"
API = "https://api.github.com/repos/" + REPOSITORY
FILES = ("Image.dmg", "Image.dmg.trustcache", "BuildManifest.plist")
ROOT = "PersonalizedImages/Xcode_iOS_DDI_Personalized"
MAX_BYTES = 100 * 1024 * 1024


def request(path, raw=False):
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github.raw+json" if raw else "application/vnd.github+json",
        "User-Agent": "ghostpin",
    })
    return urllib.request.urlopen(req, timeout=60)


def get_json(path):
    with request(path) as response:
        return json.load(response)


def verify_blob(data, expected_size, expected_sha):
    actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if len(data) != expected_size or actual != expected_sha:
        raise ValueError("Git blob size/hash mismatch; refusing file")


def download(out, ref):
    # Resolve once so a moving branch cannot mix files from different revisions.
    if not re.fullmatch(r"[A-Za-z0-9._-]+", ref):
        raise ValueError("ref must be a simple branch name, tag, or commit SHA")
    commit = get_json("/commits/" + ref)["sha"]
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("Invalid upstream commit")
    entries = get_json(f"/contents/{ROOT}?ref={commit}")
    by_name = {item["name"]: item for item in entries}
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"repository": REPOSITORY, "commit": commit, "files": {}}
    for name in FILES:
        item = by_name[name]
        size, sha = item["size"], item["sha"]
        if not isinstance(size, int) or not (0 < size <= MAX_BYTES) or not re.fullmatch(r"[a-f0-9]{40}", sha):
            raise ValueError("Invalid upstream blob metadata")
        print(f"Downloading {name} ({size:,} bytes)", flush=True)
        with request("/git/blobs/" + sha, raw=True) as response:
            data = response.read(size + 1)
        verify_blob(data, size, sha)
        with tempfile.NamedTemporaryFile(dir=out, delete=False) as f:
            temp = Path(f.name)
            f.write(data)
        os.replace(temp, out / name)
        manifest["files"][name] = {"size": size, "git_blob_sha1": sha,
                                    "sha256": hashlib.sha256(data).hexdigest()}
        print(f"Verified {name}", flush=True)
    (out / "download-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Complete: {out}. Git blob checks verify consistency, not Apple signatures.")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--ref", default="main", help="Resolve to one commit before downloading; optionally supply a recorded commit")
    args = p.parse_args()
    try:
        download(args.out.resolve(), args.ref)
    except Exception as e:
        p.exit(1, f"下载Not completed: {e}\nDo not mount an incomplete directory; resolve networking before retrying.\n")


if __name__ == "__main__":
    main()
