## PostgreSQL setup (local development)

This project uses SQLAlchemy and can be configured to use PostgreSQL via the `DATABASE_URL` environment variable. If `DATABASE_URL` is not set the app will fall back to a local SQLite file.

Quick steps (Ubuntu/Debian):

1. Install PostgreSQL:

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

2. Create a DB user and database (replace `myuser`/`mypassword`/`mydb`):

```bash
sudo -u postgres createuser --pwprompt myuser
sudo -u postgres createdb -O myuser mydb
```

3. Set `DATABASE_URL` and install Python deps:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Example DATABASE_URL (psycopg2):
export DATABASE_URL="postgresql://myuser:mypassword@localhost:5432/mydb"
```

4. Run the app (it will call `db.create_all()` to create tables):

```bash
# from repo root
python server/run.py
```

Notes:
- The app reads `DATABASE_URL` (preferred) or `SQLALCHEMY_DATABASE_URI` from the environment.
- We added `psycopg2-binary` to `requirements.txt` so SQLAlchemy can talk to Postgres.
- If you prefer a `.env` file, consider adding `python-dotenv` and loading it in `create_app()`.
