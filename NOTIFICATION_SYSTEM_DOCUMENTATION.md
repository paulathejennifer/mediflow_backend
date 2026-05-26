# 🔔 MediFlow Notification System Documentation

## Overview
The MediFlow Notification System is a hybrid real-time and persistent messaging engine designed for a multi-tenant healthcare environment. It supports role-based broadcasting (Super Admin, Facility Admin, Clinician) and facility-scoped isolation.

---

## 📂 File Structure

### Backend (FastAPI)
| Path | Purpose |
| :--- | :--- |
| `app/models/notifications.py` | Database schemas for Notifications, Deliveries, and Preferences. |
| `app/services/notification_service.py` | Core business logic: retrieval, per-user read tracking, and dispatching. |
| `app/services/notification_events.py` | Mixin containing 50+ specialized creator methods (SA001, FA001, etc.). |
| `app/api/v1/endpoints/notifications.py` | REST API for history, stats, and marking read/all. |
| `app/api/v1/websocket.py` | WebSocket endpoint for real-time bi-directional communication. |
| `app/tasks/monitoring_jobs.py` | Background loop for system health and storage alerts. |
| `app/websocket/manager.py` | Connection state management and broadcasting logic. |

### Frontend (React/TypeScript)
| Path | Purpose |
| :--- | :--- |
| `src/features/notifications/hooks/useNotifications.ts` | Custom hook for WebSocket lifecycle and REST integration. |
| `src/features/notifications/hooks/NotificationProvider.tsx` | Context provider ensuring a singleton connection across the app. |
| `src/features/notifications/hooks/NotificationCenter.tsx` | Tailwind-styled UI component for the notification dropdown. |

---

## 🔄 The Notification Flow

### 1. Trigger Phase
An event occurs in the business logic (e.g., `app/api/v1/endpoints/referrals.py`).
```python
# Example trigger in an endpoint
notif_service = get_notification_service(db)
notif_service.create_incoming_referral_notification(referral)
```

### 2. Creation Phase
The `NotificationService` (inheriting from `NotificationEventCreators`):
1.  Formats the specific event data (Title, Actions, Backend Source).
2.  Saves a new record to the `notifications` table.
3.  Initiates an asynchronous background task using `asyncio.create_task`.
    *   *Note: We pass only the ID to the background task to prevent database session expiration errors.*

### 3. Dispatch Phase (Push)
The `NotificationBroadcaster` (inside `websocket/manager.py`):
1.  Opens a fresh database session.
2.  Fetches the notification details.
3.  Identifies target recipients based on `user_id`, `roles`, or `facility_id`.
4.  Pushes JSON data to all active WebSocket connections matching the criteria.

### 4. Delivery & Read Phase
*   **Direct Notifications:** If a `user_id` is present, the `is_read` flag on the `Notification` table tracks status.
*   **Broadcast Notifications:** (e.g., "New Referral" sent to all clinicians).
    *   The `NotificationDelivery` table tracks status per user.
    *   When User A marks it read, it stays unread for User B in the same facility.

### 5. Frontend Integration
1.  **Mount:** `NotificationProvider` wraps the app. `useNotifications` initializes.
2.  **Sync:** A REST call to `GET /api/v1/notifications` fetches history.
3.  **Real-time:** A WebSocket connection is established at `wss://.../websocket/notifications`.
4.  **Interaction:** 
    *   `PATCH /notifications/{id}/read` marks a specific item read.
    *   `POST /notifications/{id}/actions/{action_id}` triggers specific backend logic (e.g., "Accept Referral").

---

## 📊 Notification Categories

### Super Admin (SA Series)
Focuses on infrastructure and compliance.
*   **SA004:** AI Service Down (Critical)
*   **SA005:** Database Performance Alert (Critical)
*   **SA006:** System Storage Critical (Critical)
*   **SA008:** HIPAA Violation detected (Critical)

### Facility & Clinician (FA Series)
Focuses on clinical operations.
*   **FA001:** Incoming Referral (Urgent/Emergency)
*   **FA002:** Referral Accepted (Info)
*   **FA011:** Voice Note Transcribed (Info)
*   **FA103:** Facility-specific Storage Warning (Warning)

---

## 🛡️ Security & Filtering

*   **WebSocket Auth:** Authenticates via JWT in the query string (`?token=...`).
*   **Data Isolation:** The `get_user_notifications` service method uses an `outerjoin` with `NotificationDelivery` and strict `WHERE` clauses to ensure users never see notifications from other facilities.
*   **Token Lifecycle:** The frontend hook listens to `isAuthenticated` from `useAuth`. On logout, the WebSocket is explicitly closed with code `1000`.

---

## 🛠️ Maintenance & Monitoring

### Background Jobs
The `start_monitoring()` function in `app/main.py` kicks off a persistent loop that:
1.  Scans `system_metrics` for high error rates (>10% in 10 mins).
2.  Checks disk usage via `psutil`.
3.  Pings AI service health endpoints.

### Testing the Flow
Use the `test_notifications_flow.py` script to simulate the end-to-end lifecycle:
1.  Authenticates a user.
2.  Fetches current notifications.
3.  Verifies the "Mark Read" transition.
```bash
python test_notifications_flow.py
```
```

<!--
[PROMPT_SUGGESTION]Check the WebSocket ConnectionManager in manager.py to ensure the broadcast_to_facility logic handles multi-role overlaps correctly.[/PROMPT_SUGGESTION]
[PROMPT_SUGGESTION]Help me update the requirements.txt to include any missing libraries found in the new documentation.[/PROMPT_SUGGESTION]
-->