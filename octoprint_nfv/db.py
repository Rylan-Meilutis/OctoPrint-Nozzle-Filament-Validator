import os
import sqlite3


def get_db(path):
    data_folder = path
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)

    # Construct the path to the SQLite database file
    db_path = os.path.join(data_folder, "nozzle_filament_database.db")
    return sqlite3.connect(db_path)


def init_db(path):
    # Connect to the SQLite database
    conn = get_db(path)
    conn.execute("CREATE TABLE IF NOT EXISTS nozzles (id INTEGER PRIMARY KEY, size REAL)")
    conn.execute("CREATE TABLE IF NOT EXISTS extruders (id INTEGER PRIMARY KEY, nozzle_id int, extruder_position int UNIQUE)")
    conn.execute("CREATE TABLE IF NOT EXISTS current_selections (id REAL PRIMARY KEY, selection INTEGER)")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS build_plates (id INTEGER PRIMARY KEY, name REAL, compatible_filaments REAL)")
    conn.commit()
