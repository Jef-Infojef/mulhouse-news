@echo off
title LOGS MULHOUSE NEWS
cd /d "C:\dev\Mulhouse-News"
powershell -Command "Get-Content nextjs-logs.txt -Wait -Tail 100"
