# wayback-scraper
Scrapes HTML pages from the Wayback Machine using asynchronous processing in Python.  
**TestPyPI page:** https://test.pypi.org/project/wb-scraper

## Getting Started
Install temporarily located at:  
```  
pip install -i https://test.pypi.org/simple/ wb-scraper  
```  
This makes the tool usable from any directory.  

To scrape a specific URL, run:  
```  
wb-scraper scrape -u <exact URL>  
```  
This retrieves the HTML snapshots the Wayback Machine has of that URL; either all snapshots, or snapshots within the specified date range.
This command creates a new folder with the name of the website inside the directory the command is run in. HTML files are stored in this folder.

## Text Files
When prompted, wayback-scraper automatically extracts text from the HTML pages and creates separate text files for each snapshot.  
These are stored in a separate "text files" folder inside the new folder.

## Formatting Input
When prompted for a date, enter in the format YYYYMMDD.
