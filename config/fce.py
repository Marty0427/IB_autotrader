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

def get_fills(api: bool) -> pd.DataFrame:
    '''
    connects to IBKR API
    loads todays executions and returns a dataframe with it
    disconnects API
    '''
    if api: #true znamená, že načte obchody přes API, jinak ze souboru trades.csv v tomto adresáři
        ib.connect(setIB['IP'], setIB['port'], setIB['clientID'])
        exekuce = (e for e in ib.fills())
        exekuce = [(e.time,e.contract.symbol,e.execution.side,e.execution.shares,e.execution.avgPrice,e.commissionReport.commission,e.execution.orderRef) 
               for e in exekuce]
        '''exekuce = [(e.time,e.execution.acctNumber,e.execution.clientId,e.contract.symbol,e.execution.permId,e.execution.side,e.execution.shares,e.execution.avgPrice,e.commissionReport.commission,e.execution.orderRef) 
               for e in exekuce]'''
        exe=pd.DataFrame(exekuce, columns=['cas','ticker','smer','pocet','cena','komise','orderRef'])
    else:
        exe = pd.read_csv('trades.csv', sep=';')
    exe.cas = pd.to_datetime(exe.cas) 
    exe['cas'] = exe['cas'].dt.strftime('%d.%m.%Y') #přepíše datum na český formát a vymaže čas (prohazuje den a měsíc)
    ib.disconnect()
    return exe

def get_close(ticker: str) -> float:
    #returns last close price of todays ticker
    data = pdr.get_data_yahoo(ticker)
    return round(data['Close'].iloc[-1],2)

def index(df):
    #reindex the dataframe (better use .reset_index(drop = True)
    df.index = np.arange(0,len(df))

def AMI_exit(strategy: str) -> pd.DataFrame:
    '''
    loads open trades of a strategy ({strategy}_open.csv file)
    returns a dataframe of tickers to close according to Amibroker scan file    
    call before time_exit
    '''
    str_scan = pd.read_csv(f'AMI/{strategy}_scan.csv', sep = ',')
    str_scan_sell = str_scan[str_scan.Trade == 'Sell']
    index(str_scan_sell)
    str_opened = pd.read_csv(f'Deník/{strategy}_open.csv', sep = ';')
    index(str_opened)
    str_to_close = str_opened[0:0]
    for i in range(len(str_scan_sell)):
        for j in range(len(str_opened)):
            if str_scan_sell.Symbol[i] == str_opened.Trh[j]:
                col = len(str_to_close)
                str_to_close.loc[col] = str_opened.loc[j]
                str_to_close.Vystup_cena[col] = str_scan_sell.Close[i]
    str_to_close.Vstup = pd.to_datetime(str_to_close.Vstup)
    str_to_close = str_to_close[str_to_close.Vstup == (dt.date.today() - dt.timedelta(days = 1))]
    return str_to_close
                
def time_exit(strategy: str, days: int) -> pd.DataFrame:
    '''
    loads open trades of a strategy and appends tickers (after a defined days in position) to dataframe str_to_close
    call after AMI_exit
    '''
    str_opened = pd.read_csv(f'Deník/{strategy}_open.csv', sep = ';')
    index(str_opened)
    str_opened.Vstup = pd.to_datetime(str_opened.Vstup).dt.strftime('%d.%m.%Y')
    str_opened.Vstup = pd.to_datetime(str_opened.Vstup)
    #str_opened.Vstup = str_opened.Vstup.strftime('%d.%m.%Y')
    try:
        if str_to_close is not None:
            print('df to_close already exists')
    except:
        str_to_close = str_opened[0:0]
        
    date = str_opened.Vstup.values.astype('datetime64[D]')
    wdays = np.busday_count(date, dt.date.today())
    str_expired = str_opened[wdays >= days]
    index(str_expired)
    for i in range(len(str_expired)):
        col = len(str_to_close)
        str_to_close.loc[col] = str_expired.loc[i]
    str_to_close.Vstup = pd.to_datetime(str_to_close.Vstup)
    close = len(str_to_close)
    return str_to_close


def enter(strategy: str, positions: int, Limit = False) -> pd.DataFrame:
    '''
    loads Amibroker explore file to a dataframe
    sort the dataframe and slices it accordingly to a number of positions
    '''    
    
    str_explore = pd.read_csv(f'AMI/{strategy}_explore.csv')
    str_explore['Contract'] = ''
    str_explore['Order'] = ''
    str_explore = str_explore.sort_values(by=['Score'], ascending = False)
    index(str_explore)
    str_opened = pd.read_csv(f'Deník/{strategy}_open.csv', sep = ';')
    str_to_close = AMI_exit(strategy)
    str_to_close = time_exit(strategy, days)
    to_open = positions - len(str_opened) + len(str_to_close)
    
    str_to_open = str_explore
    
    str_to_open['Date/Time'] = pd.to_datetime(str_to_open['Date/Time'])
    str_to_open['Date/Time'] = str_to_open['Date/Time'].dt.strftime('%d.%m.%Y')
    str_to_open['Date/Time'] = pd.to_datetime(str_to_open['Date/Time'])
    date = str_to_open['Date/Time'].values.astype('datetime64[D]')
    sdays = np.busday_count(date, dt.date.today())
    str_to_open = str_to_open[sdays == 1] 
    index(str_to_open)
    
    
    if not Limit:
        str_to_open = str_to_open.head(to_open)
    return str_to_open
    
    

def rotate(strategy: str, positions: int) -> pd.DataFrame, pd.DataFrame:

    '''
    used for rotational strategies
    compares open trades of a strategy with trades highest positionScore ticker from Amibroker and closes and opens accordingly
    '''
    
    str_explore = pd.read_csv(f'AMI/{strategy}_explore.csv')
    str_explore['Contract'] = ''
    str_explore['Order'] = ''
    str_explore = str_explore.sort_values(by=['Score'], ascending = False)
    index(str_explore)
    str_new = str_explore.head(positions)
    str_opened = pd.read_csv(f'Deník/{strategy}_open.csv', sep = ';')
    index(str_opened)
    str_to_open = str_new[str_new.Ticker.isin(str_opened.Trh) == False]
    index(str_to_open)
    str_to_close = str_opened[str_opened.Trh.isin(str_new.Ticker) == False]
    index(str_to_close)
    return str_to_close, str_to_open


def send_orders(strategy: str, Limit: bool, positions: int):
    '''
    sends BUY orders according to a str_to_open dataframe and SELL orders according to a str_to_close dataframe
    eventually activates Limit_order
    '''
    str_to_open['Contract'] = ''
    str_to_open['Order'] = ''
    str_to_close['Contract'] = ''
    str_to_close['Order'] = ''
    
    ib.connect(setIB['IP'], setIB['port'], setIB['clientID'])
    
    if not str_to_open.empty:
        for i in range(len(str_to_open)):
            if round(str_to_open.Buy_shares[i]) > 0:
                str_to_open.Contract[i] = Stock(str_to_open.Ticker[i], 'SMART','USD')
                if Limit:
                    lmt = str_to_open.Limit[i]
                else:
                    lmt = str_to_open.Close[i]
                    
                str_to_open.Order[i] = Order(orderType='LMT', action="BUY", 
                                             totalQuantity=int(round(str_to_open.Buy_shares[i])),
                                             lmtPrice = lmt, orderRef = strategy)
                contract = str_to_open.Contract[i]
                order = str_to_open.Order[i]
                print('BUY', round(str_to_open.Buy_shares[i]), str_to_open.Ticker[i])
                trade=ib.placeOrder(contract, order)
                ib.sleep(1)
            else:
                print("Long ticker ",str_to_open.Ticker[i], " byl zaokrouhlen na 0 shares!",sep = "")
    
    if not str_to_close.empty:
        for i in range(len(str_to_close)):
            if round(str_to_close.Shares[i]) > 0:
                str_to_close.Contract[i] = Stock(str_to_close.Trh[i], 'SMART','USD')
                str_to_close.Order[i] = Order(orderType='LMT', action="SELL", totalQuantity=int(str_to_close.Shares[i]),
                                             lmtPrice=get_close(str_to_close.Trh[i]), orderRef = strategy)
                contract = str_to_close.Contract[i]
                order = str_to_close.Order[i]
                print('SELL', round(str_to_close.Shares[i]), str_to_close.Trh[i])
                trade=ib.placeOrder(contract, order)
                ib.sleep(1)
            else:
                print("Short ticker ", str_to_close.Ticker[i], " byl zaokrouhlen na 0 shares!",sep = "")
                
    ib.disconnect()
    
    if Limit:
        Limit_order(strategy, positions)    

    
def Limit_order(strategy: str, positions: int):
    '''
    sends all orders from Amibroker explore file for a lower limit price
    controls how many orders got open
    cancels all orders if the  number of positions is as desired
    '''
    str_opened = pd.read_csv(f'Deník/{strategy}_open.csv', sep = ';')
    index(str_opened)
    to_open = positions - len(str_opened) + len(str_to_close)

    #entry loop 
    str_now = 0
    while(str_now != to_open):
        exe = get_fills()
        str_now = len(exe[(exe.smer == 'BOT') & (exe.orderRef == strategy)])
        str_now_opened = str_now + len(str_opened) - len(str_to_close)
        print(f'Počet pozice strategie {strategy}:', str_now_opened)
        ib.sleep(1)
        if str_now >= to_open:
            break

    #cancel loop
    for k in range(len(str_to_open)):
        try:
            ib.cancelOrder(str_to_open.Order[k])
            print('Obj', str_to_open.Ticker[k], 'zrušena')
        except:
            print('Obj', str_to_open.Ticker[k], 'nebyla zrušena!')
    ib.disconnect()
    print('Konec Limit')


