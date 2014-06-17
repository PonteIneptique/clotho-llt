clotho-llt
==========

Convert LLT pdf export to readable occurrences json file for Clotho or CSV

#Dependencies
- PdfQuery `easy_install pdfquery` or `pip install pdfquery`
- numpy `apt-get install scipy

#Defaults
Default use for this script:
- A pdf folder `./pdf/` in the same folder where you put your LLT pdf files
- That's all

#Commands
```
Optional parameters :
-i  <input> Input folder where Brepols pdf remains (default: ./pdf/) or json previous export
-o  <output> Output file without extension .json or .csv (default ./llt)
--csv Only csv output (Default: disabled)
--json  Only json output (Default: disabled)
--nocache Don't use cache files
--authors Output a txt file with authors
--check Check the results manually again

Really optional parameters
--cache Place to cache intermediary results (Default : ./json/)
--temp  Place to put PDFQuery temp files (Default: ./tmp)
```
