import sys
import os
import json
import re
from typing import Any


def main() -> None:
    """
    Main function
    """
    gcode_path = sys.argv[2]
    json_path = sys.argv[1]
    json_data = parse_json_file(json_path)
    gcode = parse_gcode(gcode_path)
    new_file = replace_names(gcode, json_data)
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
            out_list[int(key)] = value['sm_name']
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


def replace_names(gcode: str, json_data: list[Any]) -> str:
    """
    Replace the db ids in the gcode with the correct values
    :param gcode: the last 1000 lines of the gcode
    :param json_data: the list of db ids in order
    :return: the last 1000 lines of the gcode with the db ids replaced
    """
    # Replace the db ids in the gcode with the correct values
    # it should match the gcode using a regex patter and replace the values with those in the json file provided.
    # the json data is as follows, it is a list where the index is the extruder position and the value is the db id
    # ["blue PLA+", "blue petg", "purple abs", "grey pla"] if there is no db id for a given extruder position,
    # the value will be None
    # ["blue PLA+", "blue petg", None, "grey pla"] in this case, the db id for extruder position 3 is not assigned.
    if json_data is None:
        return gcode
    # match the regex
    filament_notes_pattern = re.compile(r'; filament_notes = (.+)')
    filament_notes_match = filament_notes_pattern.search(gcode)
    filament_notes = None
    if filament_notes_match:
        filament_notes = filament_notes_match.group(1).strip().split(';')
    if filament_notes is None:
        return gcode

    # Filament_notes is a list of strings containing the notes of the filament, you need to search for "sm_name = "
    # with optional spaces around the equal sign and then optionally a number.
    # You will be replacing the number if it is there.

    # loop through the json data
    for i in range(len(json_data)):
        if json_data[i] is None:
            continue

        # replace the match with the json data
        pass

    return gcode


if __name__ == "__main__":
    main()
