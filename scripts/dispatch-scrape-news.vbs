Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "%comspec% /c ""C:\dev\mulhouse-news\scripts\dispatch-scrape-news.cmd""", 0, True
