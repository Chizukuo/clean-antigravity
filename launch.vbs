Set oWS = WScript.CreateObject("WScript.Shell")
sHome = oWS.ExpandEnvironmentStrings("%USERPROFILE%")
sScriptPath = sHome & "\.gemini\launch_antigravity.py"
oWS.Run "python.exe """ & sScriptPath & """", 0, False
