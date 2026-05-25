# Notification System Implementation Roadmap

## Phase 1: Backend Notification Service (In Progress)
- [x] Base NotificationService class
- [x] Basic create_notification method
- [x] User notification retrieval
- [x] Mark as read functionality
- [ ] **TODO**: Add all 50+ notification event creators (FA001-SA009, etc.)
- [ ] **TODO**: Add facility-specific notification filtering
- [ ] **TODO**: Add AI service integration triggers
- [ ] **TODO**: Add system health monitoring triggers

## Phase 2: WebSocket Infrastructure (Partial)
- [x] ConnectionManager class
- [x] Connection/disconnection handling
- [x] Role-based connections tracking
- [x] Facility connections tracking
- [ ] **TODO**: Complete broadcast_notification method
- [ ] **TODO**: Implement broadcast_to_role method
- [ ] **TODO**: Implement broadcast_to_facility method
- [ ] **TODO**: Add connection health checks/ping-pong

## Phase 3: API WebSocket Endpoint (Todo)
- [ ] **TODO**: Create /api/v1/websocket/notifications endpoint
- [ ] **TODO**: JWT token verification
- [ ] **TODO**: Connection lifecycle management
- [ ] **TODO**: Message receive/send handlers

## Phase 4: Notification Triggers (Todo)
- [ ] **TODO**: Referral service - incoming referral trigger (FA001)
- [ ] **TODO**: Referral service - accept referral trigger (FA002)
- [ ] **TODO**: Referral service - reject referral trigger (FA003)
- [ ] **TODO**: Referral service - in transit trigger (FA004)
- [ ] **TODO**: Referral service - received trigger (FA005)
- [ ] **TODO**: Facility service - facility created trigger (SA001)
- [ ] **TODO**: Facility service - facility admin created trigger (SA003)
- [ ] **TODO**: Document service - document upload trigger (FA008)
- [ ] **TODO**: AI service - analysis complete trigger (FA010)
- [ ] **TODO**: System monitor - storage warning (SA006, FA103)
- [ ] **TODO**: System monitor - failed logins (SA007)
- [ ] **TODO**: System monitor - AI health (SA004)
- [ ] **TODO**: System monitor - DB performance (SA005)

## Phase 5: Frontend Integration (Todo)
- [ ] **TODO**: WebSocket client hook (useNotifications)
- [ ] **TODO**: NotificationCenter component
- [ ] **TODO**: NotificationBadge component
- [ ] **TODO**: NotificationPreferences component
- [ ] **TODO**: Real-time notification display
- [ ] **TODO**: Action handlers for notifications

## Success Criteria
- All 50+ notification types implemented
- Real-time delivery via WebSocket
- Offline storage for persistent notifications
- Role-based filtering working correctly
- Facility-scoped notifications
- All 3 user roles receiving appropriate notifications
- Frontend displays notifications in real-time
