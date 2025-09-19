import queue
import threading
from pathlib import Path
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
        self.stop_event = threading.Event()
        self._is_paused = False # Use a simple boolean for pause state

        self.loop = loop_by_default
        self._reader_thread = None
        self._stream = None
        self._file_handle = None

        if not self.filepath.exists():
            raise FileNotFoundError(f"Audio file not found: {self.filepath}")

    def _callback(self, outdata, frames, time, status):
        """The audio callback function that feeds the stream."""
        if status.output_underflow:
            logger.error("Output underflow! Increase buffer_size.")
            raise sd.CallbackAbort

        # If paused, just feed silence and return immediately.
        if self._is_paused:
            # --- FIX: Correct way to write silence to a CFFI buffer ---
            outdata[:] = b'\x00' * len(outdata)
            return

        try:
            data = self.audio_queue.get_nowait()
            if len(data) < len(outdata):
                outdata[:len(data)] = data
                outdata[len(data):] = b'\x00' * (len(outdata) - len(data))
                if not self.loop:
                    raise sd.CallbackStop
            else:
                outdata[:] = data
        except queue.Empty:
            # This can happen briefly. Outputting silence is a safe fallback.
            # --- FIX: Correct way to write silence to a CFFI buffer ---
            outdata[:] = b'\x00' * len(outdata)

    def _read_chunks(self):
        """The file reader function."""
        logger.info("Audio reader thread started.")
        while not self.stop_event.is_set():
            try:
                if self._is_paused:
                    # When paused, sleep briefly to prevent this loop from
                    # consuming CPU unnecessarily.
                    threading.Event().wait(0.1)
                    continue

                if self._file_handle is None:
                    break

                numpy_array = self._file_handle.read(self.blocksize, dtype="float32")

                if not numpy_array.size:
                    if self.loop:
                        self._file_handle.seek(0)
                        continue
                    else:
                        break # End of file
                
                # This will block until there is space in the queue.
                self.audio_queue.put(numpy_array.tobytes(), timeout=0.5)

            except queue.Full:
                # If the queue is full, just wait and try again.
                continue
            except Exception as e:
                logger.error(f"Error in reader thread: {e}")
                break
        logger.info("Audio reader thread finished.")

    def play(self):
        """Starts audio playback."""
        try:
            self._file_handle = sf.SoundFile(self.filepath)
            self.stop_event.clear()
            self._is_paused = False

            self._reader_thread = threading.Thread(target=self._read_chunks)
            self._reader_thread.daemon = True
            self._reader_thread.start()

            self._stream = sd.RawOutputStream(
                samplerate=self._file_handle.samplerate,
                channels=self._file_handle.channels,
                blocksize=self.blocksize,
                device=self.device,
                dtype="float32",
                callback=self._callback,
                finished_callback=self.playback_finished.set,
            )
            self._stream.start()
            logger.success(f"Playback started for: {self.filepath.name}")

        except Exception as e:
            logger.exception(f"An unexpected error occurred: {e}")

    def stop(self):
        """Stops playback and cleans up all resources."""
        if self.stop_event.is_set():
            return
        logger.warning("Stopping playback...")
        self.stop_event.set()

        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=1)
        if self._stream:
            self._stream.stop()
            self._stream.close()
        if self._file_handle:
            self._file_handle.close()

        self.playback_finished.set()
        logger.info("Playback stopped.")

    def pause(self):
        """Pauses playback."""
        if not self._is_paused:
            self._is_paused = True
            logger.info("Playback paused.")

    def resume(self):
        """Resumes playback."""
        if self._is_paused:
            self._is_paused = False
            logger.info("Playback resumed.")

    def toggle_loop(self):
        """Toggles the looping state."""
        self.loop = not self.loop
        status = "ON" if self.loop else "OFF"
        logger.info(f"Looping is now {status}.")

    @property
    def is_playing(self):
        """Returns True if the audio is currently playing."""
        return not self.playback_finished.is_set() and not self.stop_event.is_set()