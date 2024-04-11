import logging
import os
import sqlite3
import time


def get_db(path: str) -> sqlite3.Connection:
    """
    Get the database connection
    :param path: path to db
    :return: the sqlite3 connection
    """
    data_folder = path
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)

    # Construct the path to the SQLite database file
    db_path = os.path.join(data_folder, "nozzle_filament_database.db")
    return sqlite3.connect(db_path)


def init_db(path: str) -> None:
    """
    Initialize the db with the correct tables
    :param path: the path to the db
    """
    # Connect to the SQLite database
    conn = get_db(path)
    conn.execute("CREATE TABLE IF NOT EXISTS nozzles (id INTEGER PRIMARY KEY, size REAL)")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS extruders (id INTEGER PRIMARY KEY, build_plate_id int, extruder_position int "
        "UNIQUE)")
    conn.execute("CREATE TABLE IF NOT EXISTS current_selections (id REAL PRIMARY KEY, selection INTEGER)")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS build_plates (id INTEGER PRIMARY KEY, name REAL, compatible_filaments REAL)")
    conn.execute("CREATE TABLE IF NOT EXISTS filament_data (id REAL PRIMARY KEY, data INTEGER)")
    conn.commit()


def check_and_insert_to_db(data_path: str, logger: logging.Logger, row: str, value: any = 1) -> None:
    """
    Check if the column exists in the current_selections table and insert it if it does not
    :param data_path: the path to the database dir
    :param logger: the logger object
    :param row: the row to check
    :param value: the value to insert
    """
    conn = get_db(data_path)
    try:
        retry = 0
        index = conn.cursor()

        # Check if the table already exists in the table schema
        index.execute("SELECT COUNT(*) FROM current_selections WHERE id = ?",
                      (str(row),))
        exists = index.fetchone()[0]

        if not exists:
            while retry < 3:
                try:
                    index.execute("INSERT INTO current_selections (id, selection) VALUES (?, ?)",
                                  (row, value))
                    conn.commit()
                    break
                except sqlite3.OperationalError as error:
                    logger.warning(f"Database operation failed: {error}")
                    logger.warning("Retrying...")
                    retry += 1
                    time.sleep(1)  # Wait for 1 second before retrying

            if retry == 3:
                logger.error(
                    "Failed to insert row into current_selections after multiple attempts. Plugin "
                    "initialization may be incomplete.")
    except Exception as error:
        logger.error(f"Error adding nozzle to the database: {error}")
    conn.close()


def add_row_to_db(data_path: str, logger: logging.Logger, table: str, insert_function: callable, params: tuple,
                  num_rows: int = 0, num_retries: int = 3) -> None:
    """
    Add a row to a database.
    :param data_path: the path to the database dir
    :param logger: the logger object
    :param table: the table to add the row to
    :param insert_function: the function to insert the row
    :param params: the parameters to pass to the insert function
    :param num_rows: the number of rows that should be in the table
    :param num_retries: the number of times to retry adding the row
    """
    conn = get_db(data_path)

    try:
        retries = 0
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        if int(count) < num_rows or num_rows == 0 and int(count) == 0:
            while retries < num_retries:
                try:
                    insert_function(*params)
                    break
                except sqlite3.OperationalError as e:
                    logger.warning(f"Database operation failed: {e}")
                    logger.warning("Retrying...")
                    retries += 1
                    time.sleep(1)  # Wait for 1 second before retrying

            if retries == 3:
                logger.error(
                    f"Failed to insert row into {table} after multiple attempts. Plugin initialization may "
                    "be incomplete.")
    except Exception as e:
        logger.error(f"Error adding to the database: {e}")
    conn.close()
