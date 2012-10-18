#! /usr/local/bin/pythonw
# see readme for notes

import sys
import re
from datetime import datetime, timedelta

# Define our uniqify function for removing duplicate records
# from Peter Bengtsson, peterbe.com
def uniqify(seq, idfun=None): 
   # order preserving
   if idfun is None:
       def idfun(x): return x
   seen = {}
   result = []
   for item in seq:
       marker = idfun(item)
       # in old Python versions:
       # if seen.has_key(marker)
       # but in new ones:
       if marker in seen: continue
       seen[marker] = 1
       result.append(item)
   return result

# Get list index from value
def get_positions(xs, item):
    if isinstance(xs, list):
        for i, it in enumerate(xs):
            for pos in get_positions(it, item):
                yield (i,) + pos
    elif xs == item:
        yield ()

# Get file names 
f = open(sys.argv[1])
target = open(str(sys.argv[2]+'.txt'), "w")

# Check for decay time argument
if sys.argv[3]:
	decayTime = int(sys.argv[3])
	nodelist = []
	
# Read source file
unparsedTweets = f.read()

# Find individual tweets
newentry = re.compile(r'\n"[a-zA-Z]{3,3}.+?(?=\n"[a-zA-Z]{3,3}|\Z)', re.DOTALL)

# Load individual tweets into list parsedTweets
parsedTweets = newentry.findall(unparsedTweets)

# Find unique entries in list parsedTweets, load in uniqueTweets
uniqueTweets = uniqify(parsedTweets)

# Compile regex statements to find the date of message ("tweettime"), any retweets in message ("retweet"), any tweet-ats ("tweetat"), and the username of message author ("usr")

tweettime = re.compile(r'(?<="[a-zA-Z]{3,3},\s)\d{2,2}\s*[a-zA-Z]{3,3}\s\d{4,4}\s(\d{2,2}:){2,2}\d{2,2}\s(\+\d{4,4})(?=")', re.MULTILINE) # Timestamp (pubDate) regex statement
retweet = re.compile(r'(?<=RT\s@)[\w_]+(?=[\s:,])', re.IGNORECASE|re.MULTILINE)			# Retweet regex statement
tweetat = re.compile(r'(?<!RT\s@)(?<=@)[\w_]+(?=[\s:,])', re.IGNORECASE|re.MULTILINE)	# Tweet-at regex statement
usr = re.compile(r'(?<=,")[\w\W][^,]+(?=@twitter.com \()', re.IGNORECASE|re.MULTILINE)	# Username of author

# Now we write out edglist (no time argument)
# Loop through all parsed tweets, feed each tweet in "line"
for line in uniqueTweets:
	pubDate = tweettime.search(line) # Look for timestamp
	RT = retweet.search(line) 		 # Look for retweets
	AT = tweetat.findall(line)    	 # Look for tweet-ats
	SN = usr.search(line)            # Look for the username of the author	
	
	# If message is a retweet, create an edge leading from the original poster (mentioned in retweet) and the current author.
	if RT:
		toPrint = str(RT.group() + ',' + SN.group() + ',' + pubDate.group() + '\n')	# Create a string specifing a Retweet edge.
		toPrintStr = toPrint.lower() 		# Set all usernames to lowercase, as twitter is case-insensative.
		target.write(toPrintStr) 			# Print retweet edge to file.
		# Prepare a nodelist for graphml file if we were passed a time argument
		nodelist.append(SN.group())
		nodelist.append(RT.group())		

	# If the message contains tweet-ats, create a edge from the current author to each user tweeted at.
	if AT:
		for s in AT:
			toPrint = str(SN.group() + ',' + s + ',' + pubDate.group() +'\n')   # Create a string specifing a Tweet-at edge.
			toPrintStr = toPrint.lower()        # Set all usernames to lowercase.
			target.write(toPrintStr) 			# Print Tweet-at edge to file.
			nodelist.append(SN.group())
			nodelist.append(s)
    		
# Now the gexf file (if we were passed a time argument)

if decayTime:
	# remove duplicate entries from node list, save as an array (for "reverse" indexing)
	uniqueEdgelist = []
	uniqueNodelist = []
	
	for node in uniqify(nodelist):
		uniqueNodelist.append([node,])

	edgeID = 0
	# loop over tweets, create edgelist
	# format: <edge id="0" source="0" target="1" start="2009-03-01"/>
	for line in uniqueTweets:
		pubDate = tweettime.search(line) # Look for timestamp
		RT = retweet.search(line) 		 # Look for retweets
		AT = tweetat.findall(line)    	 # Look for tweet-ats
		SN = usr.search(line)            # Look for the username of the author

		# Convert timestamp to datetime object, create decay time.
		startTime = datetime.strptime(pubDate.group(), "%d %b %Y %H:%M:%S +0000")
		#GEXF accepts the XML dateTime object, formatted as: YYYY-MM-DDThh:mm:ss
		eTime = startTime + timedelta(hours=3)
		if decayTime > 0:
			endTime = str(' end=\"' + eTime.strftime("%Y-%m-%dT%H:%M:%S") + '\" ')
		
		
		# If the message contains a retweet tag:
		if RT:
			# Add the edge entry
			uniqueEdgelist.append(str('<edge id =\"' + str(edgeID) + '\" source=\"' + RT.group() + '\" target=\"' + SN.group() + '\" start=\"' + startTime.strftime("%Y-%m-%dT%H:%M:%S") + '\"' + endTime + '/>'))
			edgeID = edgeID + 1
			# Add a "spell" (see gexf format for more info) for corresponding nodes:
			uniqueNodelist[list(get_positions(uniqueNodelist, SN.group()))[0][0]].append(str('<spell start=\"' + startTime.strftime("%Y-%m-%dT%H:%M:%S") + '\"' + endTime + '/>'))
			uniqueNodelist[list(get_positions(uniqueNodelist, RT.group()))[0][0]].append(str('<spell start=\"' + startTime.strftime("%Y-%m-%dT%H:%M:%S") + '\"' + endTime + '/>'))
		
		# If the message contains tweet-at tags:
		if AT:
			for s in AT:
				uniqueEdgelist.append(str('<edge id =\"' + str(edgeID) + '\" source=\"' + SN.group() + '\" target=\"' + s + '\" start=\"' + startTime.strftime("%Y-%m-%dT%H:%M:%S") + '\"' + endTime + '/>'))
				edgeID = edgeID + 1
				# Add a "spell" (see gexf format for more info) for corresponding nodes:
				uniqueNodelist[list(get_positions(uniqueNodelist, SN.group()))[0][0]].append(str('<spell start=\"' + startTime.strftime("%Y-%m-%dT%H:%M:%S") + '\"' + endTime + '/>'))
				uniqueNodelist[list(get_positions(uniqueNodelist, s))[0][0]].append(str('<spell start=\"' + startTime.strftime("%Y-%m-%dT%H:%M:%S") + '\"' + endTime + '/>'))
	
	# Print results to file
	gexf = open(str(sys.argv[2]+'.gexf'), 'w')
	
	#GEXF header junk
	gexf.write('<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n')
	gexf.write('<gexf xmlns=\"http://www.gexf.net/1.2draft\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:schemaLocation=\"http://www.gexf.net/1.2draft http://www.gexf.net/1.2draft/gexf.xsd\" version=\"1.2\">\n')
	gexf.write('\t<graph mode=\"dynamic\" defaultedgetype=\"directed\" timeformat=\"dateTime\">\n')
	
	#Nodes
	gexf.write('\t\t<nodes>\n')
	for node in uniqueNodelist:
		gexf.write(str('\t\t\t<node id=\"' + node[0] + '\">\n'))
		gexf.write("\t\t\t\t<spells>\n")
		for spell in node[1:]:
			gexf.write(str("\t\t\t\t\t" + spell +"\n"))
		gexf.write("\t\t\t\t</spells>\n")
		gexf.write("\t\t\t</node>\n")
	gexf.write("\t\t</nodes>\n")
	
	#Edges
	gexf.write("\t\t<edges>\n")
	for edge in uniqueEdgelist:
		gexf.write(str("\t\t\t" + edge +"\n"))
	gexf.write("\t\t</edges>\n")
	
	#GEXF footer junk
	gexf.write("\t</graph>\n")
	gexf.write("</gexf>")
		