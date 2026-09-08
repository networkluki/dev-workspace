@echo off
py -3 "%~dp0exa.py" %*
exit /b %errorlevel%
