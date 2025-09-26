#!/usr/bin/env python3

from parsers import *
import random
import sys
import hashlib
import os.path
from args import *

__version__ = "0.3" # https://semver.org/
__date__ = "2023-03-25"
__description__ = "Mitra v%s (%s) by Ange Albertini" % (__version__, __date__)

PARSERS = [
# magic at 0
	arj, ar, bmp, bpg, cpio, cab, ebml, elf, flac, flv, gif, icc, ico, ilda, java,
	jp2, jpg, lnk, id3v2, nes, ogg, pcap, pcapng, pe_sec, pe_hdr, png, psd, riff,
	svg, tiff, wad, wasm, xz, zstd,

# magic potentially further but checked at 0
	_7z, mp4, pdf, gzip, bzip2, postscript, zip_, rar, rtf,

# magic further
	dcm, tar, pdfc, iso,

# footer
	id3v1,
]

# Global list to store generated files
generated_files = []

def randbuf(length):
	res = b"\0" * length
	res = bytes([random.randrange(255) for i in range(length)])
	return res


def separatePayloads(fn, exts, data, swaps, overlap):
	NoFile, SplitDir = getVars(["NOFILE", "SPLITDIR"])

	ext1, ext2 = exts
	p1 = b""
	p2 = b""
	start = 0
	for end in swaps:
		p1 += data[start:end]
		p2 += randbuf(end-start)

		start = end
		p1, p2 = p2, p1
	p1 += data[end:]
	p2 += randbuf(len(data)-end)

	p2 = overlap + p2[len(overlap):]

	if not NoFile:
		with open(os.path.join(SplitDir, "%s.%s" % (fn, ext1)), "wb") as f:
				f.write(p1)
		with open(os.path.join(SplitDir, "%s.%s" % (fn, ext2)), "wb") as f:
				f.write(p2)
	return


def writeFile(name, exts, data, swaps=[], overlap=b""):
	global generated_files
	OutDir, NoFile, Split = getVars(["OUTDIR", "NOFILE", "SPLIT"])

	random.seed(0)
	hash = hashlib.sha256(data).hexdigest()[:8].lower()

	if Split and swaps != []:
		separatePayloads(name, exts, data, swaps, overlap)

	fn = "%s.%s.%s" % (name, hash, ".".join(exts))
	generated_files.append((fn, data))

	if not NoFile:
		with open(os.path.join(OutDir, "%s" % fn), "wb") as f:
			f.write(data)
	return


def isStackOk(ftype1, ftype2):
	dprint("Stack: %s-%s" % (ftype1.TYPE, ftype2.TYPE))
	result = True
	if not ftype1.bAppData:
		dprint("! File type 1 (%s) doesn't support appended data." % (ftype1.TYPE))
		result = False

	if ftype2.start_o == 0:
		dprint("! File type 2 (%s) starts at offset 0 - it can't be appended." % (ftype2.TYPE))
		return False
	else:
		len1 = len(ftype1.data)
		if len1 >= ftype2.start_o:
			dprint("! File 1 is too big (0x%X). File 2 should start at offset 0x%X or less." % (len1, ftype2.start_o) )
			result = False

	return result


def isCavOk(ftype1, ftype2):
	dprint("Cavity: %s_%s" % (ftype1.TYPE, ftype2.TYPE))
	filling = ftype1.data
	filling_l = len(ftype1.data)

	result = True
	if not ftype1.bAppData:
		dprint("! File type 1 (%s) doesn't support appended data." % (ftype1.TYPE))
		result = False

	if not ftype2.precav_s:
		dprint("! File type 2 (%s) doesn't start with any cavity." % (ftype2.TYPE))
		return False
	elif filling_l > ftype2.precav_s:
		dprint("! File 1 is too big (0x%X). File 2's cavity is only 0x%X." % (filling_l, ftype2.precav_s) )
		result = False

	return result


def isParasiteOk(ftype1, ftype2):
	dprint("Parasite: %s[%s]" % (ftype1.TYPE, ftype2.TYPE))
	result = True
	if not ftype1.bParasite:
		dprint("! File type 1 (%s) doesn't support parasites." % (ftype1.TYPE))
		return False

	# start_o is 0 when precav_s isn't
	if (ftype1.parasite_o > ftype2.start_o + ftype2.precav_s):
		dprint("! File type 1 (%s) can only host parasites at offset 0x%X. File 2 should start at offset 0x%X or less." % (ftype1.TYPE, ftype1.parasite_o, ftype2.start_o) )
		result = False

	if ftype1.parasite_s < len(ftype2.data):
		dprint("! File type 1 (%s) can accept parasites only of size 0x%X max. File 2 is too big (%X)." % (ftype1.TYPE, ftype1.parasite_s, len(ftype2.data)) )
		result = False

	return result


def isZipperOk(ftype1, ftype2):
	dprint("Zipper: %s^%s" % (ftype1.TYPE, ftype2.TYPE))
	result = True
	if not ftype1.bZipper:
		dprint("! File type 1 (%s) doesn't support zippers." % (ftype1.TYPE))
		return False
#  if not ftype1.bAppData:
#    dprint("! File type 1 (%s) doesn't support appended data." % (ftype1.TYPE))
#    result = False

	if not ftype1.bParasite:
		dprint("! File type 1 (%s) doesn't support parasites." % (ftype1.TYPE))
		return False

	if not ftype2.bParasite:
		dprint("! File type 2 (%s) doesn't support parasites." % (ftype2.TYPE))
		return False

	return result


def Hit(type1, type2, results):
	global VERBOSE
	if getVar("VERBOSE"):
		dprint("HIT " + ";".join(sorted([type1, type2])))


def Stack(ftype1, ftype2, fn1, fn2, results):
	if isStackOk(ftype1, ftype2):
		results.append(("Stack: concatenation of File1 (type %s) and File2 (type %s)" % (ftype1.TYPE, ftype2.TYPE)))
		appData = ftype2.data
		swap_o = len(ftype1.data + 
			ftype1.wrappend(b""))

		Hit(ftype1.TYPE, ftype2.TYPE, results)
		writeFile(
			"S(%x)-%s-%s" % (swap_o, ftype1.TYPE, ftype2.TYPE),
			[ext(fn2), ext(fn1)],
			ftype1.data + 
			ftype1.wrappend(appData),
			[swap_o]
		)


def Parasite(ftype1, ftype2, fn1, fn2, results):
	if isParasiteOk(ftype1, ftype2):
		results.append(("Parasite: hosting of File2 (type %s) in File1 (type %s)" % (
			ftype2.TYPE, ftype1.TYPE)))
		parasitized, swaps = ftype1.parasitize(ftype2)
		if parasitized is None:
			return

		filealig = len(parasitized) % 16
		if getVar("AESGCM") and filealig > 0:
			wrap = ftype1
			if len(ftype2.wrappend(b"")) != 0:
				wrap = ftype2

			for i in range(17, 32):
				aligned = parasitized + wrap.wrappend(b"\0" * i)
				if len(aligned) % 16 == 0:
					break
			if wrap == ftype2:
				swaps += [len(parasitized)]
			parasitized = aligned

		swapstr = "(%s)" % "-".join("%x" % s for s in swaps) if swaps != [] else ""
		Hit(ftype1.TYPE, ftype2.TYPE, results)
		writeFile(
			"P%s-%s[%s]" % (swapstr, ftype1.TYPE, ftype2.TYPE),
			[ext(fn1), ext(fn2)],
			parasitized,
			swaps
		)


def Zipper(ftype1, ftype2, fn1, fn2, results):
	if isZipperOk(ftype1, ftype2):
		zipper, swaps = ftype1.zipper(ftype2)
		if (zipper, swaps) == (None, []):
			return
		results.append(("Zipper: interleaving of File1 (type %s) and File2 (type %s)" % (
			ftype1.TYPE, ftype2.TYPE)))
		swapstr = "(%s)" % "-".join("%x" % s for s in swaps) if swaps != [] else ""
		Hit(ftype1.TYPE, ftype2.TYPE, results)
		writeFile(
			"Z%s-%s^%s" % (swapstr, ftype1.TYPE, ftype2.TYPE),
			[ext(fn1), ext(fn2)],
			zipper,
			swaps
		)


def Cavity(ftype1, ftype2, fn1, fn2, results):
	if isCavOk(ftype1, ftype2):
		results.append(("Cavity: File1 (type %s) into File2 (type %s)" % (ftype1.TYPE, ftype2.TYPE)))
		filling = ftype1.data
		filling_l = len(filling + ftype1.wrappend(b""))
		filled = filling + ftype1.wrappend(ftype2.data[filling_l:])
		swap = filling_l
		Hit(ftype1.TYPE, ftype2.TYPE, results)
		writeFile(
			"C(%x)-%s-%s" % (swap, ftype1.TYPE, ftype2.TYPE),
			[ext(fn2), ext(fn1)],
			filled,
			[swap]
		)


def JpegOver5(jpeg, other, swaps, overlap):
	highnib = jpeg[4]
	lownib = jpeg[5]
	offset = 4 + 0x100*highnib + lownib

	if highnib == 0xff or not other.startswith(overlap) or len(swaps) != 2 or swaps[0] != 6 or len(overlap) != 6:
		return jpeg, swaps, overlap

	othernib = other[5]
	delta = 0x100 - lownib
	swaps[0] -= 1
	swaps[1] += delta
	overlap = overlap[:-1]
	jpeg = b"".join([
		jpeg[:4],
		bytes([highnib + 1]),
		bytes([othernib]),
		jpeg[6:offset],
		delta*b"\0",
		jpeg[offset:],
		])

	dprint("Jpeg overlap file: reducing one byte")
	dprint("  (don't forget to postprocess after bruteforcing)")
	return jpeg, swaps, overlap


def JpegOver4(jpeg, other, swaps, overlap):
	if not other.startswith(overlap) or len(swaps) != 2 or swaps[0] != 6 or len(overlap) != 6:
		return jpeg, swaps, overlap

	offset = swaps[-1]
	swaps[0] -= 2
	overlap = overlap[:-2]
	jpeg = b"".join([
		jpeg[:4],
		other[4:6],
		jpeg[6:],
		])

	dprint("Jpeg overlap file: reducing two bytes")
	dprint("  (don't forget to postprocess after bruteforcing)")
	return jpeg, swaps, overlap


def Overlap(ftype1, ftype2, fn1, fn2, results, THRESHOLD=6):
	dprint("Overlapping parasite")
	if not ftype1.bParasite:
		dprint("! Parasite not supported.", ftype1.TYPE)
		return False
	ftype1.getCut()
	overlap_l = ftype1.parasite_o
	if overlap_l is None:
		results.append("! Error - overlap is None " + ftype1.TYPE)
		return False
	if overlap_l > THRESHOLD:
		dprint("! Overlap (length:%i) too long (threshold:%i)." % (overlap_l, THRESHOLD))
		return False

	fextra = blob.reader(ftype2.data[overlap_l:])
	parasitized, swaps = ftype1.parasitize(fextra)
	if parasitized is None:
		return False

	overlap = ftype2.data[:overlap_l]

	if ftype1.TYPE == "JPG":
		parasitized, swaps, overlap = JpegOver4(parasitized, ftype2.data, swaps, overlap)

	overlap_s = "".join("%02X" % c for c in overlap)
	swapstr = "(%s)" % "-".join("%x" % s for s in swaps) if swaps != [] else ""
	Hit(ftype1.TYPE, ftype2.TYPE, results)
	writeFile(
		"O%s-%s[%s]{%s}" % (swapstr, ftype1.TYPE, ftype2.TYPE, overlap_s),
		[ext(fn1), ext(fn2)],
		parasitized,
		swaps=swaps,
		overlap=overlap,	
	)
	results.append("Generic overlapping polyglot file created.")
	return True


def OverlapPE(ftype1, ftype2, fn1, fn2, results):
	SIG_l = 2
	ELFANEW_o = 0x3c

	if not ftype2.TYPE.startswith("PE"):
		return False
	overlap_l = SIG_l

	dprint("PE Reverse overlapping parasite")
	if not ftype1.bParasite:
		return False
	if ftype1.parasite_o is None:
		dprint("! Error - overlap is None", ftype1.TYPE)
		return False
	cut = ftype1.getCut()
	if ftype1.parasite_o > ELFANEW_o:
		dprint("! Parasite offset too far: type (%s) parasite offset (0x%X)" % (ftype1.TYPE, ftype1.parasite_o))
		return False
	if len(ftype2.data) > ftype1.parasite_s:
		dprint("! PE file (size:%i) can't fit in parasite (max: %i)." % (len(ftype2.data), ftype1.parasite_s))
		return False

	fextra = blob.reader(ftype2.data[ftype1.parasite_o:])
	parasitized, swaps = ftype1.parasitize(fextra)

	if parasitized is None:
		return False

	overlap = ftype2.data[:overlap_l]
	overlap_s = "".join("%02X" % c for c in overlap)
	swapstr = "(%s)" % "-".join("%x" % s for s in swaps) if swaps != [] else ""
	Hit(ftype1.TYPE, ftype2.TYPE, results)
	writeFile(
		"OR%s-%s[%s]{%s}" % (swapstr, ftype1.TYPE, ftype2.TYPE, overlap_s),
		[ext(fn1), ext(fn2)],
		parasitized,
		swaps=swaps,
		overlap=overlap,
	)
	results.append("Specific PE overlapping polyglot file created.")
	return True


def OverlapAll(ftype1, ftype2, fn1, fn2, results):
	OverlapPE(ftype1, ftype2, fn1, fn2, results)
	Overlap(ftype1, ftype2, fn1, fn2, results)


ext = lambda s:os.path.splitext(s)[1]


def DoAll(ftype1, ftype2, fn1, fn2, results):
	Stack(ftype1, ftype2, fn1, fn2, results)
	Parasite(ftype1, ftype2, fn1, fn2, results)
	Zipper(ftype1, ftype2, fn1, fn2, results)
	Cavity(ftype1, ftype2, fn1, fn2, results)
	if getVar("OVERLAP"):
		OverlapAll(ftype1, ftype2, fn1, fn2, results)


def process_files(fn1, fdata1, fn2, fdata2):
	global generated_files
	generated_files = []
	results = []

	pad = getVar("PAD")
	if pad > 0:
		fdata1 += b"\1" * (pad - len(fdata1))
		fdata2 += b"\1" * (pad - len(fdata2))

	ftype1 = None
	ftype2 = None

	for parser in PARSERS:
		ftype = parser.parser
		f = ftype(fdata1)
		if f.identify():
			ftype1 = f
		f = ftype(fdata2)
		if f.identify():
			ftype2 = f

	results.append(f"{fn1}")
	if ftype1 is None:
		results.append("ERROR: Unknown type file 1 - aborting.")
		return results, []
	results.append(f"File 1: {ftype1.DESC}")

	results.append(f"{fn2}")
	if ftype2 is None:
		if getVar("FORCE"):
			ftype2 = blob.reader(fdata2)
		else:
			results.append("ERROR: Unknown type file 2 (try -f ?) - aborting.")
			return results, []

	results.append(f"File 2: {ftype2.DESC}")
	results.append("")

	if ftype1.TYPE == ftype2.TYPE:
		results.append("ERROR: Same file types - aborting.")
		return results, []

	DoAll(ftype1, ftype2, fn1, fn2, results)
	if getVar("REVERSE"):
		dprint("REVERSE: Switching files order")
		dprint("")
		DoAll(ftype2, ftype1, fn2, fn1, results)

	return results, generated_files


def main():
	args = Setup(__description__)
	fn1,fn2 = args.file1, args.file2
	with open(fn1, "rb") as f:
		fdata1 = f.read()
	with open(fn2, "rb") as f:
		fdata2 = f.read()

	# The Setup function is called first to configure the application
	results, files = process_files(fn1, fdata1, fn2, fdata2)
	for r in results:
		print(r)

if __name__ == "__main__":
	main()