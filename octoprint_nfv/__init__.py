# coding=utf-8
from __future__ import absolute_import

import sqlite3
import time

import flask
import octoprint.plugin
from flask_login import current_user
from octoprint.events import Events
from octoprint.filemanager import FileDestinations

import octoprint_nfv.build_plate as build_plate
import octoprint_nfv.extruders as extruders
import octoprint_nfv.nozzle as nozzle
import octoprint_nfv.validate as validate
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
        self.extruders = None
        self.validator = None

    def get_api_commands(self):
        return dict(
            addNozzle=["size"],
            removeNozzle=["nozzleId"],
            add_build_plate=["name", "compatibleFilaments", "id"],
            select_build_plate=["buildPlateId"],
            remove_build_plate=["buildPlateId"],
            get_build_plate=["buildPlateId"],
            update_extruder=["extruderPosition", "nozzleId"],
            get_extruder_info=["extruderId"],
            get_loaded_filaments=[]
        )

    def on_api_get(self, request):
        nozzles = self.nozzle.fetch_nozzles_from_database()
        number_of_extruders = self.extruders.get_number_of_extruders()
        build_plates = self.build_plate.fetch_build_plates_from_database()
        current_build_plate = self.build_plate.get_current_build_plate_name()
        current_build_plate_filaments = self.build_plate.get_current_build_plate_filaments()
        filaments = build_plate.get_filament_types()
        is_multi_extruder = str(self.extruders.is_multi_tool_head())

        return flask.jsonify(nozzles=nozzles, number_of_extruders=number_of_extruders,
                             build_plates=build_plates, currentBuildPlate=current_build_plate,
                             currentBuildPlateFilaments=current_build_plate_filaments, filaments=filaments,
                             isMultiExtruder=is_multi_extruder)

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

        elif command == "removeNozzle":
            nozzle_Size = data.get("nozzleId")
            if nozzle_Size is not None:
                try:
                    self.nozzle.remove_nozzle_from_database(nozzle_Size)
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

        elif command == "add_extruder":
            nozzle_Size = data.get("nozzleId")
            extruder_position = data.get("extruderPosition")
            if nozzle_Size is not None and extruder_position is not None:
                try:
                    self.extruders.add_extruder_to_database(nozzle_Size, extruder_position)
                except Exception as e:
                    self.send_alert(f"Error adding extruder to the database: {e}", "error")
                return flask.jsonify(success=True)
            else:
                return flask.abort(400)

        elif command == "update_extruder":
            extruder_position = data.get("extruderPosition")
            nozzle_id = data.get("nozzleId")
            # extruder_id = data.get("extruderID")
            if extruder_position is not None and nozzle_id is not None:
                try:
                    self.extruders.update_extruder(extruder_position=extruder_position, nozzle_id=nozzle_id)
                except Exception as e:
                    self.send_alert(f"Error updating extruder: {e}", "error")
                return flask.jsonify(success=True)
            else:
                return flask.abort(400)
        elif command == "remove_extruder":
            extruder_id = data.get("extruderId")
            if extruder_id is not None:
                try:
                    self.extruders.remove_extruder_from_database(extruder_position=extruder_id)
                except Exception as e:
                    self.send_alert(f"Error removing extruder from the database: {e}", "error")
                return flask.jsonify(success=True)
            else:
                return flask.abort(400)
        elif command == "get_extruder_info":
            extruder_id = data.get("extruderId")
            if extruder_id is not None:
                try:
                    nozzle_size = self.extruders.get_nozzle_size_for_extruder(extruder_id)
                    self._logger.info(f"nozzle_size: {nozzle_size}")
                    extruder_position = extruder_id
                    self._logger.info(f"extruder_position: {extruder_position}")
                    try:
                        filament = self._spool_manager.get_loaded_filaments()[extruder_position - 1]
                    except Exception:
                        filament = None
                    self._logger.info(f"filament: {filament}")
                    return flask.jsonify(nozzleSize=nozzle_size, extruderPosition=extruder_position,
                                         filamentType=filament)
                except Exception as e:
                    self.send_alert(f"Error retrieving extruder info: {e}", "tmp_error")
                    return flask.abort(500)
        elif command == "get_loaded_filaments":
            try:
                filaments = str(self._spool_manager.get_loaded_filaments()).replace("[", "").replace("]", "")
                return flask.jsonify(filaments=filaments)
            except Exception as e:
                self.send_alert(f"Error retrieving filament info: {e}", "tmp_error")
                return flask.abort(500)
        elif command == "set_multiple_tool_heads":
            value = data.get("value")
            if value is not None:
                try:
                    self.extruders.set_multiple_tool_heads(value.lower() == "true")
                    return flask.jsonify()
                except Exception as e:
                    self.send_alert(f"Error setting multiple tool heads: {e}", "error")
                    return flask.abort(500)

        return flask.abort(400)

    def send_alert(self, message, alert_type="popup"):
        self._plugin_manager.send_plugin_message(self._identifier, dict(type=alert_type, msg=message))

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

    def initialize(self):
        conn = get_db(self.get_plugin_data_folder())

        smplugin = self._plugin_manager.plugins.get("SpoolManager").implementation
        self._spool_manager = SpoolManagerIntegration(smplugin, self._logger)
        init_db(self.get_plugin_data_folder())

        self.nozzle = nozzle.nozzle(self.get_plugin_data_folder(), self._logger)
        self.build_plate = build_plate.build_plate(self.get_plugin_data_folder(), self._logger)
        self.extruders = extruders.extruders(self.nozzle, self.get_plugin_data_folder(), self._logger,
                                             self._printer_profile_manager)
        self.validator = validate.validator(self.nozzle, self.build_plate, self.extruders, self._spool_manager,
                                            self._printer, self._logger, self._plugin_manager, self._identifier,
                                            self._printer_profile_manager)

        # Retry inserting a row into current_selections with a maximum of 3 attempts
        def check_and_insert_to_db(column: str, value: any = 1):
            try:
                retry = 0
                index = conn.cursor()

                # Check if the table already exists in the table schema
                index.execute("SELECT COUNT(*) FROM current_selections WHERE id = ?",
                              (str(column),))
                exists = index.fetchone()[0]

                if not exists:
                    while retry < 3:
                        try:
                            index.execute("INSERT INTO current_selections (id, selection) VALUES (?, ?)",
                                          (column, value))
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

        def add_row_to_db(table: str, insert_function: callable, params: tuple):
            try:
                retries = 0
                cursor = conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                if int(count) == 0:
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
                self._logger.error(f"Error adding to the database: {e}")

        # Check if the nozzle and build plate columns exist in the current_selections table
        check_and_insert_to_db("build_plate")
        # Add default nozzle and build plate to the database
        add_row_to_db("nozzles", self.nozzle.add_nozzle_to_database, (0.4,))
        add_row_to_db("build_plates", self.build_plate.insert_build_plate_to_database,
                      ("Generic", "PLA, PETG, ABS", "1"))

        add_row_to_db("extruders", self.extruders.add_extruder_to_database, (1, 1))

        self.extruders.update_data()
        conn.close()

    def on_event(self, event, payload,):
        if event == Events.PRINT_STARTED:
            with self._printer.job_on_hold(blocking=True):
                self._logger.info("detected print_start_event")
                selected_file = payload.get("file", "")
                if not selected_file:
                    path = payload.get("path", "")
                    if payload.get("origin") == "local":
                        # Get full path to local file
                        path = self._file_manager.path_on_disk(FileDestinations.LOCAL, path)
                    selected_file = path

                self.validator.check_print(selected_file)

        if "PrinterProfile" in event or event == Events.CONNECTED:
            self.extruders.update_data()
            self.send_alert("", "reload")

    # ~~ TemplatePlugin mixin

    def get_template_configs(self):
        return [
            dict(type="settings", template="nozzle_filament_validator_page.jinja2", custom_bindings=False)  # Custom
            # page
        ]

    # ~~ AssetPlugin mixin

    def get_assets(self):
        return {
            "js": ["js/Nozzle_Filament_Validator.js", "js/nozzles.js", "js/build_plate.js", "js/filament.js",
                   "js/extruders.js"],
            "css": ["css/Nozzle_Filament_Validator.css"],
        }

    def on_after_startup(self):
        self._logger.info("NozzleFilamentValidatorPlugin initialized")

    # ~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        return {
            # put your plugin's default settings here
        }

    # ~~ Softwareupdate hook

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
