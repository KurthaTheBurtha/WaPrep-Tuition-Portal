# 🚀 WaPrep Tuition Portal - Render Deployment Quick Start

## Overview

This guide provides step-by-step instructions for deploying the WaPrep Tuition Portal to Render quickly and securely.

---

## 📋 **Pre-Deployment Checklist**

### **1. Run Deployment Check**
```bash
# Check if your application is ready for deployment
python scripts/deploy_to_render.py
```

### **2. Generate Strong SECRET_KEY**
```python
# Run this in Python shell
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

### **3. Prepare Environment Variables**
Create a `.env` file with these production settings:

```bash
# Django Settings
SECRET_KEY=your-generated-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-app-name.onrender.com,your-custom-domain.com

# Database (will be set by Render)
DATABASE_URL=postgresql://user:password@host:port/database

# Security Settings
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SESSION_EXPIRE_AT_BROWSER_CLOSE=True

# Email Settings
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-email-password
DEFAULT_FROM_EMAIL=your-email@example.com

# Stripe Settings
STRIPE_SECRET_KEY=sk_live_your-stripe-secret-key
STRIPE_PUBLISHABLE_KEY=pk_live_your-stripe-publishable-key

# Admin Token
SUPERUSER_TOKEN=your-secure-admin-token-here
```

---

## 🎯 **Render Deployment Steps**

### **Step 1: Create Render Account**
1. Go to [render.com](https://render.com)
2. Sign up with your GitHub account
3. Verify your email address

### **Step 2: Connect Your Repository**
1. Click "New +" in the Render dashboard
2. Select "Web Service"
3. Connect your GitHub repository
4. Select the repository containing your WaPrep Tuition Portal

### **Step 3: Configure Web Service**
```
Service Name: waprep-tuition-portal
Environment: Python 3
Region: Choose closest to your users
Branch: main (or your production branch)
Root Directory: (leave blank if root)
```

### **Step 4: Build Configuration**
```
Build Command: pip install -r requirements.txt
Start Command: gunicorn tuition.wsgi:application
```

### **Step 5: Create PostgreSQL Database**
1. Click "New +" → "PostgreSQL"
2. Configure:
   ```
   Name: waprep-tuition-db
   Database: waprep_tuition_prod
   User: waprep_user
   Plan: Choose appropriate plan
   ```
3. Copy the `DATABASE_URL` from the database dashboard

### **Step 6: Configure Environment Variables**
In your web service settings, add these environment variables:

| Variable | Value |
|----------|-------|
| `SECRET_KEY` | Your generated secret key |
| `DEBUG` | `False` |
| `DATABASE_URL` | From PostgreSQL service |
| `SECURE_SSL_REDIRECT` | `True` |
| `SECURE_HSTS_SECONDS` | `31536000` |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `True` |
| `SECURE_HSTS_PRELOAD` | `True` |
| `SESSION_COOKIE_SECURE` | `True` |
| `CSRF_COOKIE_SECURE` | `True` |
| `SESSION_EXPIRE_AT_BROWSER_CLOSE` | `True` |
| `EMAIL_HOST_USER` | Your email |
| `EMAIL_HOST_PASSWORD` | Your email password |
| `DEFAULT_FROM_EMAIL` | Your email |
| `STRIPE_SECRET_KEY` | Your Stripe secret key |
| `STRIPE_PUBLISHABLE_KEY` | Your Stripe publishable key |
| `SUPERUSER_TOKEN` | Your admin token |

### **Step 7: Configure Health Check**
```
Health Check Path: /health/
```

### **Step 8: Deploy**
1. Click "Create Web Service"
2. Monitor the deployment process
3. Check logs for any errors

---

## 🔧 **Post-Deployment Setup**

### **1. Run Database Migrations**
```bash
# In Render shell or via management command
python manage.py migrate
```

### **2. Create Superuser**
```bash
# Create admin user
python manage.py createsuperuser
```

### **3. Collect Static Files**
```bash
# Collect static files
python manage.py collectstatic --noinput
```

### **4. Test Application**
1. Visit your Render URL
2. Test user registration
3. Test payment processing
4. Test admin functions

---

## 🔒 **Security Verification**

### **1. Run Security Audit**
```bash
# After deployment, run security tests
python scripts/security_audit.py
```

### **2. Test HTTPS**
- Verify all pages redirect to HTTPS
- Check SSL certificate is valid
- Test security headers

### **3. Verify Environment Variables**
- Ensure no secrets are exposed in logs
- Verify all security settings are enabled
- Test authentication and authorization

---

## 📊 **Monitoring Setup**

### **1. Enable Logs**
- Go to your service dashboard
- Click "Logs" tab
- Monitor for errors and warnings

### **2. Set Up Alerts**
- Configure alerts for high CPU/memory usage
- Set up error rate alerts
- Monitor response times

### **3. Health Monitoring**
- Verify `/health/` endpoint returns 200
- Set up uptime monitoring
- Monitor database connections

---

## 🚨 **Troubleshooting**

### **Common Issues**

#### **Build Failures**
```bash
# Check build logs for:
- Missing dependencies in requirements.txt
- Python version compatibility
- Import errors
```

#### **Database Connection Issues**
```bash
# Verify:
- DATABASE_URL is correct
- Database service is running
- Network connectivity
```

#### **Static Files Not Loading**
```bash
# Run collectstatic:
python manage.py collectstatic --noinput
```

#### **Environment Variable Issues**
```bash
# Check:
- All required variables are set
- No typos in variable names
- Values are properly formatted
```

### **Debug Commands**
```bash
# Check application status
python manage.py check --deploy

# Test database connection
python manage.py dbshell

# Check environment variables
python manage.py shell
>>> import os
>>> print(os.getenv('SECRET_KEY'))
```

---

## 📈 **Performance Optimization**

### **1. Database Optimization**
```python
# In settings_production.py
DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}
```

### **2. Caching Configuration**
```python
# Add caching for better performance
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
```

### **3. Static File Optimization**
- Use CDN for static files
- Enable compression
- Optimize images

---

## 🔄 **Continuous Deployment**

### **1. Auto-Deploy Setup**
- Enable auto-deploy in Render dashboard
- Set up branch protection rules in GitHub
- Configure deployment notifications

### **2. Staging Environment**
- Create staging service for testing
- Use separate database for staging
- Test all changes before production

### **3. Rollback Plan**
- Keep previous deployment ready
- Document rollback procedures
- Test rollback process

---

## 📞 **Support Resources**

### **Render Documentation**
- [Render Docs](https://render.com/docs)
- [Python on Render](https://render.com/docs/deploy-python)
- [PostgreSQL on Render](https://render.com/docs/deploy-postgres)

### **Django Deployment**
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [Django Security](https://docs.djangoproject.com/en/stable/topics/security/)

### **Monitoring Tools**
- [Sentry for Error Tracking](https://sentry.io/)
- [Uptime Robot for Monitoring](https://uptimerobot.com/)
- [Google Analytics for Usage](https://analytics.google.com/)

---

## 🎉 **Deployment Complete!**

Once your application is deployed and tested:

1. **Update DNS** (if using custom domain)
2. **Configure SSL** (automatic with Render)
3. **Set up monitoring** and alerts
4. **Document** the deployment process
5. **Train** team members on maintenance procedures

Your WaPrep Tuition Portal is now live and secure on Render! 🚀 