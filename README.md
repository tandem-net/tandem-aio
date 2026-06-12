# Tandem

nothing yet lolmao

## Using a .env file

Copy `.env.example` to `.env` and edit values for `DATABASE_URL` and `REDIS_URL`.
The app now loads environment variables from `.env` automatically (via `python-dotenv`).

Example:

```bash
cp .env.example .env
# edit .env to set a Postgres DATABASE_URL or leave the SQLite default
source venv/bin/activate
pip install -r requirements.txt
python server/run.py
```
