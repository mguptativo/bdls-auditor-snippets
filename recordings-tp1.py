import logging
import requests
import sys
import json
import datetime

class Recordings(object):

    try:
        import http.client as http_client
    except ImportError:
        # Python 2
        import httplib as http_client

    http_client.HTTPConnection.debuglevel = 1

    # You must initialize logging, otherwise you'll not see debug output.
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True

    config = dict()
    config['sls'] = "http://sls.tivoservice.com/Get?bodyId=tsn:"
    config['seamless'] = "http://janus-prod-admin-0.digitalsmiths.net/"
    config['kvmind']="http://sjkvmind-vip-v120.tivo.com:8083"

    def setConfig(self, tsn):
        r = requests.get("http://sls.tivoservice.com/Get?bodyId=tsn:" + tsn + "&service=httpinternal")

        self.config['tsn'] = tsn

        if r.text:
            fields = r.text.split(":")
            self.config['mind'] = "http://" + fields[1] + ":8085"
            fields2 = fields[1].split(".")
            self.config['env'] = fields2[1]
            if self.config['env'] == "st":
                self.config['seamless'] = "http://janus-staging-admin-0.digitalsmiths.net"
            else:
                self.config['seamless'] = "http://janus-prod-admin-0.digitalsmiths.net"

        self.config['tcid'] = self.getTcid(tsn)
        self.config['deviceId'] = self.getInternalId("tsn:" + tsn)
        self.config['userId'] = self.getInternalId(self.config['tcid'])

    def getTcid(self, tsn):
        headers = {'Accept': 'application/json', 'X-KV-Encoding': 'New'}

        r = requests.get(
            self.config['kvmind'] + "/mind/mind21?type=bodyKeyValueSearch&bodyId=tsn:" + tsn + "&key=auth",
            headers=headers)

        data = r.json()

        if 'bodyKeyValue' in data:
            bodyKeyValue = data['bodyKeyValue'][0]
            values = bodyKeyValue['value'].split("|")
            return values[5]

    def getInternalId(self, str):
        headers = {'Content-type': 'application/json'}
        payload = {'type': 'anonymizerExternalIdTranslate', 'externalId': str}

        try:
            r = requests.post("http://anonymizer.tpa1.tivo.com/anonymizerExternalIdTranslate", data=json.dumps(payload), headers=headers)
        except:
            return 0

        data = r.json()

        if 'internalId' in data:
            return data['internalId']

        return -1

    def recordingListWrite(self):
        print self.config['tsn']

        ## Get Recordings from STB
        stbRecs = self.stbRecordings(self.config['tsn'])
        ## Get Recordings from PCD
        pcdOnly, stbOnly = self.pcdRecordings(self.config['tsn'], stbRecs)

        file_name = self.config['tsn'] + "-recs"
        write_file_stb = open(file_name + "_stb.txt", 'w')
        write_file_pcd = open(file_name + "_pcd.txt", 'w')
        if(stbOnly != None):
            write_file_stb.write('\n'.join(list(stbOnly)) + "\n\n")
        if(pcdOnly != None):
            write_file_pcd.write('\n'.join(list(pcdOnly)) + "\n\n")

    def stbRecordings(self, tsn):
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        try:
            r = requests.get(self.config['mind'] + "/mind/mind25?type=myShowsItemSearch&bodyId=tsn:" + self.config['tsn'] + "&flatten=true", headers=headers)
            print(self.config['mind'] + "/mind/mind25?type=myShowsItemSearch&bodyId=tsn:" + self.config['tsn'] + "&flatten=true")
        except:
            output = "Failed to find myshows in the mind for: " + self.config['tsn']
            return output

        data = r.json()
        
        if 'myShowsItem' not in data:
            return None
        
        items = data.get('myShowsItem')
        recs = set()
        fullRecs = list()

        if len(items) == 0:
            return None

        for item in items:
            rec = dict()
            rec['id'] = item['myShowsItemId']
            rec['itemId'] = item['contentId']

            startTime = item['startTime']
            ts = datetime.datetime.strptime(startTime, "%Y-%m-%d %H:%M:%S")
            epoch = datetime.datetime.utcfromtimestamp(0)
            timestamp = int((ts - epoch).total_seconds() * 1000)

            rec['timestamp'] = timestamp

            if 'duration' in item:
                rec['duration'] = item['duration']

            if 'stationId' in item:
                rec['stationId'] = item['stationId']

            rec['deviceId'] = self.config['deviceId']

            fullRecs.append(rec)

            recs.add(item['contentId'])

        return recs

    def pcdRecordings(self, tsn, recs):
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        try:
            r = requests.get(self.config['seamless'] + "/sd/tivo/deviceRecordings/users/{userId}/recordings?deviceId={deviceId}".format(userId=self.config['userId'], deviceId=self.config['deviceId']), headers=headers)
            print(self.config['seamless'] + "/sd/tivo/deviceRecordings/users/{userId}/recordings?deviceId={deviceId}".format(userId=self.config['userId'], deviceId=self.config['deviceId']))
        except:
            return 0

        data = r.json()
        
        pcdRecs = set()
        for rec in data:
            pcdRecs.add(rec['itemId'])

        if(recs == None):
            return pcdRecs, None
        pcdOnly = pcdRecs - recs
        mindOnly = recs - pcdRecs
       
        return pcdOnly, mindOnly

def main():
    input_tsn = open("./hydra-tcds.txt", 'r')
    for line in input_tsn:
        tsn, anonTsn = line.strip().split('-')
        tsn = tsn.strip().split(':')[1].upper()
        anonTsn = anonTsn.strip().split(':')[1].upper()
        obj = Recordings()
        obj.setConfig(tsn)
        obj.recordingListWrite()

if __name__ == "__main__":
    main()
