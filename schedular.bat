@echo off
setlocal
cd /d "C:\inetpub\wwwroot\nspl"
call "C:\inetpub\wwwroot\nspl\env\Scripts\activate.bat"
python manage.py run_daily_jobs >> logs\scheduler_log.txt 2>&1
endlocal
