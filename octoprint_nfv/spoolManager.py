import json
import logging
import threading
import time
from typing import Any, List, Dict, Union

from octoprint.server import app


class SpoolManagerException(Exception):
    pass


class SpoolManagerIntegration:
    def __init__(self, impl: Any, logger: logging.Logger, fallback_filaments=None,
                 spoolman_impl: Any = None, rme_compatibility_impl: Any = None) -> None:
        """
        Constructor
        :param impl: implementation of the Spool Manager
        :param logger: logger object
        """
        self._logger = logger
        self._impl = impl
        self._fallback_filaments = fallback_filaments
        self._spoolman_impl = spoolman_impl
        self._rme_compatibility_impl = rme_compatibility_impl
        self._spoolman_cache = None
        self._spoolman_cache_key = None
        self._spoolman_cache_time = 0.0
        self._spoolman_cache_lock = threading.Lock()

    def is_available(self) -> bool:
        return (self._impl is not None or self._spoolman_impl is not None
                or self._has_rme_provider())

    def _has_rme_provider(self) -> bool:
        return callable(getattr(self._rme_compatibility_impl, "_filament_report", None))

    def get_source_name(self) -> str:
        if self._impl is not None:
            return "spoolmanager"
        if self._spoolman_impl is not None:
            return "spoolman"
        if self._has_rme_provider():
            return "rme_compatibility"
        return "manual"

    def _get_rme_tools(self) -> List[Dict[str, Any]]:
        """Return RME Compatibility's provider-neutral per-tool loadout."""
        if self._rme_compatibility_impl is None:
            return []
        try:
            reporter = getattr(self._rme_compatibility_impl, "_filament_report", None)
            if not callable(reporter):
                self._logger.warning(
                    "Installed RME Compatibility plugin does not expose filament-report metadata.")
                return []
            report = reporter()
            if not isinstance(report, dict) or report.get("schema") != "rme-filament-report-v1":
                self._logger.warning("RME Compatibility returned an unsupported filament report.")
                return []
            tools = report.get("data", {}).get("tools", [])
            return [tool if isinstance(tool, dict) else {} for tool in tools]
        except Exception as error:
            self._logger.warning(
                "Skipping RME Compatibility assignment due to integration error: %s", error)
            return []

    @staticmethod
    def _rme_spool_identifier(tool: Dict[str, Any]) -> Union[str, None]:
        """Build a stable name-validation value for an inventory-backed RME tool."""
        spool_id = tool.get("spool_id")
        if spool_id in (None, ""):
            return None
        provider = str(tool.get("provider") or "internal").strip().lower().replace(" ", "-")
        return f"rme:{provider}:{spool_id}"

    def _get_spoolman_selected_spools(self) -> List[Union[Dict[str, Any], None]]:
        """Return Spoolman's selected spool object for each zero-based tool."""
        if self._spoolman_impl is None:
            return []
        try:
            selections = self._spoolman_impl._settings.get(["selectedSpoolIds"]) or {}
            normalized = {
                int(tool): str(data.get("spoolId"))
                for tool, data in selections.items()
                if data and data.get("spoolId") not in (None, "")
            }
            cache_key = tuple(sorted(normalized.items()))
            with self._spoolman_cache_lock:
                now = time.monotonic()
                if (self._spoolman_cache is not None and self._spoolman_cache_key == cache_key
                        and now - self._spoolman_cache_time < 1.0):
                    return list(self._spoolman_cache)

                result = self._spoolman_impl.getSpoolmanConnector().handleGetSpoolsAvailable()
                if result.get("error"):
                    self._logger.warning("Could not retrieve selected Spoolman spools: %s", result["error"])
                    return []
                available = result.get("data", {}).get("spools", [])
                by_id = {str(spool.get("id")): spool for spool in available if spool.get("id") is not None}
                selected = [None] * (max(normalized.keys()) + 1 if normalized else 0)
                for tool, spool_id in normalized.items():
                    selected[tool] = by_id.get(spool_id)

                self._spoolman_cache = list(selected)
                self._spoolman_cache_key = cache_key
                self._spoolman_cache_time = now
                return selected
        except Exception as error:
            self._logger.warning("Skipping Spoolman assignment due to integration error: %s", error)
            return []

    def get_materials(self) -> List[str]:
        """
        Get the materials from the Spool Manager
        :return:
        """
        try:
            if self._impl is None:
                return []
            materials = self._impl.api_getSelectedSpoolInformations()
            materials = [
                f"{m['material']}_{m['colorName']}_{m['color']}"
                if m is not None
                else None
                for m in materials
            ]
            return materials
        except Exception as e:
            self._logger.warning(
                f"Skipping material assignment due to SpoolManager error: {e}"
            )
            return []

    def get_filament_metadata(self):
        """Return loaded materials and names from one provider snapshot."""
        try:
            if self._impl is not None:
                selected = self._impl.api_getSelectedSpoolInformations() or []
                materials = []
                names = []
                for spool in selected:
                    if spool is None:
                        materials.append(None)
                        names.append(None)
                    else:
                        materials.append(spool.get("material"))
                        names.append(str(spool.get("spoolName"))
                                     if spool.get("spoolName") is not None else None)
                return materials, names
            if self._spoolman_impl is not None:
                selected = self._get_spoolman_selected_spools()
                return (
                    [(spool.get("filament") or {}).get("material") if spool else None
                     for spool in selected],
                    [f"spoolman:{spool['id']}"
                     if spool and spool.get("id") is not None else None
                     for spool in selected],
                )
            if self._has_rme_provider():
                tools = self._get_rme_tools()
                return ([tool.get("material") or None for tool in tools],
                        [self._rme_spool_identifier(tool) for tool in tools])
            if self._fallback_filaments is not None:
                return self._fallback_filaments(), []
            return [], []
        except Exception as error:
            self._logger.warning("Could not retrieve filament provider metadata: %s", error)
            return [], []

    def allowed_to_print(self) -> Dict[str, Any]:
        """
        Check if the printer is allowed to print
        :return: the response from the Spool Manager
        """
        with app.app_context():
            r = self._impl.allowed_to_print()
        if r.status_code != 200:
            raise SpoolManagerException(
                f"SpoolManager allowed_to_print() error: {r.data}"
            )
        return json.loads(r.data)

    def start_print_confirmed(self) -> Dict[str, Any]:
        """
        Start of a print job confirmed
        :return: information about the print job
        """
        with app.app_context():
            r = self._impl.start_print_confirmed()
        if r.status_code != 200:
            raise SpoolManagerException(
                f"SpoolManager error {r.status_code} on print start: {r.data}"
            )
        return json.loads(r.data)

    def get_loaded_filament(self) -> Union[str, None]:
        """
        Get the currently loaded filament
        :return: the currently loaded filament
        """
        try:
            materials = self.get_materials()
            if materials:
                # Assuming the first loaded filament is the currently used one
                loaded_filament = materials[0]
                return loaded_filament
            else:
                return None  # No filament loaded
        except Exception as e:
            self._logger.error(f"Error retrieving loaded filament: {e}")
            return None

    def get_loaded_filaments(self) -> Union[List[str], int, None]:
        """
        Get the currently loaded filaments
        :return: a list of the currently loaded filaments
        """
        try:
            if self._impl is None:
                if self._spoolman_impl is not None:
                    return [
                        (spool.get("filament") or {}).get("material") if spool else None
                        for spool in self._get_spoolman_selected_spools()
                    ]
                if self._has_rme_provider():
                    return [tool.get("material") or None for tool in self._get_rme_tools()]
                if self._fallback_filaments is None:
                    self._logger.warning(
                        "Spool Manager is not installed and no manual filament provider is configured.")
                    return -1
                return self._fallback_filaments()

            materials = self.get_materials()

            if not materials:
                self._logger.warning("No filament selected in Spool Manager. Filament alert_type will not be checked.")
                return None

            # Assuming the first loaded filament is the currently used one
            filaments = []
            for material in materials:
                try:
                    filaments.append(material.split("_")[0])
                except Exception:
                    filaments.append(None)

            return filaments if len(filaments) > 0 else None
        except Exception as e:
            self._logger.error(f"Error retrieving loaded filament: {e}")
            return -2

    def get_names(self) -> Union[List[str], None]:
        """
        Get the name of the spools
        :return: the name of the spool
        """
        """
        Get the materials from the Spool Manager
        :return:
        """
        try:
            if self._impl is None:
                if self._spoolman_impl is not None:
                    return [
                        f"spoolman:{spool['id']}" if spool and spool.get("id") is not None else None
                        for spool in self._get_spoolman_selected_spools()
                    ]
                if self._has_rme_provider():
                    return [self._rme_spool_identifier(tool) for tool in self._get_rme_tools()]
                return []
            spool_names = self._impl.api_getSelectedSpoolInformations()
            spool_names = [
                f"{m['spoolName']}"
                if m is not None
                else None
                for m in spool_names
            ]
            return spool_names
        except Exception as e:
            self._logger.warning(
                f"Skipping material assignment due to SpoolManager error: {e}"
            )
            return []

    def get_db_id(self) -> Union[List[str], None]:
        """
        Get the database id's of the spools
        :return: the db_id's of the spool
        """
        """
        Get the materials from the Spool Manager
        :return:
        """
        try:
            db_ids = self._impl.api_getSelectedSpoolInformations()
            db_ids = [
                f"{m['databaseId']}"
                if m is not None
                else None
                for m in db_ids
            ]
            return db_ids
        except Exception as e:
            self._logger.warning(
                f"Skipping material assignment due to SpoolManager error: {e}"
            )
            return []
