# Railway Cloud Deployment Guide

## Step 1: Prepare Your Repository

Make sure your project is in a Git repository:

```powershell
cd c:\Users\HomePC\Documents\FreemanTech_Project
git init
git add .
git commit -m "Initial commit for cloud deployment"
```

If you don't have Git installed:
```powershell
choco install git
```

## Step 2: Create GitHub Repository

1. Go to [github.com](https://github.com) and sign in (or create account)
2. Click **New Repository**
3. Name it: `freeman-school-portal`
4. Do NOT initialize with README (you already have files)
5. Click **Create Repository**
6. Follow the instructions to push your local repo:

```powershell
git remote add origin https://github.com/YOUR_USERNAME/freeman-school-portal.git
git branch -M main
git push -u origin main
```

## Step 3: Deploy to Railway

1. Go to [railway.app](https://railway.app)
2. Click **Login** → Sign in with GitHub
3. Click **New Project** → **Deploy from GitHub repo**
4. Find and select `freeman-school-portal`
5. Railway automatically detects Flask app
6. Wait for deployment (~2-3 minutes)
7. You'll get a public URL: `https://yourapp-prod.railway.app`

## Step 4: Update Dashboard Settings

Back in your Freeman desktop app:

1. Click **⚙️ Setup School Branding**
2. In **Cloud Portal URL**, paste your Railway URL:
   - Example: `https://yourapp-prod.railway.app`
   
3. Fill in:
   - Cloud School Code: `FREEMAN26`
   - Cloud Teacher Username: `portal`
   - Cloud Teacher Password: `FREEMAN26`
4. Click **🚀 SAVE ALL SETTINGS**

## Step 5: Test Cloud Sync

1. Click **🔄 Sync Students Cloud** on dashboard
2. Enter credentials when prompted
3. If successful, you'll see: "Students synced successfully"
4. Your cloud portal is live!

## Environment Variables on Railway

Railway automatically sets:
- `PORT` (Railway assigns a port dynamically)
- Add more in Railway dashboard → Variables

To set `SECRET_KEY` for production:
1. Go to Railway project → **Variables**
2. Add variable:
   - Key: `SECRET_KEY`
   - Value: `your-secure-random-key-here`
3. Redeploy

## Custom Domain (Optional)

To use a custom domain like `school-portal.com`:

1. Railway Dashboard → **Project** → **Domains**
2. Add custom domain
3. Update your DNS records at your domain registrar
4. Wait 5-10 minutes for DNS propagation

## Troubleshooting

**Error: "Could not connect to cloud portal"**
- Check Railway deployment status (should be "Running")
- Verify URL is correct
- Check if there are Flask errors in Railway logs

**Database not persisting?**
- Railway containers are ephemeral
- Add persistent volume in Railway settings, OR
- Use Railway's PostgreSQL plugin (recommended for production)

**How to view logs:**
- Railway Dashboard → **Project** → **Deployments** → Click latest
- Scroll down to see logs

## Next Steps

- Set up PostgreSQL database for production
- Configure SSL certificates (automatic with Railway)
- Monitor usage in Railway dashboard
- Keep `cloud_portal.db` backed up

