# MediFlow Deployment Guide

## Pre-Deployment Checklist

### Backend (Render.com)

✅ **Backend is already deployed at:** `https://mediflow-backend-r2c4.onrender.com`

**Required Actions:**

1. **Update CORS Settings on Render**
   - Go to your Render dashboard
   - Navigate to the mediflow-backend environment
   - Add/Update environment variables:
   ```
   ALLOWED_HOSTS=["https://mediflow-frontend-omega.vercel.app","http://localhost:3000"]
   FRONTEND_URL=https://mediflow-frontend-omega.vercel.app
   ```
   The frontend is currently deployed at `https://mediflow-frontend-omega.vercel.app`
   - Redeploy the backend after updating

2. **Verify Database**
   - Ensure PostgreSQL is properly configured on Render
   - Run migrations if needed: `alembic upgrade head`

3. **Check Environment Variables on Render**
   ```
   DATABASE_URL=postgresql://... (should already be set)
   SECRET_KEY=... (should already be set)
   OPENAI_API_KEY=... (if using OpenAI features)
   GROQ_API_KEY=... (for AI summarization)
   SMTP_PASSWORD=... (for email notifications)
   ```

### Frontend (Vercel)

**Repository:** `https://github.com/paulathejennifer/mediflow_frontend`

**Environment Variables to Set in Vercel:**
```
NEXT_PUBLIC_API_URL=https://mediflow-backend-r2c4.onrender.com/api/v1
NEXT_PUBLIC_WS_URL=wss://mediflow-backend-r2c4.onrender.com/api/v1/websocket/notifications
NEXT_PUBLIC_APP_NAME=MediFlow
NEXT_PUBLIC_ENABLE_MOCK_DATA=false
NEXT_PUBLIC_ENABLE_AI_FEATURES=true
```

## Deployment Steps

### Step 1: Update Backend CORS (CRITICAL)

The backend currently has `ALLOWED_HOSTS=["*"]` which allows all origins. For production security, update it to only allow your Vercel domain.

**Option A: Update via Render Dashboard**
1. Go to Render.com dashboard
2. Find your mediflow-backend service
3. Go to Environment tab
4. Add/Update `ALLOWED_HOSTS` variable
5. Click "Manual Deploy" to restart the service

**Option B: Keep Wildcard (Development Only)**
If you want to keep testing, you can leave it as `["*"]` temporarily.

### Step 2: Deploy Frontend to Vercel

1. **Import Repository**
   - Go to Vercel dashboard
   - Click "Add New Project"
   - Import `paulathejennifer/mediflow_frontend`

2. **Configure Environment Variables**
   In Vercel project settings → Environment Variables, add:
   ```
   NEXT_PUBLIC_API_URL=https://mediflow-backend-r2c4.onrender.com/api/v1
   NEXT_PUBLIC_WS_URL=wss://mediflow-backend-r2c4.onrender.com/api/v1/websocket/notifications
   NEXT_PUBLIC_APP_NAME=MediFlow
   NEXT_PUBLIC_ENABLE_MOCK_DATA=false
   NEXT_PUBLIC_ENABLE_AI_FEATURES=true
   ```

3. **Deploy**
   - Click "Deploy"
   - Wait for build to complete
   - Note your production URL (e.g., `https://mediflow-frontend.vercel.app`)

4. **Update Backend CORS Again**
   - Go back to Render
   - Update `ALLOWED_HOSTS` to include your new Vercel URL
   - Redeploy backend

### Step 3: Smoke Testing

After both deployments are complete, test the following:

#### 1. Authentication Flow
```bash
# Test login
curl -X POST https://mediflow-backend-r2c4.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@mediflow.com", "password": "admin123"}'
```

Expected: Should return access_token and refresh_token

#### 2. Frontend Login
- Go to your Vercel URL
- Try logging in with:
  - Email: `admin@mediflow.com`
  - Password: `admin123`
- Should redirect to dashboard

#### 3. Dashboard Access by Role

**Super Admin:**
- Should see system-wide analytics
- Can access Facilities, Staff, Patients, Referrals pages
- KPI cards should show data (or mock data if enabled)

**Facility Admin / Clinician:**
- Should see facility-specific data
- Can create patients and referrals
- Analytics show facility-level metrics

#### 4. Core Features Test

**Patients:**
- [ ] List patients
- [ ] Create new patient
- [ ] View patient details
- [ ] Edit patient

**Referrals:**
- [ ] List referrals
- [ ] Create new referral
- [ ] View referral details
- [ ] Submit draft referral

**Facilities (Super Admin only):**
- [ ] List facilities
- [ ] Create new facility
- [ ] Edit facility

**Users (Super Admin / Facility Admin):**
- [ ] List users
- [ ] Create new user
- [ ] Edit user

#### 5. Analytics Pages

**Note:** Currently, analytics use mock/static data as mentioned in your task notes. This is expected for v1.

- [ ] Dashboard charts display (even with mock data)
- [ ] Referrals by status pie chart
- [ ] Turnaround time trend
- [ ] Referrals by reason
- [ ] Top referring facilities

#### 6. WebSocket Notifications

- [ ] Login triggers notification connection
- [ ] New referrals trigger notifications
- [ ] Notification badge updates

## Troubleshooting

### CORS Errors

If you see CORS errors in browser console:

1. **Check Backend ALLOWED_HOSTS**
   ```python
   # In Render environment variables, should be:
   ALLOWED_HOSTS=["https://your-frontend.vercel.app","http://localhost:3000"]
   ```

2. **Verify Frontend URL**
   - Make sure the URL in ALLOWED_HOSTS matches your Vercel URL exactly
   - Include `https://` prefix
   - No trailing slash

### Authentication Issues

If login fails:

1. **Check Backend Logs on Render**
   - Go to Render dashboard → Logs
   - Look for error messages

2. **Verify Database Connection**
   - Ensure PostgreSQL is running on Render
   - Check DATABASE_URL is correct

3. **Test API Directly**
   ```bash
   curl https://mediflow-backend-r2c4.onrender.com/health
   ```
   Should return: `{"status": "healthy", "service": "mediflow-backend"}`

### Mock Data Still Showing

If you still see mock data after setting `NEXT_PUBLIC_ENABLE_MOCK_DATA=false`:

1. **Check Environment Variable**
   - Verify it's set correctly in Vercel
   - Redeploy frontend after setting

2. **Clear Browser Cache**
   - Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)
   - Or clear cache and reload

### WebSocket Connection Issues

If notifications aren't working:

1. **Check WebSocket URL**
   - Should be: `wss://mediflow-backend-r2c4.onrender.com/api/v1/websocket/notifications`
   - Note the `wss://` (secure WebSocket)

2. **Browser Console**
   - Check for WebSocket connection errors
   - May need to wait for backend to establish connection

## Post-Deployment Tasks

### 1. Change Default Admin Password
- Login as admin@mediflow.com
- Go to profile/settings
- Change password immediately

### 2. Create Production Facilities
- As super admin, create actual healthcare facilities
- Assign facility admins to each

### 3. Set Up Email Notifications
- Verify SMTP settings are working
- Test password reset emails
- Test referral notification emails

### 4. Monitor Performance
- Check Render dashboard for resource usage
- Monitor database performance
- Set up alerts if needed

### 5. Backup Strategy
- Set up automated database backups on Render
- Regular backups of uploads directory

## Analytics Integration (✅ COMPLETED)

The backend now has full analytics endpoints available! The following endpoints are ready to use:

### Available Analytics Endpoints

| Endpoint | Description | Access |
|----------|-------------|--------|
| `GET /api/v1/analytics/referrals` | Referral analytics with status/priority breakdown | All authenticated users |
| `GET /api/v1/analytics/dashboard` | Dashboard KPIs (patients, facilities, referrals) | All authenticated users |
| `GET /api/v1/analytics/referrals/by-status` | Referrals grouped by status (for pie chart) | All authenticated users |
| `GET /api/v1/analytics/referrals/by-priority` | Referrals grouped by priority (for bar chart) | All authenticated users |
| `GET /api/v1/analytics/referrals/trend` | Referral trend over time (for line chart) | All authenticated users |
| `GET /api/v1/analytics/facilities/top-referring` | Top referring facilities (for bar chart) | Super Admin only |

### Frontend Integration Examples

```typescript
// Dashboard KPIs
const fetchDashboardKPIs = async () => {
  const response = await fetch(`${API_URL}/analytics/dashboard`)
  const data = await response.json()
  // data.total_patients, data.total_facilities, data.total_referrals_30d, etc.
  return data
}

// Referral Analytics
const fetchReferralAnalytics = async (days = 30) => {
  const response = await fetch(`${API_URL}/analytics/referrals?days=${days}`)
  const data = await response.json()
  // data.status_breakdown, data.priority_breakdown, data.acceptance_rate, etc.
  return data
}

// For Pie Chart (Referrals by Status)
const fetchReferralsByStatus = async () => {
  const response = await fetch(`${API_URL}/analytics/referrals/by-status`)
  const data = await response.json()
  // data.labels = ['draft', 'submitted', 'accepted', ...]
  // data.data = [5, 12, 8, ...]
  return data
}

// For Trend Line Chart
const fetchReferralTrend = async (days = 30) => {
  const response = await fetch(`${API_URL}/analytics/referrals/trend?days=${days}`)
  const data = await response.json()
  // data.labels = ['2024-01-01', '2024-01-02', ...]
  // data.data = [3, 5, 2, ...]
  return data
}

// For Top Referring Facilities (Super Admin only)
const fetchTopReferringFacilities = async (limit = 10) => {
  const response = await fetch(`${API_URL}/analytics/facilities/top-referring?limit=${limit}`)
  const data = await response.json()
  // data.labels = ['Hospital A', 'Clinic B', ...]
  // data.data = [45, 32, ...]
  return data
}
```

## Support

If you encounter issues during deployment:

1. **Check Backend Logs** on Render dashboard
2. **Check Frontend Build Logs** on Vercel dashboard
3. **Test API directly** using curl or Postman
4. **Review browser console** for frontend errors

## Deployment Summary

✅ **Backend:** Already deployed on Render  
✅ **Frontend:** Deploy to Vercel with environment variables  
✅ **CORS:** Update ALLOWED_HOSTS on Render to include Vercel URL  
✅ **Test:** Follow smoke test checklist  
✅ **Monitor:** Check logs and performance  

Good luck with your deployment! 🚀