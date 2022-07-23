# import the necessary packages
from imutils.video import VideoStream
from flask import Response
from flask import Flask
from flask import render_template
from flask import request
from requests_html import HTMLSession
from selenium import webdriver
import argparse
import time
import requests
import urllib
import cv2 as cv
import pytesseract

#this should be your path to tesseract.exe (Change between '')
pytesseract.pytesseract.tesseract_cmd = r''

outputFrame = None

# initialize a flask object
app = Flask(__name__)
vs = VideoStream(src=0).start()
time.sleep(2.0)

@app.route("/")
def index():
	return render_template("main.html")


def generate():
	global vs, outputFrame

	while True:
		frame = vs.read()
		outputFrame = frame.copy()
		
		# creates a red box around location where the title of the card should be
		cv.rectangle(frame, (50, 225), (400, 275), (0, 0, 255), 2)

		# check if the output frame is available, otherwise skip the iteration of the loop
		if outputFrame is None:
			continue
		# encode the frame in JPEG format
		(flag, encodedImage) = cv.imencode(".jpg", outputFrame)
		# ensure the frame was successfully encoded
		if not flag:
			continue
		# yield the output frame in the byte format
		yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
			bytearray(encodedImage) + b'\r\n')

		

@app.route("/video_feed")
def video_feed():
	# return the response generated along with the specific media
	return Response(generate(),
		mimetype = "multipart/x-mixed-replace; boundary=frame")

#Makes sure that the URLs are valid
def get_source(url):
	try:
		session = HTMLSession()
		response = session.get(url)
		return response
	except requests.exceptions.RequestException as e:
		print(e)

# finds the line with the card name and finds the exact name
def format_search(google_check):
	findString = google_check

	# keeps the search result names
	file = open("googleSearch.txt", "r")

	lines = file.readlines()

	# find the line with one of the tags with it, dbscardwiki or tcgplayer
	for line in lines:
		if findString in line:
			correctedLine = line
			break

	file.close()

	# changes the corrected lines to be usable
	removeCharacters = "{'}"

	for character in removeCharacters:
		correctedLine = correctedLine.replace(character,"")

	if (findString == "dbscardwiki"):
		correctedLine = correctedLine.replace(" – dbscardwiki","")
	else:
		return(correctedLine)
	return(correctedLine)

#googles the query to find the card and grabs the name on google
def correct_name(query):
	# grabs the url
	query = urllib.parse.quote_plus(query)
	#finds the titles of websites
	response = get_source("https://www.google.com/search?q=" + query)
	css_identifier_result = ".tF2Cxc"
	css_identifier_title = "h3"

	results = response.html.find(css_identifier_result)

	output = []
	#grabs a few search results
	for result in results:
		item = {
			result.find(css_identifier_title, first = True).text
		}

		output.append(item)

	results = output
	#writes the results to this file
	file = open("googleSearch.txt", "w")

	for item in results:
		file.write("%s\n" % item)

	file.close()
	data = format_search("dbscardwiki")
	return(data)

# goes to the website and runs it on an emulator selenium
# runs it and grabs the html code from the site
def web_scrap(correctedLine):
	url = correctedLine

	driver = webdriver.Chrome()

	driver.get(url)
	pageSource = driver.page_source
	fileToWrite = open("page_source.txt", "w")
	fileToWrite.write(pageSource)
	fileToWrite.close()
	driver.quit()

# finds the location of the data you're looking for in the downloaded html code from the website
def findData(findString, end):
    file = open("page_source.txt", "r")
    lines = file.readlines()

    foundFirst = 1

    stringFound = ""

	# locates and records in stringFound the data that is between two strings to narrow down the results
    for line in lines:
        if foundFirst == 2:
            stringFound += line
            if end in line:
                break
        elif findString in line:
            stringFound = line
            foundFirst = 2

	# if the string isn't found then return N/A to the function that this function was called from
	# else split the beginning and end of the strings to find the string purely with data and search terms in it
    if stringFound == "":
        substring = "N/A"
    else:
        split_string = stringFound.split(findString, 1)
        substring = split_string[1]

        split_string = substring.split(end, 1)
        substring = split_string[0]

    file.close()

	# if the string is way too large, it's not the right data and will return N/A
    if (len(substring) > 1000):
        return("N/A")
    return(substring)

# finds each individual data characteristic like name, color, energy
# then it returns and prints the data
def extractData(name, start, end):
	variable = findData(start, end)
	temp = (name + variable)
	print(temp)
	return(temp)

# finds the url of the tcgplayer, scraps the website for data and extracts each portion
def call_tcgplayer(search):
	tag = "tcgplayer"
	query = urllib.parse.quote_plus(search + tag)

	#googles the search term for the tcgplayer link for the card
	response = get_source("https://www.google.com/search?q=" + query)

	#finds the links
	css_identifier_result = ".tF2Cxc"
	css_identifier_link = ".yuRUbf a"

	results = response.html.find(css_identifier_result)

	output = []

	for result in results:

		item = {
        	result.find(css_identifier_link, first = True).attrs['href']
    	}

		output.append(item)

	results = output

	file = open("googleSearch.txt", "w")

	for item in results:
		file.write("%s\n" % item)

	file.close()

	#finds the correct link with tcgplayer
	correctedLine = format_search("tcgplayer")

	#grabs the website's html
	web_scrap(correctedLine)

	data =[]

	#CardName
	cardName =  findData("\"Product\",\"name\":\"", "\"")
	tempCardName = cardName
	cardName = ("Name: " + cardName)
	print(cardName)
	data.append(cardName)

	#CardDetails
	cardDetails = findData("listings on TCGplayer for " + tempCardName + " - Dragon Ball Super CCG - ", "<meta data-vue-meta")
	cardDetails = cardDetails.replace("<br>• ","")
	cardDetails = cardDetails.replace("<br>","")
	cardDetails = cardDetails.replace("<","")
	cardDetails = cardDetails.replace(">","")
	cardDetails = ("Card Details: " + cardDetails)
	print(cardDetails)
	data.append(cardDetails)

	#NormalPrice
	normalPrice = findData("class=\"price\">", "<")
	normalPrice = ("Normal Price: " + normalPrice)
	print(normalPrice)
	data.append(normalPrice)

	#FoilPrice
	foilPrice = findData(normalPrice, "</span></li><li data-v")
	if foilPrice == "N/A":
		print(foilPrice)
	else:
		tempfoilPrice = foilPrice.split("class=\"price\">", 1)
		foilPrice = tempfoilPrice[1]
		print(foilPrice)
	foilPrice = ("Foil Price: " + foilPrice)
	data.append(foilPrice)

	#Set
	data.append(extractData("Set: ", "ProductDetailsSetName\">", "</span>"))

	#CardImage
	data.append(extractData("Card Image: ", "\"image\":", ","))

	#Rarity
	data.append(extractData("Rarity: ", "Rarity:</strong><span data-v-349313ed=\"\">", "</span>"))

	#Number
	data.append(extractData("Number: ", "Number:</strong><span data-v-349313ed=\"\">", "</span>"))

	#CardType
	data.append(extractData("Card Type: ", "Card Type:</strong><span data-v-349313ed=\"\">", "</span>"))

	#Color
	data.append(extractData("Color: ", "Color:</strong><span data-v-349313ed=\"\">", "</span>"))

	#Energy
	data.append(extractData("Energy: ", "Energy(Color Cost):</strong><span data-v-349313ed=\"\">", "</span>"))

	#Power
	data.append(extractData("Power: ", "Power:</strong><span data-v-349313ed=\"\">", "</span>"))

	#ComboPower
	data.append(extractData("Combo Power: ", "Combo Power:</strong><span data-v-349313ed=\"\">", "</span>"))

	#ComboEnergy
	data.append(extractData("Combo Energy: ", "Combo Energy:</strong><span data-v-349313ed=\"\">", "</span>"))

	#Era
	data.append(extractData("Era: ", "Era:</strong><span data-v-349313ed=\"\">", "</span>"))

	#Character
	data.append(extractData("Character: ", "Character:</strong><span data-v-349313ed=\"\">", "</span>"))

	return(data)

@app.route("/btn_click")
def btn_click():
	#Grabs the final frame of the video stream
	frame = vs.read()
	img_name = "analyze.png".format()
	cv.imwrite(img_name, frame)
	img_name = cv.imread('analyze.png')
	
	#crops the image around the red box
	cropped_image = img_name[225:275, 50:400]
	cv.imwrite("analyze.png", cropped_image)

	img = cv.imread("analyze.png")

	#grayscales the image
	gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

	#translates the image to text
	data = pytesseract.image_to_string(gray, lang='eng', config='--psm 6')

	data = data.strip()
	print(data)
	vs.stop()
	#looks up the message on google to get a more accurate read on the card's face
	data = correct_name(data + " dbscardwiki")

	#looks up the information on the card and goes to the next page to display it
	dataList = call_tcgplayer(data)
	return render_template("dataDisplayed.html", dataList = dataList)

#looks up data on the card that the user input by typing in a text box
@app.route('/', methods=['POST'])
def text_only():
	data = request.form['CardName']
	dataList = call_tcgplayer(data)
	return render_template("dataDisplayed.html", dataList = dataList)

# check to see if this is the main thread of execution
if __name__ == '__main__':
	# construct the argument parser and parse command line arguments
	ap = argparse.ArgumentParser()
	ap.add_argument("-i", "--ip", type=str, required=True,
		help="ip address of the device")
	ap.add_argument("-o", "--port", type=int, required=True,
		help="ephemeral port number of the server (1024 to 65535)")
	ap.add_argument("-f", "--frame-count", type=int, default=32,
		help="# of frames used to construct the background model")
	args = vars(ap.parse_args())

	# start the flask app
	app.run(host=args["ip"], port=args["port"], debug=True,
		threaded=True, use_reloader=False)
# release the video stream pointer
vs.stop()

