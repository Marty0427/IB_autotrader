from ib_insync import *
import pandas as pd
pd.options.mode.chained_assignment = None  # default='warn'
import numpy as np
import datetime as dt
from config.settings import *
util.startLoop()
from time import sleep
ib = IB()
run = 1
open_pos = 10 #nastavím kolik pozic je otevřených
import pandas_datareader as pdr

def get_fills(api = True):
    if api: #true znamená, že načte obchody přes API jinak ze souboru trades csv v tomto adresáři
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
    exe['cas'] = exe['cas'].dt.strftime('%d.%m.%Y') #přepíše datum na správný formát a vymaže čas (prohazuje den a měsíc)
    #exe.set_index("cas",inplace=True)
    ib.disconnect()
    return exe

def get_close(ticker):
    data = pdr.get_data_yahoo(ticker)
    return round(data['Close'].iloc[-1],2)

def AMI_exit(strategy):
    '''
    načte otevřené obchody a zapíše do df str_to_close obchody, které mají podle AMI vystoupit
    nevolat po time_exit, volat před
    '''
    str_scan = pd.read_csv(f'AMI/{strategy}_scan.csv', sep = ',')
    str_scan_sell = str_scan[str_scan.Trade == 'Sell']
    str_scan_sell.index = np.arange(0, len(str_scan_sell))
    str_opened = pd.read_csv(f'Deník/{strategy}_open.csv', sep = ';')
    str_opened.index = np.arange(0, len(str_opened))
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
                
def time_exit(strategy, days):
    '''
    načte otevřené obchody strategie (strategy) a přidá do df(str_to_close) obchody, které jsou již daný 
    počet dní (days) v pozici
    volat až po AMI_exit
    '''
    str_opened = pd.read_csv(f'Deník/{strategy}_open.csv', sep = ';')
    str_opened.index = np.arange(0, len(str_opened))
    str_opened.Vstup = pd.to_datetime(str_opened.Vstup)#.strftime('%d.%m.%Y')
    try:
        if str_to_close is not None:
            print('df to_close already exists')
    except:
        str_to_close = str_opened[0:0]
        
    date = str_opened.Vstup.values.astype('datetime64[D]')
    wdays = np.busday_count(date, dt.date.today())
    str_expired = str_opened[wdays >= days]
    str_expired.index = np.arange(0, len(str_expired))
    for i in range(len(str_expired)):
        col = len(str_to_close)
        str_to_close.loc[col] = str_expired.loc[i]
    str_to_close.Vstup = pd.to_datetime(str_to_close.Vstup)
    close = len(str_to_close)
    return str_to_close

def enter(strategy, positions, Limit = False):
    
    str_explore = pd.read_csv(f'AMI/{strategy}_explore.csv')
    str_explore['Contract'] = ''
    str_explore['Order'] = ''
    str_explore = str_explore.sort_values(by=['Score'], ascending = False)
    str_explore.index = np.arange(0, len(str_explore))
    str_opened = pd.read_csv(f'Deník/{strategy}_open.csv', sep = ';')
    #str_to_close = time_exit(strategy, days)
    to_open = positions - len(str_opened) + len(str_to_close)
    str_to_open = str_explore
    
    if not Limit:
        str_to_open = str_to_open.head(to_open)
    return str_to_open


def rotate():
    


    
def send_orders(strategy, Limit):
    '''
    odešle příkazy BUY podle df str_to_open a SELL podle df str_to_close
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
                print('Bought ', round(str_to_open.Buy_shares[i]), str_to_open.Ticker[i])
                trade=ib.placeOrder(contract, order)
            else:
                print("Long ticker ",str_to_open.Ticker[i], " byl zaokrouhlen na 0 shares!",sep = "")
    
    if not str_to_close.empty:
        for i in range(len(str_to_close)):
            if round(str_to_close.Shares[i]) > 0:
                str_to_close.Contract[i] = Stock(str_to_close.Trh[i], 'SMART','USD')
                str_to_close.Order[i] = Order(orderType='LMT', action="SELL", totalQuantity=int(round(str_to_close.Shares[i])),
                                             lmtPrice=get_close(str_to_close.Trh[i]), orderRef = strategy)
                contract = str_to_close.Contract[i]
                order = str_to_close.Order[i]
                print('Sold ', round(str_to_close.Shares[i]), str_to_close.Trh[i])
                trade=ib.placeOrder(contract, order)
            else:
                print("Short ticker ", str_to_close.Ticker[i], " byl zaokrouhlen na 0 shares!",sep = "")
    ib.disconnect()
    
    if Limit:
        Limit_order(strategy)    

def auto(strategy, positions, days):
    '''
    spojuje funkce z autotraderu
    vystoupí z pozic podle Ami_exit, time_exit a vstoupí podle entry
    '''
    str_to_close = AMI_exit(strategy)
    str_to_close = time_exit(strategy, days)
    str_to_open = enter(strategy, positions, days, Limit = False)
    send_orders(strategy, smer = False)

    
def Limit_order(strategy):
    str_opened = pd.read_csv(f'Deník/{strategy}_open.csv', sep = ';')
    str_opened.index = np.arange(0, len(str_opened))
    to_open = positions - len(str_opened) + len(str_to_close)

    #smyčka pro vstup kontrolu 
    str_now = 0
    while(str_now != to_open):
        exe = get_fills()
        str_now = len(exe[(exe.smer == 'BOT') & (exe.orderRef == strategy)])
        str_now_opened = str_now + len(str_opened) - len(str_to_close)
        print(f'Počet pozice strategie {strategy}:', str_now_opened)
        sleep(1)
        if str_now > to_open:
            break

    #smyčka pro zrušení objednávek
    for k in range(len(str_to_open)):
        try:
            ib.cancelOrder(str_to_open.Order[k])
            print('Obj', str_to_open.Ticker[k], ' zrušena')
        except:
            print('Obj', str_to_open.Ticker[k], ' nebyla zrušena!')
    ib.disconnect()
    print('Konec Limit')
    
strategy = 'Mopul'
positions = 15
days = 4
Limit = False

str_to_close = AMI_exit(strategy)
str_to_close = time_exit(strategy, days)
str_to_open = enter(strategy, positions, Limit)

send_orders(strategy, Limit)
