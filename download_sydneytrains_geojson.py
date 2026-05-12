"""Download the Sydney Trains network GeoJSON from TfNSW Open Data."""
import urllib.request
from pathlib import Path

URL = "https://opendata.transport.nsw.gov.au/data/dataset/3e349c1c-9ac0-4f70-8a3f-b1d3e4cb1042/resource/14e612f4-a20a-412a-8c10-558bb0de9553/download/sydneytrains.geojson"
OUT = Path(__file__).parent / "data" / "sydneytrains.geojson"

OUT.parent.mkdir(parents=True, exist_ok=True)

print(f"Downloading to {OUT} ...")
urllib.request.urlretrieve(URL, OUT)
print(f"Done — {OUT.stat().st_size / 1024:.1f} KB")
