# FCM (Firebase Cloud Messaging) Integration Guide

This guide will help you set up free push notifications using Firebase Cloud Messaging instead of SMS.

## Prerequisites

- Firebase account (free tier is sufficient)
- Firebase Admin SDK installed (already done: `pip install firebase-admin`)
- Firebase service account credentials

## Step 1: Set up Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Add project" or use existing project
3. Follow the setup wizard:
   - Enable Google Analytics (optional but recommended)
   - Choose your account
   - Wait for project to be created

## Step 2: Enable Cloud Messaging

1. In your Firebase project, go to **Project Settings** (gear icon)
2. Click on the **Cloud Messaging** tab
3. Note your **Server Key** and **Sender ID** (you'll need these later)
4. Ensure Cloud Messaging API is enabled

## Step 3: Get Service Account Credentials

1. In Firebase Console, go to **Project Settings** → **Service Accounts**
2. Click **Generate New Private Key**
3. Download the JSON file (save it as `firebase-service-account.json`)
4. **IMPORTANT**: Place this file in your project root directory
5. **SECURITY WARNING**: Never commit this file to git! Add it to `.gitignore`

## Step 4: Configure Backend

The backend is already configured to use FCM. The following files have been updated:

- `fcm_service.py` - FCM service module
- `cloud_portal_v2.py` - FCM token registration and notification sending
- `newsletter.py` - Newsletter sync with FCM notifications

## Step 5: Configure Frontend (Parent Portal)

### Option A: Web App (PWA)

1. Add Firebase SDK to your HTML:

```html
<!-- Add to your base template or parent portal HTML -->
<script src="https://www.gstatic.com/firebasejs/9.0.0/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.0.0/firebase-messaging-compat.js"></script>
```

2. Initialize Firebase in JavaScript:

```javascript
// Replace with your Firebase config
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_PROJECT_ID.firebaseapp.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT_ID.appspot.com",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID"
};

firebase.initializeApp(firebaseConfig);
const messaging = firebase.messaging();
```

3. Request permission and get token:

```javascript
async function registerFCMToken() {
  try {
    // Request permission
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
      console.log('Notification permission denied');
      return;
    }
    
    // Get FCM token
    const token = await messaging.getToken();
    console.log('FCM Token:', token);
    
    // Send token to server
    await sendTokenToServer(token);
    
  } catch (error) {
    console.error('Error registering FCM token:', error);
  }
}

async function sendTokenToServer(token) {
  const response = await fetch('/api/register_fcm_token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      student_id: {{ session.get('parent_student_id') }},
      token: token,
      device_info: navigator.userAgent
    })
  });
  const result = await response.json();
  console.log('Token registration result:', result);
}
```

4. Handle token refresh:

```javascript
messaging.onTokenRefresh(async () => {
  const newToken = await messaging.getToken();
  await sendTokenToServer(newToken);
});
```

5. Handle incoming notifications:

```javascript
messaging.onMessage((payload) => {
  console.log('Received notification:', payload);
  // Show notification or update UI
  new Notification(payload.notification.title, {
    body: payload.notification.body,
    icon: '/static/icon-144x144.png'
  });
});
```

### Option B: Mobile App (React Native)

1. Install dependencies:

```bash
npm install @react-native-firebase/app @react-native-firebase/messaging
```

2. Configure Firebase in your Android/iOS project (follow React Native Firebase docs)

3. Request permission and get token:

```javascript
import messaging from '@react-native-firebase/messaging';

async function requestUserPermission() {
  const authStatus = await messaging().requestPermission();
  const enabled = 
    authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
    authStatus === messaging.AuthorizationStatus.PROVISIONAL;
  
  if (enabled) {
    const token = await messaging().getToken();
    console.log('FCM Token:', token);
    await sendTokenToServer(token);
  }
}
```

## Step 6: Test the Integration

1. Place `firebase-service-account.json` in your project root
2. Restart your Flask server
3. Open parent portal in browser
4. Allow notification permissions when prompted
5. Check browser console for FCM token
6. Publish a newsletter from the admin panel
7. Check if notification appears on registered device

## Step 7: Deploy to Cloud (Railway)

When deploying to Railway:

1. Set the Firebase service account JSON as an environment variable:
   - Name: `FIREBASE_SERVICE_ACCOUNT`
   - Value: Paste the entire JSON content

2. Update `fcm_service.py` to read from environment variable:

```python
import os
import json

# Instead of reading from file, read from environment
service_account_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
if service_account_json:
    cred_dict = json.loads(service_account_json)
    cred = credentials.Certificate(cred_dict)
else:
    # Fallback to file for local development
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
```

## Troubleshooting

**Issue**: "Firebase service account file not found"
- **Solution**: Ensure `firebase-service-account.json` is in the project root

**Issue**: "Permission denied"
- **Solution**: Check Firebase Console → Project Settings → Cloud Messaging settings

**Issue**: "Invalid registration token"
- **Solution**: Token may have expired, implement token refresh handling

**Issue**: Notifications not received on web
- **Solution**: Ensure site is served over HTTPS (required for FCM on web)

## Cost

FCM is **completely free** for:
- Unlimited push notifications
- Unlimited devices
- Unlimited messages

The free tier is sufficient for most school management systems.

## Next Steps

1. Complete Firebase project setup
2. Download service account credentials
3. Add Firebase SDK to your frontend (web or mobile)
4. Test with a sample newsletter
5. Deploy to production with environment variables

## Support

For issues:
- Firebase Console: https://console.firebase.google.com/
- Firebase Documentation: https://firebase.google.com/docs
- React Native Firebase: https://rnfirebase.io/
