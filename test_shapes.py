import psycopg

cfg = {"host": "localhost", "port": 5432, "user": "postgres", "password": "301415", "dbname": "metro"}
with psycopg.connect(**cfg) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM core.shape_points")
        print(f"shape_points rows: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM core.shapes")
        print(f"shapes rows: {cur.fetchone()[0]}")
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='core' AND table_name='shapes' ORDER BY ordinal_position")
        print(f"shapes columns: {[c[0] for c in cur.fetchall()]}")
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='core' AND table_name='shape_points' ORDER BY ordinal_position")
        print(f"shape_points columns: {[c[0] for c in cur.fetchall()]}")
