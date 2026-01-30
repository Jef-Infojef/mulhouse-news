@echo off
title SERVEUR MULHOUSE NEWS
cd /d "C:\dev\Mulhouse-News"
echo Lancement du serveur Next.js (Mulhouse News)...
echo Les logs sont rediriges vers nextjs-logs.txt
npm run dev > nextjs-logs.txt 2>&1
