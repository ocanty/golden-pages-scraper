
import asks
import csv
import trio
import string
import json
import bs4
import signal
import sys
from urllib.parse import urlencode

asks.init('trio')
http = asks.Session()

categories = set()
businesses = { }

API = 'https://www.goldenpages.ie/q/ajax/'

async def add_autosuggested_category(input_string) -> set:
    """
        Add suggested categories to the global categories for a given string
        goldenpages.ie uses an API endpoint that recommends categories based off what the user is typing
    """
    query = urlencode({'text':input_string})
    suggestions_json_resp = await http.get(f'{API}/autosuggestion.json?{query}')

    try:
        suggestions_resp = json.loads(suggestions_json_resp.content)
    except ValueError:
        print('/autosuggestion.json returned bad JSON :(, the API may have changed', file=sys.stderr)
        return

    if 'autoSuggestionList' in suggestions_resp:
        for suggestionsContainer in suggestions_resp['autoSuggestionList']:
            categories.add(suggestionsContainer['suggestion'])

async def add_businesses_on_page(location, category, page):
    """
        Adds business results for a location, category and by page to the business list
    """
    query = urlencode({
        'input':            category.replace(' ', '+'),
        'what':             category.replace(' ', '+'),
        'where':            location,
        'page':             str(page),
        'resultlisttype':   'A_AND_B',
        'sort':             'distance',
        'localsearch':      '1',
        'type':             'DOUBLE',
        'refine':           'locality2_' + location
    })

    business_json_resp = await http.get(f'{API}/business?{query}')
    
    try:
        business_resp = json.loads(business_json_resp.content)
    except ValueError:
        print('/business returned bad JSON :(, the API may have changed', file=sys.stderr)
        return

    if 'html' in business_resp:
        # html returned in the decoded json object
        soup = bs4.BeautifulSoup(business_resp['html'],'html.parser')

        # parse it
        listings = soup.find_all('div',class_='listing')

        for listing in listings:
            listingContent = listing.find('div',class_='listing_content')
            
            if listingContent:
                titleNode = listingContent.find('h3',class_='listing_title')
                title     = titleNode.select_one('a').text.strip() if (titleNode and titleNode.select_one('a')) else ''
            
                addressNode = listingContent.find('div',class_='result-address')
                address = addressNode.text.strip() if addressNode else ''
                
                phoneNode = listingContent.find('div',class_='listing_number')
                phone     =  phoneNode.select_one('a').text.strip() if (phoneNode and  phoneNode.select_one('a')) else ''

                
                if title in businesses:
                    businesses[title]['categories'].add(category)
                else:
                    businesses[title] = { 
                        'title': title,
                        'address': address,
                        'phone': phone,
                        'categories': set()
                    }
                    print(f'Total: {len(businesses.keys())}\t{title}\t\t\t\t{category}')
                    businesses[title]['categories'].add(category)

                

async def dump_businesses_to_file():
    print('Dumping to output.tsv...')
    with open('output.tsv','w') as file:
        w = csv.DictWriter(file,['Business Title','Address','Phone','Categories'],dialect='excel-tab')
        w.writeheader()

        for key in businesses:
            business = businesses[key]
            w.writerow({
                'Business Title':   business['title'],
                'Address':          business['address'],
                'Phone':            business['phone'],
                'Categories':       business['categories']
            })

async def main():
    """
        Main entrypoint
    """
    print('Golden Pages Business Scraper')
    print('Exit at any time with Ctrl+C')
    input('Press enter to begin...')
    print('Getting categories...\n')

    async with trio.open_nursery() as nursery:
        # get each possible category by cycling
        # through every letter of the alphabet and asking for a suggestion
        for letter in string.ascii_lowercase:
            await trio.sleep(0.1)
            nursery.start_soon(add_autosuggested_category, letter)
    
    print(categories)

    location = input('Enter town-name: ')
    print('Targeting businesses in ' + location)

    page_depth = int(input('Specify the maximum page depth: '))
 
    input('Press enter to begin scraping to output.tsv...')
    
    async with trio.open_nursery() as nursery:        
        # start scraping
        for category in categories:
            for page in range(0,page_depth):
                await trio.sleep(0.1)
                nursery.start_soon(add_businesses_on_page,location,category,page)
    
    await dump_businesses_to_file()
        
def gpscraper():
    trio.run(main)

 