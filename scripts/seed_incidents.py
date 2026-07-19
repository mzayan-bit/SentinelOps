import time
import random
import requests

def seed_incidents():
    base_url = "http://localhost:8001/api/incidents"
    cameras = ["CAM-MAIN-GATE", "CAM-SCAFFOLDING-01", "CAM-ZONE-B", "CAM-LOADING-DOCK"]
    severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    descriptions = [
        "Worker missing hard hat in scaffolding zone",
        "Worker missing high-visibility safety vest",
        "Unauthorized entry into restricted hazardous zone",
        "Loitering detected near fuel storage",
        "Missing safety goggles during operation",
        "Suspicious unknown object left unattended"
    ]
    
    print("Seeding Incidents to backend timeline...")
    count = 0
    # Because backend auth was bypassed to accept any token, this will succeed.
    headers = {"Authorization": "Bearer demo-token"}
    
    for _ in range(35):
        payload = {
            "camera_id": random.choice(cameras),
            "severity": random.choices(severities, weights=[40, 30, 20, 10])[0],
            "description": random.choice(descriptions),
            "screenshot_path": None
        }
        try:
            res = requests.post(base_url, json=payload, headers=headers)
            if res.status_code == 201:
                count += 1
                time.sleep(0.05) # Add slight stagger for realism
            else:
                print(f"Failed to post: {res.status_code} {res.text}")
        except Exception as e:
            print("Error connecting to backend:", e)
            return

    print(f"✅ Successfully seeded {count} incidents for the Violations page!")

if __name__ == "__main__":
    seed_incidents()
