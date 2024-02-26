from octoprint_nfv.db import get_db


def get_filament_types():
    return ["PLA", "PETG", "ASA", "ABS", "TPU", "Nylon", "PC", "Wood", "Metal", "Carbon Fiber", "PVA", "HIPS",
            "PETT", "PP", "PEI", "POM", "PMMA", "PBT", "PES", "PC-ABS", "PPO", "PEEK", "PEKK", "PEI", "PES"]


class build_plate:

    def __init__(self, data_folder, logger):
        super().__init__()
        self._conn = None
        self._spool_manager = None
        self.data_folder = data_folder
        self._logger = logger

    def fetch_build_plates_from_database(self):
        con = get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("SELECT id, name, compatible_filaments FROM build_plates")
        con.commit()
        return [{"id": row[0], "name": row[1], "compatible_filaments": row[2].replace(" ", "").split(",")} for row in
                cursor.fetchall()]

    def insert_build_plate_to_database(self, name, compatible_filaments, id: str = "null"):
        try:
            con = get_db(self.data_folder)
            cursor = con.cursor()
            if id == "null":
                # Check if the nozzle size already exists in the database
                cursor.execute("SELECT name FROM build_plates WHERE name = ?", (str(name),))
                existing_size = cursor.fetchone()
                con.commit()

                # If the name already exists, log an error
                if existing_size:
                    self._logger.error(f"build plate name{name} already exists in the database")
                    raise Exception(f"build plate name{name} already exists in the database")
                else:
                    # Otherwise, insert the nozzle size into the database
                    cursor.execute("INSERT INTO build_plates (name, compatible_filaments) VALUES (?, ?)",
                                   (str(name), str(compatible_filaments)))
                    con.commit()
            else:
                cursor.execute("UPDATE build_plates SET name = ?, compatible_filaments = ? WHERE id = ?",
                               (str(name), str(compatible_filaments), int(id)))
                con.commit()
        except Exception as e:
            self._logger.error(f"Error adding build plate to the database: {e}")

    def select_current_build_plate(self, selected_nozzle_id):
        con = get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("UPDATE current_selections SET selection = ? WHERE id = 'build_plate'",
                       (int(selected_nozzle_id),))  # Assuming there's only one current nozzle
        con.commit()

    def get_current_build_plate_name(self):
        build_plate_id = self.get_current_build_plate_id()

        if build_plate_id is not None:
            con = get_db(self.data_folder)
            cursor = con.cursor()
            # Extract the ID from the fetched row

            # Execute a SELECT query to retrieve the size based on the current nozzle ID
            cursor.execute("SELECT name FROM build_plates WHERE id = ?", (build_plate_id,))
            con.commit()
            # Fetch the size corresponding to the current nozzle ID
            result = cursor.fetchone()

            # Return the size if found
            return result[0] if result else None
        else:
            # Return None if no current nozzle ID was found
            self._logger.error("No current build plate ID found in the database")
            return None

    def get_current_build_plate_filaments(self):
        build_plate_id = self.get_current_build_plate_id()

        if build_plate_id is not None:
            con = get_db(self.data_folder)
            cursor = con.cursor()
            # Extract the ID from the fetched row

            # Execute a SELECT query to retrieve the size based on the current nozzle ID
            cursor.execute("SELECT compatible_filaments FROM build_plates WHERE id = ?", (build_plate_id,))
            con.commit()
            # Fetch the size corresponding to the current nozzle ID
            result = cursor.fetchone()
            # Return the size if found
            return str(result[0]).split(",") if result else None
        else:
            # Return None if no current nozzle ID was found
            self._logger.error("No current build plate ID found in the database")
            return None

    def get_current_build_plate_id(self):
        # Create a cursor to execute SQL queries
        con = get_db(self.data_folder)
        cursor = con.cursor()

        # Execute a SELECT query to retrieve the current nozzle ID
        cursor.execute("SELECT selection FROM current_selections WHERE id = 'build_plate'")

        # Fetch the current nozzle ID
        data_id = cursor.fetchone()
        con.commit()

        return data_id[0] if data_id else None

    def remove_build_plate_from_database(self, nozzle_id):
        con = get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("DELETE FROM build_plates WHERE id = ?", (nozzle_id,))
        con.commit()

        # Check if the removed nozzle was the current nozzle
        current_nozzle_id = self.get_current_build_plate_id()
        if current_nozzle_id == nozzle_id:
            cursor.execute("UPDATE current_selections SET selection = ? WHERE id = 'build_plate'",
                           (1, "nozzle"))  # Assuming there's only one current nozzle
            con.commit()

    def get_build_plate_name_by_id(self, id):
        con = get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("SELECT name FROM build_plates WHERE id = ?", (int(id),))
        con.commit()
        result = cursor.fetchone()
        return result[0] if result else None

    def get_build_plate_filaments_by_id(self, id):
        con = get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("SELECT compatible_filaments FROM build_plates WHERE id = ?", (int(id),))
        con.commit()
        result = cursor.fetchone()
        return str(result[0]).split(",") if result else None

    def is_filament_compatible_with_build_plate(self, filament_type):
        build_plate_filaments = self.get_current_build_plate_filaments()
        if build_plate_filaments is not None:
            return filament_type in build_plate_filaments
        else:
            return False
