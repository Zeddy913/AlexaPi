import os
import threading
import logging

import alsaaudio

import alexapi.triggers as triggers
from .basetrigger import BaseTrigger
from snowboy import snowboydetect

logger = logging.getLogger(__name__)

RESOURCE_FILE = "snowboy/common.res"


class SnowboyTrigger(BaseTrigger):

	type = triggers.TYPES.VOICE

	def __init__(self, config, trigger_callback):
		super(SnowboyTrigger, self).__init__(config, trigger_callback, 'snowboy')

		self._enabled_lock = threading.Event()
		self._disabled_sync_lock = threading.Event()
		self._detector = None

	def setup(self):
		# Get recognition parameters from config
		model_path = self._tconfig['model_path']
		audio_gain = self._tconfig['audio_gain']
		sensitivity = self._tconfig['sensitivity']

		self._detector = snowboydetect.SnowboyDetect(
                    resource_filename=RESOURCE_FILE.encode(), model_str=model_path.encode())
                self._detector.SetAudioGain(audio_gain)

                self._detector.SetSensitivity("1".encode())



	def run(self):
		thread = threading.Thread(target=self.thread, args=())
		thread.setDaemon(True)
		thread.start()

	def thread(self):
		while True:
			self._enabled_lock.wait()

			# Enable reading microphone raw data
			inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, self._config['sound']['input_device'])
			inp.setchannels(1)
			inp.setrate(16000)
			inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
			inp.setperiodsize(1024)

			triggered = False
			while not triggered:

				if not self._enabled_lock.isSet():
					break

				# Read from microphone
				_, buf = inp.read()

				# Detect if keyword/trigger word was said
				ans = self._detector.RunDetection(buf)

				if ans == -1:
                                        logger.warning("Error initializing streams or reading audio data")
                                elif ans > 0:
                                        triggered = ans is not None

			# To avoid overflows close the microphone connection
			inp.close()

			self._disabled_sync_lock.set()

			if triggered:
				self._trigger_callback(self)

	def enable(self):
		self._enabled_lock.set()
		self._disabled_sync_lock.clear()

	def disable(self):
		self._enabled_lock.clear()
		self._disabled_sync_lock.wait()
