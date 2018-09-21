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

    config = dict()
    config['sls'] = "http://sls.tivoservice.com/Get?bodyId=tsn:"
    config['seamless'] = "http://janus-staging-admin-0.digitalsmiths.net/"
    config['kvmind']="http://sjkvmind-vip-v120.tivo.com:8083"
    config['internalId'] = ""

    def setConfig(self, tsn):
        r = requests.get("http://sls.tivoservice.com/Get?bodyId=tsn:" + tsn + "&service=httpinternal")

        self.config['tsn'] = tsn

        if r.text:
            fields = r.text.split(":")
            self.config['mind'] = "http://" + fields[1] + ":8085"
            print self.config['mind']
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
            r = requests.post("http://anonymizer.tpa1.tivo.com:80/anonymizerExternalIdTranslate", data=json.dumps(payload), headers=headers)
        except:
            return 0

        data = r.json()

        if 'internalId' in data:
            self.config['internalId'] = data['internalId']
            return data['internalId']

        return -1

    def recordingListWrite(self):
        print self.config['tsn']

        ## Get Recordings from PCD
        pcdRecs= self.pcdRecordings(self.config['tsn'])
        stbRecs= self.stbRecordings(self.config['tsn'])
        
        file_name_internal = self.config['internalId'] + "-trial"
        file_name_external = "tsn:" + self.config['tsn'] + "-trial"
        write_file_pcd = open(file_name_internal + "_pcd_norecs.txt", 'w')
        write_file_stb = open(file_name_external + "_stb.txt", 'w')

        if(pcdRecs != None):
            for line in pcdRecs:
                pcdOnly = json.dumps(line)
                write_file_pcd.write(pcdOnly + "\n")
        if(stbRecs != None):
            for line in stbRecs:
                stbOnly = json.dumps(line)
                write_file_stb.write(stbOnly + "\n")
       
        

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
        fullRecs = list()

        if len(items) == 0:
            return None

        for item in items:
            rec = dict()
            '''
            rec['id'] = item['myShowsItemId']
            rec['itemId'] = item['contentId']

            startTime = item['startTime']
            ts = datetime.datetime.strptime(startTime, "%Y-%m-%d %H:%M:%S")
            epoch = datetime.datetime.utcfromtimestamp(0)
            timestamp = int((ts - epoch).total_seconds() * 1000)

            rec['timestamp'] = startTime

            if 'duration' in item:
                rec['duration'] = item['duration']

            if 'stationId' in item:
                rec['stationId'] = item['stationId']

            rec['deviceId'] = self.config['deviceId']
            '''
            fullRecs.append(item)

        return fullRecs
       
    def pcdRecordings(self, tsn):
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        try:
            r = requests.get(self.config['seamless'] + "/sd/tivo/deviceRecordings/users/{userId}/recordings?deviceId={deviceId}".format(userId=self.config['userId'], deviceId=self.config['deviceId']), headers=headers)
            print(self.config['seamless'] + "/sd/tivo/deviceRecordings/users/{userId}/recordings?deviceId={deviceId}".format(userId=self.config['userId'], deviceId=self.config['deviceId']))
        except:
            return 0

        data = r.json()
        
        pcdRecs = list()
        for rec in data:
            if 'requestedByUser' not in rec:
                recs = dict()
                recs['id'] = rec['id']
                recs['itemId'] = rec['itemId']
                timestamp = rec['timestamp']/1000
                startTime = datetime.datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                recs['timestamp'] = startTime
                if 'duration' in rec:
                    recs['duration'] = rec['duration']

                if 'stationId' in rec:
                    recs['stationId'] = rec['stationId']
                recs['deviceId'] = rec['deviceId']

                if(rec['id'] == "tivo:ctl.15000001"):
                    print json.dumps(rec, indent=2)
                
                pcdRecs.append(recs)

        return pcdRecs

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
