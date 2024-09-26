# coding=utf-8
from __future__ import absolute_import, annotations

from typing import Dict, List

import flask
import octoprint.plugin
from flask_login import current_user
from octoprint.events import Events
from octoprint.filemanager import FileDestinations

import octoprint_nfv.build_plate as build_plate
import octoprint_nfv.extruders as extruders
import octoprint_nfv.nozzle as nozzle
import octoprint_nfv.validate as validate
from octoprint_nfv.constants import alert_types
from octoprint_nfv.db import get_db, init_db
from octoprint_nfv.filament import filament
from octoprint_nfv.spoolManager import SpoolManagerIntegration


class Nozzle_filament_validatorPlugin(octoprint.plugin.StartupPlugin, octoprint.plugin.SettingsPlugin,
                                      octoprint.plugin.AssetPlugin,
                                      octoprint.plugin.TemplatePlugin,
                                      octoprint.plugin.SimpleApiPlugin,
                                      octoprint.plugin.EventHandlerPlugin
                                      ):
    """
    Class to handle the Nozzle Filament Validator plugin
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self._spool_manager: spoolManager = None
        self.nozzle: validate = None
        self.build_plate: build_plate = None
        self.extruders: extruders = None
        self.validator: validate = None
        self.filament: filament = None

    def get_api_commands(self):
        """
        Get the API commands for the plugin
        :return: the API commands
        """
        if current_user.is_anonymous():
            return flask.abort(403)

        return dict(
            addNozzle=["size"],
            removeNozzle=["nozzleId"],
            add_build_plate=["name", "compatibleFilaments", "id"],
            select_build_plate=["buildPlateId"],
            remove_build_plate=["buildPlateId"],
            get_build_plate=["buildPlateId"],
            update_extruder=["extruderPosition", "nozzleId"],
            get_extruder_info=["extruderId"],
            get_loaded_filaments=[],
            updateWaitState=["state"],
            update_filament_timeout=["timeout"],
            update_check_spool_id=["checkSpoolId"],
        )

    def on_api_get(self, request: flask.Request) -> flask.Response:
        """
        Handle the API get requests
        :param request: the request to handle
        """
        if current_user.is_anonymous():
            return flask.abort(403)

        nozzles = self.nozzle.fetch_nozzles_from_database()
        number_of_extruders = self.extruders.get_number_of_extruders()
        build_plates = self.build_plate.fetch_build_plates_from_database()
        current_build_plate = self.build_plate.get_current_build_plate_name()
        current_build_plate_filaments = self.build_plate.get_current_build_plate_filaments()
        filaments = build_plate.get_filament_types()
        is_multi_extruder = str(self.extruders.is_multi_tool_head())
        check_ids = str(self.filament.get_enable_spool_checking())
        check_spool_id_timeout = self.filament.get_timeout()
        return flask.jsonify(nozzles=nozzles, number_of_extruders=number_of_extruders,
                             build_plates=build_plates, currentBuildPlate=current_build_plate,
                             currentBuildPlateFilaments=current_build_plate_filaments, filaments=filaments,
                             isMultiExtruder=is_multi_extruder, check_spool_id=check_ids,
                             check_spool_id_timeout=check_spool_id_timeout)

    def on_api_command(self, command: str, data: Dict) -> flask.response:
        """
        Handle the API commands from the frontend
        :param command: the command to handle
        :param data: the data to handle
        :return:
        """
        if current_user.is_anonymous():
            return flask.abort(403)

        if command == "addNozzle":
            nozzle_size = data["size"]
            if nozzle_size is not None:
                try:
                    self.nozzle.add_nozzle_to_database(nozzle_size)
                except Exception as e:
                    self.send_alert(f"Error adding nozzle to the database: {e}", alert_types.error)
                return flask.jsonify(success=True)
            else:
                return flask.abort(400)

        elif command == "removeNozzle":
            nozzle_size = data.get("nozzleId")
            if nozzle_size is not None:
                try:
                    self.nozzle.remove_nozzle_from_database(nozzle_size)
                except Exception as e:
                    self.send_alert(f"Error removing nozzle from the database: {e}", alert_types.error)
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
                    self.send_alert(f"Error adding build plate: {e}", alert_types.tmp_error)
                return flask.jsonify(success=True)
            else:
                return flask.abort(400)

        elif command == "select_build_plate":
            selected_build_plate_id = data.get("buildPlateId")
            if selected_build_plate_id is not None:
                try:
                    self.build_plate.select_current_build_plate(selected_build_plate_id)
                except Exception as e:
                    self.send_alert(f"Error selecting build_plate: {e}", alert_types.error)
                return flask.jsonify(success=True)
            else:
                return flask.abort(400)

        elif command == "remove_build_plate":
            selected_build_plate_id = data.get("buildPlateId")
            if selected_build_plate_id is not None:
                try:
                    self.build_plate.remove_build_plate_from_database(selected_build_plate_id)
                except Exception as e:
                    self.send_alert(f"Error removing build_plate from the database: {e}", alert_types.error)
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
                    self.send_alert(f"Error retrieving build_plate from the database: {e}", alert_types.tmp_error)
                    return flask.abort(502)
            else:
                return flask.abort(400)

        elif command == "add_extruder":
            nozzle_size = data.get("nozzleId")
            extruder_position = data.get("extruderPosition")
            if nozzle_size is not None and extruder_position is not None:
                try:
                    self.extruders.add_extruder_to_database(nozzle_size, extruder_position)
                except Exception as e:
                    self.send_alert(f"Error adding extruder to the database: {e}", alert_types.error)
                return flask.jsonify(success=True)
            else:
                return flask.abort(400)

        elif command == "update_extruder":
            extruder_position = data.get("extruderPosition")
            nozzle_id = data.get("nozzleId")
            # extruder_position = data.get("extruderID")
            if extruder_position is not None and nozzle_id is not None:
                try:
                    self.extruders.update_extruder(extruder_position=extruder_position, nozzle_id=nozzle_id)
                except Exception as e:
                    self.send_alert(f"Error updating extruder: {e}", alert_types.error)
                return flask.jsonify(success=True)
            else:
                return flask.abort(400)

        elif command == "remove_extruder":
            extruder_id = data.get("extruderId")
            if extruder_id is not None:
                try:
                    self.extruders.remove_extruder_from_database(extruder_position=extruder_id)
                    return flask.jsonify(success=True)
                except Exception as e:
                    self.send_alert(f"Error removing extruder from the database: {e}", alert_types.error)

            return flask.abort(400)

        elif command == "get_extruder_info":
            extruder_id = data.get("extruderId")
            if extruder_id is not None:
                try:
                    nozzle_size = self.extruders.get_nozzle_size_for_extruder(extruder_id)
                    extruder_position = extruder_id
                    try:
                        filaments = self._spool_manager.get_loaded_filaments()[extruder_position - 1]
                    except Exception as e:
                        self._logger.error(f"Error retrieving filament info: {e}")
                        filaments = None
                    return flask.jsonify(nozzleSize=nozzle_size, extruderPosition=extruder_position,
                                         filamentType=filaments,
                                         spoolName=self._spool_manager.get_names()[extruder_position - 1])
                except Exception as e:
                    self.send_alert(f"Error retrieving extruder info: {e}", alert_types.tmp_error)
                    return flask.abort(500)

        elif command == "get_loaded_filaments":
            try:
                filaments = str(self._spool_manager.get_loaded_filaments()).replace("[", "").replace("]", "")
                self._spool_manager.get_names()
                return flask.jsonify(filaments=filaments)
            except Exception as e:
                self.send_alert(f"Error retrieving filament info: {e}", alert_types.tmp_error)
                return flask.abort(500)

        elif command == "set_multiple_tool_heads":
            value = data.get("value")
            if value is not None:
                try:
                    self.extruders.set_multiple_tool_heads(value.lower() == "true")
                    return flask.jsonify()
                except Exception as e:
                    self.send_alert(f"Error setting multiple tool heads: {e}", alert_types.error)
                return flask.abort(500)

        elif command == "updateWaitState":
            data = data.get("state")
            if data is not None:
                self.validator.update_filament_wait_status(data)
                return flask.jsonify(success=True)
            flask.abort(400)

        elif command == "update_filament_timeout":
            data = data.get("timeout")
            if data is not None:
                self.filament.update_timeout(int(data))
                return flask.jsonify(success=True)
            flask.abort(400)

        elif command == "update_check_spool_id":
            data = data.get("checkSpoolId")
            if data is not None:
                self.filament.update_enable_spool_checking(bool(data))
                return flask.jsonify(success=True)
            flask.abort(400)
        return flask.abort(400)

    def send_alert(self, message: str, alert_type: str = alert_types.popup) -> None:
        """
        Send an alert to the frontend
        :param message: the message to send
        :param alert_type: what type of alert to send
        """
        self._plugin_manager.send_plugin_message(self._identifier, dict(type=alert_type, msg=message))

    def on_settings_save(self, data) -> None:
        """
        Save the settings
        :param data: the data to save
        """
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

    def initialize(self) -> None:
        """
        Initialize the plugin
        """

        init_db(self.get_plugin_data_folder())

        conn = get_db(self.get_plugin_data_folder())

        spool_manager_plugin = self._plugin_manager.plugins.get("SpoolManager").implementation
        self._spool_manager = SpoolManagerIntegration(spool_manager_plugin, self._logger)

        self.nozzle = nozzle.nozzle(self.get_plugin_data_folder(), self._logger)
        self.build_plate = build_plate.build_plate(self.get_plugin_data_folder(), self._logger)
        self.extruders = extruders.extruders(self.nozzle, self.get_plugin_data_folder(), self._logger,
                                             self._printer_profile_manager)
        self.filament = filament(self.get_plugin_data_folder(), self._logger)

        self.validator = validate.validator(self.nozzle, self.build_plate, self.extruders, self._spool_manager,
                                            self.filament,
                                            self._printer, self._logger, self._plugin_manager, self._identifier,
                                            self._printer_profile_manager)

        # Check if the nozzle and build plate columns exist in the current_selections table
        db.check_and_insert_to_db(self.get_plugin_data_folder(), self._logger, "build_plate")

        # Add default nozzle and build plate to the database
        db.add_row_to_db(self.get_plugin_data_folder(), self._logger, "nozzles", self.nozzle.add_nozzle_to_database,
                         (0.4,))
        db.add_row_to_db(self.get_plugin_data_folder(), self._logger, "build_plates",
                         self.build_plate.insert_build_plate_to_database, ("Generic", "PLA, PETG, ABS", "1"))

        db.add_row_to_db(self.get_plugin_data_folder(), self._logger, "extruders",
                         self.extruders.add_extruder_to_database, (1, 1))
        db.add_row_to_db(self.get_plugin_data_folder(), self._logger, "filament_data",
                         self.filament.initial_db_add, (False, 300), 2)

        self.extruders.update_data()
        conn.close()

    def on_event(self, event, payload) -> None:
        """
        Handle octoprint events
        :param event: the event to handle
        :param payload: the payload of the event
        """
        if event == Events.PRINT_STARTED:
            with self._printer.job_on_hold(blocking=True):
                self._logger.info("detected print_start_event")
                selected_file = payload.get("file", "")
                if not selected_file:
                    path = payload.get("path", "")
                    if payload.get("origin") == "local":
                        # Get the full path to local file
                        path = self._file_manager.path_on_disk(FileDestinations.LOCAL, path)
                    selected_file = path

                self.validator.check_print(selected_file)

        if "PrinterProfile" in event or event == Events.CONNECTED:
            self.extruders.update_data()
            self.send_alert("", "reload")

    # ~~ TemplatePlugin mixin

    def get_template_configs(self) -> List[Dict[str, str | bool]]:
        """
        get the html templete for the plugin
        :return: the html template
        """
        return [
            dict(type="settings", template="nozzle_filament_validator_page.jinja2", custom_bindings=False)  # Custom
            # page
        ]

    # ~~ AssetPlugin mixin

    def get_assets(self) -> Dict[str, List[str]]:
        """
        returns the web assets for the plugin
        :return: the web assets
        """
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
        }

    # ~~ Software update hook

    def get_update_information(self):
        """
        Get the update information for the plugin so it can be auto updated by the software update plugin
        :return: the update information
        """

        return dict(
            Nozzle_Filament_Validator=dict(
                displayName="Nozzle Filament Validator",
                displayVersion=self._plugin_version,

                # version check: GitHub repository
                type="github_release",
                user="Rylan-Meilutis",
                repo="OctoPrint-Nozzle-Filament-Validator",
                current=self._plugin_version,
                stable_branch=dict(
                    name="Stable",
                    branch="main",
                    commitish=["main"]
                ),
                prerelease_branches=[
                    dict(
                        name="Release Candidate",
                        branch="rc",
                        commitish=["rc", "main"]
                    ),
                    dict(
                        name="Development",
                        branch="dev",
                        commitish=["dev", "rc", "main"]
                    )
                ],

                # update method: pip
                pip="https://github.com/Rylan-Meilutis/OctoPrint-Nozzle-Filament-Validator/archive/{"
                    "target_version}.zip"
            )
        )


# set the plugin's friendly name
__plugin_name__ = "Nozzle Filament Validator"

# specify the plugin's python compatibility
__plugin_pythoncompat__ = ">=3,<4"  # Only Python 3


def __plugin_load__() -> None:
    """
    Load the plugin
    """
    global __plugin_implementation__
    __plugin_implementation__ = Nozzle_filament_validatorPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
