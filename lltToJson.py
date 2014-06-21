#!/usr/bin/python
# -*- coding: utf-8 -*-

import re
import codecs
import json
import sys, getopt
import os
error = False
try:
	import pdfquery
except:
	print "PDFQuery not found, install through easy_install pdfquery or pip install pdfquery."
	error = True

try:
	import numpy
except:
	print "Numpy not installed"
	error = True


#Cache should be change to ./tmp/
class lltToJson(object):
	def __init__(self, output = "llt", source = "./pdf/", cache = "./json/", jsonFolder = "./json/", temp = "./tmp/", nocache = False, author = False):
		self.temp = temp
		self.cache = cache
		self.source = source
		self.json = jsonFolder
		self.nocache = nocache
		self.onlyauthor = author
		self.recheck = False
		self.filter = False

		self.output = output 
		self.outputCSV = output + ".csv"
		self.outputJSON = output + ".json"
		self.outputTXT = output + ".txt"

	def makeDirs(self):
		if not os.path.exists(self.json):
			os.mkdir(self.json)
		if not os.path.exists(self.cache):
			os.mkdir(self.cache)
		if not os.path.exists(self.temp):
			os.mkdir(self.temp)

	def getOutput(self, output):
		self.outputCSV = output + ".csv"
		self.outputJSON = output + ".json"
		self.outputTXT = output + ".txt"

	def getText(self, line):
		"""	Return the text for a given line
		"""
		if isinstance(line, str):
			text = line
		elif line.text != None:
			text = line.text
		else:
			text = ""
		return text

	def getDict(self, text, obj = False):
		isIdentifier = re.compile("[a-zA-Z]*[\.]*\s*\: ([0-9]|X|I|V|L|C)+")
		""" Format the return string

		"""
		if obj == False:
			return {"author" : text}
		elif "identifier" not in obj:
			if isIdentifier.search(text):
				#There is often a bug where a line finishin [*] contains text, here is a workaround:
				if "[*]" in text:
					sp = text.split("[*]")
					obj["text"] = sp[-1]
					obj["identifier"] = sp[0:-2]
				else:
					obj["identifier"] = text
			else:
				obj["author"] += text
		elif "text" not in obj:
			obj["text"] = text
		else:
			obj["text"] += " " + text
		return obj

	def checkOccurences(self, occurences, filename):

		#Setting up list of BREPOLS noise
		brepols = ["Brepols Publishers", "l'exportation"]
		noiseBrepols = re.compile("Total\: [1-9]+")

		#GO GO GO
		forget = []
		i = len(occurences)
		while i > 0:
			occurence = occurences[i]
			if occurence:
				if len(occurence) < 3:
					previous = i - 1
					#If we have only author, it means it never passed the text of identifier, which means it is text of previous item
					if "identifier" not in occurence:
						if previous in occurences and previous != None:
							occurences[previous] = self.getDict(occurence["author"], occurences[previous])
							occurences[i] = None
						elif previous-1 in occurences:
							previous -= 1
							occurences[previous] = self.getDict(occurence["author"], occurences[previous])
							occurences[i] = None
					else:
						print "There was a bug in the automatic conversion " + str(i) + " for file " + filename
						print occurence["identifier"]
						digit = None
						process = True
						for index, letter in enumerate(occurence["identifier"]):
							if letter.isdigit():
								digit = index + 1
						if digit:
							data = [occurence["identifier"][0:digit], occurence["identifier"][digit:]]
							print data
							if raw_input("Is this guess correct ?").lower() == "y":
								occurences[i]["identifier"] = occurence["identifier"][0:digit]
								occurences[i]["text"] = occurence["identifier"][digit:]
								process = False

						if digit == None or process == True:
							occurences[i]["identifier"] = raw_input("Enter the LLT identifier for this string : \n")
							occurences[i]["text"] = raw_input("Enter the sentence identifier for this string : \n")

					for noise in brepols:
						if noise.encode("utf-8") in occurence["author"].encode("utf-8") or ("identifier" in occurence and noise.encode("utf-8") in occurence["identifier"].encode("utf-8")):
							occurences[i] = None
				else:
					for noise in brepols:
						if noise.encode("utf-8") in occurence["text"].encode("utf-8"):
							occurences[i] = None
					if noiseBrepols.match(occurence["text"]):
							occurences[i] = None
				#We also need to recheck if it is not brepols stuff
			i -= 1 
		return occurences
	def getFile(self, filename, check = 2):
		temp = self.temp
		pathCache = self.cache
		shortfilename = filename.split("/")[-1]
		try:
			with codecs.open(pathCache + shortfilename + ".json", "r", "utf-8") as f:
				d = json.load(f)
				f.close()
				return d
		except:
			con = 1
		#Getting the file
		pdf = pdfquery.PDFQuery(filename)
		pdf.load()
		pages = pdf.pq("LTPage")

		#Setting up tokens
		occurences = {} # We set up a dictionnary
		index = 0 # We set it up before anything happens
		i = 0

		#Getting the content
		for page in pages:
			boxNumber = 1
			boxCount = len(page)
			for box in page:
				for line in box:
					i += 1#Setting a counter

					text = self.getText(line)

					if text.strip():
						if index in occurences:
							occurences[index] = self.getDict(text, occurences[index])
						else:
							occurences[index] = self.getDict(text)

				if i == 2 or i == 1: #If we have only title and author with the first line or only the author
					if boxNumber == boxCount:
						index = len(occurences)
					else:
						index = len(occurences) + 1
						i = 0
				else:
					index = len(occurences) + 1
					i = 0
				boxNumber += 1

		#And now we clean for occurences which has no identifier or text
		i = 1
		while i <= check:
			occurences = self.checkOccurences(occurences, filename)
			i += 1

		occurences = [occurences[occ] for occ in occurences if occurences[occ] != None]
		#Caching
		with codecs.open(pathCache + shortfilename + ".json", "w", "utf-8") as f:
			d = f.write(json.dumps(occurences))
			f.close()
		return occurences

	def getFolder(self):
		from os import listdir
		from os.path import isfile, join
		path = self.source

		files = [ f for f in listdir(path) if isfile(join(path,f)) and len(f.split(".")) > 1 and f.split(".")[-1] == "pdf"]
		occurences = {}
		for f in files:
			print "Reading " + f
			identifier = f.replace(" ", "").split(".")[0]
			if "-" in identifier:
				identifier = identifier.split("-")[0]
			if identifier not in occurences:
				occurences[identifier] = self.getFile(join(path,f))
			else:
				occurences[identifier] += self.getFile(join(path,f))
		return occurences

	def getCache(self, occurences = {}, output = False, identifier = True):
		path = self.json
		if identifier == True:
			for identifier in occurences:
				filename = path + identifier + ".json"
				with codecs.open(filename, "w", "utf-8") as f:
					d = f.write(json.dumps(occurences[identifier]))
					f.close()
		if output:
			with codecs.open(self.outputJSON, "w", "utf-8") as f:
				d = f.write(json.dumps(occurences))
				f.close()

	def getString(self, o, i):
		"""	Returns a string from a dictionnary object, even if index is non existent (avoiding bug)

		Keyword arguments
		o --- Dictionnary of results
		i --- index
		"""
		if i not in o:
			return " "
		elif isinstance(o[i], list):
			return " ".join(o[i])
		else:
			return o[i]

	def getCSV(self, occurences):
		with codecs.open(self.outputCSV, "w", "utf-8") as f:
			for identifier in occurences:
				for occurence in occurences[identifier]:
					l = [identifier, self.getString(occurence, "author").replace(";", ","), self.getString(occurence, "identifier").replace(";", ","), self.getString(occurence, "text").replace(";", ",")]
					f.write(";".join(l) + "\n")
			f.close()

	def load(self):
		with codecs.open(self.source, "r", "utf-8") as f:
			d = json.load(f)
			f.close()
			return d

	def getAuthor(self, string):
		return string.replace(";", ",").split("-")[0].strip()

	def getAuthors(self, occurences):
		authors = []

		for identifier in occurences:
			for occurence in occurences[identifier]:
				a = self.getAuthor(self.getString(occurence, "author"))
				if a not in authors:
					authors.append(a)

		with codecs.open(self.outputTXT, "w", "utf-8") as f:
			f.write("\n".join(authors))
			f.close()

	def getChecked(self, occurences):
		#checkLLA = re.compile("\(([A-Z]+ [0-9]+\.*[A-Z0-9]*[ ]*[0-9A-Za-z\+]{0,1}\,*[ ]*\(*[A-Z]*\)*)+\)\s*$")
		checkLLA = re.compile("\((CPL|LLA)[A-Za-z0-9 \,\.\(\)\+\°\-]+\)\s*$")
		lengths = []
		for identifier in occurences:
			for occurence in occurences[identifier]:
				a = len(self.getString(occurence, "author"))
				lengths.append(a)
		#Statistic :
		avg = float(sum(lengths))/len(lengths) if len(lengths) > 0 else float('nan')
		med = numpy.percentile(lengths, 50)
		nin = numpy.percentile(lengths, 90)
		fiv = numpy.percentile(lengths, 95)
		nn = numpy.percentile(lengths, 99)
		nn = numpy.percentile(lengths, 99.8)
		print "Average : " + str(avg) + " (avg)"
		print "Median : " + str(med) + " (med)"
		print "90 percentile : " + str(nin) + " (nin)"
		print "95 percentile : " + str(fiv) + " (ninefive)"
		print "99.8 percentile : " + str(nn) + " (ninenine)"

		choices = ["avg", "med", "nin", "ninefive", "ninenine"]
		choice = raw_input("\t Which value do you want to filter on ? You can give us an integer or choose in : " + ", ".join(choices) + "\n").replace(" ", "")
		if choice.isdigit() == True:
			fil = int(choice)
		elif choice not in choices:
			sys.exit()
		elif choice == "avg":
			fil = avg
		elif choice == "med":
			fil = med
		elif choice == "nin":
			fil = nin
		elif choice == "ninefive":
			fil = fiv
		elif choice == "ninenine":
			fil = nn

		ok = []
		for identifier in occurences:
			for index, occurence in enumerate(occurences[identifier]):
				author = self.getString(occurence, "author")
				if float(len(author)) > float(fil) or (author not in ok and not checkLLA.search(author)):
					print "--------------------------"
					print "Actual author :" + author
					print "Actual :"
					for elem in occurences[identifier][index]:
						print "\t" + elem + " : " +self.getString(occurences[identifier][index], elem)
					action = raw_input("Is this line ok ? (y/n/r(->for Remove))").lower().replace(" ", "")

					if action == "r":
						occurences[identifier][index] = None
					elif action != "y":
						if index - 1 > 0 and index - 1 < len(occurences[identifier]):
							print "Previous line "
							for elem in occurences[identifier][index -1]:
								print "\t" + elem + " : " +self.getString(occurences[identifier][index -1], elem)

						if raw_input("Change this line alone ? (y/n)").lower().replace(" ", "") != "y":
							#Merge
							if "text" not in occurences[identifier][index -1]:
								occurences[identifier][index -1]["text"] = author + self.getString(occurence, "text") + self.getString(occurence, "identifier")

								occurences[identifier][index] = None
							else:
								action = raw_input("Merge with previous text ? (y/n)").lower().replace(" ", "")
								if action == "y":
									occurences[identifier][index -1]["text"] = occurences[identifier][index -1]["text"] + author + self.getString(occurence, "text") + self.getString(occurence, "identifier")
									occurences[identifier][index] = None
								#Rewrite
								else:
									action = raw_input("Rewrite actual and previous ? (y/n)").lower().replace(" ", "")
									if action == "y":
										for elem in occurences[identifier][index -1]:
											print "Previous -> "
											occurences[identifier][index -1][elem] = raw_input("\t" + elem + " : ")
										for elem in occurences[identifier][index -1]:
											print "Actual -> "
											occurences[identifier][index][elem] = raw_input("\t" + elem + " : ")
						else:
							for elem in occurences[identifier][index -1]:
								print "Actual -> "
								occurences[identifier][index][elem] = raw_input("\t" + elem + " : ")
					else:
						ok.append(author)

		occ = {}
		for identifier in occurences:
			occ[identifier] = []
			for index, occurence in enumerate(occurences[identifier]):
				if occurence:
					occ[identifier].append(occurence)

		return occ

	def getFiltered(self, filterFile, occurences):
		""" Get filtered output according to authors name
		"""

		#First we get the filters
		lines = []
		filters = []
		groups = []
		with codecs.open(filterFile, "r", "utf-8") as f:
			for line in f:
				if len(line.replace(" ", "")) > 2:
					lines.append(line.replace("\n", ""))
			f.close()
		if len(lines) == 0:
			print "No filters found"
			sys.exit()
		lines = sorted(lines, key = len)[::-1]

		filters = [line.split(";") for line in lines]
		groups = set([f[1] for f in filters])

		#Then we copy the structure of our occurences
		nongrouped = occurences
		grouped = {}
		for g in groups:
			grouped[g] = {}
			for term in occurences:
				grouped[g][term] = []

		for term in occurences:
			l = occurences[term]
			for occ in l:
				b = False
				for author in filters:
					if len(occ["author"]) >= len(author[0]) and author[0] == occ["author"].strip()[0:len(author[0])]:
						grouped[author[1]][term].append(occ)
						b = True
						break
				if b == False:
					print occ["author"] + " has no equivalent..."

		return grouped





def main(argv):
	llt = lltToJson()
	modes = []
	outputJSON = False
	outputCSV = False


	try:
		opts, args = getopt.getopt(argv,"hi:o",["input=","output=", "check", "authors", "csv", "json", "nocache", "cache=", "temp=", "filter="])
	except getopt.GetoptError:
		opts = False

	if opts != False:
		for opt, arg in opts:
			if opt == '-h':
				print 'test.py -options'
				print """
Optional parameters :
-i\t<input> Input folder where Brepols pdf remains (default: ./pdf/) or json previous export
-o\t<output> Output file without extension .json or .csv (default ./llt)
--csv\tOnly csv output (Default: disabled)
--json\tOnly json output (Default: disabled)
--nocache\tDon't use cache files
--authors\tOutput a txt file with authors
--check\tCheck the results manually again
--filter\tFilter results according to a CSV file where column 1 is author name, seconde one a group identifier

Really optional parameters
--cache\t Place to cache intermediary results (Default : ./json/)
--temp\t Place to put PDFQuery temp files (Default: ./tmp)
"""
				sys.exit()
			elif opt in ("-i", "--input"):
				llt.source = arg
			elif opt in ("-o", "--output"):
				llt.output = arg
				llt.getOutput(arg)
				print llt.outputTXT
			elif opt in ("--csv"):
				outputJSON = False
				outputCSV = True
			elif opt in ("--json"):
				outputJSON = True
				outputCSV = False
			elif opt in ("--cache"):
				llt.jsonFolder = arg
			elif opt in ("--temp"):
				llt.temp = arg
				llt.cache = arg
			elif opt in ("--nocache"):
				llt.nocache = True
			elif opt in ("--authors"):
				llt.onlyauthor = True
			elif opt in ("--check"):
				llt.recheck = True
			elif opt in ("--filter"):
				llt.filter = arg

	print llt.source
	if llt.nocache == False:
		llt.makeDirs()

	if os.path.isfile(llt.source):
		occurences = llt.load()
	else:
		occurences = llt.getFolder()

	if llt.filter != False:
		groups = llt.getFiltered(llt.filter, occurences)
		for group in groups:
			occurences = groups[group]
			llt.getOutput(llt.output + "-" + group)
			if outputCSV:
				llt.getCSV(occurences)
			elif outputJSON:
				llt.getCache(occurences, True, False)
			else:
				llt.getCache(occurences, True, False)
				llt.getCSV(occurences)
	elif llt.onlyauthor:
		llt.getAuthors(occurences)
	elif outputCSV:
		llt.getCache(occurences, False)
		llt.getCSV(occurences)
	elif outputJSON:
		llt.getCache(occurences, True)
	else:
		llt.getCache(occurences, True)
		llt.getCSV(occurences)


if __name__ == "__main__":
	main(sys.argv[1:])