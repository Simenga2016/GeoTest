initialization = """
CREATE TABLE IF NOT EXISTS limits (
    server TEXT PRIMARY KEY,
    total NUMERIC NOT NULL,
    used NUMERIC DEFAULT 0
);
"""

set_limits = f"""
    INSERT INTO limits (server, total, used)
    VALUES (%s, %s, -1)
    ON CONFLICT (server) 
    DO UPDATE SET total = EXCLUDED.total, used = EXCLUDED.used;
"""


get_status = f"SELECT total, used FROM limits WHERE server = %s;"

stat_reset = f"UPDATE limits SET used = -1 WHERE server = %s;"

rule_reset = f"DELETE FROM limits WHERE server = %s;"
