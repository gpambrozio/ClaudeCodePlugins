"""Tests for the simulator-slimming catalog and its platform handling.

These cover the parts that decide *what gets disabled on which device* and that
no simulator is needed to exercise: runtime parsing, the persistence gate, and
the merge that layers a platform's own daemons onto the upstream iOS data. A
wrong answer here is expensive and quiet - a watch runtime read as iOS would
slim it against the wrong catalog, and a platform block naming a category that
no longer exists would silently stop disabling those daemons.
"""

import importlib.util
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "iOSSimulator" / "skills" / "simulator-slimming" / "scripts"


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


catalog = load_module("slim_catalog")
launchd = load_module("slim_launchd")


class PlatformParsingTests(unittest.TestCase):
    def test_reads_platform_and_version_from_runtime_identifier(self):
        cases = {
            "com.apple.CoreSimulator.SimRuntime.iOS-26-5": ("ios", "26.5"),
            "com.apple.CoreSimulator.SimRuntime.iOS-27-0": ("ios", "27.0"),
            "com.apple.CoreSimulator.SimRuntime.watchOS-27-0": ("watchos", "27.0"),
            "com.apple.CoreSimulator.SimRuntime.watchOS-11-5": ("watchos", "11.5"),
        }
        for runtime, expected in cases.items():
            with self.subTest(runtime=runtime):
                self.assertEqual(launchd._platform_and_version(runtime), expected)

    def test_skips_platforms_with_no_measured_catalog(self):
        # "tvOS-" and "visionOS-" both end in "OS-", so a sloppier match would
        # read them as iOS and slim them against a catalog nobody has tested
        # there. They must come back unknown instead.
        for runtime in ("com.apple.CoreSimulator.SimRuntime.tvOS-27-0",
                        "com.apple.CoreSimulator.SimRuntime.visionOS-26-0",
                        "com.apple.CoreSimulator.SimRuntime.xrOS-26-0"):
            with self.subTest(runtime=runtime):
                self.assertEqual(launchd._platform_and_version(runtime), (None, "?"))

    def test_os_label_names_the_runtime_the_way_a_person_would(self):
        self.assertEqual(
            launchd.os_label({"platform": "watchos", "os_version": "27.0"}), "watchOS 27.0")
        self.assertEqual(
            launchd.os_label({"platform": "ios", "os_version": "26.5"}), "iOS 26.5")


class PersistenceGateTests(unittest.TestCase):
    def test_ios_gate_is_unchanged(self):
        self.assertFalse(launchd.supports_persistent_overrides("17.5", "ios"))
        self.assertFalse(launchd.supports_persistent_overrides("18.3", "ios"))
        self.assertTrue(launchd.supports_persistent_overrides("18.5", "ios"))
        self.assertTrue(launchd.supports_persistent_overrides("27.0", "ios"))

    def test_ios_is_the_default_platform(self):
        self.assertTrue(launchd.supports_persistent_overrides("18.5"))

    def test_watchos_gate_matches_what_was_measured(self):
        self.assertFalse(launchd.supports_persistent_overrides("11.5", "watchos"))
        self.assertFalse(launchd.supports_persistent_overrides("26.0", "watchos"))
        self.assertTrue(launchd.supports_persistent_overrides("27.0", "watchos"))
        self.assertTrue(launchd.supports_persistent_overrides("27.2", "watchos"))

    def test_unknown_platform_and_unparsable_version_are_not_persistent(self):
        self.assertFalse(launchd.supports_persistent_overrides("27.0", "tvos"))
        self.assertFalse(launchd.supports_persistent_overrides("27", "ios"))
        self.assertFalse(launchd.supports_persistent_overrides("beta", "ios"))


class CatalogPlatformViewTests(unittest.TestCase):
    def setUp(self):
        catalog.select_platform(catalog.DEFAULT_PLATFORM)

    def tearDown(self):
        catalog.select_platform(catalog.DEFAULT_PLATFORM)

    def test_ios_is_the_upstream_catalog_untouched(self):
        raw = catalog.load_catalog()
        self.assertEqual(catalog.categories(), raw["categories"])
        self.assertEqual(catalog.features(), raw["features"])

    def test_watchos_extends_rather_than_replaces_the_shared_categories(self):
        ios_labels = catalog.slimmable_labels()
        catalog.select_platform("watchos")
        watch_labels = catalog.slimmable_labels()
        self.assertTrue(ios_labels < watch_labels,
                        "a watch must disable everything a phone does, plus its own")
        # A profile written against a phone has to keep validating against a
        # watch, which is what lets one committed profile slim both halves of a
        # paired pair.
        self.assertIn("com.apple.MapKit.SnapshotService", watch_labels)

    def test_watch_daemons_land_in_the_category_that_already_means_that(self):
        catalog.select_platform("watchos")
        by_id = {category["id"]: category["labels"] for category in catalog.categories()}
        self.assertIn("com.apple.nanoweatherd", by_id["apps"])
        self.assertIn("com.apple.nanopassd", by_id["store"])
        self.assertIn("com.apple.nanobackupd", by_id["icloud"])
        self.assertIn("com.apple.sleepd", by_id["health"])

    def test_the_daemons_watchos_re_enables_at_boot_are_not_slimmable(self):
        # Measured on watchOS 27.0: these three accept `launchctl disable` and
        # stop, and the next boot writes them back to enabled - the watch
        # re-enables the daemons mirroring its phone apps. Verified twice, once
        # inside a full slim and once with only these three disabled, so it is
        # the daemons and not a race. Cataloguing them fails every run at the
        # post-reboot check, which is why they are features-only.
        catalog.select_platform("watchos")
        slimmable = catalog.slimmable_labels()
        for label in ("com.apple.nanomaild", "com.apple.nanomessagesd",
                      "com.apple.nanophotosd"):
            with self.subTest(label=label):
                self.assertNotIn(label, slimmable)
                self.assertTrue(catalog.describe_service(label),
                                "still described, so --find and the doctor know it")

    def test_every_platform_block_names_categories_and_features_that_exist(self):
        for platform in catalog.known_platforms():
            with self.subTest(platform=platform):
                catalog.select_platform(platform)
                catalog.categories()  # raises ProfileError on an unknown ID

    def test_every_slimmable_label_has_a_description(self):
        for platform in catalog.known_platforms():
            with self.subTest(platform=platform):
                catalog.select_platform(platform)
                undescribed = sorted(
                    label for label in catalog.slimmable_labels()
                    if not catalog.describe_service(label))
                self.assertEqual(undescribed, [])

    def test_always_enabled_labels_are_never_also_slimmable(self):
        # They are the daemons a platform cannot lose - the watch's pairing
        # registry, its home screen - so a catalog edit that made one
        # disableable would strand the simulator.
        for platform in catalog.known_platforms():
            with self.subTest(platform=platform):
                catalog.select_platform(platform)
                overlap = catalog.always_enabled_labels() & catalog.slimmable_labels()
                self.assertEqual(overlap, set())

    def test_watch_pairing_and_home_screen_are_protected(self):
        catalog.select_platform("watchos")
        protected = catalog.always_enabled_labels()
        for label in ("com.apple.Carousel", "com.apple.nanoregistryd",
                      "com.apple.nanoregistrylaunchd", "com.apple.nanotimekitd"):
            with self.subTest(label=label):
                self.assertIn(label, protected)

    def test_managed_is_slimmable_plus_always_enabled(self):
        catalog.select_platform("watchos")
        self.assertEqual(
            catalog.managed_labels(),
            catalog.slimmable_labels() | catalog.always_enabled_labels())

    def test_unknown_platform_is_rejected(self):
        with self.assertRaises(catalog.ProfileError):
            catalog.select_platform("tvos")


class ProfileTests(unittest.TestCase):
    def setUp(self):
        catalog.select_platform(catalog.DEFAULT_PLATFORM)

    def tearDown(self):
        catalog.select_platform(catalog.DEFAULT_PLATFORM)

    def test_excepting_a_category_keeps_its_watch_daemons_too(self):
        catalog.select_platform("watchos")
        profile = catalog.build_profile(["health"], [])
        self.assertNotIn("com.apple.sleepd", profile["desired"])
        self.assertNotIn("com.apple.healthd", profile["desired"])

    def test_a_watch_profile_disables_more_than_the_same_profile_on_a_phone(self):
        catalog.select_platform(catalog.DEFAULT_PLATFORM)
        on_phone = catalog.build_profile([], [])["desired"]
        catalog.select_platform("watchos")
        on_watch = catalog.build_profile([], [])["desired"]
        self.assertTrue(on_phone < on_watch)


if __name__ == "__main__":
    unittest.main()
