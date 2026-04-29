# firmware_update_manager.py
# Infineon Technologies - Embedded Systems Group
# Manages firmware version tracking and update eligibility for AURIX microcontrollers
# (Used in automotive ECU production lines - ADAS & powertrain applications)
# Author: aurix-team | Created: 2011 | Python 2.7
# Migrated to Python 3 — see inline comments marked [Py3 migration]

import sys
import hashlib
import functools
# [Py3 migration] urllib2 → urllib.request/urllib.error; httplib → http.client;
# cPickle removed (Py3 pickle auto-uses C implementation);
# ConfigParser import removed (was unused in original)
import urllib.request
import urllib.error
import http.client
import pickle

FIRMWARE_REGISTRY_URL = "http://internal-fw-registry.infineon.corp/api/versions"
SUPPORTED_FAMILIES = ['TC2xx', 'TC3xx', 'XMC4000', 'XMC1000']
CACHE_FILE = "/tmp/fw_registry_cache.pkl"


# [Py3 migration] Added @functools.total_ordering to derive full set of comparison
# operators from __eq__ and __lt__, replacing the removed __cmp__/cmp() pattern.
@functools.total_ordering
class FirmwareVersion:
    """Represents a specific firmware build for an Infineon MCU family."""

    def __init__(self, family, version_str, checksum):
        self.family = family
        self.version_str = version_str
        self.checksum = checksum
        self.major, self.minor, self.patch = self._parse_version(version_str)

    def _parse_version(self, v):
        parts = v.split('.')
        if len(parts) != 3:
            # [Py3 migration] raise Type, "msg" → raise Type("msg")
            raise ValueError("Invalid version format: %s" % v)
        return int(parts[0]), int(parts[1]), int(parts[2])

    # [Py3 migration] Replaced __cmp__/cmp() with __eq__ and __lt__ rich comparisons.
    # Combined with @functools.total_ordering, this preserves the original sort behaviour.
    def __eq__(self, other):
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    def __lt__(self, other):
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def is_newer_than(self, other):
        return self > other

    def __repr__(self):
        return "FirmwareVersion(%s, %s)" % (self.family, self.version_str)


class FirmwareRegistry:
    """Fetches and caches the available firmware versions from internal registry."""

    def __init__(self):
        self.versions = {}  # family -> list of FirmwareVersion

    def fetch_from_network(self):
        """Pull firmware manifest from internal registry server."""
        try:
            # [Py3 migration] urllib2.urlopen → urllib.request.urlopen
            response = urllib.request.urlopen(FIRMWARE_REGISTRY_URL, timeout=10)
            raw = response.read()
            # [Py3 migration] urlopen returns bytes in Py3; decode to str for text parsing
            self._parse_manifest(raw.decode('utf-8'))
            self._save_cache()
            print("Registry updated from network.")
        # [Py3 migration] except Type, e → except Type as e; urllib2 → urllib.error
        except urllib.error.URLError as e:
            print("Network error fetching registry: %s" % e)
            print("Falling back to cache...")
            self._load_cache()
        # [Py3 migration] httplib → http.client
        except http.client.HTTPException as e:
            print("HTTP error: %s" % e)
            self._load_cache()

    def _parse_manifest(self, raw_text):
        for line in raw_text.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('|')
            if len(parts) != 3:
                continue
            family, version, checksum = parts
            if family not in SUPPORTED_FAMILIES:
                print("Unknown family in manifest: %s" % family)
                continue
            fw = FirmwareVersion(family.strip(), version.strip(), checksum.strip())
            if family not in self.versions:
                self.versions[family] = []
            self.versions[family].append(fw)

    def _save_cache(self):
        # [Py3 migration] Added context manager for safe file handling
        with open(CACHE_FILE, 'wb') as f:
            pickle.dump(self.versions, f)

    def _load_cache(self):
        try:
            # [Py3 migration] Added context manager for safe file handling
            with open(CACHE_FILE, 'rb') as f:
                self.versions = pickle.load(f)
            print("Loaded registry from cache.")
        except IOError:
            print("No cache available. Registry is empty.")

    def get_latest(self, family):
        if family not in self.versions or not self.versions[family]:
            return None
        return sorted(self.versions[family])[-1]


def check_device_update_eligibility(device_family, installed_version_str):
    """Check whether a device needs a firmware update."""
    if device_family not in SUPPORTED_FAMILIES:
        print("Unsupported device family: %s" % device_family)
        return False

    registry = FirmwareRegistry()
    registry.fetch_from_network()

    latest = registry.get_latest(device_family)
    if latest is None:
        print("No firmware versions available for %s" % device_family)
        return False

    try:
        installed = FirmwareVersion(device_family, installed_version_str, "")
    # [Py3 migration] except Type, e → except Type as e
    except ValueError as e:
        print("Bad installed version string: %s" % e)
        return False

    if latest.is_newer_than(installed):
        print("Update available for %s: %s -> %s" % (
            device_family, installed_version_str, latest.version_str))
        return True
    else:
        print("Device %s is up to date (%s)" % (device_family, installed_version_str))
        return False


def verify_firmware_checksum(filepath, expected_checksum):
    """Verify a downloaded firmware binary against expected MD5 checksum."""
    h = hashlib.md5()
    try:
        # [Py3 migration] Added context manager for safe file handling
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)
    # [Py3 migration] except Type, e → except Type as e
    except IOError as e:
        print("Cannot open firmware file: %s" % e)
        return False
    actual = h.hexdigest()
    if actual != expected_checksum:
        print("CHECKSUM MISMATCH: expected %s, got %s" % (expected_checksum, actual))
        return False
    print("Checksum verified OK.")
    return True


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python firmware_update_manager.py <device_family> <installed_version>")
        sys.exit(1)
    check_device_update_eligibility(sys.argv[1], sys.argv[2])
