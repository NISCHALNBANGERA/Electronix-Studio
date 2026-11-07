@echo off
echo ========================================================
echo  Building Electronix Studio Desktop Application
echo ========================================================
echo.

:: 1. Ensure PyInstaller is installed in virtualenv
echo [1/3] Checking PyInstaller...
call .\.venv\Scripts\python.exe -m pip install pyinstaller

:: 2. Build the application with icon and assets
echo.
echo [2/3] Bundling application into standalone desktop app...
call .\.venv\Scripts\pyinstaller --noconfirm --onedir --windowed ^
    --name "ElectronixStudio" ^
    --icon "app_icon.ico" ^
    --add-data "app_icon.ico;." ^
    --add-data "app_icon.png;." ^
    --add-data "projects;projects" ^
    main.py

:: 3. Create Desktop Shortcut
echo.
echo [3/3] Creating shortcut on your Windows Desktop...
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $d = [Environment]::GetFolderPath('Desktop'); $s = $WshShell.CreateShortcut(\"$d\Electronix Studio.lnk\"); $s.TargetPath = (Convert-Path '.\dist\ElectronixStudio\ElectronixStudio.exe'); $s.WorkingDirectory = (Convert-Path '.\dist\ElectronixStudio'); $s.IconLocation = (Convert-Path '.\dist\ElectronixStudio\ElectronixStudio.exe') + ',0'; $s.Description = 'Electronix Studio - Digital Design & Learning Suite'; $s.Save()"

:: 4. Finish
echo.
echo ========================================================
echo  Build Complete!
echo  A shortcut named "Electronix Studio" 
echo  has been placed directly on your Windows Desktop!
echo ========================================================
pause
