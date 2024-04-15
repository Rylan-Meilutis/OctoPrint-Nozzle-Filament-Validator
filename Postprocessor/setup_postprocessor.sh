#!/bin/sh

chmod +x postprocessor.py

if ! which python >/dev/null 2>&1; then
    echo "Python is not installed or not on the PATH."
    echo "Please install Python and ensure it is on the PATH."
    exit 1
fi

touch data.json
echo "Postprocessor setup complete."
echo
echo "enter the following in your slicers post processor section:"
echo
python3 -m pip install --upgrade -r requirements.txt
echo "$(which python3) $(pwd)/nvfPostprocessor.py"

