import json 

file_path = "realtime/metro/metro_updates/trip_updates_20260505_190017_778994.json"

def summarize_json(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    for item in data.get('trip_updates', []):
        print(f"Trip ID: {item['trip_id']}, Route ID: {item['route_id']}, Stop ID: {item['stop_id']}, Arrival Time: {item['arrival_time']}")


if __name__ == "__main__":
    summarize_json(file_path)