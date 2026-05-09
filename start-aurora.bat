@echo off
set CI=true
cd /d C:\Users\ME\aurora-gracewood\backend
C:\Python310\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 8000 > ..\uvicorn.log 2>&1
