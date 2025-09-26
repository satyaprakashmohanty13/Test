#!/usr/bin/env python3

from parsers import FType

class parser(FType):
	DESC = "MP3 / MPEG-1 Audio Layer III (no ID3 tag)"
	TYPE = "MP3"
	# No single MAGIC, so we override identify()

	def __init__(self, data=""):
		FType.__init__(self, data)
		self.data = data
		# MP3s are streams and generally tolerate appended data.
		self.bAppData = True

		# For simplicity, we don't support complex operations like parasites
		# on raw MP3 frames. The id3v2 parser handles that for tagged files.
		self.bParasite = False

	def identify(self):
		"""
		Identifies an MP3 file by looking for a frame sync word.
		It deliberately ignores files with ID3v2 tags, as those are handled
		by the id3v2 parser.
		"""
		# Let the id3v2 parser handle tagged files.
		if self.data.startswith(b'ID3'):
			return False

		# Check for the MP3 frame sync word (11 leading bits set to 1).
		# This means the first byte is 0xFF and the upper 3 bits of the
		# second byte are 111 (masked as 0xE0).
		if len(self.data) > 1 and self.data[0] == 0xFF and (self.data[1] & 0xE0) == 0xE0:
			return True

		return False