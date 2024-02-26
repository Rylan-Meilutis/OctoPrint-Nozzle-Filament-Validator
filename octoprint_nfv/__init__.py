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

import octoprint_nfv.build_plate as build_plate
import octoprint_nfv.nozzle as nozzle
from octoprint_nfv.db import get_db, init_db
from octoprint_nfv.spoolManager import SpoolManagerIntegration


class Nozzle_filament_validatorPlugin(octoprint.plugin.StartupPlugin, octoprint.plugin.SettingsPlugin,
                                      octoprint.plugin.AssetPlugin,
                                      octoprint.plugin.TemplatePlugin,
                                      octoprint.plugin.SimpleApiPlugin,
                                      octoprint.plugin.EventHandlerPlugin
                                      ):

    def __init__(self):
        super().__init__()
        self._spool_manager = None
        self.nozzle = None
        self.build_plate = None

    def get_api_commands(self):
        return dict(
            addNozzle=["size"],
            selectNozzle=["nozzleId"],
            removeNozzle=["nozzleId"],
            add_build_plate=["name", "compatibleFilaments", "id"],
            select_build_plate=["buildPlateId"],
            remove_build_plate=["buildPlateId"],
            get_build_plate=["buildPlateId"]
        )

    def on_api_get(self, request):
        nozzles = self.nozzle.fetch_nozzles_from_database()
        filament_type = self.get_loaded_filament()
        current_nozzle = self.nozzle.get_current_nozzle_size()
        build_plates = self.build_plate.fetch_build_plates_from_database()
        current_build_plate = self.build_plate.get_current_build_plate_name()
        current_build_plate_filaments = self.build_plate.get_current_build_plate_filaments()
        filaments = build_plate.get_filament_types()
        return flask.jsonify(nozzles=nozzles, filament_type=filament_type, currentNozzle=current_nozzle,
                             build_plates=build_plates, currentBuildPlate=current_build_plate,
                             currentBuildPlateFilaments=current_build_plate_filaments, filaments=filaments)

    def on_api_command(self, command, data):
        import flask

        if current_user.is_anonymous():
            return "Insufficient rights", 403

        if command == "addNozzle":
            nozzle_size = data["size"]
            if nozzle_size is not None:
                try:
                    self.nozzle.add_nozzle_to_database(nozzle_size)
                except Exception as e:
                    self.send_alert(f"Error adding nozzle to the database: {e}", "error")
                return flask.jsonify(success=True)
            else:
                return flask.abort(400)

        elif command == "selectNozzle":
            selected_nozzle_id = data.get("nozzleId")
            if selected_nozzle_id is not None:
                try:
                    self.nozzle.select_current_nozzle(selected_nozzle_id)
                except Exception as e:
                    self.send_alert(f"Error selecting nozzle: {e}", "error")
                return flask.jsonify(success=True)
            else:
                return flask.abort(400)

        elif command == "removeNozzle":
            nozzle_id = data.get("nozzleId")
            if nozzle_id is not None:
                try:
                    self.nozzle.remove_nozzle_from_database(nozzle_id)
                except Exception as e:
                    self.send_alert(f"Error removing nozzle from the database: {e}", "error")
                return flask.jsonify(success=True)
            else:
                return flask.abort(400)

        elif command == "add_build_plate":
            name = data["name"]
            compatible_filaments = data["compatibleFilaments"]
            db_position = data.get("id") if data.get("id") is not None or data.get("id") != "" else None
            if name is not None and compatible_filaments is not None:
                try:
                    self.build_plate.insert_build_plate_to_database(name, compatible_filaments, db_position)
                except Exception as e:
                    self.send_alert(e, "tmp_error")
                return flask.jsonify(success=True)
            else:
                return flask.abort(400)

        elif command == "select_build_plate":
            selected_build_plate_id = data.get("buildPlateId")
            if selected_build_plate_id is not None:
                try:
                    self.build_plate.select_current_build_plate(selected_build_plate_id)
                except Exception as e:
                    self.send_alert(f"Error selecting build_plate: {e}", "error")
                return flask.jsonify(success=True)
            else:
                return flask.abort(400)

        elif command == "remove_build_plate":
            selected_build_plate_id = data.get("buildPlateId")
            if selected_build_plate_id is not None:
                try:
                    self.build_plate.remove_build_plate_from_database(selected_build_plate_id)
                except Exception as e:
                    self.send_alert(f"Error removing build_plate from the database: {e}", "error")
                return flask.jsonify(success=True)
            else:
                return flask.abort(400)

        elif command == "get_build_plate":
            selected_build_plate_id = data.get("buildPlateId")
            if selected_build_plate_id is not None:
                try:
                    current_build_plate = self.build_plate.get_build_plate_name_by_id(selected_build_plate_id)
                    current_build_plate_filaments = str(self.build_plate.get_build_plate_filaments_by_id(
                        selected_build_plate_id))
                    return flask.jsonify(name=current_build_plate, filaments=current_build_plate_filaments)
                except Exception as e:
                    self.send_alert(f"Error retrieving build_plate from the database: {e}", "tmp_error")
                    return flask.abort(502)
            else:
                return flask.abort(400)

        return flask.abort(400)

    def send_alert(self, message, alert_type="popup"):
        self._plugin_manager.send_plugin_message(self._identifier, dict(type=alert_type, msg=message))

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

    def check_print(self, file_path):
        self._logger.setLevel(logging.INFO)
        nozzle_passed = True
        filament_passed = True
        build_plate_passed = True
        # Retrieve the loaded filament alert_type from spool manager
        self._logger.info("Checking print for nozzle and filament settings...")
        try:
            loaded_filament = self.get_loaded_filament()
        except Exception as e:
            self.send_alert(f"Error retrieving loaded filament: {e}", "error")
            return
        # Parse the GCODE file to extract the nozzle size and filament alert_type
        gcode_info = self.parse_gcode(file_path)

        # Check if the loaded filament matches the filament alert_type in the GCODE
        if gcode_info["filament_type"] is None:
            self.send_alert("No filament alert_type found in GCODE, error checking won't be performed", "info")
            filament_passed = False

        elif loaded_filament is None:
            self.send_alert("No filament loaded, error checking won't be performed", "info")
            filament_passed = False

        elif loaded_filament == -1:
            self.send_alert("Spool Manager plugin is not installed. Filament alert_type will not be checked.", "info")
            filament_passed = False

        elif loaded_filament == -2:
            self.send_alert("Error retrieving loaded filament, filament error checking won't be performed", "info")
            filament_passed = False

        if (gcode_info["filament_type"].lower() != str(loaded_filament).lower() and gcode_info["filament_type"] is not
                None and filament_passed is not False):
            self._logger.error("Print aborted: Incorrect filament alert_type")
            self.send_alert("Print aborted: Incorrect filament type", "error")
            self._printer.cancel_print()
            return

        # Check if the loaded nozzle size matches the nozzle size in the GCODE
        if gcode_info["nozzle_size"] is None:
            self.send_alert("No nozzle size found in GCODE, error checking won't be performed", "info")
            nozzle_passed = False

        elif self.nozzle.get_current_nozzle_size() is None:
            self.send_alert("No nozzle selected, error checking won't be performed", "info")
            nozzle_passed = False

        if (float(gcode_info["nozzle_size"]) != float(self.nozzle.get_current_nozzle_size()) and gcode_info[
            "nozzle_size"] is
                not None and nozzle_passed is not False):
            self._logger.error("Print aborted: Incorrect nozzle size")
            self.send_alert("Print aborted: Incorrect nozzle size", "error")
            self._printer.cancel_print()
            return

        # Check if the build plate is compatible with the loaded filament
        if gcode_info["filament_type"] is not None:
            if not self.build_plate.is_filament_compatible_with_build_plate(gcode_info["filament_type"]):
                self._logger.error("Print aborted: Incompatible build plate")
                self.send_alert("Print aborted: Incompatible build plate", "error")
                self._printer.cancel_print()
                return

        if nozzle_passed and filament_passed and build_plate_passed:
            self.send_alert("Print passed nozzle and filament check", "success")
            self._logger.info("Print passed nozzle and filament check...")

    def initialize(self):
        conn = get_db(self.get_plugin_data_folder())

        smplugin = self._plugin_manager.plugins.get("SpoolManager").implementation
        self._spool_manager = SpoolManagerIntegration(smplugin, self._logger)
        init_db(self.get_plugin_data_folder())

        self.nozzle = nozzle.nozzle(self.get_plugin_data_folder(), self._logger)
        self.build_plate = build_plate.build_plate(self.get_plugin_data_folder(), self._logger)

        # Retry inserting a row into current_selections with a maximum of 3 attempts
        def check_and_insert_to_db(column: str):
            try:
                retry = 0
                index = conn.cursor()

                # Check if the column already exists in the table schema
                index.execute("SELECT COUNT(*) FROM pragma_table_info('current_selections') WHERE name = ?",
                              (column,))
                exists = index.fetchone()[0]

                if not exists:
                    while retry < 3:
                        try:
                            index.execute("INSERT INTO current_selections (id, selection) VALUES (?, ?)",
                                          (column, 1))
                            conn.commit()
                            break
                        except sqlite3.OperationalError as error:
                            self._logger.warning(f"Database operation failed: {error}")
                            self._logger.warning("Retrying...")
                            retry += 1
                            time.sleep(1)  # Wait for 1 second before retrying

                    if retry == 3:
                        self._logger.error(
                            "Failed to insert row into current_selections after multiple attempts. Plugin "
                            "initialization may be incomplete.")
            except Exception as error:
                self._logger.error(f"Error adding nozzle to the database: {error}")

        def add_row_to_db(column: str, insert_function: callable, params: tuple):
            try:
                retries = 0
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM ?", (column,))
                count = cursor.fetchone()[0]
                if count == 0:
                    while retries < 3:
                        try:
                            insert_function(*params)
                            break
                        except sqlite3.OperationalError as e:
                            self._logger.warning(f"Database operation failed: {e}")
                            self._logger.warning("Retrying...")
                            retries += 1
                            time.sleep(1)  # Wait for 1 second before retrying

                    if retries == 3:
                        self._logger.error(
                            "Failed to insert row into current_selections after multiple attempts. Plugin "
                            "initialization "
                            "may "
                            "be incomplete.")
            except Exception as e:
                self._logger.error(f"Error adding nozzle to the database: {e}")

        # Check if the nozzle and build plate columns exist in the current_selections table
        check_and_insert_to_db("nozzle")
        check_and_insert_to_db("build_plate")
        # Add default nozzle and build plate to the database
        add_row_to_db("nozzles", self.nozzle.add_nozzle_to_database, (0.4,))
        add_row_to_db("build_plates", self.build_plate.insert_build_plate_to_database,
                      ("Generic", "PLA, PETG, ABS", "1"))
        conn.close()

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
            "js": ["js/Nozzle_Filament_Validator.js", "js/nozzles.js", "js/build_plate.js", "js/filament.js"],
            "css": ["css/Nozzle_Filament_Validator.css"],
        }

    def get_loaded_filament(self):
        try:
            if self._spool_manager is None:
                self._logger.warning("Spool Manager plugin is not installed. Filament alert_type will not be checked.")
                return -1

            materials = self._spool_manager.get_materials()

            if not materials:
                self._logger.warning("No filament selected in Spool Manager. Filament alert_type will not be checked.")
                return None

            # Assuming the first loaded filament is the currently used one
            loaded_filament = materials[0]
            return loaded_filament.split("_")[0] if loaded_filament is not None else None
        except Exception as e:
            self._logger.error(f"Error retrieving loaded filament: {e}")
            return -2

    def parse_gcode(self, file_path):
        # Regular expression patterns to extract nozzle diameter and filament alert_type
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

            # Extract nozzle diameter and filament alert_type from the collected lines
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
                "displayName": "Nozzle Filament Validator Plugin",
                "displayVersion": self._plugin_version,

                # version check: github repository
                "alert_type": "github_release",
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
