import psycopg
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')

cfg = {
    'host': os.getenv('POSTGRES_CONN_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_CONN_PORT', '5432')),
    'user': os.getenv('POSTGRES_USERNAME'),
    'password': os.getenv('POSTGRES_PASSWORD'),
    'dbname': 'metro',
}

with psycopg.connect(**cfg) as conn:
    with conn.cursor() as cur:
        # Get all tables in staging
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='staging' ORDER BY table_name")
        tables = [row[0] for row in cur.fetchall()]
        
        for table in tables:
            cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema='staging' AND table_name=%s ORDER BY ordinal_position",
                (table,)
            )
            staging_cols = [row[0] for row in cur.fetchall()]
            
            cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema='core' AND table_name=%s ORDER BY ordinal_position",
                (table,)
            )
            core_cols = [row[0] for row in cur.fetchall()]
            
            dropped = set(staging_cols) - set(core_cols)
            added = set(core_cols) - set(staging_cols)
            
            status = "OK"
            if dropped:
                status = f"DROPS {sorted(dropped)}"
            if added:
                status = f"ADDS {sorted(added)}"
            
            print(f"{table:<20} staging={len(staging_cols):2d} core={len(core_cols):2d}  {status}")
