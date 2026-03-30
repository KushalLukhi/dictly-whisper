# Dictly Whisper

Open-source offline Whisper dictation app for Windows desktop voice typing and local speech-to-text.

[![GitHub Releases](https://img.shields.io/github/v/release/KushalLukhi/dictly-whisper?display_name=tag)](https://github.com/KushalLukhi/dictly-whisper/releases)
[![Download Latest](https://img.shields.io/badge/Download-Windows%20ZIP-2563eb)](https://github.com/KushalLukhi/dictly-whisper/releases/latest)

Dictly is an open-source offline Whisper dictation app for Windows built around Whisper, faster-whisper, WhisperX, and local speech-to-text workflows. Hold a hotkey, speak, release, and Dictly transcribes your voice locally and pastes the text into the active app. No API keys, no cloud dependency, no subscription.

## What Dictly Is

Dictly is a local AI dictation tool for:

- offline voice typing on Windows
- Whisper speech recognition
- faster-whisper transcription
- push-to-talk speech to text
- desktop dictation in any app

If someone is searching for a Whisper dictation app, offline speech-to-text for Windows, open-source voice typing software, or a faster-whisper desktop transcription tool, this repository is for that use case.

## Open Source

Dictly is released under the MIT license in [LICENSE](LICENSE).

This repository is the source code. End users do not need to install Python packages if you publish the packaged Windows build from GitHub Releases.

## Features

- Offline transcription with Whisper and faster-whisper
- Push-to-talk global hotkey
- Desktop waveform overlay
- Settings UI for backend, model, beam size, language, theme, and device
- Transcription history
- Tray icon and startup option
- CPU fallback when GPU backend is unavailable
- Packaged Windows EXE build for non-technical users

## Keywords

Whisper, faster-whisper, whisperx, speech to text, offline dictation, Windows dictation, voice typing, local transcription, AI dictation, desktop dictation, push-to-talk transcription, offline voice input, open source Whisper app, offline speech recognition, Windows voice typing, local AI transcription, desktop speech-to-text.

## Download

Latest release:

- Releases page: `https://github.com/KushalLukhi/dictly-whisper/releases`
- Latest release: `https://github.com/KushalLukhi/dictly-whisper/releases/latest`

GitHub does not run `.exe` files inside the repository page itself. For Windows users, the correct flow is:

1. Open the repo's **Releases** page.
2. Download `Dictly-windows.zip`.
3. Extract the ZIP on your PC.
4. Open the extracted `Dictly` folder.
5. Run `Dictly.exe`.

Do not download only the standalone `.exe` from inside the folder tree. The app needs the bundled `_internal` files next to it.

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

## Build A Windows Installer

If you want a normal Windows installer instead of opening the packaged EXE folder directly:

1. Build the app package first.
2. Run:

```powershell
.\build-installer.bat
```

Installer output:

- `installer-dist\Dictly-Setup.exe`

Default behavior:

- uses Inno Setup if available
- otherwise falls back to a built-in IExpress installer

The installer puts Dictly under the current user's `AppData\Local\Programs\Dictly` folder and creates Start Menu shortcuts.

## Build An Offline Windows Installer

If you want users to install Dictly without downloading models on first run, bundle models into the app before building the installer.

Recommended flow:

1. Download the models you want to ship:

```powershell
.\download-models.bat
```

2. Build the offline installer:

```powershell
.\build-offline-installer.bat
```

Notes:

- The build includes everything found under `models\`
- The installer will contain those bundled model files
- Larger models make the installer much bigger
- For most users, bundling `small` is the best size versus quality tradeoff

## Publishing Releases On GitHub

Recommended release flow:

1. Build the Windows package locally.
2. Open GitHub and create a new Release.
3. Upload `Dictly-windows.zip` as a release asset.
4. Tell users to download the ZIP from Releases, extract it, and run `Dictly.exe`.

## Current Backend Notes

- `auto`: prefers the best available supported backend
- `insanely-fast-whisper`: CUDA-only `transformers` backend tuned for fast chunked Whisper inference
- `faster-whisper`: reliable CPU path with optional CUDA device selection
- `whisperx`: experimental live mode without alignment or diarization
- `whisper-directml`: optional and guarded; falls back to CPU if unsupported

## Offline Model Setup

Dictly can now load `faster-whisper` models from disk instead of downloading them from the Hugging Face Hub.

To download every Dictly model locally into the repo:

```powershell
.\download-models.bat
```

This downloads:

- `tiny`
- `base`
- `small`
- `medium`
- `large-v2`
- `large-v3`

The files are stored under `models\<model-name>` and are automatically picked up by the packaged app.

Option 1: pick a local model folder in Settings.

- Open `Settings`
- Set `Model` to match the local model you downloaded, for example `small`
- Set `Local Model Directory` to the extracted model folder
- Save and reload

Option 2: bundle models into the packaged app.

Place the model files under this repo before building:

```text
models/
  small/
    config.json
    model.bin
    tokenizer.json
    vocabulary.json
    ...
```

Then rebuild with:

```powershell
.\build.bat
```

The packaged app will automatically look for bundled models under `models\<model-name>` before trying the Hub.

## Insanely Fast Whisper Notes

The `insanely-fast-whisper` backend is intended for NVIDIA CUDA systems with `torch` + `transformers` available.

- It is not used by `auto`; select it explicitly in Settings.
- It falls back to `faster-whisper` if CUDA or the required Python deps are unavailable.
- It uses OpenAI Whisper checkpoints from Hugging Face such as `openai/whisper-small`.
- The shared `Local Model Directory` field must point to a transformers-compatible Whisper model folder for this backend. The bundled `models/` layout produced by `download_models.py` is for faster-whisper and should not be reused here.

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

- The packaged app still downloads Whisper model weights on first use unless a compatible local or bundled model directory is provided.
- First-run model downloads depend on valid TLS certificates. Packaged Windows builds now try the Windows trust store first, then fall back to `certifi`; machines behind SSL inspection still need their root CA installed in Windows.
- Global hotkeys, microphone access, and text insertion behavior can vary across operating systems.
