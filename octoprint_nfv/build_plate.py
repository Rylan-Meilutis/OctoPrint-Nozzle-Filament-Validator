from typing import NoReturn, Any, Union, Dict, List

from octoprint_nfv.db import get_db


def get_filament_types():
    """
    Get the filament types
    :return: the available filament types
    """

    return ["PLA",
            "PETG",
            "ABS",
            "NYLON",
            "TPU",
            "PC",
            "Wood",
            "PC_ABS",
            "HIPS",
            "PVA",
            "BVOH",
            "ASA",
            "PP",
            "POM",
            "PMMA",
            "FPE"
            ]


class build_plate:
    """
    Class to handle the build plate settings and db
    """

    def __init__(self, data_folder: str, logger: Any):
        """
        Constructor
        :param data_folder: data folder of the plugin
        :param logger: logger for outputting errors
        """
        super().__init__()
        self._spool_manager = None
        self.data_folder = data_folder
        self._logger = logger

    def fetch_build_plates_from_database(self) -> List[Dict[str, Any]]:
        """
        Fetch all build plates from the database
        :return: a list of all available build plates
        """
        con = get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("SELECT id, name, compatible_filaments FROM build_plates")
        con.commit()
        return [{"id": row[0], "name": row[1], "compatible_filaments": row[2].replace(" ", "").split(",")} for row in
                cursor.fetchall()]

    def insert_build_plate_to_database(self, name: str, compatible_filaments: str, id: str = "null") -> NoReturn:
        """
        Insert a build plate into the database
        :param name: name of the build plate
        :param compatible_filaments: compatible filaments
        :param id: numerical build_plate_id of the build plate
        :return: none
        """
        try:
            con = get_db(self.data_folder)
            cursor = con.cursor()
            if id == "null":
                # Check if the nozzle size already exists in the database
                cursor.execute("SELECT name FROM build_plates WHERE name = ?", (str(name),))
                name_exists = cursor.fetchone()
                con.commit()

                # If the name already exists, log an error
                if name_exists:
                    self._logger.error(f"build plate name {name} already exists in the database")
                    raise Exception(f"build plate name {name} already exists in the database")
                else:
                    # Otherwise, insert the nozzle size into the database
                    cursor.execute("INSERT INTO build_plates (name, compatible_filaments) VALUES (?, ?)",
                                   (str(name), str(compatible_filaments)))
                    con.commit()
            else:

                cursor.execute("SELECT id FROM build_plates WHERE id = ?", (str(id),))
                id_exists = cursor.fetchone()
                con.commit()
                if id_exists:
                    cursor.execute("UPDATE build_plates SET name = ?, compatible_filaments = ? WHERE id = ?",
                                   (str(name), str(compatible_filaments), int(id)))
                else:
                    cursor.execute("INSERT INTO build_plates (name, compatible_filaments, id) VALUES (?, ?, ?)",
                                   (str(name), str(compatible_filaments), int(id)))
                con.commit()
        except Exception as e:
            self._logger.error(f"Error adding build plate to the database: {e}")

    def select_current_build_plate(self, selected_build_plate_id: int) -> NoReturn:
        """
        Select the current build plate in the current selections db
        :param selected_build_plate_id: the build_plate_id of the selected build plate
        :return:
        """
        con = get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("UPDATE current_selections SET selection = ? WHERE id = 'build_plate'",
                       (int(selected_build_plate_id),))  # Assuming there's only one current nozzle
        con.commit()

    def get_current_build_plate_name(self) -> Union[str, None]:
        """
        Get the current build plate name
        :return: the name of the current build plate or none if not found
        """
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

    def get_current_build_plate_filaments(self) -> Union[List[str], None]:
        """
        Get the current build plate filaments
        :return: a list of the current build plate filaments or none if not found
        """
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

    def get_current_build_plate_id(self) -> Union[int, None]:
        """
        Get the current build plate ID
        :return: the current build plate ID or none if not found
        """
        # Create a cursor to execute SQL queries
        con = get_db(self.data_folder)
        cursor = con.cursor()

        # Execute a SELECT query to retrieve the current nozzle ID
        cursor.execute("SELECT selection FROM current_selections WHERE id = 'build_plate'")

        # Fetch the current nozzle ID
        data_id = cursor.fetchone()
        con.commit()

        return data_id[0] if data_id else None

    def remove_build_plate_from_database(self, build_plate_id) -> NoReturn:
        """
        Remove a build plate from the database
        :param build_plate_id: the build_plate_id of the build plate to remove
        :return: Nothing
        """
        con = get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("DELETE FROM build_plates WHERE id = ?", (build_plate_id,))
        con.commit()

        # Check if the removed nozzle was the current nozzle
        current_nozzle_id = self.get_current_build_plate_id()
        if current_nozzle_id == build_plate_id:
            cursor.execute("UPDATE current_selections SET selection = ? WHERE id = 'build_plate'",
                           (1, "nozzle"))  # Assuming there's only one current nozzle
            con.commit()

    def get_build_plate_name_by_id(self, build_plate_id: int) -> Union[str, None]:
        """
        Get the build plate name by the build plate ID
        :param build_plate_id: the build plate ID
        :return: the name of the build plate or none if not found
        """
        con = get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("SELECT name FROM build_plates WHERE id = ?", (int(build_plate_id),))
        con.commit()
        result = cursor.fetchone()
        return result[0] if result else None

    def get_build_plate_filaments_by_id(self, build_plate_id: int) -> Union[List[str], None]:
        """
        Get the build plate filaments by the build plate ID
        :param build_plate_id: the build plate ID
        :return: the list of compatible filaments or none if not found
        """
        con = get_db(self.data_folder)
        cursor = con.cursor()
        cursor.execute("SELECT compatible_filaments FROM build_plates WHERE id = ?", (int(build_plate_id),))
        con.commit()
        result = cursor.fetchone()
        return str(result[0]).split(",") if result else None

    def is_filament_compatible_with_build_plate(self, filament_type: str) -> bool:
        """
        Check if the filament type is compatible with the current build plate
        :param filament_type: the filament type to check
        :return: true if the filament is compatible, false otherwise
        """
        build_plate_filaments = self.get_current_build_plate_filaments()
        if build_plate_filaments is not None:
            return filament_type in build_plate_filaments
        else:
            return False
