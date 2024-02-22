# coding=utf-8
from __future__ import absolute_import

import logging
import os
import re
import sqlite3
import time

import flask
import octoprint.plugin
from flask_login import current_user
from octoprint.events import Events
from octoprint.filemanager import FileDestinations

from octoprint_nfv.spoolManager import SpoolManagerIntegration


class Nozzle_filament_validatorPlugin(octoprint.plugin.StartupPlugin, octoprint.plugin.SettingsPlugin,
                                      octoprint.plugin.AssetPlugin,
                                      octoprint.plugin.TemplatePlugin,
                                      octoprint.plugin.SimpleApiPlugin,
                                      octoprint.plugin.EventHandlerPlugin
                                      ):

    def __init__(self):
        super().__init__()
        self._conn = None
        self._spool_manager = None

    def get_api_commands(self):
        return dict(
            addNozzle=["size"],
            selectNozzle=["nozzleId"],
            removeNozzle=["nozzleId"]
        )

    def on_api_command(self, command, data):
        import flask

        if current_user.is_anonymous():
            return "Insufficient rights", 403

        if command == "addNozzle":
            nozzle_size = data["size"]
            if nozzle_size is not None:
                try:
                    self.add_nozzle_to_database(nozzle_size)
                except Exception as e:
                    self.send_alert(f"Error adding nozzle to the database: {e}", "error")
                return flask.jsonify(success=True)
            else:
                return flask.abort(400)

        elif command == "selectNozzle":
            selected_nozzle_id = data.get("nozzleId")
            if selected_nozzle_id is not None:
                try:
                    self.select_current_nozzle(selected_nozzle_id)
                except Exception as e:
                    self.send_alert(f"Error selecting nozzle: {e}", "error")
                return flask.jsonify(success=True)
            else:
                return flask.abort(400)

        elif command == "removeNozzle":
            nozzle_id = data.get("nozzleId")
            if nozzle_id is not None:
                try:
                    self.remove_nozzle_from_database(nozzle_id)
                except Exception as e:
                    self.send_alert(f"Error removing nozzle from the database: {e}", "error")
                return flask.jsonify(success=True)
            else:
                return flask.abort(400)

        return flask.jsonify(error="'{}' is an invalid command".format(command)), 400

    def send_alert(self, message, type="popup"):
        self._plugin_manager.send_plugin_message(self._identifier, dict(type=type, msg=message))

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

    def on_api_get(self, request):
        nozzles = self.fetch_nozzles_from_database()
        filament_type = self.get_loaded_filament()
        current_nozzle = self.get_current_nozzle_size()
        return flask.jsonify(nozzles=nozzles, filament_type=filament_type, currentNozzle=current_nozzle)

    def check_print(self, file_path):
        self._logger.setLevel(logging.INFO)
        passed = True
        # Retrieve the loaded filament type from spool manager
        self._logger.info("Checking print for nozzle and filament settings...")
        try:
            loaded_filament = self.get_loaded_filament()
        except Exception as e:
            self.send_alert(f"Error retrieving loaded filament: {e}", "error")
            return
        # Parse the GCODE file to extract the nozzle size and filament type
        gcode_info = self.parse_gcode(file_path)

        # Check if the loaded filament matches the filament type in the GCODE
        if gcode_info["filament_type"] is None:
            self.send_alert("No filament type found in GCODE, error checking won't be performed", "info")
            passed = False

        elif loaded_filament is None:
            self.send_alert("No filament loaded, error checking won't be performed", "info")
            passed = False

        elif loaded_filament == -1:
            self.send_alert("Spool Manager plugin is not installed. Filament type will not be checked.", "info")
            passed = False

        elif loaded_filament == -2:
            self.send_alert("Error retrieving loaded filament, filament error checking won't be performed", "info")
            passed = False

        if (gcode_info["filament_type"].lower() != str(loaded_filament).lower() and gcode_info["filament_type"] is not
                None):
            self._logger.error("Print aborted: Incorrect filament type")
            self.send_alert("Print aborted: Incorrect filament type", "error")
            self._printer.cancel_print()
            return

        # Check if the loaded nozzle size matches the nozzle size in the GCODE
        if gcode_info["nozzle_size"] is None:
            self.send_alert("No nozzle size found in GCODE, error checking won't be performed", "info")
            passed = False

        elif self.get_current_nozzle_size() is None:
            self.send_alert("No nozzle selected, error checking won't be performed", "info")
            passed = False

        if (float(gcode_info["nozzle_size"]) != float(self.get_current_nozzle_size()) and gcode_info["nozzle_size"] is
                not None):
            self._logger.error("Print aborted: Incorrect nozzle size")
            self.send_alert("Print aborted: Incorrect nozzle size", "error")
            self._printer.cancel_print()
            return
        
        if passed:
            self.send_alert("Print passed nozzle and filament check", "info")
            self._logger.info("Print passed nozzle and filament check...")

    def fetch_nozzles_from_database(self):
        con = self.get_db()
        cursor = con.cursor()
        cursor.execute("SELECT id, size FROM nozzles")
        con.commit()
        return [{"id": row[0], "size": row[1]} for row in cursor.fetchall()]

    def add_nozzle_to_database(self, nozzle_size):
        try:
            con = self.get_db()
            cursor = con.cursor()

            # Check if the nozzle size already exists in the database
            cursor.execute("SELECT size FROM nozzles WHERE size = ?", (float(nozzle_size),))
            existing_size = cursor.fetchone()
            con.commit()

            # If the size already exists, log an error
            if existing_size:
                self._logger.error("Nozzle size already exists in the database")
            else:
                # Otherwise, insert the nozzle size into the database
                cursor.execute("INSERT INTO nozzles (size) VALUES (?)", (float(nozzle_size),))
                con.commit()
        except Exception as e:
            self._logger.error(f"Error adding nozzle to the database: {e}")

    def select_current_nozzle(self, selected_nozzle_id):
        con = self.get_db()
        cursor = con.cursor()
        cursor.execute("UPDATE current_nozzle SET nozzle_id = ? WHERE id = 1",
                       (int(selected_nozzle_id),))  # Assuming there's only one current nozzle
        con.commit()

    def get_db(self):
        data_folder = self.get_plugin_data_folder()
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)

        # Construct the path to the SQLite database file
        db_path = os.path.join(data_folder, "nozzle_filament_database.db")
        return sqlite3.connect(db_path)

    def initialize(self):
        # Connect to the SQLite database
        self._conn = self.get_db()

        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS nozzles (id INTEGER PRIMARY KEY, size REAL)")
        self._conn.execute("CREATE TABLE IF NOT EXISTS current_nozzle (id INTEGER PRIMARY KEY, nozzle_id INTEGER)")
        self._conn.commit()

        smplugin = self._plugin_manager.plugins.get("SpoolManager").implementation
        self._spool_manager = SpoolManagerIntegration(smplugin, self._logger)

        # Retry inserting a row into current_nozzle with a maximum of 3 attempts
        try:
            retries = 0
            cursor = self._conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM current_nozzle")
            count = cursor.fetchone()[0]
            if count == 0:
                while retries < 3:
                    try:
                        cursor = self._conn.cursor()
                        cursor.execute("INSERT INTO current_nozzle (nozzle_id) VALUES (?)", (1,))
                        self._conn.commit()
                        break
                    except sqlite3.OperationalError as e:
                        self._logger.warning(f"Database operation failed: {e}")
                        self._logger.warning("Retrying...")
                        retries += 1
                        time.sleep(1)  # Wait for 1 second before retrying

                if retries == 3:
                    self._logger.error(
                        "Failed to insert row into current_nozzle after multiple attempts. Plugin initialization may be"
                        "incomplete.")
        except Exception as e:
            self._logger.error(f"Error adding nozzle to the database: {e}")

        try:
            retries = 0
            cursor = self._conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM nozzles")
            count = cursor.fetchone()[0]
            if count == 0:
                while retries < 3:
                    try:
                        self.add_nozzle_to_database(0.4)
                        break
                    except sqlite3.OperationalError as e:
                        self._logger.warning(f"Database operation failed: {e}")
                        self._logger.warning("Retrying...")
                        retries += 1
                        time.sleep(1)  # Wait for 1 second before retrying

                if retries == 3:
                    self._logger.error(
                        "Failed to insert row into current_nozzle after multiple attempts. Plugin initialization may "
                        "be incomplete.")
        except Exception as e:
            self._logger.error(f"Error adding nozzle to the database: {e}")

    def get_current_nozzle_size(self):
        nozzle_id = self.get_current_nozzle_id()

        if nozzle_id is not None:
            con = self.get_db()
            cursor = con.cursor()
            # Extract the ID from the fetched row

            # Execute a SELECT query to retrieve the size based on the current nozzle ID
            cursor.execute("SELECT size FROM nozzles WHERE id = ?", (nozzle_id,))
            con.commit()
            # Fetch the size corresponding to the current nozzle ID
            result = cursor.fetchone()

            # Return the size if found
            return result[0] if result else None
        else:
            # Return None if no current nozzle ID was found
            self._logger.error("No current nozzle ID found in the database")
            return None

    def get_current_nozzle_id(self):
        # Create a cursor to execute SQL queries
        con = self.get_db()
        cursor = con.cursor()

        # Execute a SELECT query to retrieve the current nozzle ID
        cursor.execute("SELECT nozzle_id FROM current_nozzle WHERE id = 1")

        # Fetch the current nozzle ID
        data_id = cursor.fetchone()
        con.commit()

        return data_id[0] if data_id else None

    def remove_nozzle_from_database(self, nozzle_id):
        con = self.get_db()
        cursor = con.cursor()
        cursor.execute("DELETE FROM nozzles WHERE id = ?", (nozzle_id,))
        con.commit()

        # Check if the removed nozzle was the current nozzle
        current_nozzle_id = self.get_current_nozzle_id()
        if current_nozzle_id == nozzle_id:
            cursor.execute("UPDATE current_nozzle SET nozzle_id = ? WHERE id = ?",
                           (1, 1))  # Assuming there's only one current nozzle
            con.commit()

    def on_event(self, event, payload):
        if event == Events.PRINT_STARTED:
            self._logger.info("detected print_start_event")
            selected_file = payload.get("file", "")
            if not selected_file:
                path = payload.get("path", "")
                if payload.get("origin") == "local":
                    # Get full path to local file
                    path = self._file_manager.path_on_disk(FileDestinations.LOCAL, path)
                selected_file = path
            self.check_print(selected_file)

    ##~~ TemplatePlugin mixin

    def get_template_configs(self):
        return [
            dict(type="settings", template="nozzle_filament_validator_page.jinja2", custom_bindings=False)  # Custom
            # page
        ]

    ##~~ AssetPlugin mixin

    def get_assets(self):
        return {
            "js": ["js/Nozzle_Filament_Validator.js"],
            "css": ["css/Nozzle_Filament_Validator.css"],
            "less": ["less/Nozzle_Filament_Validator.less"]
        }

    def get_loaded_filament(self):
        try:
            if self._spool_manager is None:
                self._logger.warning("Spool Manager plugin is not installed. Filament type will not be checked.")
                return -1

            materials = self._spool_manager.get_materials()

            if not materials:
                self._logger.warning("No filament selected in Spool Manager. Filament type will not be checked.")
                return None

            # Assuming the first loaded filament is the currently used one
            loaded_filament = materials[0]
            return loaded_filament.split("_")[0] if loaded_filament is not None else None
        except Exception as e:
            self._logger.error(f"Error retrieving loaded filament: {e}")
            return -2

    def parse_gcode(self, file_path):
        # Regular expression patterns to extract nozzle diameter and filament type
        nozzle_pattern = re.compile(r'; nozzle_diameter = (\d+\.\d+)')
        filament_pattern = re.compile(r'; filament_type = (.+)')

        # Number of lines to read from the end of the file
        num_lines = 400

        with open(file_path, 'r') as file:
            # Move the file pointer to the end
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            # Track the position in the file
            pos = file_size - 1
            newline_count = 0
            # Read the file backwards until we find the last 100 lines or reach the beginning of the file
            while pos > 0 and newline_count < num_lines:
                file.seek(pos)
                char = file.read(1)
                if char == '\n':
                    newline_count += 1
                    if newline_count == num_lines:
                        break
                pos -= 1
            # Read the last 100 lines
            lines = file.readlines()

            # Extract nozzle diameter and filament type from the collected lines
            gcode_content = ''.join(lines)
            nozzle_match = nozzle_pattern.search(gcode_content)
            filament_match = filament_pattern.search(gcode_content)
            nozzle_size = None
            filament_type = None
            if nozzle_match:
                nozzle_size = float(nozzle_match.group(1))
            if filament_match:
                filament_type = filament_match.group(1).strip()

        return {"nozzle_size": nozzle_size, "filament_type": filament_type}

    def on_after_startup(self):
        self._logger.info("NozzleFilamentValidatorPlugin initialized")

    ##~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        return {
            # put your plugin's default settings here
        }

    ##~~ Softwareupdate hook

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
        # for details.
        return {
            "Nozzle_Filament_Validator": {
                "displayName": "Nozzle_filament_validator Plugin",
                "displayVersion": self._plugin_version,

                # version check: github repository
                "type": "github_release",
                "user": "Rylan-Meilutis",
                "repo": "OctoPrint-Nozzle-Filament-Validator",
                "current": self._plugin_version,

                # update method: pip
                "pip": "https://github.com/Rylan-Meilutis/OctoPrint-Nozzle-Filament-Validator/archive/{"
                       "target_version}.zip",
            }
        }


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Nozzle Filament Validator"

# Set the Python version your plugin is compatible with below. Recommended is Python 3 only for all new plugins.
# OctoPrint 1.4.0 - 1.7.x run under both Python 3 and the end-of-life Python 2.
# OctoPrint 1.8.0 onwards only supports Python 3.
__plugin_pythoncompat__ = ">=3,<4"  # Only Python 3


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = Nozzle_filament_validatorPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
