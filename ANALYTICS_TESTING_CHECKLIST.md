# Analytics Endpoints - Testing Checklist

## Overview
This document outlines the complete testing strategy for all 14 analytics endpoints before deployment to Render.

## Endpoints to Test (14 total)

### 1. `/api/v1/analytics/referrals` - GET
- **Function**: `get_referral_analytics`
- **Purpose**: Core analytics for referral data
- **Expected Behavior**:
  - Super Admin: Returns system-wide referral metrics (all facilities)
  - Facility Admin/Clinician: Returns facility-specific metrics (only their facility)
- **Test Cases**:
  - ✓ Super admin receives unrestricted data
  - ✓ Facility users receive only their facility data
  - ✓ Returns proper error (403 Forbidden) for users without facility_id
  - ✓ Response includes: total_referrals, active_referrals, pending_referrals, etc.

### 2. `/api/v1/analytics/dashboard` - GET
- **Function**: `get_dashboard_kpis`
- **Purpose**: Main dashboard KPIs
- **Expected Behavior**:
  - Super Admin: System-wide statistics + all facilities count
  - Facility Admin/Clinician: Facility-specific KPIs + sent/received breakdown
- **Test Cases**:
  - ✓ Super admin: total_patients (all), total_facilities, system_utilization_percent
  - ✓ Facility user: facility_name, total_patients (facility only), sent/received metrics
  - ✓ Proper HTTP 403 response for unauthorized access
  - ✓ Indentation and if/elif/else structure correct

### 3. `/api/v1/analytics/referrals/by-status` - GET
- **Function**: `get_referrals_by_status`
- **Purpose**: Referral count grouped by status (pie chart)
- **Test Cases**:
  - ✓ Only shows: submitted, accepted, in_transit, completed statuses
  - ✓ Facility-scoped for non-super-admin
  - ✓ Response format: `{status_name: count, ...}`

### 4. `/api/v1/analytics/referrals/by-priority` - GET
- **Function**: `get_referrals_by_priority`
- **Purpose**: Referral distribution by priority level
- **Test Cases**:
  - ✓ Returns: urgent, high, normal, low counts
  - ✓ Facility-scoped filtering applied

### 5. `/api/v1/analytics/referrals/trend` - GET
- **Function**: `get_referral_trend`
- **Purpose**: Referral trends over last 30 days
- **Test Cases**:
  - ✓ Uses database aggregation (func.date, func.count)
  - ✓ Returns daily breakdown by status
  - ✓ No memory exhaustion from .all() loading

### 6. `/api/v1/analytics/facilities/top-referring` - GET
- **Function**: `get_top_referring_facilities`
- **Purpose**: Top referring facilities ranking
- **Test Cases**:
  - ✓ Facility-based users see only their data
  - ✓ Super admin sees all facilities
  - ✓ Returns facility_name, referral_count, acceptance_rate

### 7. `/api/v1/analytics/system-activity` - GET
- **Function**: `get_system_activity`
- **Purpose**: Real-time system activity monitoring
- **Test Cases**:
  - ✓ Super admin only (403 for others)
  - ✓ Returns: active_users, recent_referrals, pending_tasks

### 8. `/api/v1/analytics/referrals/volume` - GET
- **Function**: `get_referral_volume_by_facility`
- **Purpose**: Referral volume distribution
- **Test Cases**:
  - ✓ Database aggregation (func.sum, func.count)
  - ✓ No N+1 query problems
  - ✓ Single query returns all data

### 9. `/api/v1/analytics/referrals/turnaround-time` - GET
- **Function**: `get_turnaround_time_trend`
- **Purpose**: Average time to complete referrals
- **Test Cases**:
  - ✓ Uses func.avg() for efficient calculation
  - ✓ Time difference calculated in database (extract('epoch'))
  - ✓ Returns: date, avg_hours_to_completion

### 10. `/api/v1/analytics/referrals/by-reason` - GET
- **Function**: `get_referrals_by_reason`
- **Purpose**: Referral reasons breakdown
- **Test Cases**:
  - ✓ Returns count by reason code
  - ✓ Facility-scoped

### 11. `/api/v1/analytics/facilities/performance` - GET
- **Function**: `get_facility_performance`
- **Purpose**: Facility performance metrics
- **Expected Behavior**:
  - Fixed N+1 query issue: single aggregated query with case()
  - Before fix: 10 facilities = 30+ queries
  - After fix: 1 query with case() for conditional sums
- **Test Cases**:
  - ✓ Load 10+ facilities - should complete in <1s (not 504 timeout)
  - ✓ Single DB query (verify via logs/profiling)
  - ✓ Returns: facility_name, submission_rate, acceptance_rate, completion_time

### 12. `/api/v1/analytics/system-health` - GET
- **Function**: `get_system_health`
- **Purpose**: System health/performance metrics
- **Expected Behavior**:
  - Super admin only (403 for others)
  - Aggregated metrics, no memory exhaustion
- **Test Cases**:
  - ✓ 403 Forbidden for facility users
  - ✓ Returns: db_connection_healthy, avg_response_time_ms, error_rate

### 13. `/api/v1/analytics/api-requests` - GET
- **Function**: `get_system_requests_metric`
- **Purpose**: API request metrics and trends
- **Test Cases**:
  - ✓ Super admin only
  - ✓ Returns: totalRequests, requestsLast24h, trend percentage

### 14. `/api/v1/analytics/metrics` - GET
- **Function**: `get_metrics`
- **Purpose**: General system metrics endpoint
- **Test Cases**:
  - ✓ Aggregated data from multiple sources
  - ✓ Proper exception handling

---

## Critical Bug Fixes Verified

### ✓ Syntax Error (Line 199)
- **Issue**: Malformed if/elif/else structure with code after return statement
- **Fix**: Restructured to proper if/elif/else with correct nesting
- **Verification**: No SyntaxError in imports

### ✓ Indentation Error (Line 201)
- **Issue**: elif block not properly indented
- **Fix**: Indented all elif block contents
- **Verification**: No IndentationError

### ✓ Parenthesis Error (Line 1024)
- **Issue**: Missing closing parentheses in previous_patients query
- **Fix**: Added closing parens for and_() and filter()
- **Verification**: Balanced parentheses

### ✓ Migration Chain
- **Issue**: Multiple head revisions (add_notification_system placeholder conflicting with 011)
- **Fix**: Removed placeholder, made 011 depend on 010
- **Verification**: Linear migration chain 001→...→011

---

## Data Access Control Tests

### Super Admin (role: "super_admin")
- [ ] Dashboard: See total_patients (ALL), total_facilities (ALL)
- [ ] Dashboard: See system_utilization_percent
- [ ] System Health: Can access (returns 200)
- [ ] System Activity: Can access (returns 200)
- [ ] Facility Performance: See all facilities with all metrics
- [ ] Referrals: See all referrals from all facilities

### Facility Admin (role: "facility_admin", facility_id: 1)
- [ ] Dashboard: See total_patients (facility 1 only)
- [ ] Dashboard: See facility_name, sent_referrals_30d, received_referrals_30d
- [ ] Dashboard: See facility_utilization_percent (based on facility 1 data)
- [ ] System Health: Get 403 Forbidden
- [ ] System Activity: Get 403 Forbidden
- [ ] Facility Performance: See facility 1 metrics only
- [ ] Referrals: See only referrals from/to facility 1

### Clinician (role: "clinician", facility_id: 1)
- [ ] Same as Facility Admin (same role-based access control)

### No Facility User (facility_id: null)
- [ ] Any analytics endpoint: Get 403 Forbidden
- [ ] Error message: "User not assigned to a facility"

---

## Performance Tests

### Query Optimization
- [ ] Facility Performance: Single query (not 30+)
  - Check with: `SELECT query_count FROM pg_stat_statements`
  - Expected: <2 queries total per request
- [ ] Dashboard KPIs: <100ms response time for super_admin
- [ ] Referral Trend: Uses func.date/func.count (not .all())
  - Verify: No "MemoryError" or excessive memory usage
- [ ] Turnaround Time: Uses func.avg() with extract('epoch')

### Timeout Tests
- [ ] Facility Performance with 100 facilities: <2s response
- [ ] System-wide Dashboard with 10k referrals: <1s response
- [ ] No 504 Gateway Timeout errors

---

## Error Handling Tests

### Authorization Errors
- [ ] 401 Unauthorized: Missing/invalid JWT token
- [ ] 403 Forbidden: Insufficient permissions for endpoint
  - Non-super-admin accessing /system-health
  - User without facility_id accessing any endpoint
- [ ] Error message in JSON: `{"detail": "..."}`

### Exception Handling
- [ ] Database connection error: 500 with error logged
- [ ] Invalid filter parameters: 400 Bad Request
- [ ] All exceptions caught and logged (check logs for tracebacks)

---

## Frontend Integration Tests

### WebSocket Notifications
- [ ] Frontend connects to `ws://backend/api/v1/websocket/notifications?token=JWT`
- [ ] Receives notification events:
  - `referral_created`: When new referral submitted
  - `referral_status_updated`: When status changes
  - `facility_admin_created`: When new facility admin added
- [ ] Notification contains: `{type, title, message, details, actions, timestamp}`

### Dashboard Integration
- [ ] Dashboard fetches `/api/v1/analytics/dashboard`
- [ ] Displays correct metrics for logged-in user's role
- [ ] Real-time updates via WebSocket

### Analytics Page
- [ ] Analytics page fetches all 14 endpoints
- [ ] Charts render correctly with returned data
- [ ] No 403/401 errors for authorized users
- [ ] Proper error display for unauthorized access

---

## Deployment Validation Checklist

### Before Pushing to Render
- [ ] Run validation test: `python test_analytics_validation.py`
  - All checks pass ✓
- [ ] All analytics endpoints defined and callable
- [ ] No syntax/indentation errors
- [ ] User role validation implemented
- [ ] try-except blocks on all endpoints

### After Render Deployment
- [ ] Gunicorn/Uvicorn workers boot successfully
- [ ] Alembic migrations complete (or fallback succeeds)
- [ ] Test 3 user roles via Postman/curl:
  ```bash
  # Super Admin
  curl -H "Authorization: Bearer TOKEN_SUPER_ADMIN" \
    https://mediflow-backend.render.com/api/v1/analytics/system-health
  
  # Facility Admin (should return data)
  curl -H "Authorization: Bearer TOKEN_FACILITY_ADMIN" \
    https://mediflow-backend.render.com/api/v1/analytics/dashboard
  
  # Facility Admin (should return 403)
  curl -H "Authorization: Bearer TOKEN_FACILITY_ADMIN" \
    https://mediflow-backend.render.com/api/v1/analytics/system-health
  ```
- [ ] Frontend WebSocket connects and receives notifications
- [ ] Analytics dashboard displays correct data for each user
- [ ] No 504 timeouts on facility performance endpoint

---

## Test Execution Order

1. **Local Validation** (Before git push)
   - Run test_analytics_validation.py
   - Check for syntax errors
   - Verify endpoint definitions

2. **Code Review** (Before git push)
   - All 14 endpoints have try-except
   - All non-super-admin endpoints check facility_id
   - All auth errors use proper HTTP status codes

3. **Deployment** (git push origin main)
   - Render auto-deploys
   - Monitor worker boot in Render logs

4. **Production Validation** (After deployment)
   - Test 3 user roles
   - Verify data isolation (facility users see only their data)
   - Check WebSocket notifications
   - Monitor for errors in logs

---

## Success Criteria

✓ All 14 endpoints respond with 200 OK (authorized) or 403 Forbidden (unauthorized)
✓ Super admin sees system-wide data
✓ Facility users see only their facility's data
✓ No 504 timeouts (queries optimized)
✓ No memory errors (using aggregation, not .all())
✓ WebSocket notifications flow from backend to frontend
✓ Dashboard and analytics pages display correctly for all 3 user roles
✓ All errors logged with full traceback (no silent failures)
