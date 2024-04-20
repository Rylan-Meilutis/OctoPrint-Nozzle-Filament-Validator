CREATE TABLE IF NOT EXISTS nozzles
(
    id   INTEGER PRIMARY KEY,
    size REAL
);
CREATE TABLE IF NOT EXISTS extruders
(
    id                INTEGER PRIMARY KEY,
    nozzle_id         int,
    extruder_position int UNIQUE
);
CREATE TABLE IF NOT EXISTS current_selections
(
    id        REAL PRIMARY KEY,
    selection INTEGER
);
CREATE TABLE IF NOT EXISTS build_plates
(
    id                   INTEGER PRIMARY KEY,
    name                 REAL,
    compatible_filaments REAL
);
CREATE TABLE IF NOT EXISTS filament_data
(
    id   REAL PRIMARY KEY,
    data INTEGER
);