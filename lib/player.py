import queue
import threading
from pathlib import Path
import sounddevice as sd
import soundfile as sf
from loguru import logger
import numpy as np

class AudioPlayer:
    def __init__(
        self,
        filepath,
        device=None,
        blocksize=2048,
        buffer_size=20,
        loop_by_default=True,
        preload=False # New option to preload the file
    ):
        self.filepath = Path(filepath)
        self.device = device
        self.blocksize = blocksize
        self.buffer_size = buffer_size
        self.audio_queue = queue.Queue(maxsize=buffer_size)
        self.loop = loop_by_default
        self.preload_data = None

        self.playback_finished = threading.Event()
        self.stop_event = threading.Event()
        self._is_paused = False

        self._reader_thread = None
        self._stream = None
        self._file_handle = None

        if not self.filepath.exists():
            raise FileNotFoundError(f"Audio file not found: {self.filepath}")

        # *** Preload audio data if requested (For small silent audio file used to keep the audio out active...)
        if preload:
            try:
                self.preload_data, samplerate = sf.read(self.filepath, dtype='float32')
                logger.info(f"Preloaded '{self.filepath.name}' into memory.")
            except Exception as e:
                logger.error(f"Failed to preload audio file: {e}")
                self.preload_data = None


    def _callback(self, outdata, frames, time, status):
        if status.output_underflow:
            logger.error("Output underflow! Increase buffer_size.")
            raise sd.CallbackAbort

        if self._is_paused:
            outdata[:] = 0 # Send silence when paused
            return

        try:
            data = self.audio_queue.get_nowait()
            chunk_size = len(data)
            outdata[:chunk_size] = data
            if chunk_size < len(outdata):
                outdata[chunk_size:] = 0 # Pad with silence if chunk is too small
        except queue.Empty:
            outdata[:] = 0 # Send silence if the queue is empty

    def _read_chunks_from_disk(self):
        """The original file reader function."""
        logger.info(f"Audio reader thread started for {self.filepath.name} (Disk Mode).")
        while not self.stop_event.is_set():
            try:
                if self._is_paused:
                    time.sleep(0.1)
                    continue

                numpy_array = self._file_handle.read(self.blocksize)
                if not numpy_array.any(): # Check if the array is all zeros (end of file)
                    if self.loop:
                        self._file_handle.seek(0)
                        continue
                    else:
                        break # End of file and not looping
                self.audio_queue.put(numpy_array)
            except Exception as e:
                logger.error(f"Error in disk reader thread: {e}")
                break
        logger.info(f"Audio reader thread finished for {self.filepath.name}.")

    def _read_chunks_from_ram(self):
        """New reader that serves data from the preloaded numpy array."""
        logger.info(f"Audio reader thread started for {self.filepath.name} (RAM Mode).")
        position = 0
        while not self.stop_event.is_set():
            try:
                if self._is_paused:
                    time.sleep(0.1)
                    continue
                
                # Get the next chunk from the preloaded data
                chunk = self.preload_data[position : position + self.blocksize]
                position += self.blocksize
                
                # If we've reached the end of the data
                if len(chunk) == 0:
                    if self.loop:
                        position = 0 # Reset to the beginning
                        continue
                    else:
                        break # End of data and not looping

                self.audio_queue.put(chunk)

            except Exception as e:
                logger.error(f"Error in RAM reader thread: {e}")
                break
        logger.info(f"Audio reader thread finished for {self.filepath.name}.")


    def play(self):
        try:
            if self.preload_data is not None:
                # Get info from the preloaded data
                info = sf.info(str(self.filepath))
                samplerate = info.samplerate
                channels = info.channels
                target_thread = self._read_chunks_from_ram
            else:
                # Get info by opening the file
                self._file_handle = sf.SoundFile(self.filepath)
                samplerate = self._file_handle.samplerate
                channels = self._file_handle.channels
                target_thread = self._read_chunks_from_disk
            
            self.stop_event.clear()
            self._is_paused = False

            self._reader_thread = threading.Thread(target=target_thread)
            self._reader_thread.daemon = True
            self._reader_thread.start()

            self._stream = sd.OutputStream(
                samplerate=samplerate,
                channels=channels,
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
        if not self._is_paused:
            self._is_paused = True
            logger.info("Playback paused.")

    def resume(self):
        if self._is_paused:
            self._is_paused = False
            logger.info("Playback resumed.")

    def wait(self):
        self.playback_finished.wait()

    @property
    def is_playing(self):
        return not self.playback_finished.is_set() and not self.stop_event.is_set()