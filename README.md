# Speech Transcription Tool

A GUI application for real-time speech transcription using OpenAI's Whisper model.

## Issue Resolution

The original `speech_transcription.py` uses PyAudio, which has compatibility issues with Python 3.13 on macOS. The error you encountered:

```
Could not import the PyAudio C module 'pyaudio._portaudio'.
ImportError: dlopen(...): symbol not found in flat namespace '_PaMacCore_SetupChannelMap'
```

## Solution

I've created an alternative version `speech_transcription_alt.py` that uses `sounddevice` instead of PyAudio. This version is fully compatible with Python 3.13.

## Installation

1. Activate your virtual environment:

   ```bash
   source venv/bin/activate
   ```

2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. **Install FFmpeg** (required for audio processing):

   ```bash
   brew install ffmpeg
   ```

4. **Fix SSL Certificate Issues (macOS)**: If you encounter SSL certificate errors when loading the Whisper model, run:
   ```bash
   "/Applications/Python 3.13/Install Certificates.command"
   ```

## Usage

Run the alternative version:

```bash
python speech_transcription_alt.py
```

## Features

- Real-time speech recording and transcription
- Multiple Whisper model options (tiny, base, small, medium, large)
- Copy transcription to clipboard
- Save transcription to file
- macOS native UI integration
- SSL certificate handling for model downloads

## Requirements

- Python 3.13 (or earlier versions)
- FFmpeg (for audio processing)
- Microphone permissions granted to Terminal/Python
- Internet connection for initial Whisper model download

## Troubleshooting

### FFmpeg Missing

If you get "no such file or directory ffmpeg":

```bash
brew install ffmpeg
```

### SSL Certificate Issues

If you get SSL certificate errors when loading the Whisper model:

1. Run: `"/Applications/Python 3.13/Install Certificates.command"`
2. Or try: `pip install --upgrade certifi`

### Homebrew macOS Version Issues

If you get "unknown or unsupported macOS version":

1. Update Homebrew: `brew update`
2. If that fails, run: `git -C /usr/local/Homebrew/Library/Taps/homebrew/homebrew-core fetch --unshallow`

### Microphone Permission Issues

If you encounter microphone permission issues on macOS:

1. Go to System Preferences > Security & Privacy > Privacy > Microphone
2. Add Terminal or your Python executable to the allowed apps
3. Restart the application

### Model Loading Issues

The application now includes automatic SSL certificate handling. If the model still fails to load:

1. Check your internet connection
2. Try running the certificate installation command above
3. Restart the application
