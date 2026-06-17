Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "d:\PERSONAL\GRACE"
WshShell.Run "d:\PERSONAL\GRACE\venv\Scripts\python.exe d:\PERSONAL\GRACE\main.py", 0, False
