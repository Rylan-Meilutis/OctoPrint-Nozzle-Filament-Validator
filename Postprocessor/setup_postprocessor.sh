#!/bin/sh

chmod +x postprocessor.py

if ! which python >/dev/null 2>&1; then
    echo "Python is not installed or not on the PATH."
    echo "Please install Python and ensure it is on the PATH."
fi

cp example_data.json data.json
echo "Postprocessor setup complete."
echo
echo "enter the following in your slicers post processor section:"
echo
echo "$(pwd)/postprocessor.py data.json"

