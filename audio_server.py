"""Minimal looping audio server.

The server starts a precise timer, plays the provided audio files in a loop,
and prints the exact timing for every loop completion.
"""

from __future__ import annotations

import argparse
import threading
import time
from pathlib import Path
from typing import List, Sequence

import numpy as np
import pyaudio
import soundfile as sf


class LoopingAudioTrack:
    """Load an audio file and expose looping playback."""

    def __init__(self, file_path: Path, index: int) -> None:
        self.file_path = Path(file_path)
        self.index = index
        self.name = self.file_path.stem

        data, sample_rate = sf.read(self.file_path, dtype=np.float32)
        if data.ndim == 1:
            data = np.column_stack((data, data))
        elif data.shape[1] == 1:
            data = np.tile(data, (1, 2))

        self.audio_data = data
        self.sample_rate = sample_rate
        self.frames = len(data)
        self.position = 0
        self.last_loop_timestamp: float | None = None

        self.duration_seconds = self.frames / float(self.sample_rate)

        memory_mb = (self.frames * self.audio_data.shape[1] * 4) / (1024 * 1024)
        print(f"✅ Loaded track {self.index}: {self.name} ({memory_mb:.1f} MB)")

    def next_chunk(self, chunk_size: int) -> tuple[np.ndarray, List[float]]:
        """Return the next chunk of audio and timestamps where looping occurred."""
        output = np.zeros((chunk_size, 2), dtype=np.float32)
        out_pos = 0
        loop_events: List[float] = []

        while out_pos < chunk_size:
            remaining = self.frames - self.position
            if remaining <= 0:
                self.position = 0
                continue

            to_copy = min(chunk_size - out_pos, remaining)
            end_pos = self.position + to_copy
            output[out_pos:out_pos + to_copy] = self.audio_data[self.position:end_pos]
            self.position = end_pos
            out_pos += to_copy

            if self.position >= self.frames:
                self.position = 0
                loop_events.append(time.perf_counter())

        return output, loop_events


class SimpleLoopServer:
    """Play multiple audio files in sync and report loop timing."""

    def __init__(self, audio_paths: Sequence[Path], chunk_size: int = 1024, device: int | None = None):
        if not audio_paths:
            raise ValueError("At least one audio file must be provided")

        self.chunk_size = chunk_size
        self.tracks = [LoopingAudioTrack(path, idx) for idx, path in enumerate(audio_paths, start=1)]

        sample_rates = {track.sample_rate for track in self.tracks}
        if len(sample_rates) != 1:
            raise ValueError("All audio files must share the same sample rate")
        self.sample_rate = sample_rates.pop()

        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(
            format=pyaudio.paFloat32,
            channels=2,
            rate=self.sample_rate,
            output=True,
            frames_per_buffer=self.chunk_size,
            output_device_index=device,
        )

        self.running = False
        self.start_timestamp: float | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        self.running = True
        self.start_timestamp = time.perf_counter()
        for track in self.tracks:
            track.last_loop_timestamp = self.start_timestamp
        print("🎛️ Simple loop server starting")
        print(f"   • Tracks: {len(self.tracks)}")
        print(f"   • Sample rate: {self.sample_rate} Hz")
        print(f"   • Chunk size: {self.chunk_size} frames")
        print(f"   • Start timestamp: {self.start_timestamp:.9f}")

        self.thread = threading.Thread(target=self._audio_loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.pa:
            self.pa.terminate()
        print("👋 Simple loop server stopped")

    def _audio_loop(self) -> None:
        assert self.start_timestamp is not None
        while self.running:
            mix = np.zeros((self.chunk_size, 2), dtype=np.float32)
            for track in self.tracks:
                chunk, loop_events = track.next_chunk(self.chunk_size)
                mix += chunk

                for event_time in loop_events:
                    last_start = track.last_loop_timestamp or self.start_timestamp
                    loop_duration = event_time - last_start
                    since_start = event_time - self.start_timestamp
                    print(
                        f"🔁 Track {track.index} ({track.name}) looped: "
                        f"{loop_duration:.9f}s since previous start | "
                        f"{since_start:.9f}s since server start"
                    )
                    track.last_loop_timestamp = event_time

            mix /= max(len(self.tracks), 1)
            self.stream.write(mix.astype(np.float32).tobytes())

    def wait_forever(self) -> None:
        try:
            while self.running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n🛑 Interrupt received")
            self.stop()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Loop audio files and report timing")
    parser.add_argument("files", nargs="+", type=Path, help="Audio files to loop")
    parser.add_argument("--chunk-size", type=int, default=1024, help="Audio buffer size (default: 1024)")
    parser.add_argument("--device", type=int, help="PyAudio output device index")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    server = SimpleLoopServer(args.files, chunk_size=args.chunk_size, device=args.device)
    server.start()
    server.wait_forever()


if __name__ == "__main__":
    main()
