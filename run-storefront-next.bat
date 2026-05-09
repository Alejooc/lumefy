@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "APP_DIR=%ROOT_DIR%storefront_next"

if not exist "%APP_DIR%\package.json" (
  echo [ERROR] No se encontro storefront_next en: %APP_DIR%
  pause
  exit /b 1
)

pushd "%APP_DIR%"

if not exist ".env.local" (
  if exist ".env.example" (
    copy /Y ".env.example" ".env.local" >nul
    echo [INFO] Se creo .env.local desde .env.example
    echo [INFO] Revisa NEXT_PUBLIC_API_URL y NEXT_PUBLIC_ROOT_DOMAIN en .env.local
  )
)

if not exist "node_modules" (
  echo [INFO] Instalando dependencias...
  call npm install
  if errorlevel 1 (
    echo [ERROR] Fallo npm install
    popd
    pause
    exit /b 1
  )
)

echo [INFO] Iniciando storefront_next en http://localhost:3000
call npm run dev

popd
endlocal
