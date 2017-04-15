

var request = require("request")
var cheerio = require("cheerio")
var readline = require("readline")

var categories = [ ]
var businesses = { }
var alphabet = "abcdefghijklmnopqrstuvwxyz"


var fs = require('fs');

var logStream = fs.createWriteStream('log.txt', {flags:'a'});

function log (str) {
  logStream.write(str);
}

module.exports = log;

console.log("Golden Pages Business Scraper")
console.log("Delete log.txt before use! New data will not overwrite previous. This is intentional")
console.log("log.txt will be populated with businesses, each line seperated by tabs, we cannot account for business owners who felt the need to spam their business across many categories. duplicate and malformed entries will not be removed\n\n")
console.log("Press Ctrl-C to stop the scraping process at any time")
console.log("Successful use cannot be guaranteed as the GoldenPages API is not publically documented\n\n\n")
console.log("The creator of this program assumes no responsibility for any issues or problems the use of this program may cause\n\n\n")
console.log("For educational use only\n\n")

console.log("GoldenPages API still returns businesses with bad locations for categories with little businesses, you will have to filter this yourself")
console.log("I personally filtered the businesses by landline prefixes which are based on county, eg.. 02x for Southern Ireland. This just leaves you with mobile numbers to filter")

var rl = readline.createInterface({
	input: process.stdin,
	output: process.stdout
});

rl.question("Enter location (typically inaccurate): (eg. Cork)\n", function(answer)
{
	doDump(answer)
	rl.close()
})


// http://www.goldenpages.ie//q/ajax/wheresuggestion.json?text=<area>
// will suggest areas in ireland, unused for now

// http://www.goldenpages.ie//q/ajax/autosuggestion.json?text=<text>
// suggests categories in golden pages, simply check each letter of the alphabet and scrape every single category

function doDump(location)
{
	var lastRequest = false
	console.log(location)
	console.log("Getting categories...")
	for(i = 0; i <	alphabet.length; i++)
	{
		if( (i+1) > alphabet.length)
		{
			lastRequest = true
		}
		
		request("http://www.goldenpages.ie//q/ajax/autosuggestion.json?text=" + alphabet.substring(i,i+1),
			function(error, response, body)
			{
				if(!error && response.statusCode == 200)
				{
					var autosuggestion = JSON.parse(body);
					for(var pair in autosuggestion.autoSuggestionList)
					{
						//console.log(autosuggestion.autoSuggestionList[pair]["suggestion"]);
						categories.push(autosuggestion.autoSuggestionList[pair]["suggestion"]);
					}
				}
				else
				{
					console.log("Error requesting category")
				}
			}
		);
	}
	
	// wait awhile, then request data
	setTimeout(function()
	{
		for(var category in categories)
		{
			// scrape 10 pages
			for(var page = 1; page < 10; page++)
			{
				setTimeout(function(category,page){
					// http://www.goldenpages.ie/q/ajax/business?what=Hairdressers%20-%20Ladies&location=Mallow&resultlisttype=A_AND_B&page=1&sort=distance&localsearch=1
					//console.log("http://www.goldenpages.ie/q/ajax/business?type=DOUBLE&location="+location+"&what=" + category + "&resultlisttype=A_AND_B&page=" + page + "&sort=distance&localsearch=1")
					request("http://www.goldenpages.ie/q/ajax/business?type=DOUBLE&location="+location+"&what=" + category + "&resultlisttype=A_AND_B&page=" + page + "&sort=distance&localsearch=1",
						function(error, response, body)
						{
							if(!error && response.statusCode == 200)
							{
								// load html into cheerio and parse it
								var json = JSON.parse(body)
								var html = json["html"]
								$ = cheerio.load(html);
								//var num = (page*20)-19;
								var _base = $(".listing");
								for(var i = 0; i < _base.length; i++)	
								{
									
									var base = $($(_base[i])[0])
								
									var name = $(base.find( ".listing_title" )[0]).text().trim()
									var address = $(base.find( ".listing_address" )[0]).text().trim()
									var number = $(base.find( ".listing_number" )[0]).text().trim()
									var list_category = $(base.find( ".listing_category" )[0]).text().trim()
									//console.log(name)
									console.log(response.socket._httpMessage.path,"\n",categories[category],list_category, name, address, number)
									//break;
									// log business
									log(list_category + "	" + name + "	" + address + "	" + number + "\n")
									
									//num++;
								}
								
							}
							else
							{
								console.log("failed request ",error);
							}
						}
					)
				},	category*100*page,categories[category],page) // Stagger the requests to stop annoying goldenpages or getting anyone arrested (:/), 
				// also pass the category we want and page
			}
		}
	},1000)
}
