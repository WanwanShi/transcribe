@echo off
echo Starting Speech Transcription Tool...
cd /d C:\Chatbot
call venv\Scripts\activate
python speech_transcription_windows.py
pause 