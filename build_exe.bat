@echo off
echo Building Submarine Color Correction Executable...
echo.

cd /d "d:\OneDrive\DOCS\BATEAU-SCUBA\SCUBA\PHOTOS\COLOR CORRECTION\ColCor\submarine-color-correction"

rem Activate virtual environment and build
call .venv\Scripts\activate.bat
pyinstaller --onefile --windowed --name "SubmarineColorCorrection" --distpath "./executable" src/main.py

echo.
echo Build complete! Check the 'executable' folder for SubmarineColorCorrection.exe
pause
