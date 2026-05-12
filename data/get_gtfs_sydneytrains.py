# this script contains an api call to download zip files containing GTFS data for static feeds. It is used to download the latest data for the GTFS feed experiments.
# Static timetable, stop locations & route shape information in GTFS format.


import requests
import os 
import zipfile
import io
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("TRANSPORT_NSW_API_KEY")

url = "https://api.transport.nsw.gov.au/v1/gtfs/schedule/sydneytrains"

print("Downloading GTFS timetable data...")
response = requests.get(url, headers={"Authorization": f"apikey {API_KEY}"})

if response.status_code == 200:
    # The response is a ZIP file containing CSV files
    zip_file = zipfile.ZipFile(io.BytesIO(response.content))
    
    print(f"\nGTFS ZIP contains these files:")
    print("-" * 40)
    for filename in zip_file.namelist():
        print(f"  {filename}")
    
    # Example: Read and preview stops.txt
    print("\n--- Preview of stops.txt (first 5 lines) ---")
    with zip_file.open("stops.txt") as f:
        for i, line in enumerate(f):
            if i >= 5:
                break
            print(line.decode("utf-8").strip())
    
    # Extract all files to a folder
    zip_file.extractall("gtfs_sydneytrains")
    print("\n✅ Extracted to ./gtfs_sydneytrains/")
    
    zip_file.close()
else:
    print(f"Error: {response.status_code}")
    print(response.text)