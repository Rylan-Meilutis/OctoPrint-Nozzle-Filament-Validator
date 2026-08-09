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
    sys.modules.setdefault("octoprint.filemanager", filemanager)

    server = types.ModuleType("octoprint.server")
    server.app = types.SimpleNamespace()
    sys.modules.setdefault("octoprint.server", server)


_install_octoprint_stubs()

from octoprint_nfv import Nozzle_filament_validatorPlugin


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


class PreflightGateTests(unittest.TestCase):
    def make_plugin(self, validation_result):
        plugin = Nozzle_filament_validatorPlugin()
        plugin.validator = _Validator(validation_result)
        plugin._printer = _Printer()
        plugin._logger = logging.getLogger("nfv-preflight-tests")
        return plugin

    def test_failure_suppresses_start_and_first_file_command(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "print.gcode")
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
        plugin = self.make_plugin(True)
        comm = _Comm("print.gcode")
        self.assertIsNone(plugin.validate_before_queuing(
            comm, "queuing", "M110 N0", None, "M110", tags={"source:job"}))
        self.assertIsNone(plugin.validate_before_queuing(
            comm, "queuing", "G28", None, "G28", tags={"source:file"}))
        self.assertEqual(1, plugin.validator.calls)
        self.assertEqual(0, plugin._printer.cancel_calls)


if __name__ == "__main__":
    unittest.main()
