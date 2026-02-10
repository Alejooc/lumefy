@echo off
cd /d %~dp0
echo Iniciando Frontend Lumefy...
start http://localhost:4200
npm start
pause
