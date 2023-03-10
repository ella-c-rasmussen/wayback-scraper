import urllib.request as urq
from json import loads
import os
import asyncio
from asyncio import CancelledError
import aiohttp
import time
import sys
import bs4

# Global variable for directory separator
fd = '/'

def wayback_scrape(URLin):
    check_os()
    
    uvURL =  URLin
    headers = {"User-Agent": 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36'}
    
    # Retrieve list of available snapshots from the Wayback CDX Server API
    url = 'http://web.archive.org/cdx/search/cdx?url=' + uvURL + '&output=json'
    req = urq.Request(url, headers = headers)
    cdx_response = urq.urlopen(req).read()
    url_list = loads(cdx_response)
    
    num_urls = len(url_list) - 1 # Subtract 1 entry for the header
    
    if num_urls <= 0:
        print("No captures found.")
    
    else:
        # Retrieve start and end dates
        start_date = url_list[1][1]
        end_date = url_list[num_urls][1]
        print(f"\nFound {num_urls} captures for the site {uvURL} from " +
            f"{parse_timestamp(start_date)} to {parse_timestamp(end_date)}. " +
            "Continue? (Y/N)")
        
        flag = True
        while flag == True:
            response = input().upper()
            if response == 'Y':
                flag = False
            elif response == 'N':
                exit()
            else:
                print("Invalid response.")
        
        # Prompt for range or retrieve all
        flag = True
        while flag == True:
            print("Enter R for a range of dates, or A for all captures.")
        
            entered = input().upper()
            if entered == 'R':
                date_range(url_list, uvURL)
                flag = False
            elif entered == 'A':
                all_captures(url_list, uvURL)
                flag = False
            else:
                print("Invalid input.")    

# Parse a Wayback Machine timestamp into a MM/DD/YYYY date.
# Returns date as a string.
def parse_timestamp(timestamp):
    year = str(timestamp[:4])
    month = str(timestamp[4:6])
    day = str(timestamp[6:8])
    
    return month + "/" + day + "/" + year

# Retrieve a list dates within the date range specified by the user.
# Returns a list of timestamps as integers.
#        start : start date in format YYYYMMDD
#        end : end date in format YYYYMMDD
#        url_list : list of snapshots from the CDX server JSON response
def find_date_range(start, end, url_list):
    length = len(url_list)
    valid_dates = []
    if start > int(url_list[length - 1][1]) or end < int(url_list[1][1]):
        print("Invalid date range -- outside of capture range.")
    elif start > end:
        print("Start date must be before end date.")
        
    else:
        timestamp_list = []
        for entry in url_list[1:]:
            timestamp_list.append(int(entry[1]))
        
        for time in timestamp_list:
            if start <= time <= end:
                valid_dates.append(time)
            elif time > end:
                break
    
    return valid_dates

# Get snapshots within the range of dates.
#        url_list : list of snapshots from the CDX server JSON response
#        uvURL : the URL the user entered
def date_range(url_list, uvURL):
    flag = True
    while flag == True:
        print("Enter the start date in the format YYYYMMDD:")
        start = input() + "000000"
        print("Enter the end date in the format YYYYMMDD:")
        end = input() + "000000"
    
        if len(start) != 14:
            print("Invalid start date format.")
        elif len(end) != 14:
            print("Invalid end date format.")
        
        else:
            flag = False
    
    dates = find_date_range(int(start), int(end), url_list)
    asyncio.run(retrieve_pages(dates, uvURL))

# Get snapshots from all available timestamps.
#        url_list : list of snapshots from the CDX server JSON response
#        uvURL : the URL the user entered
def all_captures(url_list, uvURL):
    timestamp_list = []
    for entry in url_list[1:]:
        timestamp_list.append(int(entry[1]))
    
    asyncio.run(retrieve_pages(timestamp_list, uvURL))

# Create folder in cwd to store snapshots in. 
def create_directory(folder):
    flag = True
    while flag:
        try:
            os.mkdir(folder)
        except Exception as e:
            print(f'Failed to create directory {os.getcwd()}{fd}{folder}: {e}')
            print("Try again? (Y/N)")
            response = input().upper()
            if response == "N":
                exit()
        else:
            flag = False

# Create a valid Unix/Windows folder name from the site URL.
def create_folder_name(URL):
    name = URL
    if "http" in name:
        name = name.split('/')[2]
    
    forbidden_chars = ['<', '>', ':', '"', "'", '/', '\\', '|', '?', '*']
    for char in forbidden_chars:
        name = name.replace(char, '-')
    return name

# Retrieve HTML page from the Wayback Machine for each timestamp. Store each in 
# cwd/url/timestamp.
#        timestamp_list : list of timestamps as integers in the format 
#           YYYYMMDDHrHrMinMinSecSec
#        uvURL : the URL the user entered
async def retrieve_pages(timestamp_list, uvURL):
    folder = create_folder_name(uvURL)
    create_directory(folder)
    
    print(f"{len(timestamp_list)} snapshots found. Creating files in " + 
        f'{os.getcwd()}{fd}{folder}...')
    path = folder + '/'
    
    num_duplicates = 0
    num_files = 0
    failed_retrieves = 0
    start = time.time()
    tail = 0
    flag = True
    BATCH_SIZE = 12
    sem = asyncio.Semaphore(5)
    async with aiohttp.ClientSession(trust_env = True) as session:
        while flag:
            if tail < len(timestamp_list):
                try:
                    tasks = [create_file(timestamp, uvURL, path, session, sem)
                        for timestamp in timestamp_list[tail:tail+BATCH_SIZE]]
                    for task in asyncio.as_completed(tasks, timeout=30):
                        result = await task
                        if result == 1:
                            num_files = num_files + 1
                        elif result == 0:
                            num_duplicates = num_duplicates + 1
                        elif result == 2:
                            failed_retrieves = failed_retrieves + 1
                    tail = tail + BATCH_SIZE
                    await asyncio.sleep(2)
                # KeyboardInterrupt
                except CancelledError:
                    print("Cancelled.")
                    await session.close()
                    exit()
            else:
                flag = False
    
    print(f'{num_files} files created with {num_duplicates} duplicate snapshots'
        + f' and {failed_retrieves} failures.')
    elapsed = time.time() - start
    print('Done in %.2f seconds.' % elapsed)
    
    pretty_text_loop(folder, path, num_files)

# Convert to text files.
#        folder: directory storing the snapshots
#        path: absolute path to the folder storing the snapshots
def pretty_text_loop(folder, path, files):
    print(f'Strip HTML and create {files} additional text files? [Y/N]')
    pretty_flag = True
    while pretty_flag == True:
        response = input().upper()
        if response == 'Y':
            pretty_flag = False
            print("Creating files in " + f'{os.getcwd()}{fd}{folder}{fd}text files...')
            pretty_text(path)
        elif response == 'N':
            exit()
        else:
            print("Invalid response.")

# Create a separate folder and populate with text-only files for each snapshot.
def pretty_text(path):
    create_directory(path + 'text files')
    file_counter = 0
    
    files = os.listdir(path)
    for file in files:
        if os.path.isfile(os.getcwd() + '/' + path + file):
            text_only = ""
            with open(path + '/' + file, 'r') as f:
                soup = bs4.BeautifulSoup(f, 'html.parser')
                text_only = soup.get_text()
            f.close()
            
            with open(path + '/' + 'text files' + '/' + file[:-5] + '.txt', 'w') as txt_file:
                txt_file.write(text_only)
            txt_file.close()
            file_counter += 1
    print(f'{file_counter} files created.')

# Make an asynchronous request for one Wayback Machine page. Creates a file from 
# the entire HTML response.
# Returns 1 if the file was successfully created
#         2 if the page can't be reached
#         0 if the Wayback CDX stored a duplicate snapshot.
#        timestamp : the snapshot's Wayback Machine timestamp
#        uvURL : original URL the user entered
#        path : local path where the HTML file will be stored
#        session : aiohttp asynchronous session
async def create_file(timestamp, uvURL, path, session, sem):
    url = 'https://web.archive.org/web/' + str(timestamp) + '/' + uvURL
    async with sem:
        if sem.locked(): # allow other requests to resolve
            await asyncio.sleep(2)
        async with session.get(url) as response:
            if response.status == 200:
                html_text = await response.text()
                page_path = path + str(timestamp) + '.html'
                if not os.path.exists(page_path):
                    try:
                        with open(page_path, 'w') as file:
                            file.write(html_text)
                        file.close()
                    except Exception as e:
                        print(f'Failed to create file {os.getcwd()}{fd}{page_path}: {e}')
                    else:
                        return 1
                else:
                    return 0
            else:
                print(f'Failed to retrieve snapshot {timestamp}. Response code {response.status}')
                return 2

# Set async selector loop policy if running on Windows and update directory 
# separator.
def check_os():
    if sys.platform.startswith('win32'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        global fd
        fd = '\\'
    