import requests 
import json
from dotenv import load_dotenv
load_dotenv()
import os
from google.transit import gtfs_realtime_pb2
from google.protobuf.json_format import MessageToDict
from datetime import datetime, timedelta
sys_path_add = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
if sys_path_add not in sys.path:
    sys.path.insert(0, sys_path_add)
from parser import parse_trip_updates

API_KEY = os.getenv("TRANSPORT_NSW_API_KEY")

def fetch_buses_updates():
    """Fetch buses trip updates and save to JSON file."""
    url = "https://api.transport.nsw.gov.au/v1/gtfs/realtime/buses"
    headers = {
        "Authorization": f"apikey {API_KEY}"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)

        data = MessageToDict(feed, preserving_proto_field_name=True)

        # Parse and store directly in database (no JSON file)
        import tempfile
        import json as json_module
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json_module.dump(data, tmp)
            tmp_path = tmp.name
        
        parse_trip_updates(tmp_path, "buses")
        import os as os_module
        os_module.unlink(tmp_path)  # Delete temp file
        print(f"✅ Buses trip updates stored to database")
        return True
    except requests.exceptions.RequestException as e:
        print(f"HTTP error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_buses_updates()