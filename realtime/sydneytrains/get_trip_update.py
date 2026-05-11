import requests 
import json
from dotenv import load_dotenv
load_dotenv()
import os
from google.transit import gtfs_realtime_pb2
from google.protobuf.json_format import MessageToDict
from datetime import datetime, timedelta 

API_KEY = os.getenv("TRANSPORT_NSW_API_KEY")
url = "https://api.transport.nsw.gov.au/v2/gtfs/realtime/sydneytrains"

headers = {
    "Authorization": f"apikey {API_KEY}"
}
def fetch_metro_updates():
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)

    data = MessageToDict(feed, preserving_proto_field_name=True)

    filename = f"trip_updates_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
    filepath = f"./realtime/sydneytrains/sydneytrains_updates/{filename}"

    with open(filepath, "w") as f:
        json.dump(data, f)

    print(f"✅ Saved: {filepath}")

if __name__ == "__main__":
    try:
        fetch_metro_updates()
    except requests.exceptions.RequestException as e:
        print(f"HTTP error: {e}")
    except Exception as e:
        print(f"Error: {e}")