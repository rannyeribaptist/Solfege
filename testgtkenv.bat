@echo off
rem GNU Solfege - free ear training
rem Copyright (C) 2009  Tom Cato Amundsen
rem

if exist configure.ac goto infomsg

:runsolfege
python.exe testgtkenv.py
goto end
:infomsg
echo.
echo This script should only be run when installed into the win32 folder
echo or after the generated installer is installed.
echo It is used for debugging to check if the user has a sane environment.
echo.
:end
pause
