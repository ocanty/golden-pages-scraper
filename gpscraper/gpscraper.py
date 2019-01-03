
import asks
import csv
import trio
import string
import json
import bs4
import signal
import sys

asks.init("trio")
http = asks.Session()

categories = set()
businesses = [ ]

API = 'https://www.goldenpages.ie/q/ajax/'

async def add_autosuggested_category(input_string) -> set:
    """
        Add suggested categories to the global categories for a given string
        goldenpages.ie uses an API endpoint that recommends categories based off what the user is typing
    """
    suggestions_json_resp = await http.get(f'{API}/autosuggestion.json?text={input_string}')

    try
        suggestions_resp = json.loads(suggestions_json_resp.content)
    except ValueError:
        print('/autosuggestion.json returned bad JSON :(, the API may have changed', file=sys.stderr)
        return

    if 'autoSuggestionList' in suggestions_resp:
        for suggestionContainer in suggestions_resp['autoSuggestionList']:
            categories.add(suggestionsContainer['suggestion'])

async def add_businesses_on_page(location, category, page):
    """
        Adds business results for a location, category and by page to the business list
    """
    business_json_resp = await http.get(
        f"""
        {API}/business?type=DOUBLE
        &input={category.replace(' ','+')}
        &what={category.replace(' ','+')} 
        &where={location}
        &refine=locality2_{location}
        &resultlisttype=A_AND_B&page={str(page)} 
        &sort=distance
        &localsearch=1
        """
    )
    
    try:
        business_resp = json.loads(resp.content)
    except ValueError:
        print('/business returned bad JSON :(, the API may have changed', file=sys.stderr)
        return

    if 'html' in business_resp:
        # html returned in the decoded json object
        soup = bs4.BeautifulSoup(business_resp['html'],"html.parser")

        # parse it
        listings = soup.find_all("div",class_="listing")

        for listing in listings:
            listingContent = listing.find("div",class_="listing_content")
            
            if listingContent:
                titleNode = listingContent.find("h3",class_="listing_title")
                title     = titleNode.select_one('a').text.strip() if (titleNode and titleNode.select_one('a')) else ""
            
                addressNode = listingContent.find("div",class_="result-address")
                address = addressNode.text.strip() if addressNode else ""
                
                phoneNode = listingContent.find("div",class_="listing_number")
                phone     =  phoneNode.select_one('a').text.strip() if (phoneNode and  phoneNode.select_one('a')) else ""

                
                if title in businesses:
                    businesses[title]["Categories"].add(category)
                else:
                    businesses[title] = { 
                        "title": title,
                        "address": address,
                        "phone": phone,
                        "categories": set(category)
                    }

async def dump_businesses_to_file():
    with open("output.tsv","w") as file:
        w = csv.DictWriter(file,["Business Title","Address","Phone","Categories"],dialect='excel-tab')
        w.writeheader()

        for key in businesses:
            business = businesses[key]
            w.writerow({
                "Business Title":   business['title"],
                "Address":          business['address"],
                "Phone":            business['phone"],
                "Categories":       business['categories"]
            })
   
async def dump_businesses_to_file_on_ctrl_c():
    # wait for siginterupt
    # https://vorpus.org/blog/control-c-handling-in-python-and-trio/#what-if-you-want-a-manual-control-c-handler
    with trio.catch_signals({signal.SIGINT}) as sigset:
        async for _ in sigset:
            for signum in _:
                if signum == signal.SIGINT:
                    await dump_businesses()
                    quit()
                    
async def main():
    """
        Main entrypoint
    """
    print("Golden Pages Business Scraper")
    print("Exit at any time with Ctrl+C")
    input("Press enter to begin...")
    print("Getting categories...\n")
    categories = set()

    async with trio.open_nursery() as nursery:
        # get each possible category by cycling
        # through every letter of the alphabet and asking for a suggestion
        for letter in string.ascii_lowercase:
            await trio.sleep(0.05)
            nursery.start_soon(add_autosuggested_category, letter)
    
    print(categories,"\n")

    location = input("Enter town-name: ")
    print("Targeting businesses in " + location)

    page_depth = int(input("Specify the maximum page depth: "))
 
    input("Press enter to begin scraping to output.tsv...")
    
    async with trio.open_nursery() as nursery:        
        # start scraping
        for category in categories:
            for page in range(0,page_depth):
                await trio.sleep(0.1)
                nursery.start_soon(get_businesses_on_page,location,category,page)
    
        
def gpscraper():
    trio.run(main)

 