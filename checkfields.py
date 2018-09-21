import json

file1 = open('./tsn:8D60001904CCBD7-trial_stb.txt', 'r')
file2 = open('./output.txt', 'w')
missingFields= dict()

def addKeyToDict(key):
	if key in missingFields:
		missingFields[key] += 1
	else:
		missingFields[key] = 1

for line in file1:
	if 'contentId' not in line:
		addKeyToDict(line)
	if 'sourceType' not in line:
		addKeyToDict(line)
	if 'stationId' not in line:
		addKeyToDict(line)
	'''
	if 'channel' not in line:
		addKeyToDict(line)
	'''
	
print len(missingFields)