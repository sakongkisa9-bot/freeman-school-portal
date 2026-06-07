// Firebase Cloud Messaging Service Worker
// This file handles background push notifications

importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-messaging-compat.js');

// Initialize Firebase in the service worker
const firebaseConfig = {
    apiKey: "AIzaSyDK78eyayqUeCZxl_RwsC1SZEpwIgxK5EE",
    authDomain: "freeman-2202a.firebaseapp.com",
    projectId: "freeman-2202a",
    storageBucket: "freeman-2202a.appspot.com",
    messagingSenderId: "435924108891",
    appId: "1:435924108891:web:c074fb7c630cfaff3b617e"
};

if (!firebase.apps.length) {
    firebase.initializeApp(firebaseConfig);
}

// Retrieve an instance of Firebase Messaging so that it can handle background messages
const messaging = firebase.messaging();

// Handle background messages
messaging.onBackgroundMessage(function(payload) {
    console.log('[firebase-messaging-sw.js] Received background message ', payload);
    
    // Customize notification here
    const notificationTitle = payload.notification.title;
    const notificationOptions = {
        body: payload.notification.body,
        icon: '/static/icon-192x192.png',
        badge: '/static/icon-144x144.png',
        click_action: payload.notification.click_action || 'https://freeman-school-portal.up.railway.app/parent/newsletters'
    };

    self.registration.showNotification(notificationTitle, notificationOptions);
});
