#!/usr/bin/python
# -*- coding: utf-8 -*-

import pdfquery
import re
from pprint import pprint
import codecs
import json

def getText(line):
	"""	Return the text for a given line
	"""
	if isinstance(line, str):
		text = line
	elif line.text != None:
		text = line.text
	else:
		text = ""
	return text

def getDict(text, obj = False):
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

def checkOccurences(occurences, filename):

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
						occurences[previous] = getDict(occurence["author"], occurences[previous])
						occurences[i] = None
					elif previous-1 in occurences:
						previous -= 1
						occurences[previous] = getDict(occurence["author"], occurences[previous])
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
def getFile(filename, temp = "./tmp/", pathCache = "./json/", check = 2):
	shortfilename = filename.split("/")[-1]
	try:
		with codecs.open(pathCache + shortfilename + ".json", "r", "utf-8") as f:
			d = json.load(f)
			f.close()
			return d
	except:
		con = 1
	#Getting the file
	pdf = pdfquery.PDFQuery(filename, parse_tree_cacher=pdfquery.cache.FileCache(temp))
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

				text =getText(line)

				if text.strip():
					if index in occurences:
						occurences[index] = getDict(text, occurences[index])
					else:
						occurences[index] = getDict(text)

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
		occurences = checkOccurences(occurences, filename)
		i += 1

	occurences = [occurences[occ] for occ in occurences if occurences[occ] != None]
	#Caching
	with codecs.open(pathCache + shortfilename + ".json", "w", "utf-8") as f:
		d = f.write(json.dumps(occurences))
		f.close()
	return occurences

def getFolder(path = "./pdf/"):
	from os import listdir
	from os.path import isfile, join

	files = [ f for f in listdir(path) if isfile(join(path,f)) ]
	occurences = {}
	for f in files:
		print "Reading " + f
		identifier = f.replace(" ", "").split(".")[0]
		if "-" in identifier:
			identifier = identifier.split("-")[0]
		if identifier not in occurences:
			occurences[identifier] = getFile(join(path,f))
		else:
			occurences[identifier] += getFile(join(path,f))
	return occurences

def cache(occurences = {}, path = "./json/"):
	for identifier in occurences:
		filename = path + identifier + ".json"
		with codecs.open(filename, "w", "utf-8") as f:
			d = f.write(json.dumps(occurences[identifier]))
			f.close()

	with codecs.open(path + "general.json", "w", "utf-8") as f:
		d = f.write(json.dumps(occurences[identifier]))
		f.close()

occurences = getFolder()
cache(occurences)
