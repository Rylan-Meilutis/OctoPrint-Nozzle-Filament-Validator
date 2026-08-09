import logging
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path

# Load the pure validation module without executing the OctoPrint-dependent
# package initializer. OctoPrint itself is intentionally not a test dependency.
package_root = Path(__file__).resolve().parents[1] / "octoprint_nfv"
package = types.ModuleType("octoprint_nfv")
package.__path__ = [str(package_root)]
sys.modules.setdefault("octoprint_nfv", package)

from octoprint_nfv.validate import parse_gcode, validator


VALID_GCODE = """; nozzle_diameter = 0.4
; filament_type = PLA
; filament used [mm] = 100.0
; printer_model = Test Printer
G28
"""


class _BuildPlate:
    def is_filament_compatible_with_build_plate(self, filament_type):
        return filament_type == "PLA"


class _Extruders:
    def get_number_of_extruders(self):
        return 1

    def get_nozzle_size_for_extruder(self, position):
        return 0.4


class _RemappedExtruders:
    def get_number_of_extruders(self):
        return 2

    def get_nozzle_size_for_extruder(self, position):
        return {1: 0.6, 2: 0.4}[position]


class _SpoolManager:
    def get_loaded_filaments(self):
        return -1


class _Filament:
    def get_enable_spool_checking(self):
        return False

    def get_enable_filament_type_checking(self):
        return True

    def get_timeout(self):
        return 0


class _InteractiveFilament(_Filament):
    def get_timeout(self):
        return 1


class _TypesDisabledFilament(_Filament):
    def get_enable_filament_type_checking(self):
        return False


class _WrongTypeSpoolManager:
    def get_loaded_filaments(self):
        return ["ABS"]


class _ManualFilamentProvider:
    def __init__(self, material):
        self.material = material

    def is_available(self):
        return False

    def get_loaded_filaments(self):
        return [self.material]

    def get_names(self):
        return []


class _SpoolmanProvider(_ManualFilamentProvider):
    def is_available(self):
        return True

    def get_names(self):
        return ["spoolman:42"]


class _RmeProvider(_ManualFilamentProvider):
    def is_available(self):
        return True

    def get_names(self):
        return ["rme:internal:4"]


class _NameCheckingFilament(_Filament):
    def get_enable_spool_checking(self):
        return True


class _Printer:
    def __init__(self):
        self.cancelled = False
        self.paused = False

    def cancel_print(self):
        self.cancelled = True

    def pause_print(self):
        self.paused = True


class _PluginManager:
    def __init__(self):
        self.messages = []

    def send_plugin_message(self, identifier, message):
        self.messages.append((identifier, message))


class _Profiles:
    def get_current_or_default(self):
        return {"model": "Test Printer"}


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.printer = _Printer()
        self.plugin_manager = _PluginManager()
        self.validator = validator(
            nozzle=None,
            build_plate=_BuildPlate(),
            extruders=_Extruders(),
            spool_manager=_SpoolManager(),
            filament=_Filament(),
            printer=self.printer,
            logger=logging.getLogger("nfv-tests"),
            plugin_manager=self.plugin_manager,
            identifier="nfv",
            printer_profile_manager=_Profiles(),
        )

    def write_gcode(self, content):
        path = Path(self.temp_dir.name) / "print.gcode"
        path.write_text(content, encoding="utf-8")
        return str(path)

    def test_parse_short_file_includes_first_character(self):
        info = parse_gcode(self.write_gcode(VALID_GCODE))
        self.assertEqual(["0.4"], info["nozzle_size"])
        self.assertEqual(["PLA"], info["filament_type"])

    def test_valid_file_passes_without_spool_manager(self):
        self.assertTrue(self.validator.check_print(self.write_gcode(VALID_GCODE)))
        self.assertTrue(self.validator.last_check_cacheable)
        self.assertFalse(self.printer.cancelled)
        self.assertFalse(self.printer.paused)

    def test_missing_required_metadata_fails_closed(self):
        self.assertFalse(self.validator.check_print(self.write_gcode("G28\n")))
        self.assertTrue(any("Required slicer metadata" in message[1]["msg"]
                            for message in self.plugin_manager.messages))

    def test_malformed_numeric_metadata_fails_closed(self):
        malformed = VALID_GCODE.replace("100.0", "not-a-number")
        self.assertFalse(self.validator.check_print(self.write_gcode(malformed)))
        self.assertTrue(any("malformed numeric value" in message[1]["msg"]
                            for message in self.plugin_manager.messages))

    def test_explicit_override_allows_missing_metadata(self):
        self.validator._filament = _InteractiveFilament()
        timer = threading.Timer(0.02, lambda: self.validator.update_filament_wait_status("ok"))
        timer.start()
        self.addCleanup(timer.cancel)
        self.assertTrue(self.validator.check_print(self.write_gcode("G28\n")))
        self.assertFalse(self.validator.last_check_cacheable)

    def test_filament_type_toggle_is_independent_of_spool_name_toggle(self):
        self.validator._filament = _TypesDisabledFilament()
        self.validator._spool_manager = _WrongTypeSpoolManager()
        self.assertTrue(self.validator.check_print(self.write_gcode(VALID_GCODE)))

    def test_manual_filament_is_validated_without_spool_name_checking(self):
        self.validator._filament = _NameCheckingFilament()
        self.validator._spool_manager = _ManualFilamentProvider("PLA")
        self.assertTrue(self.validator.check_print(self.write_gcode(VALID_GCODE)))

        self.validator._spool_manager = _ManualFilamentProvider("ABS")
        self.assertFalse(self.validator.check_print(self.write_gcode(VALID_GCODE)))

    def test_spoolman_identifier_supports_spool_name_validation(self):
        self.validator._filament = _NameCheckingFilament()
        self.validator._spool_manager = _SpoolmanProvider("PLA")
        with_identifier = VALID_GCODE.replace(
            "G28\n", "; filament_notes = [sm_name = spoolman:42]\nG28\n")

        self.assertTrue(self.validator.check_print(self.write_gcode(with_identifier)))

    def test_rme_identifier_supports_spool_name_validation(self):
        self.validator._filament = _NameCheckingFilament()
        self.validator._spool_manager = _RmeProvider("PLA")
        with_identifier = VALID_GCODE.replace(
            "G28\n", "; filament_notes = [sm_name = rme:internal:4]\nG28\n")

        self.assertTrue(self.validator.check_print(self.write_gcode(with_identifier)))

    def test_active_prompt_can_be_replayed_then_cleared(self):
        self.validator.set_active_prompt("validation_prompt", "Still waiting", 10)
        prompt = self.validator.get_active_prompt()
        self.assertEqual("validation_prompt", prompt["type"])
        self.assertEqual("Still waiting", prompt["msg"])
        self.assertGreater(prompt["timeout"], 0)
        self.validator.update_filament_wait_status("cancel")
        self.assertIsNone(self.validator.get_active_prompt())

    def test_skip_validation_directive_is_explicit(self):
        self.assertTrue(self.validator.check_print(self.write_gcode("G28\n; skip_validation\n")))
        self.assertFalse(self.validator.check_print(self.write_gcode("G28\n; skip_validation_but_not_really\n")))

    def test_remapped_tool_uses_physical_nozzle_and_filament(self):
        self.validator.extruders = _RemappedExtruders()
        self.validator.set_tool_mapping({0: 1})
        self.assertEqual(1, self.validator.physical_tool(0))
        self.assertEqual((True, True), self.validator.check_nozzle(0, ["0.4"], True))
        self.assertEqual(
            (True, True),
            self.validator.check_filament_type(
                0, ["ABS", "PLA"], ["PLA"], {"filament_type": ["PLA"]}, True, False
            ),
        )


if __name__ == "__main__":
    unittest.main()
