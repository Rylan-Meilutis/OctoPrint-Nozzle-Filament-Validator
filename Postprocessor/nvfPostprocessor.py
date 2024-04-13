# This will be a graphical app allowing the user to easily modify the json file used as input to the postprocessor. I
# will handle the compilation into an executable using auto-py-to-exe or similar. Feel free to use a different
# language if you want such as rust, c++, c, electron, etc. The app should have the following features: gets the path
# to the json file using a file dialog, displays the entries in the in a user-friendly format, allows the user to
# modify them and saves the changes as they type, allows the user to add new entries, allows the user to delete entries.
# The app should also work in 2 modes, stand-alone mode, where the user can edit the json file, and postprocessor
# mode, where it allows editing of the current extruders and the names of the spools that should be used.
# You will be able to tell the difference based on the number of system arguments if there are none (len(sys.argv)
# < 1) or the data isn't a path, then you are in stand-alone mode. If there is an argument, and it is a path,
# then you are in postprocessor mode.

# the following code is an example of how the app's structure could look like, feel free to change it as you see fit

import sys

import postprocessor


class modes:
    STAND_ALONE = "stand-alone"
    POST_PROCESSOR = "post-processor"


MODE = modes.STAND_ALONE


def main() -> None:
    if MODE == modes.POST_PROCESSOR:
        json_data = postprocessor.parse_json_file(sys.argv[1])
        # show interface to change and confirm the json data based on the length of the gcode data

        postprocessor.main(sys.argv[1], json_data=json_data)

    elif MODE == modes.STAND_ALONE:
        # show interface to edit the json data and add/remove extruders
        pass


if __name__ == "__main__":
    if len(sys.argv) > 1:
        MODE = modes.POST_PROCESSOR
    main()
