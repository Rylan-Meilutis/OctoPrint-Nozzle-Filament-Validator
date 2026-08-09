import logging
import sys
import tempfile
import types
import unittest
from pathlib import Path


def _install_octoprint_stubs():
    flask = types.ModuleType("flask")
    flask.Request = object
    flask.Response = object
    flask.response = object
    flask.abort = lambda status: status
    flask.jsonify = lambda **data: data
    sys.modules.setdefault("flask", flask)

    flask_login = types.ModuleType("flask_login")
    flask_login.current_user = types.SimpleNamespace(is_anonymous=False)
    sys.modules.setdefault("flask_login", flask_login)

    plugin = types.ModuleType("octoprint.plugin")
    for name in ("StartupPlugin", "SettingsPlugin", "AssetPlugin", "TemplatePlugin",
                 "SimpleApiPlugin", "EventHandlerPlugin"):
        setattr(plugin, name, type(name, (), {}))

    octoprint = types.ModuleType("octoprint")
    octoprint.plugin = plugin
    sys.modules.setdefault("octoprint", octoprint)
    sys.modules.setdefault("octoprint.plugin", plugin)

    events = types.ModuleType("octoprint.events")
    events.Events = types.SimpleNamespace(
        PRINT_CANCELLED="PrintCancelled",
        PRINT_DONE="PrintDone",
        PRINT_FAILED="PrintFailed",
        CONNECTED="Connected",
    )
    sys.modules.setdefault("octoprint.events", events)

    filemanager = types.ModuleType("octoprint.filemanager")
    filemanager.FileDestinations = types.SimpleNamespace(LOCAL="local")
    filemanager.valid_file_type = lambda path, type=None: path.lower().endswith((".gcode", ".gco", ".g"))
    sys.modules.setdefault("octoprint.filemanager", filemanager)

    server = types.ModuleType("octoprint.server")
    server.app = types.SimpleNamespace()
    sys.modules.setdefault("octoprint.server", server)


_install_octoprint_stubs()

from octoprint_nfv import Nozzle_filament_validatorPlugin
from octoprint_nfv.db import init_db
from octoprint_nfv.filament import filament
from octoprint_nfv.spoolManager import SpoolManagerIntegration


class _CurrentFile:
    def __init__(self, path):
        self.path = path

    def getFilename(self):
        return self.path


class _Comm:
    def __init__(self, path):
        self._currentFile = _CurrentFile(path)

    def isSdFileSelected(self):
        return False


class _Validator:
    def __init__(self, result):
        self.result = result
        self.calls = 0
        self.last_check_cacheable = True

    def check_print(self, path):
        self.calls += 1
        return self.result


class _Printer:
    def __init__(self):
        self.cancel_calls = 0

    def cancel_print(self):
        self.cancel_calls += 1

    def is_cancelling(self):
        # Model OctoPrint ignoring cancel_print while its state is STARTING.
        return self.cancel_calls >= 2

    def get_current_job(self):
        return {}


class _FileManager:
    def __init__(self):
        self.metadata = {}

    def path_on_disk(self, origin, path):
        return path

    def path_in_storage(self, origin, path):
        return path

    def set_additional_metadata(self, origin, path, key, data, overwrite=False):
        self.metadata[(origin, path, key)] = data

    def get_additional_metadata(self, origin, path, key):
        return self.metadata.get((origin, path, key))

    def remove_additional_metadata(self, origin, path, key):
        self.metadata.pop((origin, path, key), None)


class _Settings:
    def __init__(self, validate_on_upload=False):
        self.validate_on_upload = validate_on_upload

    def get_boolean(self, path):
        return self.validate_on_upload


class _FallbackExtruders:
    def get_nozzle_size_for_extruder(self, position):
        return 0.4

    def get_number_of_extruders(self):
        return 2


class _SpoolmanSettings:
    def get(self, path):
        return {"0": {"spoolId": "42"}, "1": {"spoolId": "84"}}


class _SpoolmanConnector:
    def handleGetSpoolsAvailable(self):
        return {"data": {"spools": [
            {"id": 42, "filament": {"material": "PLA", "name": "Galaxy PLA"}},
            {"id": 84, "filament": {"material": "PETG", "name": "Tough PETG"}},
        ]}}


class _SpoolmanPlugin:
    def __init__(self):
        self._settings = _SpoolmanSettings()

    def getSpoolmanConnector(self):
        return _SpoolmanConnector()


class _RmeCompatibilityPlugin:
    def _filament_report(self):
        return {
            "schema": "rme-filament-report-v1",
            "provider": "internal",
            "data": {"tools": [
                {"name": "Orange PLA", "material": "PLA", "spool_id": "4",
                 "provider": "internal"},
                {"name": "PETG", "material": "PETG", "spool_id": "",
                 "provider": "RME firmware"},
            ], "spools": []},
        }


class PreflightGateTests(unittest.TestCase):
    def make_plugin(self, validation_result):
        plugin = Nozzle_filament_validatorPlugin()
        plugin.validator = _Validator(validation_result)
        plugin._printer = _Printer()
        plugin._logger = logging.getLogger("nfv-preflight-tests")
        plugin._file_manager = _FileManager()
        plugin._settings = _Settings()
        plugin.config_hash = "config-a"
        plugin._validation_config_hash = lambda: plugin.config_hash
        return plugin

    def test_failure_suppresses_start_and_first_file_command(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "print.gcode")
            Path(path).write_text("G28\n", encoding="utf-8")
            comm = _Comm(path)
            plugin = self.make_plugin(False)

            start_result = plugin.validate_before_queuing(
                comm, "queuing", "M110 N0", None, "M110", tags={"source:job"})
            file_result = plugin.validate_before_queuing(
                comm, "queuing", "G28", None, "G28", tags={"source:file"})

            self.assertEqual((None,), start_result)
            self.assertEqual((None,), file_result)
            self.assertEqual(1, plugin.validator.calls)
            self.assertEqual(2, plugin._printer.cancel_calls)

    def test_cancellation_commands_are_not_suppressed(self):
        plugin = self.make_plugin(False)
        result = plugin.validate_before_queuing(
            _Comm("print.gcode"), "queuing", "M400", None, "M400",
            tags={"source:job", "trigger:cancel"})
        self.assertIsNone(result)
        self.assertEqual(0, plugin.validator.calls)

    def test_success_validates_once_and_allows_job(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "print.gcode")
            Path(path).write_text("G28\n", encoding="utf-8")
            plugin = self.make_plugin(True)
            comm = _Comm(path)
            self.assertIsNone(plugin.validate_before_queuing(
                comm, "queuing", "M110 N0", None, "M110", tags={"source:job"}))
            self.assertIsNone(plugin.validate_before_queuing(
                comm, "queuing", "G28", None, "G28", tags={"source:file"}))
            self.assertEqual(1, plugin.validator.calls)
            self.assertEqual(0, plugin._printer.cancel_calls)

    def test_cached_success_is_reused_for_unchanged_file_and_config(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "print.gcode")
            Path(path).write_text("G28\n", encoding="utf-8")
            plugin = self.make_plugin(True)

            self.assertTrue(plugin._validate_and_cache(path, path))
            plugin._validation_cache.clear()  # Exercise persistent file metadata too.
            self.assertIsNone(plugin.validate_before_queuing(
                _Comm(path), "queuing", "G28", None, "G28", tags={"source:file"}))

            self.assertEqual(1, plugin.validator.calls)

    def test_config_change_invalidates_cached_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "print.gcode")
            Path(path).write_text("G28\n", encoding="utf-8")
            plugin = self.make_plugin(True)
            self.assertTrue(plugin._validate_and_cache(path, path))

            plugin.config_hash = "config-b"
            self.assertIsNone(plugin.validate_before_queuing(
                _Comm(path), "queuing", "G28", None, "G28", tags={"source:file"}))

            self.assertEqual(2, plugin.validator.calls)

    def test_file_change_invalidates_cached_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "print.gcode")
            Path(path).write_text("G28\n", encoding="utf-8")
            plugin = self.make_plugin(True)
            self.assertTrue(plugin._validate_and_cache(path, path))

            Path(path).write_text("G28\nM117 changed\n", encoding="utf-8")
            self.assertIsNone(plugin.validate_before_queuing(
                _Comm(path), "queuing", "G28", None, "G28", tags={"source:file"}))

            self.assertEqual(2, plugin.validator.calls)

    def test_failed_explicit_revalidation_removes_old_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "print.gcode")
            Path(path).write_text("G28\n", encoding="utf-8")
            plugin = self.make_plugin(True)
            self.assertTrue(plugin._validate_and_cache(path, path))

            plugin.validator.result = False
            self.assertFalse(plugin._validate_and_cache(path, path))

            self.assertFalse(plugin._cached_validation_matches(path, path))

    def test_override_allows_request_but_is_not_cached(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "print.gcode")
            Path(path).write_text("G28\n", encoding="utf-8")
            plugin = self.make_plugin(True)
            plugin.validator.last_check_cacheable = False

            self.assertTrue(plugin._validate_and_cache(path, path))
            self.assertFalse(plugin._cached_validation_matches(path, path))

    def test_upload_validation_only_starts_for_local_machinecode(self):
        plugin = self.make_plugin(True)
        plugin._settings.validate_on_upload = True
        requests = []
        plugin._start_file_validation = lambda disk, storage, source: requests.append(
            (disk, storage, source))

        plugin.on_event("Upload", {"target": "local", "path": "part.gcode"})
        plugin.on_event("Upload", {"target": "local", "path": "part.stl"})
        plugin.on_event("Upload", {"target": "sdcard", "path": "other.gcode"})

        self.assertEqual([("part.gcode", "part.gcode", "upload")], requests)

    def test_missing_spool_manager_uses_persisted_manual_filaments(self):
        with tempfile.TemporaryDirectory() as directory:
            init_db(directory)
            fallback = filament(directory, logging.getLogger("nfv-fallback-tests"))
            fallback.update_manual_filament(1, "PLA")
            fallback.update_manual_filament(2, "PETG")
            integration = SpoolManagerIntegration(
                None, logging.getLogger("nfv-fallback-tests"),
                lambda: fallback.get_manual_filaments(2))

            self.assertFalse(integration.is_available())
            self.assertEqual("manual", integration.get_source_name())
            self.assertEqual(["PLA", "PETG"], integration.get_loaded_filaments())
            self.assertEqual([], integration.get_names())

    def test_extruder_info_does_not_index_missing_spool_names(self):
        plugin = self.make_plugin(True)
        plugin.extruders = _FallbackExtruders()
        plugin._spool_manager = SpoolManagerIntegration(
            None, logging.getLogger("nfv-fallback-tests"), lambda: ["PLA", "PETG"])

        response = plugin.on_api_command("get_extruder_info", {"extruderId": 1})

        self.assertEqual("PLA", response["filamentType"])
        self.assertIsNone(response["spoolName"])

    def test_spoolman_selected_spools_supply_materials_and_unique_names(self):
        integration = SpoolManagerIntegration(
            None, logging.getLogger("nfv-spoolman-tests"),
            fallback_filaments=lambda: ["ABS", "ABS"],
            spoolman_impl=_SpoolmanPlugin())

        self.assertTrue(integration.is_available())
        self.assertEqual("spoolman", integration.get_source_name())
        self.assertEqual(["PLA", "PETG"], integration.get_loaded_filaments())
        self.assertEqual(["spoolman:42", "spoolman:84"], integration.get_names())

    def test_rme_compatibility_is_used_after_other_external_providers(self):
        integration = SpoolManagerIntegration(
            None, logging.getLogger("nfv-rme-tests"),
            fallback_filaments=lambda: ["ABS", "ABS"],
            rme_compatibility_impl=_RmeCompatibilityPlugin())

        self.assertTrue(integration.is_available())
        self.assertEqual("rme_compatibility", integration.get_source_name())
        self.assertEqual(["PLA", "PETG"], integration.get_loaded_filaments())
        self.assertEqual(["rme:internal:4", None], integration.get_names())

    def test_old_rme_plugin_without_report_keeps_manual_fallback_available(self):
        integration = SpoolManagerIntegration(
            None, logging.getLogger("nfv-old-rme-tests"),
            fallback_filaments=lambda: ["ABS"],
            rme_compatibility_impl=object())

        self.assertFalse(integration.is_available())
        self.assertEqual("manual", integration.get_source_name())
        self.assertEqual(["ABS"], integration.get_loaded_filaments())

    def test_spoolman_takes_priority_over_rme_compatibility(self):
        integration = SpoolManagerIntegration(
            None, logging.getLogger("nfv-provider-priority-tests"),
            spoolman_impl=_SpoolmanPlugin(),
            rme_compatibility_impl=_RmeCompatibilityPlugin())

        self.assertEqual("spoolman", integration.get_source_name())
        self.assertEqual(["spoolman:42", "spoolman:84"], integration.get_names())


if __name__ == "__main__":
    unittest.main()
