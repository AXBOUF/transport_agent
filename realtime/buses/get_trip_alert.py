import requests 
import json
from dotenv import load_dotenv
load_dotenv()
import os
from google.transit import gtfs_realtime_pb2
from google.protobuf.json_format import MessageToDict
from datetime import datetime, timedelta 

API_KEY = os.getenv("TRANSPORT_NSW_API_KEY")
url = "https://api.transport.nsw.gov.au/v2/gtfs/alerts/buses"

headers = {
    "Authorization": f"apikey {API_KEY}"
}
response = requests.get(url, headers=headers)
if response.status_code == 200:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)
    data = MessageToDict(feed , preserving_proto_field_name=True)
    # print(json.dumps(data, indent=2))
    # name the file with the current date and time
    filename = f"trip_alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = f"./realtime/buses/buses_alerts/{filename}"
    with open(filepath, "w") as f:
        json.dump(data, f)
    print(f"✅ Trip alerts saved to {filepath}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)