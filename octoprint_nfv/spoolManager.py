import json
import logging
from typing import Any
from typing import Union

from octoprint.server import app


class SpoolManagerException(Exception):
    pass


class SpoolManagerIntegration:
    def __init__(self, impl: Any, logger: logging.Logger) -> None:
        """
        Constructor
        :param impl: implementation of the Spool Manager
        :param logger: logger object
        """
        self._logger = logger
        self._impl = impl

    def get_materials(self) -> list[str]:
        """
        Get the materials from the Spool Manager
        :return:
        """
        try:
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

    def allowed_to_print(self) -> dict[str, Any]:
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

    def start_print_confirmed(self) -> dict[str, Any]:
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

    def get_loaded_filaments(self) -> Union[list[str], int, None]:
        """
        Get the currently loaded filaments
        :return: a list of the currently loaded filaments
        """
        try:
            if self._impl is None:
                self._logger.warning("Spool Manager plugin is not installed. Filament alert_type will not be checked.")
                return -1

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

    def get_names(self) -> Union[list[str], None]:
        """
        Get the name of the spools
        :return: the name of the spool
        """
        """
        Get the materials from the Spool Manager
        :return:
        """
        try:
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

    def get_db_id(self) -> Union[list[str], None]:
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
