import logging
from typing import Any

from octoprint_nfv.db import get_db


class nozzle:
    """
    Class to handle nozzle operations
    """

    def __init__(self, data_folder: str, logger: logging.Logger) -> None:
        """
        Constructor
        :param data_folder: path to the data folder
        :param logger: the logger instance
        """
        super().__init__()
        self.data_folder = data_folder
        self._logger = logger

    def fetch_nozzles_from_database(self) -> list[dict[str, Any]]:
        """
        Fetch all nozzles from the database
        :return: a list of all available nozzles
        """
        con = get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("SELECT id, size FROM nozzles")
        con.commit()
        return [{"id": row[0], "size": row[1]} for row in cursor.fetchall()]

    def add_nozzle_to_database(self, nozzle_size: float) -> None:
        """
        Add a nozzle to the database
        :param nozzle_size: the size of the nozzle
        """
        try:
            con = get_db(self.data_folder)
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

    def remove_nozzle_from_database(self, nozzle_id: int) -> None:
        """
        Remove a nozzle from the database
        :param nozzle_id: the id of the nozzle to remove
        """
        con = get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("DELETE FROM nozzles WHERE id = ?", (nozzle_id,))
        con.commit()

    def get_nozzle_size_by_id(self, nozzle_id: int) -> float:
        """
        Get the size of a nozzle by its id
        :param nozzle_id: the id of the nozzle
        :return: the size of the nozzle
        """
        con = get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("SELECT size FROM nozzles WHERE id = ?", (nozzle_id,))
        con.commit()
        result = cursor.fetchone()
        return result[0] if result else None
