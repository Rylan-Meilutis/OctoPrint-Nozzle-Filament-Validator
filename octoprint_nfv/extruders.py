import logging
from typing import Any, List, Dict

from octoprint_nfv.db import get_db


class extruders:
    """
    Class to handle the extruder settings
    """

    def __init__(self, nozzle: Any, data_folder: str, logger: logging.Logger,
                 _printer_profile_manager: Any) -> None:
        """
        Constructor
        :param nozzle:
        :param data_folder:
        :param logger:
        :param _printer_profile_manager:
        """
        super().__init__()
        self.data_folder = data_folder
        self._logger = logger
        self._nozzle = nozzle
        self._printer_profile_manager = _printer_profile_manager

    def fetch_extruders_from_database(self) -> List[Dict[str, Any]]:
        """
        Fetch all extruders from the database
        :return: a list of all available extruders
        """
        con = get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("SELECT id, nozzle_id, extruder_position FROM extruders")
        con.commit()
        return [{"id": row[0], "nozzle_id": row[1], "extruder_position": row[2]} for row in cursor.fetchall()]

    def add_extruder_to_database(self, nozzle_id: int, extruder_position: int) -> None:
        """
        Add an extruder to the database
        :param nozzle_id: the nozzle id of nozzle in the extruder
        :param extruder_position: the position of the extruder
        """
        try:
            con = get_db(self.data_folder)
            cursor = con.cursor()

            if not self.is_multi_tool_head() and extruder_position > 1:
                nozzle_id = self.get_nozzle_id_for_extruder(1)

            cursor.execute("INSERT INTO extruders (nozzle_id, extruder_position) VALUES (?, ?)",
                           (int(nozzle_id), int(extruder_position)))

            con.commit()

        except Exception as e:
            self._logger.error(f"Error adding extruder to the database: {e}")

    def remove_extruder_from_database(self, extruder_id: int = None, extruder_position: int = None) -> None:
        """
        Remove an extruder from the database
        :param extruder_id: the id of the extruder
        :param extruder_position: the position of the extruder
        """
        try:
            con = get_db(self.data_folder)
            cursor = con.cursor()
            if extruder_id is not None:
                cursor.execute("DELETE FROM extruders WHERE id = ?", (int(extruder_id),))
            elif extruder_position is not None:
                cursor.execute("DELETE FROM extruders WHERE extruder_position = ?", (int(extruder_position),))
            con.commit()

        except Exception as e:
            self._logger.error(f"Error removing extruder from the database: {e}")

    def get_nozzle_size_for_extruder(self, extruder_position: int) -> float:
        """
        Get the nozzle size for an extruder
        :param extruder_position: the position of the extruder
        :return: the nozzle size
        """
        con = get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("SELECT nozzle_id FROM extruders WHERE extruder_position = ?", (extruder_position,))
        con.commit()
        nozzle_id = cursor.fetchone()[0]
        return self._nozzle.get_nozzle_size_by_id(nozzle_id) if nozzle_id is not None else None

    def get_nozzle_id_for_extruder(self, extruder_position: int) -> int:
        """
        Get the nozzle id for an extruder
        :param extruder_position: the position of the extruder
        :return: the nozzle id
        """
        con = get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("SELECT nozzle_id FROM extruders WHERE extruder_position = ?", (extruder_position,))
        con.commit()
        return cursor.fetchone()[0]

    def get_extruder_position(self, db_id: int) -> int:
        """
        Get the extruder position for an extruder
        :param db_id: the id of the extruder
        :return: the extruder position
        """
        con = get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("SELECT extruder_position FROM extruders WHERE id = ?", (db_id,))
        con.commit()
        return cursor.fetchone()[0]

    def set_nozzle_for_extruder(self, extruder_position: int, nozzle_id: int) -> None:
        """
        Set the nozzle for an extruder
        :param extruder_position: the position of the extruder
        :param nozzle_id: the id of the nozzle
        """
        con = get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("UPDATE extruders SET nozzle_id = ? WHERE extruder_position = ?",
                       (nozzle_id, extruder_position))
        con.commit()

    def set_extruder_position(self, db_id: int, extruder_position: int) -> None:
        """
        Set the extruder position
        :param db_id: the extruder_position of the extruder
        :param extruder_position: the position of the extruder
        :return:
        """
        con = get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("UPDATE extruders SET extruder_position = ? WHERE id = ?", (extruder_position, db_id))
        con.commit()

    def is_multi_tool_head(self) -> bool:
        """
        Check if the printer has multiple tool heads
        :return: true if the printer has multiple tool heads
        """
        # check if the printer has multiple tool heads using the octoprint API and make sure they use different nozzles
        printer_profile = self._printer_profile_manager.get_current_or_default()
        printer_profile_tool_count = printer_profile['extruder']['count']
        shared_nozzle = printer_profile['extruder']["sharedNozzle"]
        return printer_profile_tool_count > 1 and not shared_nozzle

    def get_number_of_extruders(self) -> int:
        """
        Get the number of extruders
        :return: the number of extruders
        """
        return self._printer_profile_manager.get_current_or_default()['extruder']['count']

    def update_extruder(self, db_id: int = None, nozzle_id: int = 1, extruder_position: int = None) -> None:
        """
        Update the extruder
        :param db_id: the extruder_position of the extruder
        :param nozzle_id: the nozzle id of the nozzle in the extruder
        :param extruder_position: the position of the extruder
        """
        con = get_db(self.data_folder)
        cursor = con.cursor()
        if extruder_position is not None and db_id is not None:
            cursor.execute("UPDATE extruders SET nozzle_id = ?, extruder_position = ? WHERE id = ?",
                           (nozzle_id, extruder_position, db_id))

        elif extruder_position is not None:
            cursor.execute("UPDATE extruders SET nozzle_id = ? WHERE extruder_position = ?",
                           (nozzle_id, extruder_position))

        elif db_id is not None:
            cursor.execute("UPDATE extruders SET extruder_position = ? WHERE id = ?", (extruder_position, db_id))

        if not self.is_multi_tool_head():
            # update all extruders to have the same nozzle
            if extruder_position is not None:
                cursor.execute("UPDATE extruders SET nozzle_id = ? WHERE extruder_position != ?",
                               (nozzle_id, extruder_position))
            elif db_id is not None:
                cursor.execute("UPDATE extruders SET nozzle_id = ? WHERE id != ?", (nozzle_id, db_id))
        con.commit()

    def get_extruder_info(self, extruder_position: int) -> List[Dict[str, Any]]:
        """
        Get the extruder info
        :param extruder_position: position of the extruder
        :return: a list of extruder info
        """
        con = get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("SELECT nozzle_id, extruder_position FROM extruders WHERE extruder_position = ?",
                       (extruder_position,))
        con.commit()
        return [{"nozzle_id": row[0], "extruder_position": row[1]} for row in cursor.fetchall()]

    def update_data(self) -> None:
        """
        Update the data in the database
        """
        num_extruders_in_db = len(self.fetch_extruders_from_database())
        num_extruders_in_profile = self.get_number_of_extruders()
        self._logger.info(f"Number of extruders in database: {num_extruders_in_db}")

        if num_extruders_in_db < num_extruders_in_profile:
            for i in range(num_extruders_in_db, num_extruders_in_profile):
                self.add_extruder_to_database(1, i + 1)
        elif num_extruders_in_db > num_extruders_in_profile:
            for i in range(num_extruders_in_profile, num_extruders_in_db):
                self.remove_extruder_from_database(extruder_position=i + 1)

        # check if the nozzles are the same if multi tool head is false
        if not self.is_multi_tool_head():
            extruder_list = self.fetch_extruders_from_database()
            extruder_1_nozzle = self.get_nozzle_id_for_extruder(1)
            for extruder in extruder_list:
                if extruder['nozzle_id'] != extruder_1_nozzle:
                    self.set_nozzle_for_extruder(extruder['extruder_position'], extruder_1_nozzle)
