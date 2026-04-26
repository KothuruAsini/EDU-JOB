# Deployment TODO

## Plan
Deploy Edu2Job Django project to a PaaS platform (Railway/Render/Heroku).

## Steps
- [x] Update `requirements.txt` — Add production dependencies (python-dotenv, whitenoise, gunicorn, dj-database-url)
- [x] Update `edu2job/settings.py` — Environment-based config, WhiteNoise, static files, database URL
- [x] Create `.env.example` — Environment variable template
- [x] Create `Procfile` — Process definition for PaaS
- [x] Create `runtime.txt` — Python version specification
- [x] Create `.gitignore` — Prevent committing local/dev files
- [x] Install dependencies and test locally
- [x] Run Django deployment checks
- [x] Run collectstatic

