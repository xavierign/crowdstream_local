# crowdstream_local

Minimal Python audio loop server that plays multiple audio files simultaneously,
loops them seamlessly, and prints precise timing information for every loop
restart. The server focuses solely on timing validation so future features can
build on a reliable playback foundation.

## Requirements

- Python 3.10+
- NumPy
- SoundFile
- PyAudio

Install dependencies with:

```bash
pip install numpy soundfile pyaudio
```

## Usage

Provide one or more audio files when starting the server. All files must share
the same sample rate.

```bash
python audio_server.py loop_a.wav loop_b.wav
```

Press `Ctrl+C` to stop the server. While running, the console reports the exact
elapsed time for each loop completion alongside the time since the server
started.
