# coding=utf-8
from __future__ import absolute_import, annotations

import hashlib
import json
import os
import threading
from typing import Dict, List

import flask
import octoprint.plugin
from flask_login import current_user
from octoprint.events import Events
from octoprint.filemanager import FileDestinations, valid_file_type

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
        self._validation_lock = threading.RLock()
        self._validation_result = None
        self._validation_path = None
        self._validation_cache = {}
        self._validation_jobs = set()
        self._validation_jobs_lock = threading.Lock()

    def get_api_commands(self):
        """
        Get the API commands for the plugin
        :return: the API commands
        """
        if current_user.is_anonymous:
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
            update_check_spool_id_timeout=["timeout"],
            update_check_spool_id=["checkSpoolId"],
            update_filament_type_checking=["enabled"],
            update_validate_on_upload=["enabled"],
            validate_file=["path", "origin"],
            update_manual_filament=["extruderPosition", "filamentType"],
            add_extruder=["nozzleId", "extruderPosition"],
            remove_extruder=["extruderId"],
            set_multiple_tool_heads=["value"],
        )

    def on_api_get(self, request: flask.Request) -> flask.Response:
        """
        Handle the API get requests
        :param request: the request to handle
        """
        if current_user.is_anonymous:
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
        check_filament_type = str(self.filament.get_enable_filament_type_checking())
        spool_manager_available = self._spool_manager.is_available()
        filament_source = self._spool_manager.get_source_name()
        active_prompt = self.validator.get_active_prompt()
        validate_on_upload = self._settings.get_boolean(["validate_on_upload"])
        return flask.jsonify(nozzles=nozzles, number_of_extruders=number_of_extruders,
                             build_plates=build_plates, currentBuildPlate=current_build_plate,
                             currentBuildPlateFilaments=current_build_plate_filaments, filaments=filaments,
                             isMultiExtruder=is_multi_extruder, check_spool_id=check_ids,
                             check_spool_id_timeout=check_spool_id_timeout,
                             check_filament_type=check_filament_type,
                             spool_manager_available=spool_manager_available,
                             filament_source=filament_source,
                             validate_on_upload=validate_on_upload,
                             active_prompt=active_prompt)

    def on_api_command(self, command: str, data: Dict) -> flask.response:
        """
        Handle the API commands from the frontend
        :param command: the command to handle
        :param data: the data to handle
        :return:
        """
        if current_user.is_anonymous:
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
            db_position = data.get("id") if data.get("id") not in (None, "") else "null"
            if name is not None and compatible_filaments is not None:
                try:
                    self.build_plate.insert_build_plate_to_database(name, compatible_filaments, db_position)
                except Exception as e:
                    self.send_alert(f"Error adding build plate: {e}", alert_types.tmp_error)
                    return flask.abort(409)
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
                    spool_names = self._spool_manager.get_names() or []
                    spool_name = spool_names[extruder_position - 1] if extruder_position <= len(spool_names) else None
                    return flask.jsonify(nozzleSize=nozzle_size, extruderPosition=extruder_position,
                                         filamentType=filaments,
                                         spoolName=spool_name)
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

        elif command in ("update_filament_timeout", "update_check_spool_id_timeout"):
            data = data.get("timeout")
            if data is not None:
                timeout = int(data)
                if timeout < 0:
                    return flask.abort(400)
                self.filament.update_timeout(timeout)
                return flask.jsonify(success=True)
            flask.abort(400)

        elif command == "update_check_spool_id":
            data = data.get("checkSpoolId")
            if data is not None:
                enabled = data if isinstance(data, bool) else str(data).lower() in ("1", "true", "yes", "on")
                if enabled and not self._spool_manager.is_available():
                    self.send_alert("Install SpoolManager, Spoolman, or RME Compatibility to validate "
                                    "filament/spool names.",
                                    alert_types.error)
                    return flask.abort(409)
                self.filament.update_enable_spool_checking(enabled)
                return flask.jsonify(success=True)
            flask.abort(400)
        elif command == "update_filament_type_checking":
            value = data.get("enabled")
            if value is not None:
                enabled = value if isinstance(value, bool) else str(value).lower() in ("1", "true", "yes", "on")
                self.filament.update_enable_filament_type_checking(enabled)
                return flask.jsonify(success=True)
            flask.abort(400)
        elif command == "update_validate_on_upload":
            value = data.get("enabled")
            if value is not None:
                enabled = value if isinstance(value, bool) else str(value).lower() in ("1", "true", "yes", "on")
                self._settings.set_boolean(["validate_on_upload"], enabled)
                self._settings.save()
                return flask.jsonify(success=True)
            flask.abort(400)
        elif command == "validate_file":
            path = data.get("path")
            origin = data.get("origin")
            if not path or origin != FileDestinations.LOCAL:
                return flask.abort(400)
            try:
                disk_path = self._file_manager.path_on_disk(FileDestinations.LOCAL, path)
            except Exception:
                self._logger.exception("Could not resolve requested GCODE path %r", path)
                return flask.abort(404)
            if not os.path.isfile(disk_path):
                return flask.abort(404)
            started = self._start_file_validation(disk_path, path, "manual")
            return flask.jsonify(success=True, started=started)
        elif command == "update_manual_filament":
            if self._spool_manager.is_available():
                return flask.abort(409)
            extruder_position = data.get("extruderPosition")
            filament_type = data.get("filamentType")
            if extruder_position is None or filament_type not in build_plate.get_filament_types():
                return flask.abort(400)
            try:
                extruder_position = int(extruder_position)
            except (TypeError, ValueError):
                return flask.abort(400)
            if extruder_position < 1 or extruder_position > self.extruders.get_number_of_extruders():
                return flask.abort(400)
            self.filament.update_manual_filament(extruder_position, filament_type)
            self.send_alert(f"Extruder {extruder_position} filament set to {filament_type}.", alert_types.success)
            return flask.jsonify(success=True)
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

        self.nozzle = nozzle.nozzle(self.get_plugin_data_folder(), self._logger)
        self.build_plate = build_plate.build_plate(self.get_plugin_data_folder(), self._logger)
        self.extruders = extruders.extruders(self.nozzle, self.get_plugin_data_folder(), self._logger,
                                             self._printer_profile_manager)
        self.filament = filament(self.get_plugin_data_folder(), self._logger)

        spool_manager_info = self._plugin_manager.plugins.get("SpoolManager")
        spool_manager_plugin = spool_manager_info.implementation if spool_manager_info is not None else None
        spoolman_info = self._plugin_manager.plugins.get("Spoolman")
        spoolman_plugin = spoolman_info.implementation if spoolman_info is not None else None
        rme_info = self._plugin_manager.plugins.get("rme_compatibility")
        rme_plugin = rme_info.implementation if rme_info is not None else None
        self._spool_manager = SpoolManagerIntegration(
            spool_manager_plugin, self._logger,
            lambda: self.filament.get_manual_filaments(self.extruders.get_number_of_extruders()),
            spoolman_impl=spoolman_plugin,
            rme_compatibility_impl=rme_plugin)

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
                         self.filament.initial_db_add, (False, 300, True), 3)

        self.extruders.update_data()
        conn.close()

    def on_event(self, event, payload) -> None:
        """
        Handle octoprint events
        :param event: the event to handle
        :param payload: the payload of the event
        """
        if event in (Events.PRINT_CANCELLED, Events.PRINT_DONE, Events.PRINT_FAILED):
            with self._validation_lock:
                self._validation_result = None
                self._validation_path = None

        if event == getattr(Events, "UPLOAD", "Upload"):
            if (self._settings.get_boolean(["validate_on_upload"])
                    and payload.get("target") == FileDestinations.LOCAL
                    and payload.get("path")
                    and valid_file_type(payload["path"], type="machinecode")):
                storage_path = payload["path"]
                try:
                    disk_path = self._file_manager.path_on_disk(FileDestinations.LOCAL, storage_path)
                except Exception:
                    self._logger.exception("Could not resolve uploaded GCODE path %r", storage_path)
                else:
                    self._start_file_validation(disk_path, storage_path, "upload")

        if event == getattr(Events, "FILE_REMOVED", "FileRemoved"):
            if payload.get("storage") == FileDestinations.LOCAL and payload.get("path"):
                try:
                    disk_path = self._file_manager.path_on_disk(FileDestinations.LOCAL, payload["path"])
                except Exception:
                    disk_path = None
                if disk_path:
                    self._validation_cache.pop(os.path.realpath(disk_path), None)

        if "PrinterProfile" in event or event == Events.CONNECTED:
            self.extruders.update_data()
            self.send_alert("", "reload")

    def set_tool_mapping(self, mapping: Dict[int, int]) -> None:
        """Receive RME's confirmed mapping before preflight validation runs."""
        if self.validator is None:
            raise RuntimeError("Nozzle Filament Validator is not initialized")
        with self._validation_lock:
            self.validator.set_tool_mapping(mapping)
            # The same path must be revalidated if its physical assignment
            # changes between print attempts.
            self._validation_result = None

    @staticmethod
    def _stable_value(value):
        """Convert integration values into deterministic JSON-compatible data."""
        if isinstance(value, dict):
            return {str(key): Nozzle_filament_validatorPlugin._stable_value(item)
                    for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
        if isinstance(value, (list, tuple)):
            return [Nozzle_filament_validatorPlugin._stable_value(item) for item in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return repr(value)

    def _validation_config_hash(self) -> str:
        """Hash every live input that can affect ``validator.check_print``."""
        profile = self._printer_profile_manager.get_current_or_default()
        extruder_count = self.extruders.get_number_of_extruders()
        config = {
            "printer_profile": profile,
            "build_plate": {
                "id": self.build_plate.get_current_build_plate_id(),
                "name": self.build_plate.get_current_build_plate_name(),
                "filaments": self.build_plate.get_current_build_plate_filaments(),
            },
            "nozzles": [self.extruders.get_nozzle_size_for_extruder(position)
                        for position in range(1, extruder_count + 1)],
            "loaded_filaments": self._spool_manager.get_loaded_filaments(),
            "spool_names": self._spool_manager.get_names(),
            "check_spool_names": self.filament.get_enable_spool_checking(),
            "check_filament_types": self.filament.get_enable_filament_type_checking(),
            "validation_timeout": self.filament.get_timeout(),
            "tool_mapping": getattr(self.validator, "_tool_mapping", {}),
        }
        serialized = json.dumps(self._stable_value(config), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _file_signature(path: str) -> Dict[str, int]:
        stat = os.stat(path)
        return {
            "size": stat.st_size,
            "mtime_ns": getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000)),
            "ctime_ns": getattr(stat, "st_ctime_ns", int(stat.st_ctime * 1_000_000_000)),
        }

    def _storage_path_for_disk_path(self, disk_path: str):
        try:
            return self._file_manager.path_in_storage(FileDestinations.LOCAL, disk_path)
        except Exception:
            return None

    def _write_validation_cache(self, disk_path: str, storage_path: str,
                                file_signature: Dict[str, int], config_hash: str) -> None:
        record = {"version": 1, "file": file_signature, "config": config_hash}
        normalized_path = os.path.realpath(disk_path)
        self._validation_cache[normalized_path] = record
        storage_path = storage_path or self._storage_path_for_disk_path(disk_path)
        if storage_path:
            try:
                self._file_manager.set_additional_metadata(
                    FileDestinations.LOCAL, storage_path, "nozzle_filament_validator",
                    record, overwrite=True)
            except Exception:
                self._logger.warning("Could not persist validation metadata for %s", storage_path, exc_info=True)

    def _read_validation_cache(self, disk_path: str, storage_path: str = None):
        normalized_path = os.path.realpath(disk_path)
        record = self._validation_cache.get(normalized_path)
        if record is not None:
            return record
        storage_path = storage_path or self._storage_path_for_disk_path(disk_path)
        if not storage_path:
            return None
        try:
            record = self._file_manager.get_additional_metadata(
                FileDestinations.LOCAL, storage_path, "nozzle_filament_validator")
        except Exception:
            self._logger.debug("Could not read validation metadata for %s", storage_path, exc_info=True)
            return None
        if isinstance(record, dict):
            self._validation_cache[normalized_path] = record
            return record
        return None

    def _remove_validation_cache(self, disk_path: str, storage_path: str = None) -> None:
        self._validation_cache.pop(os.path.realpath(disk_path), None)
        storage_path = storage_path or self._storage_path_for_disk_path(disk_path)
        if storage_path:
            try:
                self._file_manager.remove_additional_metadata(
                    FileDestinations.LOCAL, storage_path, "nozzle_filament_validator")
            except Exception:
                self._logger.debug("Could not remove validation metadata for %s", storage_path, exc_info=True)

    def _cached_validation_matches(self, disk_path: str, storage_path: str = None) -> bool:
        try:
            record = self._read_validation_cache(disk_path, storage_path)
            matches = bool(record and record.get("version") == 1
                           and record.get("file") == self._file_signature(disk_path)
                           and record.get("config") == self._validation_config_hash())
            if record and not matches:
                self._remove_validation_cache(disk_path, storage_path)
            return matches
        except Exception:
            self._logger.debug("Could not verify cached validation for %s", disk_path, exc_info=True)
            return False

    def _validate_and_cache(self, disk_path: str, storage_path: str = None) -> bool:
        """Validate once and cache only an unchanged file/configuration pass."""
        # An explicit new check supersedes any older pass, even when this one
        # is cancelled or fails before it can write a replacement.
        self._remove_validation_cache(disk_path, storage_path)
        try:
            initial_file = self._file_signature(disk_path)
            initial_config = self._validation_config_hash()
        except Exception:
            self._logger.warning("Could not snapshot validation inputs for %s; result will not be cached",
                                 disk_path, exc_info=True)
            return bool(self.validator.check_print(disk_path))

        result = bool(self.validator.check_print(disk_path))
        if not result:
            return False
        if not getattr(self.validator, "last_check_cacheable", True):
            self._logger.info("Validation was explicitly overridden; allowing this request without caching it")
            return True

        try:
            final_file = self._file_signature(disk_path)
            final_config = self._validation_config_hash()
        except Exception:
            self._logger.warning("Could not verify validation inputs for %s; result will not be cached",
                                 disk_path, exc_info=True)
            return True

        if initial_file != final_file or initial_config != final_config:
            self.send_alert("The file or printer configuration changed during validation; please validate again.",
                            alert_types.error)
            return False

        self._write_validation_cache(disk_path, storage_path, final_file, final_config)
        return True

    def _start_file_validation(self, disk_path: str, storage_path: str, source: str) -> bool:
        """Start a deduplicated background validation requested by upload or UI."""
        normalized_path = os.path.realpath(disk_path)
        with self._validation_jobs_lock:
            if normalized_path in self._validation_jobs:
                return False
            self._validation_jobs.add(normalized_path)

        def run():
            try:
                with self._validation_lock:
                    self._logger.info("Validating %s GCODE %s", source, storage_path)
                    self._validate_and_cache(disk_path, storage_path)
            except Exception:
                self._logger.exception("Unexpected error during %s validation of %s", source, storage_path)
                self.send_alert("File validation failed because of an unexpected error.", alert_types.error)
            finally:
                with self._validation_jobs_lock:
                    self._validation_jobs.discard(normalized_path)

        thread = threading.Thread(target=run, name="nfv-file-validation", daemon=True)
        thread.start()
        return True

    def _get_selected_file_path(self, comm_instance=None):
        """Return the selected local job's absolute path, when available."""
        # During a select-and-print request the state monitor can still contain
        # the previously selected path. The comm layer is authoritative at the
        # point where it queues this job's first command.
        current_file = getattr(comm_instance, "_currentFile", None)
        is_sd_file_selected = getattr(comm_instance, "isSdFileSelected", None)
        is_sd_file = bool(is_sd_file_selected and is_sd_file_selected())
        if is_sd_file:
            return None
        if current_file is not None:
            filename = current_file.getFilename()
            if filename:
                return filename

        job = self._printer.get_current_job() or {}
        file_info = job.get("file") or {}
        path = file_info.get("path")
        origin = file_info.get("origin")
        if path and origin == FileDestinations.LOCAL:
            return self._file_manager.path_on_disk(FileDestinations.LOCAL, path)
        return None

    def validate_before_queuing(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        """Block the first job command until the selected GCODE has passed validation."""
        tags = kwargs.get("tags") or set()
        is_print_command = "source:job" in tags or "source:file" in tags
        is_cancellation_command = bool(
            {"trigger:cancel", "trigger:comm.cancel"} & tags
            or "script:afterPrintCancelled" in tags
        )
        if not is_print_command or is_cancellation_command:
            return None

        with self._validation_lock:
            try:
                path = self._get_selected_file_path(comm_instance)
            except Exception:
                self._logger.exception("Could not resolve the selected GCODE path")
                path = None

            if path != self._validation_path:
                self._validation_path = path
                self._validation_result = None

            if self._validation_result is None:
                try:
                    if path and self._cached_validation_matches(path):
                        self._logger.info("Using unchanged cached validation for selected GCODE")
                        self._validation_result = True
                    else:
                        self._logger.info("Validating selected GCODE before its first command is queued")
                        self._validation_result = self._validate_and_cache(path)
                except Exception:
                    self._logger.exception("Unexpected error during pre-print validation")
                    self.send_alert("Print blocked: an unexpected validation error occurred.", alert_types.error)
                    self._validation_result = False

            if not self._validation_result:
                # OctoPrint ignores cancellation while still in STARTING. The
                # hook therefore tries again when the first source:file command
                # arrives, after the state marker has changed it to PRINTING.
                is_cancelling = getattr(self._printer, "is_cancelling", lambda: False)
                if not is_cancelling():
                    self._printer.cancel_print()
                # A None command suppresses it in OctoPrint's GCODE phase hook.
                return (None,)

        return None

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
            "validate_on_upload": False,
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
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        # RME acquires its mapping hold in beforePrintStarted. This later hook
        # runs only after RME supplies the confirmed physical mapping and
        # releases the job queue.
        "octoprint.comm.protocol.gcode.queuing": (
            __plugin_implementation__.validate_before_queuing, 100
        ),
    }
