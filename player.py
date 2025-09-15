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
        self.is_paused = False
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
            data = self.audio_queue.get(timeout=0.5)  # Use a small timeout
        except queue.Empty:
            logger.error("Buffer is empty! Increase buffer_size.")
            raise sd.CallbackAbort

        # --- Handle looping and padding correctly ---
        if len(data) < len(outdata):
            # This is the last chunk of the file
            outdata[: len(data)] = data
            outdata[len(data) :] = b"\x00" * (
                len(outdata) - len(data)
            )  # Pad with silence
            if not self.loop:
                # Only stop the stream if we are not supposed to loop
                raise sd.CallbackStop
            # If self.loop is True, we do nothing here. The _read_chunks thread
            # is already rewinding the file and will refill the queue.
        else:
            outdata[:] = data

    def _read_chunks(self):
        """The file reader function, now with looping logic."""
        logger.info("Audio reader thread started.")
        while not self.playback_finished.is_set():
            if self.is_paused:
                time.sleep(0.1)
                continue
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
            self.is_paused = False
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
        self.is_paused = False
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
        if self.is_playing and not self.is_paused:
            self.is_paused = True
            if self._stream is not None:
                self._stream.stop()
            logger.info("Playback paused.")

    def resume(self):
        if self.is_paused:
            self.is_paused = False
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
