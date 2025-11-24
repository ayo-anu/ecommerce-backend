# 🚀 Production Deployment Checklist

## Pre-Deployment (Do Once)

### Security
- [ ] Generate NEW SECRET_KEY for production
- [ ] Update all .env values for production
- [ ] Verify .env is in .gitignore
- [ ] Change Stripe keys to LIVE keys (when ready)
- [ ] Set up SSL certificate (HTTPS)
- [ ] Review ALLOWED_HOSTS

### Database
- [ ] Set up production PostgreSQL database
- [ ] Create database backups schedule
- [ ] Test database connection
- [ ] Run migrations: `python manage.py migrate`
- [ ] Create superuser: `python manage.py createsuperuser`

### Static Files
- [ ] Set up S3 bucket (or CDN)
- [ ] Configure AWS credentials
- [ ] Run: `python manage.py collectstatic`
- [ ] Test static file serving

### Services
- [ ] Set up production Redis
- [ ] Set up production Elasticsearch
- [ ] Configure Celery worker service
- [ ] Configure Celery beat scheduler

### Monitoring
- [ ] Add Sentry DSN to production .env
- [ ] Test error reporting
- [ ] Set up uptime monitoring (UptimeRobot, Pingdom)

### Email
- [ ] Configure production email (SendGrid, Mailgun, SES)
- [ ] Test email sending
- [ ] Verify email templates

## Every Deployment

- [ ] Pull latest code: `git pull origin main`
- [ ] Activate virtual environment
- [ ] Install dependencies: `pip install -r requirements/prod.txt`
- [ ] Run migrations: `python manage.py migrate`
- [ ] Collect static files: `python manage.py collectstatic --noinput`
- [ ] Restart application server
- [ ] Restart Celery workers
- [ ] Check logs for errors
- [ ] Test critical endpoints (login, order creation, payment)
- [ ] Verify Sentry is receiving events

## Post-Deployment Verification

- [ ] Health check endpoint responds: `/health/`
- [ ] Admin panel accessible: `/admin/`
- [ ] API docs accessible: `/api/docs/`
- [ ] Can create an order
- [ ] Can process a payment (test mode)
- [ ] Emails are sending
- [ ] Background tasks are running
- [ ] No errors in logs
- [ ] Database queries are optimized (check Sentry performance)

## Emergency Rollback

If something goes wrong:
```bash
# Quick rollback
git checkout <previous-commit-hash>
python manage.py migrate
sudo systemctl restart gunicorn
sudo systemctl restart celery
```

## Monitoring After Deploy

- Check Sentry for errors (first 1 hour)
- Monitor server resources (CPU, Memory, Disk)
- Watch database connection pool
- Check API response times
- Monitor Celery queue length