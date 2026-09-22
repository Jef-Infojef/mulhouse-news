@echo off
setlocal
echo [%date% %time%] dispatch scrape-news.yml >> "C:\dev\mulhouse-news\scripts\logs\scrape-news-dispatch.log"
"C:\Program Files\GitHub CLI\gh.exe" workflow run scrape-news.yml -R Jef-Infojef/mulhouse-news --ref main >> "C:\dev\mulhouse-news\scripts\logs\scrape-news-dispatch.log" 2>&1
