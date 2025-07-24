from repository.postgres.main import create_weather_repository
from config.db import create_new_config
import pandas as pd
from constant.main import SevenDays
from statsmodels.tsa.vector_ar.vecm import VECM, VECMResults, coint_johansen
from statsmodels.tsa.vector_ar.var_model import VAR
from pandas import Index
import numpy as np
import logging
from migration.main import create_migration_instance
from datetime import timedelta
import warnings

warnings.filterwarnings("ignore")

def split_data(df:pd.DataFrame, n_test:int):
    train, test = df.iloc[:-n_test], df.iloc[-n_test:]
    return train, test

def cointegration_test(df:pd.DataFrame, det_order:int):
    if det_order not in [-1,0,1]:
        raise ValueError('Wrong Deterministic Order')
    
    var = VAR(df)
    lag_order_result = var.select_order(5)

    chosen_lag = lag_order_result.selected_orders['aic'].item() - 1
    test_result = coint_johansen(endog = df, det_order=det_order, 
                   k_ar_diff=chosen_lag)
    
    traces = test_result.lr1
    critical_value = test_result.cvt[:,1] #95% crit values

    r = 0
    for i in range(len(traces)):
        if traces[i] <= critical_value[i]:
            break
        r += 1
    
    return r, chosen_lag

def fit_forecast_vecm(df:pd.DataFrame, r: int, chosen_lag: int, test_index:Index):

    vecm: VECMResults = VECM(df,coint_rank=r,k_ar_diff=chosen_lag).fit()

    preds = vecm.predict(steps = len(test_index))
    preds_df = pd.DataFrame(preds, columns=df.columns, index=test_index)

    return vecm, preds_df

if __name__ == '__main__':
    logger = logging.getLogger("forecast")
    logger.setLevel(logging.DEBUG)
    try:
        config = create_new_config()
        repo = create_weather_repository(config.db)
        migration = create_migration_instance(config.db)

        migration.run()
        logger.info("Success Migrate")
        records = repo.get_all_data()
        logger.info("Successfully get weather data")
            

        df = pd.DataFrame(records, 
                        columns=["time", 
                                "temperature_2m_mean", 
                                "apparent_temperature_mean",
                                "rain_sum", 
                                "wind_gusts_10m_mean",
                                "wind_speed_10m_mean", 
                                "relative_humidity_2m_mean"])
        
        df["temperature_2m_mean"] = df["temperature_2m_mean"].map(float)
        df["apparent_temperature_mean"] = df["apparent_temperature_mean"].map(float)
        df["rain_sum"] = df["rain_sum"].map(float)
        df["wind_gusts_10m_mean"] = df["wind_gusts_10m_mean"].map(float)
        df["wind_speed_10m_mean"] = df["wind_speed_10m_mean"].map(float)
        df["relative_humidity_2m_mean"] = df["relative_humidity_2m_mean"].map(float)
        df.set_index('time', inplace=True, drop=True)


        r, chosen_lags = cointegration_test(df, -1)

        start = df.index[-1] + timedelta(days = 1)
        end = start + timedelta(days = SevenDays - 1)
        index = pd.date_range(
            start=start,
            end=end,
            freq='D'
        )

        model, res = fit_forecast_vecm(df, r, chosen_lags, index)

        res[res < 0] = 0

        res.reset_index(drop=False, inplace=True, names=['time'])
        res['time'] = res['time'].dt.strftime('%Y-%m-%d')
    
        forecast_records = res.to_records(index=False).tolist()
        repo.insert_forecast(forecast_records)
        logger.info("Forecast success")
    except Exception as e:
        logger.error(repr(e))





    

