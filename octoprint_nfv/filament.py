import logging

from octoprint_nfv import db


class filament:
    def __init__(self, data_folder: str, logger: logging.Logger) -> None:
        """
        Constructor
        :param data_folder: the data folder of the plugin
        :param logger: the logger object
        """
        self.data_folder = data_folder
        self._logger = logger

    def initial_db_add(self, enable_spool_checking: bool, timeout: int) -> None:
        """
        Add the enable spool checking and timeout to the database
        this function is called when the plugin is first initialised and should only be called then
        :param enable_spool_checking: the enable spool checking value
        :param timeout: the timeout for the filament
        """
        self.add_enable_spool_checking_to_db(enable_spool_checking)
        self.add_timeout_to_db(timeout)

    def add_timeout_to_db(self, timeout: int) -> None:
        """
        Add the timeout to the database
        :param timeout: the timeout for the filament
        """
        con = db.get_db(self.data_folder)
        cursor = con.cursor()
        # check if the timeout already exists in the database
        existing_timeout = cursor.execute("SELECT id FROM filament_data WHERE id = 'timeout'")
        existing_timeout = existing_timeout.fetchone()

        if existing_timeout:
            # log an error if the timeout already exists
            self._logger.error("Timeout already exists in the database")
        else:
            cursor.execute("INSERT INTO filament_data (id, data) VALUES (?, ?)", ("timeout", timeout,))
        con.commit()

    def add_enable_spool_checking_to_db(self, enable_spool_checking: bool) -> None:
        """
        Add the enable spool checking value to the database
        :param enable_spool_checking: the enable spool checking value
        """
        con = db.get_db(self.data_folder)
        cursor = con.cursor()
        # check if the enable_spool_checking already exists in the database
        existing_enable_spool_checking = (
            cursor.execute("SELECT id FROM filament_data WHERE id = 'enable_spool_checking'"))
        existing_enable_spool_checking = existing_enable_spool_checking.fetchone()

        if existing_enable_spool_checking:
            # log an error if the enable_spool_checking already exists
            self._logger.error("Enable spool checking already exists in the database")
        else:
            cursor.execute("INSERT INTO filament_data (id, data) VALUES (?, ?)", ("enable_spool_checking",
                                                                                  enable_spool_checking,))
        con.commit()

    def update_enable_spool_checking(self, enable_spool_checking: bool) -> None:
        """
        Update the enable spool checking value
        :param enable_spool_checking: the enable spool checking value
        """
        con = db.get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("UPDATE filament_data SET data = ? WHERE id = 'enable_spool_checking'", (enable_spool_checking,))
        con.commit()

    def update_timeout(self, timeout: int) -> None:
        """
        Update the timeout for the filament
        :param timeout: the timeout for the filament
        """
        con = db.get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("UPDATE filament_data SET data = ? WHERE id = 'timeout'", (timeout,))
        con.commit()

    def get_timeout(self) -> int:
        """
        Get the timeout for the filament
        :return: the timeout for the filament
        """
        con = db.get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("SELECT data FROM filament_data WHERE id = 'timeout'")
        return cursor.fetchone()[0]

    def get_enable_spool_checking(self) -> bool:
        """
        Get the enable spool checking value
        :return: the enable spool checking value
        """
        con = db.get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("SELECT data FROM filament_data WHERE id = 'enable_spool_checking'")
        return bool(cursor.fetchone()[0])
