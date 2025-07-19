from psycopg2._psycopg import connection

class Migrate():
    def __init__(self, db: connection):
        self.db = db
    def run(self):
        create_table_query = """
        CREATE TABLE IF NOT EXISTS forecasts(
            time TIMESTAMP PRIMARY KEY,
            temperature_2m_mean NUMERIC,
            apparent_temperature_mean NUMERIC,
            rain_sum NUMERIC, 
            wind_gusts_10m_mean NUMERIC, 
            wind_speed_10m_mean NUMERIC,
            relative_humidity_2m_mean NUMERIC
        )
        """
        driver = self.db.cursor()
        driver.execute(create_table_query)
        self.db.commit()

def create_migration_instance(db: connection) -> Migrate:
    return Migrate(db)