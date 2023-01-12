import urllib.request as urq
import json
import os
import asyncio
import aiohttp
import time
import sys

def wayback_scrape():
    print("Enter an exact URL:")
    uvURL =  input()
    headers = {"User-Agent": 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0'}
    
    # Retrieve list of available snapshots from the Wayback CDX Server API
    url = 'http://web.archive.org/cdx/search/cdx?url=' + uvURL + '&output=json'
    req = urq.Request(url, headers = headers)
    cdx_response = urq.urlopen(req).read()
    url_list = json.loads(cdx_response)
    
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
# params start : start date in format YYYYMMDD
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
# params url_list : list of snapshots from the CDX server JSON response
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
# params url_list : list of snapshots from the CDX server JSON response
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
            print(f'Failed to create directory {os.getcwd()}\\{folder}: {e}')
            print("Try again? (Y/N)")
            response = input().upper()
            if response == "N":
                exit()
        else:
            flag = False

# Retrieve HTML page from the Wayback Machine for each timestamp. Store each in 
# cwd/url/timestamp.
# params timestamp_list : list of timestamps as integers in the format 
#           YYYYMMDDHrHrMinMinSecSec
#        uvURL : the URL the user entered
async def retrieve_pages(timestamp_list, uvURL):
    folder = uvURL.split('/')[0]
    create_directory(folder)
    
    print(f"{len(timestamp_list)} snapshots found. Creating files in " + 
        f'{os.getcwd()}\\{folder}...')
    path = folder + '/'
    
    num_duplicates = 0
    num_files = 0
    failed_retrieves = 0
    tail = 0
    flag = True
    BATCH_SIZE = 15
    async with aiohttp.ClientSession(trust_env = True) as session:
        while flag:
            if tail < len(timestamp_list):
                tasks = [create_file(timestamp, uvURL, path, session) 
                    for timestamp in timestamp_list[tail:tail+BATCH_SIZE]]
                for task in asyncio.as_completed(tasks):
                    try:
                        result = await task
                        if result == 1:
                            num_files = num_files + 1
                        elif result == 0:
                            num_duplicates = num_duplicates + 1
                        elif result == 2:
                            failed_retrieves = failed_retrieves + 1
                    except:
                        failed_retrieves = failed_retrieves + 1
                tail = tail + BATCH_SIZE
                time.sleep(2)
            else:
                flag = False
    
    print(f'{num_files} files created with {num_duplicates} duplicate snapshots'
        + f' and {failed_retrieves} failures.')

# Make an asynchronous request for one Wayback Machine page. Creates a file from 
# the entire HTML response.
# Returns 1 if the file was successfully created, 
#         2 if the page can't be reached
#         0 if the Wayback CDX stored a duplicate snapshot.
# params timestamp : the snapshot's Wayback Machine timestamp
#        uvURL : original URL the user entered
#        path : local path where the HTML file will be stored
#        session : aiohttp asynchronous session
async def create_file(timestamp, uvURL, path, session):
    url = 'https://web.archive.org/web/' + str(timestamp) + '/' + uvURL
    
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
                    print(f'Failed to create file {os.getcwd()}\\{page_path}: {e}')
                else:
                    return 1
            else:
                return 0
        else:
            print(f'Failed to retrieve snapshot {timestamp}. Response code {response.status}')
            return 2

# Set async selector loop policy if running on Windows.
def check_os():
    if sys.platform.startswith('win32'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

check_os()
wayback_scrape()
