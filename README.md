# wayback-scraper
Scrapes HTML pages from the Wayback Machine using asynchronous processing in Python.

## Get Started
Install temporarily located at:  
`pip install -i https://test.pypi.org/simple/ wb-scraper`  
This makes the tool usable from any directory.  

To scrape a specific URL, run:  
`wb-scraper scrape -u <exact URL>`  
This retrieves the HTML snapshots the Wayback Machine has of that URL.  
This command creates a new folder with the name of the website inside the directory the command is run in. HTML files are stored in this folder.

## Text Files
When prompted, wb-scraper automatically extracts text from the HTML pages and creates separate text files for each snapshot.  
These are stored in a separate "text files" folder inside the new folder.
