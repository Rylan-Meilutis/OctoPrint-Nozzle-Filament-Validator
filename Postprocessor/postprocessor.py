#!/usr/bin/python3

import json
import os
import re
import sys
from typing import Any


def main() -> None:
    """
    Main function
    """
    gcode_path = str(sys.argv[2])
    json_path = str(sys.argv[1])
    json_data = parse_json_file(json_path)
    gcode = parse_gcode(gcode_path)
    new_file = replace_names(gcode, json_data)
    # replace the last 1000 lines of the gcode with the new data
    with open(gcode_path, 'r') as file:
        data = file.readlines()
    with open(gcode_path, 'w') as file:
        for line in data[:-1000]:
            file.write(line)
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
            out_list[int(key) -1 ] = value['sm_name']
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

    new_filament_notes = filament_notes_match.group(0)
    # loop through the json data
    for i in range(len(filament_notes)):
        try:
            if json_data[i] is None:
                continue
        except IndexError:
            continue
        if re.search(r"\[\s*sm_name\s*=\s*([^]]*\S)]", filament_notes[i]):
            tmp_string = re.sub(r"\[\s*sm_name\s*=\s*([^]]*\S)]", f"[sm_name = {json_data[i]}]", filament_notes[i])
            # replace the match with the json data
            new_filament_notes = new_filament_notes.replace(filament_notes[i], tmp_string)

    # replace the filament notes in the gcode
    gcode = gcode.replace(filament_notes_match.group(0), new_filament_notes)
    return gcode


if __name__ == "__main__":
    main()
