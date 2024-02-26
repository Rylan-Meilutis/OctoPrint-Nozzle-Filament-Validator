from octoprint_nfv.db import get_db


class nozzle:
    def __init__(self, data_folder, logger):
        super().__init__()
        self._conn = None
        self._spool_manager = None
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

    def select_current_nozzle(self, selected_nozzle_id):
        con = get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("UPDATE current_selections SET selection = ? WHERE id = 'nozzle'",
                       (int(selected_nozzle_id),))  # Assuming there's only one current nozzle
        con.commit()

    def get_current_nozzle_size(self):
        nozzle_id = self.get_current_nozzle_id()

        if nozzle_id is not None:
            con = get_db(self.data_folder)
            cursor = con.cursor()
            # Extract the ID from the fetched row

            # Execute a SELECT query to retrieve the size based on the current nozzle ID
            cursor.execute("SELECT size FROM nozzles WHERE id = ?", (nozzle_id,))
            con.commit()
            # Fetch the size corresponding to the current nozzle ID
            result = cursor.fetchone()

            # Return the size if found
            return result[0] if result else None
        else:
            # Return None if no current nozzle ID was found
            self._logger.error("No current nozzle ID found in the database")
            return None

    def get_current_nozzle_id(self):
        # Create a cursor to execute SQL queries
        con = get_db(self.data_folder)
        cursor = con.cursor()

        # Execute a SELECT query to retrieve the current nozzle ID
        cursor.execute("SELECT selection FROM current_selections WHERE id = 'nozzle'")

        # Fetch the current nozzle ID
        data_id = cursor.fetchone()
        con.commit()

        return data_id[0] if data_id else None

    def remove_nozzle_from_database(self, nozzle_id):
        con = get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("DELETE FROM nozzles WHERE id = ?", (nozzle_id,))
        con.commit()

        # Check if the removed nozzle was the current nozzle
        current_nozzle_id = self.get_current_nozzle_id()
        if current_nozzle_id == nozzle_id:
            cursor.execute("UPDATE current_selections SET selection = ? WHERE id = 'nozzle'",
                           (1, "nozzle"))  # Assuming there's only one current nozzle
            con.commit()
