# Extract Audio

The **Extract Audio** app is a unified tool for extracting or isolating audio from media files. It supports extracting full audio tracks from videos and isolating specific stems like vocals or background music using AI.

## Features

- **Extract All Audio (Copy)**: Quickly extracts the full audio track from video files without re-encoding the video.
- **Isolate Vocal Track (AI)**: Uses AI (Demucs/Audio-Separator) to isolate the vocal track from an audio or video source.
- **Isolate Background Music (AI)**: Uses AI to isolate the background music (instrumental) from an audio or video source.

## How to Use

1. **Input Media**: Drag and drop video or audio files into the drop zone.
2. **Extraction Mode**: Select your desired mode from the dropdown menu.
3. **Run**: Click the **Extract** button to begin the process.
4. **Results**: The extracted files will be saved in a subfolder next to the source files (`Extracted_Audio` or `Separated_Audio`).

## Requirements

- **FFmpeg**: Required for basic audio extraction.
- **AI Models**: Required for vocal/BGM isolation. These may be downloaded automatically on first use.
