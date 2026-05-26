import requests
import json
import os

# Read from environment variable or fallback to production Render URL
BASE_URL = os.getenv("NEXT_PUBLIC_API_URL", "https://mediflow-backend-r2c4.onrender.com/api/v1")

# Replace with your test user credentials
LOGIN_DATA = {"email": "admin@mediflow.com", "password": "admin123"}

def test_flow():
    print("🚀 Starting Notification Flow Test...")
    
    # 1. Login
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=LOGIN_DATA)
        response.raise_for_status()
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Login successful")
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return

    # 2. Get Notifications
    try:
        response = requests.get(f"{BASE_URL}/notifications", headers=headers)
        response.raise_for_status()
        notifications = response.json()
        print(f"✅ Fetched {len(notifications)} notifications")
        if notifications:
            print(f"   Latest: {notifications[0]['title']}")
    except Exception as e:
        print(f"❌ Fetching notifications failed: {e}")
        return

    # 3. Get Stats
    try:
        response = requests.get(f"{BASE_URL}/notifications/stats", headers=headers)
        response.raise_for_status()
        print(f"✅ Stats: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"❌ Fetching stats failed: {e}")

    # 4. Mark Read (if notifications exist)
    if notifications:
        notif_id = notifications[0]["id"]
        try:
            response = requests.patch(f"{BASE_URL}/notifications/{notif_id}/read", headers=headers)
            response.raise_for_status()
            print(f"✅ Notification {notif_id} marked as read")
        except Exception as e:
            print(f"❌ Marking read failed: {e}")

if __name__ == "__main__":
    test_flow()