#!/bin/sh

touch data.json
touch nfvsettings.json
echo "Postprocessor setup complete."
echo
echo "enter the following in your slicers post processor section:"
echo
echo "$(pwd)/nvfPostprocessor"

