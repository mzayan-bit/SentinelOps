import sys
import random
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure project root is in PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.alert import AlertCreate, AlertType, Severity, AlertStatus
from app.services.alert_service import AlertService

def main():
    print("Generating SentinelOps Demo Data...")
    
    # Initialize the alert service
    svc = AlertService()
    
    types = list(AlertType)
    severities = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
    cameras = ["CAM-MAIN-GATE", "CAM-SCAFFOLDING-01", "CAM-ZONE-B", "CAM-LOADING-DOCK"]
    workers = ["W-104", "W-209", "W-311", "W-442", "W-501", "W-UNKNOWN"]
    
    now = datetime.now(timezone.utc)
    
    total_alerts = 0
    # Generate data for the last 14 days
    for day in range(14, -1, -1):
        target_date = now - timedelta(days=day)
        
        # Random number of alerts per day (more active recently)
        num_alerts = random.randint(5, 25) + (10 if day < 3 else 0)
        
        for _ in range(num_alerts):
            # Randomize time within the day
            hour = random.randint(6, 18)  # Working hours
            minute = random.randint(0, 59)
            alert_time = target_date.replace(hour=hour, minute=minute)
            
            # Weighted randoms to make charts look realistic
            alert_type = random.choice(types)
            severity = random.choices(severities, weights=[50, 30, 15, 5])[0]
            camera = random.choice(cameras)
            worker = random.choice(workers)
            
            # Status: mostly resolved for old ones, mostly new for today
            if day == 0:
                status = random.choices([AlertStatus.NEW, AlertStatus.INVESTIGATING, AlertStatus.RESOLVED], weights=[70, 20, 10])[0]
            else:
                status = random.choices([AlertStatus.RESOLVED, AlertStatus.FALSE_POSITIVE, AlertStatus.NEW], weights=[80, 15, 5])[0]
            
            payload = AlertCreate(
                camera_id=camera,
                alert_type=alert_type,
                severity=severity,
                confidence=round(random.uniform(0.65, 0.98), 2),
                worker_id=worker,
            )
            
            # We bypass the standard .create() because we want to inject historical timestamps
            # rather than current time. So we build the internal representation manually.
            alert_dict = payload.model_dump()
            alert_dict["alert_id"] = f"ALR-DEMO-{int(alert_time.timestamp())}-{random.randint(1000, 9999)}"
            alert_dict["timestamp"] = alert_time.isoformat()
            alert_dict["status"] = status.value
            alert_dict["duplicate_count"] = random.randint(0, 4)
            if status == AlertStatus.RESOLVED:
                alert_dict["resolved_at"] = (alert_time + timedelta(minutes=random.randint(5, 120))).isoformat()
                
            from app.models.alert import Alert
            alert_obj = Alert(**alert_dict)
            svc._save_alert(alert_obj)
            svc._index[alert_obj.alert_id] = svc._build_index_entry(alert_obj)
            
            total_alerts += 1
            
    svc._save_index()
    print(f"✅ Successfully generated {total_alerts} historical alerts across {len(cameras)} cameras!")
    print("Restart your backend to see the rich analytics on the dashboard.")

if __name__ == "__main__":
    main()
