from octoprint_nfv.db import get_db


class nozzle:
    def __init__(self, data_folder, logger):
        super().__init__()
        self._conn = None
        self.data_folder = data_folder
        self._logger = logger

    def fetch_nozzles_from_database(self):
        con = get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("SELECT id, size FROM nozzles")
        con.commit()
        return [{"id": row[0], "size": row[1]} for row in cursor.fetchall()]

    def add_nozzle_to_database(self, nozzle_size):
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

    def remove_nozzle_from_database(self, nozzle_id):
        con = get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("DELETE FROM nozzles WHERE id = ?", (nozzle_id,))
        con.commit()

    def get_nozzle_size_by_id(self, nozzle_id):
        con = get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("SELECT size FROM nozzles WHERE id = ?", (nozzle_id,))
        con.commit()
        result = cursor.fetchone()
        return result[0] if result else None
