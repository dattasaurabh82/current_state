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
        
        # --- Threading Events ---
        self.playback_finished = threading.Event()
        self.is_paused = threading.Event()
        self.stop_event = threading.Event()

        self.loop = loop_by_default
        self._reader_thread = None
        self._stream = None
        self._file_handle = None

        if not self.filepath.exists():
            raise FileNotFoundError(f"Audio file not found: {self.filepath}")

    def _callback(self, outdata, frames, time, status):
        """The audio callback function."""
        if status.output_underflow:
            logger.error("Output underflow! Increase buffer_size.")
            raise sd.CallbackAbort

        try:
            data = self.audio_queue.get_nowait()
        except queue.Empty:
            logger.error("Buffer is empty! This should not happen. Increase buffer_size.")
            outdata.fill(0) # Fill with silence to avoid glitches
            return

        if len(data) < len(outdata):
            outdata[:len(data)] = data
            outdata[len(data):] = b'\x00' * (len(outdata) - len(data))
            if not self.loop:
                raise sd.CallbackStop
        else:
            outdata[:] = data

    def _read_chunks(self):
        """The file reader function, now managed by events."""
        logger.info("Audio reader thread started.")
        while not self.stop_event.is_set():
            self.is_paused.wait() # Blocks here if pause() is called

            if self.stop_event.is_set():
                break # Exit if stop was called while paused

            try:
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
                
                # Wait until there is space in the queue before putting new data
                self.audio_queue.put(numpy_array.tobytes(), timeout=1)

            except queue.Full:
                # This is normal if playback is slower than reading.
                # Just continue the loop and try again.
                continue
            except Exception as e:
                logger.error(f"Error in reader thread: {e}")
                break

        logger.info("Audio reader thread finished.")

    def play(self):
        """Starts audio playback."""
        try:
            self._file_handle = sf.SoundFile(self.filepath)
            
            # Reset all events
            self.stop_event.clear()
            self.playback_finished.clear()
            self.is_paused.set() # Set to "not paused" state initially
            
            samplerate = self._file_handle.samplerate
            channels = self._file_handle.channels

            self._reader_thread = threading.Thread(target=self._read_chunks)
            self._reader_thread.daemon = True
            self._reader_thread.start()

            # Pre-fill the buffer before starting the stream
            while not self.audio_queue.full() and self._reader_thread.is_alive():
                time.sleep(0.01)

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
        """Stops playback and cleans up all resources."""
        if self.stop_event.is_set():
            return # Already stopping
        
        logger.warning("Stopping playback...")
        self.stop_event.set()
        self.is_paused.set() # Ensure the reader thread is not blocked
        
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=2)
        if self._stream:
            self._stream.stop()
            self._stream.close()
        if self._file_handle:
            self._file_handle.close()
        
        # Clear the queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        
        self._stream = None
        self._file_handle = None
        self.playback_finished.set()
        logger.info("Playback stopped and resources released.")

    def pause(self):
        """Pauses the audio stream and the file reader."""
        if self.is_playing and self.is_paused.is_set():
            self.is_paused.clear() # Block the reader thread
            if self._stream is not None:
                self._stream.stop()
            logger.info("Playback paused.")

    def resume(self):
        """Resumes a paused audio stream."""
        if self.is_playing and not self.is_paused.is_set():
            # 1. Unblock the reader thread FIRST
            self.is_paused.set()
            
            # 2. Wait for the buffer to have some data before starting the stream
            while self.audio_queue.empty() and self._reader_thread.is_alive():
                time.sleep(0.01) # Give the reader thread a moment to fill the queue

            # 3. Now it's safe to start the stream
            if self._stream is not None:
                self._stream.start()
                logger.info("Playback resumed.")
            else:
                logger.warning("Cannot resume: audio stream is not initialized.")

    def wait(self):
        """Waits for the playback to complete."""
        self.playback_finished.wait()

    def toggle_loop(self):
        """Toggles the looping state."""
        self.loop = not self.loop
        status = "ON" if self.loop else "OFF"
        logger.info(f"Looping is now {status}.")

    @property
    def is_playing(self):
        """Returns True if the audio is currently playing and not finished."""
        return not self.playback_finished.is_set() and not self.stop_event.is_set()