from psycopg2._psycopg import connection
from typing import List, Tuple, Any, Sequence
from abc import ABC, abstractmethod

class AbstractWeatherRepository(ABC):
    @abstractmethod
    def get_all_data(self) -> List[Tuple[Any, ...]]:
        pass
    @abstractmethod
    def insert_forecast(self, new_data: List[Sequence[Any]]) -> None:
        pass


class WeatherRepository(AbstractWeatherRepository):
    def __init__(self, db: connection) -> None:
        self.db = db
    
    def get_all_data(self):
        driver = self.db.cursor()
        select_query = """
        SELECT
            time,
            temperature_2m_mean,
            apparent_temperature_mean,
            rain_sum,
            wind_gusts_10m_mean,
            wind_speed_10m_mean,
            relative_humidity_2m_mean
        FROM weathers
        ORDER BY time
        """

        driver.execute(select_query)
        records = driver.fetchall()

        return records
    def insert_forecast(self, 
                        new_data):
        cursor = self.db.cursor()
        insert_query = """
        INSERT INTO forecasts (time, temperature_2m_mean, apparent_temperature_mean, rain_sum, wind_gusts_10m_mean, wind_speed_10m_mean, relative_humidity_2m_mean)
        VALUES
        (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (time)
        DO UPDATE SET 
            temperature_2m_mean = EXCLUDED.temperature_2m_mean, 
            apparent_temperature_mean = EXCLUDED.apparent_temperature_mean, 
            rain_sum = EXCLUDED.rain_sum, 
            wind_gusts_10m_mean = EXCLUDED.wind_gusts_10m_mean, 
            wind_speed_10m_mean = EXCLUDED.wind_speed_10m_mean, 
            relative_humidity_2m_mean = EXCLUDED.relative_humidity_2m_mean;
        """
        cursor.executemany(insert_query, new_data)
        self.db.commit()
    
def create_weather_repository(db: connection) -> AbstractWeatherRepository:
    return WeatherRepository(db)