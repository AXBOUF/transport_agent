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
from pg_writer import write_alerts

API_KEY = os.getenv("TRANSPORT_NSW_API_KEY")

def fetch_sydneytrains_alerts():
    """Fetch sydneytrains alerts and write to PostgreSQL."""
    url = "https://api.transport.nsw.gov.au/v2/gtfs/alerts/sydneytrains"
    headers = {
        "Authorization": f"apikey {API_KEY}"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        data = MessageToDict(feed, preserving_proto_field_name=True)

        write_alerts(data, "sydneytrains")
        print(f"✅ Sydney Trains alerts stored to database")
        return True
    except requests.exceptions.RequestException as e:
        print(f"HTTP error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_sydneytrains_alerts()