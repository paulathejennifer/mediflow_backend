# MediFlow Quick Deploy Checklist

## 🚀 Deployment Steps (5 minutes)

### 1. Backend CORS Update (Render)
- [ ] Go to Render dashboard → mediflow-backend
- [ ] Environment tab → Add/Update `ALLOWED_HOSTS`
- [ ] Value: `["https://your-app.vercel.app","http://localhost:3000"]`
- [ ] Click "Manual Deploy" to restart

### 2. Frontend Deploy (Vercel)
- [ ] Go to Vercel dashboard → "Add New Project"
- [ ] Import: `paulathejennifer/mediflow_frontend`
- [ ] Environment Variables:
  ```
  NEXT_PUBLIC_API_URL=https://mediflow-backend-r2c4.onrender.com/api/v1
  NEXT_PUBLIC_WS_URL=wss://mediflow-backend-r2c4.onrender.com/api/v1/websocket/notifications
  NEXT_PUBLIC_APP_NAME=MediFlow
  NEXT_PUBLIC_ENABLE_MOCK_DATA=false
  NEXT_PUBLIC_ENABLE_AI_FEATURES=true
  ```
- [ ] Click "Deploy"
- [ ] Copy your Vercel URL (e.g., `mediflow-xyz.vercel.app`)

### 3. Update Backend CORS Again
- [ ] Update `ALLOWED_HOSTS` with your actual Vercel URL
- [ ] Redeploy backend

### 4. Test Deployment
- [ ] Visit your Vercel URL
- [ ] Login: `admin@mediflow.com` / `admin123`
- [ ] Check dashboard loads
- [ ] Test one feature (create patient or referral)

## 🔧 Quick Troubleshooting

**CORS Error?**
→ Check `ALLOWED_HOSTS` matches your Vercel URL exactly

**Login Fails?**
→ Test backend: `curl https://mediflow-backend-r2c4.onrender.com/health`

**Mock Data Still Showing?**
→ Set `NEXT_PUBLIC_ENABLE_MOCK_DATA=false` in Vercel and redeploy

**WebSocket Not Connecting?**
→ Ensure `NEXT_PUBLIC_WS_URL` uses `wss://` not `ws://`

## 📊 New Analytics Endpoints

The backend now has real analytics endpoints:

- `GET /api/v1/analytics/dashboard` - Dashboard KPIs
- `GET /api/v1/analytics/referrals` - Referral analytics
- `GET /api/v1/analytics/referrals/by-status` - For pie chart
- `GET /api/v1/analytics/referrals/trend` - For line chart
- `GET /api/v1/analytics/facilities/top-referring` - Top facilities (Super Admin)

## 📝 Post-Deploy Tasks

- [ ] Change default admin password
- [ ] Create production facilities
- [ ] Test email notifications
- [ ] Monitor Render logs

## 🆘 Need Help?

1. Check Render logs for backend errors
2. Check Vercel logs for build errors  
3. Test API directly: `https://mediflow-backend-r2c4.onrender.com/docs`
4. Review browser console for frontend errors

---

**Full documentation:** See `DEPLOYMENT_GUIDE.md`