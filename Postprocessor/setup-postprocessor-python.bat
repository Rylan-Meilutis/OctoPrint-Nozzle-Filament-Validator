@echo off
set "python_installed=true"
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python is not installed or not on the PATH.
    echo Please install Python and make sure it is on the PATH, this is essential for the post-processor to work.
    echo alternatively, you can use the path to the exe instead.
    set python_installed=false
)
if "%python_installed%"=="true" (
    echo Python is installed and on the PATH.
    )
REM Make the python script executable
attrib +r postprocessor.py

echo. > data.json

echo Postprocessor setup complete.
echo.
echo Enter the following in your slicers post processor section:
echo.
if "%python_installed%"=="true" (
    for /f "delims=" %%i in ('where python') do set "PYTHON_PATH=%%i"
    echo %PYTHON_PATH% %cd%\postprocessor.py data.json
) else (
    echo %cd%\postprocessor.exe data.json
)
