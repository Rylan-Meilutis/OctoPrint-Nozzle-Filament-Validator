@echo off

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python is not installed or not on the PATH.
    echo Please install Python and make sure it is on the PATH, this is essential for the post-processor to work.
    echo alternatively, you can use the path to the exe instead.
)
echo Python is installed and on the PATH.
REM Make the python script executable
attrib +r postprocessor.py

REM Copy the example data file to a new file named data.json
copy example_data.json data.json

echo Postprocessor setup complete.
echo.
echo Enter the following in your slicers post processor section:
echo.
echo %cd%\postprocessor.py data.json