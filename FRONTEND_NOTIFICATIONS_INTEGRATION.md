# MediFlow Notifications - Frontend Integration Guide

## Overview

The MediFlow notifications system provides real-time notifications via WebSocket with:
- 50+ notification types across 3 user roles
- Real-time delivery via WebSocket
- Offline storage for persistent notifications
- Role-based and facility-scoped filtering
- Action handlers for interactive notifications

## Frontend Setup

### 1. Create WebSocket Hook (React)

**File**: `src/hooks/useNotifications.ts`

```typescript
import { useEffect, useRef, useCallback, useState } from 'react';
import { useAuth } from './useAuth';

export interface Notification {
  id: number;
  type: 'critical' | 'warning' | 'info';
  title: string;
  message: string;
  details: Record<string, any>;
  actions: string[];
  created_at: string;
  is_read: boolean;
}

export const useNotifications = () => {
  const { token } = useAuth();
  const wsRef = useRef<WebSocket | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!token) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/websocket/notifications?token=${token}`;

    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        // Send ping every 30 seconds to keep connection alive
        setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, 30000);
      };

      ws.onmessage = (event) => {
        try {
          const ssage === 'ping' || message === 'pong') {
            return; // Ignore WebSocket keep-alive messages
          }
          const notification = JSON.parse(message);
          console.log('Notification received:', notification);
          
          setNotifications(prev => {
            const updated = [notification, ...prev];
            // Keep only last 100 notifications
            return updated.slice(0, 100);
          });
          
          if (!notification.is_read) {
            setUnreadCount(prev => prev + 1);
          }
        } catch (error) {
          console.error('Error parsing notification:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        // Attempt reconnect in 3 seconds
        setTimeout(connect, 3000);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
    }
  }, [token]);

  // Disconnect WebSocket
  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  // Mark notification as read
  const markAsRead = useCallback(async (notificationId: number) => {
    try {
      const response = await fetch(
        `/api/v1/notifications/${notificationId}/read`,
        {
          method: 'PATCH',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (response.ok) {
        setNotifications(prev =>
          prev.map(n =>
            n.id === notificationId ? { ...n, is_read: true } : n
          )
        );
        setUnreadCount(prev => Math.max(0, prev - 1));
      }
    } catch (error) {
      console.error('Error marking notification as read:', error);
    }
  }, [token]);

  // Delete notification
  const deleteNotification = useCallback(async (notificationId: number) => {
    try {
      const response = await fetch(
        `/api/v1/notifications/${notificationId}`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        setNotifications(prev =>
          prev.filter(n => n.id !== notificationId)
        );
      }
    } catch (error) {
      console.error('Error deleting notification:', error);
    }
  }, [token]);

  // Load initial notifications (offline storage)
  const loadNotifications = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/notifications?limit=50', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setNotifications(data);
        setUnreadCount(data.filter((n: Notification) => !n.is_read).length);
      }
    } catch (error) {
      console.error('Error loading notifications:', error);
    }
  }, [token]);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    if (token) {
      loadNotifications();
      connect();
      
      return () => {
        disconnect();
      };
    }
  }, [token, connect, disconnect, loadNotifications]);

  return {
    notifications,
    isConnected,
    unreadCount,
    markAsRead,
    deleteNotification,
    refresh: loadNotifications,
  };
};
```

### 2. Create NotificationCenter Component

**File**: `src/components/NotificationCenter.tsx`

```typescript
import React, { useState } from 'react';
import { useNotifications, Notification } from '../hooks/useNotifications';
import './NotificationCenter.css';

export const NotificationCenter: React.FC = () => {
  const { notifications, isConnected, unreadCount, markAsRead, deleteNotification } = useNotifications();
  const [isOpen, setIsOpen] = useState(false);

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'critical':
        return '🚨';
      case 'warning':
        return '⚠️';
      case 'info':
      default:
        return 'ℹ️';
    }
  };

  const handleNotificationClick = (notification: Notification) => {
    if (!notification.is_read) {
      markAsRead(notification.id);
    }
    // Handle notification action based on type
    handleNotificationAction(notification);
  };

  const handleNotificationAction = (notification: Notification) => {
    // Route based on notification type
    switch (notification.details.referral_id) {
      case notification.details.referral_id:
        // Navigate to referral details
        window.location.href = `/referrals/${notification.details.referral_id}`;
        break;
      // Add more routing logic based on notification type
      default:
        break;
    }
  };

  return (
    <div className="notification-center">
      {/* Notification Badge */}
      <button
        className={`notification-badge ${isConnected ? 'connected' : 'disconnected'}`}
        onClick={() => setIsOpen(!isOpen)}
        title={isConnected ? 'Connected' : 'Disconnected'}
      >
        🔔
        {unreadCount > 0 && <span className="badge-count">{unreadCount}</span>}
      </button>

      {/* Notification Dropdown */}
      {isOpen && (
        <div className="notification-dropdown">
          <div className="notification-header">
            <h3>Notifications ({notifications.length})</h3>
            <button onClick={() => setIsOpen(false)}>✕</button>
          </div>

          <div className="notification-list">
            {notifications.length === 0 ? (
              <p className="empty-state">No notifications</p>
            ) : (
              notifications.map(notification => (
                <div
                  key={notification.id}
                  className={`notification-item ${notification.type} ${notification.is_read ? 'read' : 'unread'}`}
                  onClick={() => handleNotificationClick(notification)}
                >
                  <div className="notification-icon">
                    {getNotificationIcon(notification.type)}
                  </div>

                  <div className="notification-content">
                    <h4>{notification.title}</h4>
                    <p>{notification.message}</p>
                    <div className="notification-actions">
                      {notification.actions.map((action, index) => (
                        <button
                          key={index}
                          className="action-button"
                          onClick={(e) => {
                            e.stopPropagation();
                            // Handle action
                            console.log(`Action: ${action}`);
                          }}
                        >
                          {action}
                        </button>
                      ))}
                    </div>
                    <small className="notification-time">
                      {new Date(notification.created_at).toLocaleString()}
                    </small>
                  </div>

                  <button
                    className="delete-button"
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteNotification(notification.id);
                    }}
                  >
                    ✕
                  </button>
                </div>
              ))
            )}
          </div>

          <div className="notification-footer">
            <div className="connection-status">
              <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}></span>
              {isConnected ? 'Connected' : 'Disconnected'}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
```

### 3. Notification CSS

**File**: `src/components/NotificationCenter.css`

```css
.notification-center {
  position: relative;
}

.notification-badge {
  position: relative;
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  transition: all 0.3s ease;
}

.notification-badge:hover {
  background-color: rgba(0, 0, 0, 0.1);
}

.notification-badge.connected::before {
  content: '';
  position: absolute;
  width: 8px;
  height: 8px;
  background-color: #4CAF50;
  border-radius: 50%;
  top: 4px;
  right: 4px;
  animation: pulse 2s infinite;
}

.notification-badge.disconnected::before {
  content: '';
  position: absolute;
  width: 8px;
  height: 8px;
  background-color: #FF6B6B;
  border-radius: 50%;
  top: 4px;
  right: 4px;
}

.badge-count {
  position: absolute;
  top: -4px;
  right: -4px;
  background-color: #FF6B6B;
  color: white;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
}

.notification-dropdown {
  position: absolute;
  right: 0;
  top: 100%;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  width: 400px;
  max-height: 600px;
  display: flex;
  flex-direction: column;
  z-index: 1000;
}

.notification-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #eee;
}

.notification-header h3 {
  margin: 0;
  font-size: 16px;
}

.notification-header button {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
}

.notification-list {
  overflow-y: auto;
  flex: 1;
}

.empty-state {
  padding: 40px 20px;
  text-align: center;
  color: #999;
}

.notification-item {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: background-color 0.2s;
}

.notification-item:hover {
  background-color: #f9f9f9;
}

.notification-item.unread {
  background-color: #f0f8ff;
}

.notification-item.critical {
  border-left: 4px solid #FF6B6B;
}

.notification-item.warning {
  border-left: 4px solid #FFA500;
}

.notification-item.info {
  border-left: 4px solid #4CAF50;
}

.notification-icon {
  font-size: 24px;
  min-width: 24px;
}

.notification-content {
  flex: 1;
}

.notification-content h4 {
  margin: 0 0 4px 0;
  font-size: 14px;
  font-weight: 600;
}

.notification-content p {
  margin: 0 0 8px 0;
  font-size: 13px;
  color: #666;
}

.notification-actions {
  display: flex;
  gap: 4px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}

.action-button {
  padding: 4px 8px;
  background: #f0f0f0;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.action-button:hover {
  background: #e0e0e0;
}

.notification-time {
  color: #999;
  font-size: 12px;
}

.delete-button {
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  color: #999;
  min-width: 24px;
  min-height: 24px;
}

.delete-button:hover {
  color: #FF6B6B;
}

.notification-footer {
  padding: 12px 16px;
  border-top: 1px solid #eee;
  display: flex;
  justify-content: space-between;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #666;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.status-indicator.connected {
  background-color: #4CAF50;
  animation: pulse 2s infinite;
}

.status-indicator.disconnected {
  background-color: #FF6B6B;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

@media (max-width: 600px) {
  .notification-dropdown {
    width: calc(100vw - 20px);
    left: 10px;
    right: auto;
  }
}
```

### 4. Integrate into Main App Layout

**File**: `src/layouts/MainLayout.tsx`

```typescript
import React from 'react';
import { NotificationCenter } from '../components/NotificationCenter';

export const MainLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="main-layout">
      <header className="app-header">
        <h1>MediFlow</h1>
        <div className="header-actions">
          <NotificationCenter />
          {/* Other header items */}
        </div>
      </header>

      <main className="app-main">
        {children}
      </main>
    </div>
  );
};
```

## Usage Examples

### Display Incoming Referral Notification

When a facility receives an incoming referral (FA001), the user will see:

```
🚨 NEW REFERRAL: John Smith (URGENT)
Incoming patient referral from County General

[Buttons]
✓ Accept    ✗ Reject    📞 Call Clinic
```

### Display Referral Accepted Notification

When a referral is accepted (FA002):

```
✅ REFERRAL ACCEPTED: John Smith
Your referral has been accepted by Dr. Johnson

[Buttons]
📋 Prepare Patient    🛏️ Schedule Bed    📢 Alert Staff
```

### Display System Alert

When system storage is critical (SA006):

```
💾 STORAGE CRITICAL: 90% FULL
System storage at 98.5% capacity

[Buttons]
🧹 Cleanup Storage    💾 Request Upgrade    📦 Archive Data
```

## Notification Types by Role

### Super Admin Receives:
- Facility Created (SA001)
- Facility Status Changes (SA002)
- Facility Admin Assigned (SA003)
- AI Service Down (SA004)
- Database Performance Alert (SA005)
- Storage Critical (SA006)
- Multiple Failed Logins (SA007)
- HIPAA Violations (SA008)
- System Health Reports (SA009)

### Facility Admin / Clinician Receive:
- All 17 shared notifications (FA001-FA017)
- Facility Admin also receives: Clinician Created (FA101), Clinician Updated (FA102), Storage Warning (FA103)

## Testing Notifications Locally

### 1. Create Test Data

```bash
# Create a test referral (triggers FA001)
curl -X POST http://localhost:8000/api/v1/referrals \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": 1,
    "to_facility_id": 2,
    "reason_for_referral": "Cardiac evaluation",
    "priority": "urgent"
  }'
```

### 2. Monitor WebSocket Messages

```javascript
// In browser console
const ws = new WebSocket('ws://localhost:8000/api/v1/websocket/notifications?token=YOUR_TOKEN');

ws.onmessage = (event) => {
  console.log('Notification:', JSON.parse(event.data));
};
```

### 3. Accept Referral (triggers FA002)

```bash
curl -X PATCH http://localhost:8000/api/v1/referrals/1/accept \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Watch the WebSocket for FA002 notification.

## Performance Considerations

1. **WebSocket Connection Pool**: Connections are multiplexed by role and facility
2. **Notification Batching**: Multiple notifications sent together for efficiency
3. **Offline Storage**: 50 most recent notifications kept in memory
4. **Auto-Reconnect**: Automatic reconnection with exponential backoff
5. **Heartbeat**: Ping/pong every 30 seconds to keep connection alive

## Future Enhancements

- [ ] Notification preferences (enable/disable by type)
- [ ] Sound alerts for critical notifications
- [ ] Email fallback for critical notifications
- [ ] Notification templates customization
- [ ] Scheduled digest emails
- [ ] Notification archive/history
- [ ] Advanced filtering and search
- [ ] Mobile push notifications
