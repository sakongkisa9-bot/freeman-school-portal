# FCM Deployment Checklist

## Before Deployment

### 1. Firebase Project Setup
- [ ] Create Firebase project at https://console.firebase.google.com/
- [ ] Enable Cloud Messaging in Firebase Console
- [ ] Download service account JSON file
- [ ] Save as `firebase-service-account.json` in project root
- [ ] Add `firebase-service-account.json` to `.gitignore`

### 2. Firebase Configuration
- [ ] Get Firebase config from Firebase Console → Project Settings → General
- [ ] Update `firebaseConfig` in `cloud_parent_newsletters.html` with your actual config:
  - apiKey
  - authDomain
  - projectId
  - storageBucket
  - messagingSenderId
  - appId

### 3. Enable FCM in Parent Portal
- [ ] Uncomment the FCM registration calls in `cloud_parent_newsletters.html`:
  ```javascript
  // Line 612-613
  registerFCMToken();
  setupFCMMessageListener();
  ```

### 4. Cloud Deployment (Railway)
- [ ] Copy the entire content of `firebase-service-account.json`
- [ ] Set environment variable in Railway:
  - Name: `FIREBASE_SERVICE_ACCOUNT`
  - Value: Paste the JSON content
- [ ] Redeploy the application

### 5. Testing
- [ ] Open parent portal in browser
- [ ] Allow notification permissions when prompted
- [ ] Check browser console for FCM token
- [ ] Publish a newsletter from admin panel
- [ ] Verify notification appears on registered device

## Files Modified

### Backend
- `fcm_service.py` - FCM service module (new)
- `cloud_portal_v2.py` - Database schema, API endpoints, FCM notification sending
- `newsletter.py` - Newsletter sync with cloud

### Frontend
- `templates/cloud_parent_newsletters.html` - Firebase SDK, token registration

### Documentation
- `FCM_SETUP_GUIDE.md` - Complete setup guide
- `DEPLOYMENT_CHECKLIST.md` - This file

## Important Notes

### Security
- **NEVER** commit `firebase-service-account.json` to git
- Always use environment variables in production
- The service account file gives full access to your Firebase project

### HTTPS Requirement
- FCM on web requires HTTPS
- Railway automatically provides HTTPS
- For local testing, use localhost (HTTP is allowed for localhost)

### Notification Permissions
- Users must grant notification permission
- Browsers may block notifications if not user-initiated
- Consider adding a "Enable Notifications" button in the UI

### Token Management
- Tokens can expire and refresh automatically
- The system handles token refresh automatically
- Invalid tokens are logged but don't break the system

## Troubleshooting

### "Firebase service account file not found"
- Ensure `firebase-service-account.json` is in project root
- Or set `FIREBASE_SERVICE_ACCOUNT` environment variable

### "Notification permission denied"
- Check browser settings
- Ensure site is served over HTTPS (or localhost)
- Try requesting permission from a user action (button click)

### "FCM not available"
- Check if firebase-admin is installed: `pip list | grep firebase`
- Verify service account credentials are valid
- Check server logs for initialization errors

### Notifications not received
- Check browser console for FCM token
- Verify token is registered in database
- Check server logs for notification sending errors
- Ensure device is not in Do Not Disturb mode

## Cost

FCM is **completely free**:
- Unlimited push notifications
- Unlimited devices
- Unlimited messages

## Next Steps After Deployment

1. Monitor server logs for FCM initialization
2. Test with a sample newsletter
3. Verify notifications appear on registered devices
4. Consider adding notification preference settings for parents
5. Add notification history tracking (optional)
