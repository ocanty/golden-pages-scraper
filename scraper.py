
import asks
import trio
import string
import json
import bs4
import signal

asks.init("trio")
http = asks.Session()
categories = [ ]
businesses = { }


async def get_suggested_categories(letter):
    resp = await http.get("https://www.goldenpages.ie//q/ajax/autosuggestion.json?text=" + letter)
    
    result = json.loads(resp.content)
    
    if 'autoSuggestionList' in result:
        for suggestionContainer in result['autoSuggestionList']:
            categories.append(suggestionContainer['suggestion'])

async def get_businesses_on_page(location,category,page):
    resp = await http.get(
        "http://www.goldenpages.ie/q/ajax/business?type=DOUBLE" +
        "&input=" + category +
        "&where=" + location +
        "&what=" + category + 
        "&resultlisttype=A_AND_B&page=" + str(page) + 
        "&sort=distance&localsearch=1"
    )
    
    result = json.loads(resp.content)
    
    if 'html' in result:
        soup = bs4.BeautifulSoup(result['html'],"html.parser")

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
                    businesses[title]["Categories"].append(category)
                else:
                    businesses[title] = { "Title":title,"Address":address,"Phone":phone, "Categories": [category] }

                    

import csv

async def dump_businesses():
    with open("output.tsv","w") as file:
        w = csv.DictWriter(file,["Title","Address","Phone","Categories"],dialect='excel-tab')
        w.writeheader()

        for key in businesses:
            business = businesses[key]
            w.writerow({"Title":business["Title"],"Address":business["Address"],"Phone":business["Phone"],"Categories":business["Categories"]})
   
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
    print("Golden Pages Business Scraper")
    print("Exit at any time with Ctrl+C")
    input("Press enter to begin...")
    
    # The auto suggestion json endpoint suggests categories based off entered text
    # If we use each letter of the alphabet we can use 
    # sidenote:
    # we do not need to worry about closing the connection as when the urlopen object goes out of scope,
    # it's destructor will close the request

    print("Getting categories...\n")

    async with trio.open_nursery() as nursery:
        for letter in string.ascii_lowercase:
            await trio.sleep(0.1)
            nursery.start_soon(get_suggested_categories,letter)
    
    print(categories,"\n")

    location = input("Enter location: ")
    print("Targeting businesses in " + location)

    page_depth = int(input("Specify the maximum page depth (a higher page depth will give results further away from the location): "))
    print("Page depth is " + str(page_depth))

    input("Press enter to begin scraping to output.tsv...")
    
    async with trio.open_nursery() as nursery:
        # spawn a signal watching task, which waits for CtrlC to dump businesses
        nursery.start_soon(dump_businesses_to_file_on_ctrl_c)
        
        # start scraping
        for category in categories:
            for page in range(0,page_depth):
                await trio.sleep(1)
                nursery.start_soon(get_businesses_on_page,location,category,page)
                
                print("Got \u0009" + str(len(businesses.keys())) + "\u0009 businesses! Press Ctrl-C to dump to log.csv" u"\u0009" + category + u"\u0009")
    
        dump_businesses()
        
    
trio.run(main)

 