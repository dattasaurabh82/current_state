# player.py

import queue
import threading
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf
from loguru import logger

class AudioPlayer:
    """
    A non-blocking, buffered audio player.
    """
    def __init__(self, filepath, device=None, blocksize=2048, buffer_size=20):
        # --- Store Configuration ---
        self.filepath = Path(filepath)
        self.device = device
        self.blocksize = blocksize
        self.buffer_size = buffer_size

        # --- Initialize State ---
        # The queue and event are specific to each instance of the player
        self.audio_queue = queue.Queue(maxsize=buffer_size)
        self.playback_finished = threading.Event()

        # We'll keep track of the reader thread
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
            outdata[:len(data)] = data
            outdata[len(data):] = b'\x00' * (len(outdata) - len(data))
            raise sd.CallbackStop
        else:
            outdata[:] = data

    def _read_chunks(self):
        """The file reader function, now a method."""
        logger.info("Audio reader thread started.")
        while not self.playback_finished.is_set():
            # Use the instance's file handle
            numpy_array: np.ndarray = self._file_handle.read(self.blocksize, dtype='float32')
            buffer = numpy_array.tobytes()

            if not buffer:
                logger.info("End of file reached.")
                break
            self.audio_queue.put(buffer)
        logger.info("Audio reader thread finished.")

    # ---------------------- #
    # Public control methods #
    # ---------------------- #
    # player.py

    def play(self):
        """
        Starts audio playback in a non-blocking way.
        """
        try:
            # Open the file and store the handle in the instance
            self._file_handle = sf.SoundFile(self.filepath)

            samplerate = self._file_handle.samplerate
            channels = self._file_handle.channels
            dtype = 'float32'
            logger.info(f"File Info: {samplerate} Hz, {channels} channels, {dtype} format")

            # The target no longer needs the file handle passed as an argument
            self._reader_thread = threading.Thread(target=self._read_chunks)
            self._reader_thread.daemon = True
            self._reader_thread.start()

            # FIX: Replace the ellipsis with the actual stream parameters
            self._stream = sd.RawOutputStream(
                samplerate=samplerate,
                blocksize=self.blocksize,
                device=self.device,
                channels=channels,
                dtype=dtype,
                callback=self._callback,
                finished_callback=self.playback_finished.set,
            )
            self._stream.start()
            # FIX: Complete the logger message
            logger.success(f"Playback started for: {self.filepath.name}")

        except Exception as e:
            logger.exception(f"An unexpected error occurred during playback setup: {e}")

    def stop(self):
        """Stops the playback and cleans up resources."""
        logger.warning("Stopping playback...")
        self.playback_finished.set()
        if self._reader_thread:
            self._reader_thread.join()
        if self._stream:
            self._stream.stop()
            self._stream.close()

        # ... To close the file handle
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None

    def wait(self):
        """Waits for the playback to complete."""
        self.playback_finished.wait()

    @property
    def is_playing(self):
        """Returns True if the audio is currently playing."""
        return not self.playback_finished.is_set()