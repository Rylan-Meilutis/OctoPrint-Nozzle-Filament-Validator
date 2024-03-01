import json

from octoprint.server import app


class SpoolManagerException(Exception):
    pass


class SpoolManagerIntegration:
    def __init__(self, impl, logger):
        self._logger = logger
        self._impl = impl

    def get_materials(self):
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

    def allowed_to_print(self):
        with app.app_context():
            r = self._impl.allowed_to_print()
        if r.status_code != 200:
            raise SpoolManagerException(
                f"SpoolManager allowed_to_print() error: {r.data}"
            )
        return json.loads(r.data)

    def start_print_confirmed(self):
        with app.app_context():
            r = self._impl.start_print_confirmed()
        if r.status_code != 200:
            raise SpoolManagerException(
                f"SpoolManager error {r.status_code} on print start: {r.data}"
            )
        return json.loads(r.data)

    def get_loaded_filament(self):
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

    def get_loaded_filaments(self):
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
                filaments.append(material.split("_")[0])

            return filaments if len(filaments) > 0 else None
        except Exception as e:
            self._logger.error(f"Error retrieving loaded filament: {e}")
            return -2
