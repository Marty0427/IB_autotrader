from ib_insync import *
import pandas as pd
pd.options.mode.chained_assignment = None  # default='warn'
import pandas_datareader as pdr
import numpy as np
import datetime as dt
from config.settings import *
util.startLoop()
from time import sleep
ib = IB()

if __name__ == '__main__':
    try:
        for i in range(len(setStrat['strategy'])):
            str_to_close = AMI_exit(setStrat['strategy'][i])
            str_to_close = time_exit(setStrat['strategy'][i], setStrat['days'][i])
            str_to_open = enter(setStrat['strategy'][i], setStrat['positions'][i],
                                setStrat['Limit'][i])
            send_orders(setStrat['strategy'][i], setStrat['Limit'][i], setStrat['positions'][i])
    except KeyError as e:
        print(e)
