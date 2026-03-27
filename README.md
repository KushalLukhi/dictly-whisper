# Dictly

Offline push-to-talk dictation for desktop apps.

Hold a hotkey, speak, release, and Dictly transcribes locally with Whisper and pastes the text into the active app. No API keys, no cloud dependency, no subscription.

## Open Source

Dictly is released under the MIT license in [LICENSE](LICENSE).

This repository is the source code. End users do not need to install Python packages if you publish the packaged Windows build from GitHub Releases.

## Features

- Offline transcription with Whisper
- Push-to-talk global hotkey
- Desktop waveform overlay
- Settings UI for backend, model, beam size, language, and theme
- Transcription history
- Tray icon and startup option
- CPU fallback when GPU backend is unavailable

## Download

For normal users, publish the Windows release artifact from GitHub Releases:

- `Dictly-windows.zip`

After download:

1. Extract the ZIP.
2. Open the `Dictly` folder.
3. Run `Dictly.exe`.

No `pip install` is required for release users.

## Run From Source

```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
python .\main.py
```

## Build The Windows EXE

```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements-build.txt
.\build.bat
```

Build output:

- Folder build: `dist\Dictly\`
- Release ZIP: `dist\Dictly-windows.zip`

Users can run that packaged build directly without installing Python or project dependencies.

## GitHub Release Workflow

This repo includes a GitHub Actions workflow that builds a Windows release ZIP.

Recommended release flow:

1. Push the repository to GitHub.
2. Create a tag such as `v0.1.0`.
3. Push the tag.
4. GitHub Actions builds `Dictly.exe` and uploads `Dictly-windows.zip` to the release.

You can also trigger the workflow manually from the Actions tab.

## Current Backend Notes

- `auto`: prefers the best available supported backend
- `faster-whisper`: reliable CPU path
- `whisper-directml`: optional and guarded; falls back to CPU if unsupported

## Project Layout

```text
app.py
config_manager.py
dictation_overlay.py
history_manager.py
main.py
recorder.py
settings_window.py
startup_manager.py
transcriber.py
transcription_backends.py
tray.py
typer.py
waveform_widget.py
dictly.spec
build.bat
requirements.txt
requirements-build.txt
```

## Notes For Contributors

- The packaged app still downloads Whisper model weights on first use.
- If you want fully offline first-run behavior, you need to pre-bundle model files separately.
- Global hotkeys, microphone access, and text insertion behavior can vary across operating systems.
