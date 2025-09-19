import queue
import threading
from pathlib import Path
import time
import numpy as np
import sounddevice as sd
import soundfile as sf
from loguru import logger


class AudioPlayer:
    def __init__(
        self,
        filepath,
        device=None,
        blocksize=2048,
        buffer_size=20,
        loop_by_default=True,
    ):
        self.filepath = Path(filepath)
        self.device = device
        self.blocksize = blocksize
        self.buffer_size = buffer_size
        self.audio_queue = queue.Queue(maxsize=buffer_size)
        self.playback_finished = threading.Event()
        self.is_paused = threading.Event()  # Use an Event for pausing
        self.loop = loop_by_default
        self._reader_thread = None
        self._stream = None
        self._file_handle = None

        if not self.filepath.exists():
            raise FileNotFoundError(f"Audio file not found: {self.filepath}")

    def _callback(self, outdata, frames, time, status):
        """The audio callback function"""
        if status.output_underflow:
            logger.error("Output underflow! Increase buffer_size.")
            raise sd.CallbackAbort

        try:
            data = self.audio_queue.get_nowait()
        except queue.Empty:
            logger.error("Buffer is empty! Increase buffer_size.")
            raise sd.CallbackAbort

        if len(data) < len(outdata):
            outdata[: len(data)] = data
            outdata[len(data) :] = b"\x00" * (len(outdata) - len(data))
            if not self.loop:
                raise sd.CallbackStop
        else:
            outdata[:] = data

    def _read_chunks(self):
        """The file reader function, now with looping logic."""
        logger.info("Audio reader thread started.")
        while not self.playback_finished.is_set():
            self.is_paused.wait()  # This will block if pause() is called

            if self._file_handle is None:
                break

            numpy_array: np.ndarray = self._file_handle.read(
                self.blocksize, dtype="float32"
            )

            if not numpy_array.size:
                if self.loop:
                    logger.info("End of file reached. Looping back to the beginning.")
                    self._file_handle.seek(0)
                    continue
                else:
                    logger.info("End of file reached. No looping.")
                    break

            buffer = numpy_array.tobytes()
            self.audio_queue.put(buffer)

        logger.info("Audio reader thread finished.")

    def play(self):
        try:
            self._file_handle = sf.SoundFile(self.filepath)
            self.playback_finished.clear()
            self.is_paused.set()  # Set to "not paused" state initially
            samplerate = self._file_handle.samplerate
            channels = self._file_handle.channels
            self._reader_thread = threading.Thread(target=self._read_chunks)
            self._reader_thread.daemon = True
            self._reader_thread.start()
            self._stream = sd.RawOutputStream(
                samplerate=samplerate,
                blocksize=self.blocksize,
                device=self.device,
                channels=channels,
                dtype="float32",
                callback=self._callback,
                finished_callback=self.playback_finished.set,
            )
            self._stream.start()
            logger.success(f"Playback started for: {self.filepath.name}")
        except Exception as e:
            logger.exception(f"An unexpected error occurred during playback setup: {e}")

    def stop(self):
        logger.warning("Stopping playback...")
        self.playback_finished.set()
        self.is_paused.set()  # Ensure the reader thread is not blocked
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join()
        if self._stream:
            self._stream.stop()
            self._stream.close()
        if self._file_handle:
            self._file_handle.close()
        self._stream = None
        self._file_handle = None

    def pause(self):
        if self.is_playing and self.is_paused.is_set():
            self.is_paused.clear()  # This will cause the reader thread to block
            if self._stream is not None:
                self._stream.stop()
            logger.info("Playback paused.")

    def resume(self):
        if self.is_playing and not self.is_paused.is_set():
            self.is_paused.set()  # Unblock the reader thread
            if self._stream is not None:
                self._stream.start()
                logger.info("Playback resumed.")
            else:
                logger.warning("Cannot resume: audio stream is not initialized.")

    def wait(self):
        self.playback_finished.wait()

    def toggle_loop(self):
        self.loop = not self.loop
        status = "ON" if self.loop else "OFF"
        logger.info(f"Looping is now {status}.")

    @property
    def is_playing(self):
        return not self.playback_finished.is_set()
