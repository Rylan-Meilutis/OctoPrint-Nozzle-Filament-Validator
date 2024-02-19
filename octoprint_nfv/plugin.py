import sqlite3
import re
import octoprint.plugin

from octoprint_nfv.spoolManager import SpoolManagerIntegration


class NozzleFilamentValidatorPlugin(octoprint.plugin.StartupPlugin, octoprint.plugin.EventHandlerPlugin,
                                    octoprint.plugin.TemplatePlugin):

    def __init__(self):
        super().__init__()
        self._conn = None

    def initialize(self):
        # Connect to the SQLite database
        self._conn = sqlite3.connect("nozzle_filament_database.db")
        self._conn.execute("CREATE TABLE IF NOT EXISTS nozzles (id INTEGER PRIMARY KEY, size REAL)")
        self._conn.execute("CREATE TABLE IF NOT EXISTS filament_types (id INTEGER PRIMARY KEY, type TEXT)")
        self._conn.commit()

    def on_event(self, event, payload):
        if event == "PrintStarted":
            self.check_print(payload["path"])

    def check_print(self, file_path):
        # Retrieve the loaded filament type from spool manager
        loaded_filament = self.get_loaded_filament()  # You need to implement this method

        # Parse the GCODE file to extract the nozzle size and filament type
        gcode_info = self.parse_gcode(file_path)  # You need to implement this method

        # Check if the loaded filament matches the filament type in the GCODE
        if gcode_info["filament_type"] != loaded_filament:
            self._logger.error("Print aborted: Incorrect filament type")
            # You may need to send a notification to the user here
            return

        # Check if the loaded nozzle size matches the nozzle size in the GCODE
        if gcode_info["nozzle_size"] != self.get_current_nozzle_size():
            self._logger.error("Print aborted: Incorrect nozzle size")
            # You may need to send a notification to the user here
            return

    def get_loaded_filament(self):
        try:
            if "pluginmanager" not in self._plugin_manager.get_plugin_identifiers():
                self._logger.warning("Spool Manager plugin is not installed. Filament type will not be checked.")
                return None

            spool_manager = SpoolManagerIntegration(self._impl, self._logger)
            materials = spool_manager.get_materials()

            if not materials:
                self._logger.warning("No filament selected in Spool Manager. Filament type will not be checked.")
                return None

            # Assuming the first loaded filament is the currently used one
            loaded_filament = materials[0]
            return loaded_filament
        except Exception as e:
            self._logger.error(f"Error retrieving loaded filament: {e}")
            return None

    def get_current_nozzle_size(self):
        # Retrieve the current nozzle size from the database
        cursor = self._conn.cursor()
        cursor.execute("SELECT size FROM nozzles ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        return result[0] if result else None

    def parse_gcode(self, file_path):
        # Regular expression patterns to extract nozzle diameter and filament type
        nozzle_pattern = re.compile(r'; nozzle_diameter = (\d+\.\d+)')
        filament_pattern = re.compile(r'; filament_type = (.+)')

        with open(file_path, 'r') as file:
            gcode_content = file.read()

            # Extract nozzle diameter
            nozzle_match = nozzle_pattern.search(gcode_content)
            if nozzle_match:
                nozzle_size = float(nozzle_match.group(1))
                print("Nozzle Diameter:", nozzle_size)

            # Extract filament type
            filament_match = filament_pattern.search(gcode_content)
            if filament_match:
                filament_type = filament_match.group(1).strip()
                print("Filament Type:", filament_type)
        return {"nozzle_size": nozzle_size, "filament_type": filament_type}

    def on_after_startup(self):
        self._logger.info("NozzleFilamentValidatorPlugin initialized")


__plugin_name__ = "Nozzle Filament Validator"
__plugin_version__ = "0.1.0"
__plugin_description__ = "Plugin to validate nozzle size and filament type before starting a print"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = NozzleFilamentValidatorPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate_check": __plugin_implementation__.get_update_information
    }
