import sys
import os
import json
from typing import Any


def main() -> None:
    """
    Main function
    """
    gcode_path = sys.argv[2]
    json_path = sys.argv[1]
    json_data = parse_json_file(json_path)
    gcode = parse_gcode(gcode_path)
    new_file = replace_db_ids(gcode, json_data)
    with open(gcode_path, 'w') as file:
        file.write(new_file)


def parse_json_file(json_path: str) -> list[Any]:
    """
    Parse the json file and return the db ids in order
    :param json_path: path to the json file
    :return: a list of db ids in order
    """
    with open(json_path, 'r') as file:
        data = json.load(file)
        # get each db id and the corresponding extruder position and put then in order in a list
        out_list = [None] * len(data)
        for key, value in data.items():
            out_list[int(key)] = value['db_id']
        return out_list


def parse_gcode(gcode_path: str) -> str:
    """
    Parse the gcode file and return the last 1000 lines
    :param gcode_path: path to the gcode file
    :return: the last 1000 lines of the gcode file
    """
    # Number of lines to read from the end of the file
    num_lines = 1000

    with open(gcode_path, 'r') as file:
        # Move the file pointer to the end
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        # Track the position in the file
        pos = file_size - 1
        newline_count = 0
        # Read the file backwards until we find the last 100 lines or reach the beginning of the file
        while pos > 0 and newline_count < num_lines:
            file.seek(pos)
            char = file.read(1)
            if char == '\n':
                newline_count += 1
                if newline_count == num_lines:
                    break
            pos -= 1
        # Read the last 100 lines
        lines = file.readlines()

        # Extract nozzle diameter and filament alert_type from the collected lines
        return ''.join(lines)


def replace_db_ids(gcode: str, json_data: list[Any]) -> str:
    """
    Replace the db ids in the gcode with the correct values
    :param gcode: the last 1000 lines of the gcode
    :param json_data: the list of db ids in order
    :return: the last 1000 lines of the gcode with the db ids replaced
    """
    # Replace the db ids in the gcode with the correct values
    # it should match the gcode using a regex patter and replace the values with those in the json file provided.
    # the json data is as follows, it is a list where the index is the extruder position and the value is the db id
    # [1, 2, 3, 4] if there is no db id for a given extruder position, the value will be None
    # [1, 2, None, 4] in this case, the db id for extruder position 3 is not assigned.
    if json_data is None:
        return gcode
    # match the regex

    # loop through the json data
    for i in range(len(json_data)):
        if json_data[i] is None:
            continue

        # replace the match with the json data
        pass

    return gcode


if __name__ == "__main__":
    main()
