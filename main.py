from repository.postgres.main import create_weather_repository
from config.db import create_new_config
import pandas as pd
from constant.main import SevenDays
from statsmodels.tsa.vector_ar.var_model import VAR, VARResultsWrapper
from statsmodels.tsa.stattools import adfuller
from pandas import Index
import numpy as np
from typing import List, Tuple
import logging
from migration.main import create_migration_instance
from datetime import timedelta

def split_data(df:pd.DataFrame, n_test:int):
    train, test = df.iloc[:-n_test], df.iloc[-n_test:]
    return train, test

def stationary_test(df:pd.DataFrame):
    non_stationary_columns=[]

    for col in df.columns:
        test_result = adfuller(df[col])
        pvalue = test_result[1]

        if pvalue > 0.05:
            non_stationary_columns.append(col)
    
    return non_stationary_columns

def differencing_data(df:pd.DataFrame, non_stationary_columns:List[str]):

    if len(non_stationary_columns) == 0:
        return df
    
    differenced = df.copy(deep=True)
    
    for col in df.columns:
        if col in non_stationary_columns:
            differenced[col] = differenced[col].diff()

    differenced.dropna(inplace=True)
    return differenced

def inverse_difference(pred:pd.DataFrame, df:pd.DataFrame, non_stationary_columns:List[str]):

    if len(non_stationary_columns) == 0:
        return pred
    
    for col in pred.columns:
        if col in non_stationary_columns:
            pred[col] = df[col].iloc[-1] + pred[col].cumsum()
    
    return pred

def fit_forecast_var(df:pd.DataFrame, differenced: pd.DataFrame, n_test:int, test_index:Index, non_stationary_columns: List[str]) -> Tuple[VARResultsWrapper, pd.DataFrame]:
    var = VAR(differenced)
    lag_order_result = var.select_order(20)
    chosen_lag = lag_order_result.selected_orders['aic'].item()

    var_result:VARResultsWrapper = var.fit(chosen_lag)
    lags = var_result.k_ar

    forecast_input = df.iloc[-lags:].values
    preds:np.ndarray = var_result.forecast(forecast_input,steps = n_test)
    preds_df = pd.DataFrame(preds, columns=df.columns, index = test_index)

    return var_result, inverse_difference(preds_df, df, non_stationary_columns)

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


        non_stationary_cols = stationary_test(df)
        differenced = differencing_data(df, non_stationary_cols)

        start = df.index[-1] + timedelta(days = 1)
        end = start + timedelta(days = SevenDays - 1)
        index = pd.date_range(
            start=start,
            end=end,
            freq='D'
        )

        model, res = fit_forecast_var(df, differenced, SevenDays, index, non_stationary_cols)

        res.reset_index(drop=False, inplace=True, names=['time'])
        res['time'] = res['time'].dt.strftime('%Y-%m-%d')
    
        forecast_records = res.to_records(index=False).tolist()
        repo.insert_forecast(forecast_records)
        logger.info("Forecast success")
    except Exception as e:
        logger.error(repr(e))





    

