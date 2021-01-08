'''*****************************************************************************
Purpose: To extract insider trading data from sec website
This program extracts insider trading data from the sec website and stores it in
excel file.
Usage:
Enter a ticker (ex: 'AAPL, MSFT') or type 'all' to search thru all the tickers in file: 

Here you can enter either single ticker or separate multiple tickers by comma or
type 'all' to go thru all the tickers in fName = 'ticker and cik.csv' (default name)

Enter the starting date (Ex: 2020-MM-DD): # enter date in this format no error checking

Would you like to extract data to excel file (Press enter for no OR enter filename): 
Here either enter file name or press enter if you don't want to save the data.
By default the program doesn't display any data on shell, but you can add 
print(all_df) or print(symbol_df) to print the data

Error checking:
I have implemented some error checking:
1.) If user enters incorrect ticker name ex: 'appl, msft, amzn, wrongone' in this
case program will skip 'appl' and 'wrongone' it will print out error msg with ticker
name and will continue to get insider data and save it to file for rest of the tickers.

2.) Let's say you are pulling the data for short period of time and there isn't much
info to calculate avg_purch/avg_sale and buy to sell ratio it will append rest
of the data to excel file.

-------------------------------------------------------------------
****************************************************************************'''
import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import csv

fName = 'ticker and cik.csv'    # set the ticker/CIK file name

data_dict, symbols = {}, []
with open(fName, 'r') as file:
    reader = csv.reader(file)
    for row in reader:
        data_dict[row[0]] = row[1]   # creating a dict ex. format: 'msft': '789019'
        symbols.append(row[0])


'''taking user input'''
# ticker
ticker = input("Enter a ticker (ex: 'AAPL, MSFT') or type 'all' to search thru all the tickers in file: ").replace(" ", "")
ticker = ticker.lower()
if ticker == 'all': symbols = symbols
else:
    tickers = ticker.split(",")
    symbols = tickers
    
# date
start = input("Enter the starting date (Ex: 2020-MM-DD): ")
start2 = datetime.datetime(int(start[:4]),int(start[5:7]),int(start[8:]))
end_date = datetime.date.today()

# extract to excel
extract = input("Would you like to extract data to excel file (Press enter for no OR enter filename): ")
print()


def transaction(url):
    '''gets the transaction report from url
    Parameter:    url: string
                       url for data extraction
    Return: trans_report: soup object
                       transaction report
    '''
    response = requests.get(url)
    web = response.content
    soup = BeautifulSoup(web, 'html.parser')
    trans_report = soup.find('table', {'id':'transaction-report'})
    return trans_report


def insiders(all_data, cik):
    '''gets the insider info of given cik number 
    Parameter:    all_data: list
                       empty list to add data
                  cik: string
                       cik number
    Return:       all_data: list
                       list of all the data
                  headers: list
                       list of the headers "Acquistion or Disposition...."
    '''    
    num = 0
    url = f'https://www.sec.gov/cgi-bin/own-disp?action=getissuer&CIK={cik}&type=&dateb=&owner=include&start={num}'
    
    urls, c = [], 0
    urls.append(url)
    for url in urls:
        c2, headers, data = 0, [], []
        report = transaction(url)    
        for i in report.children:
            if i != '\n':
                collection = i.get_text().split('\n')    
                c2 += 1                          
                for x in collection:
                    if x!= '':          # takng out empty data
                        if len(headers) != 12:  # 12 headers
                            headers.append(x)
                        else: 
                            x = x.replace('$','')                        
                            # checking date boundary
                            if c == 1 and start > x:     # @ c==1, x is date
                                return  all_data, headers 
                            elif (x == 'A' or x == 'D'):    # start of new row
                                if c != 0:
                                    all_data.append(data)                            
                                data, c = [], 0        # new row: clear data           
                                data.append(x)
                                c += 1
                            else: 
                                data.append(x)
                                c += 1     
               
        if c2 == 81: 
            all_data.append(data)                                            
            num += 1
            url = f'https://www.sec.gov/cgi-bin/own-disp?action=getissuer&CIK={cik}&type=&dateb=&owner=include&start={num*80}'
            urls.append(url)
    return  all_data, headers 
          

def data_df(all_df):
    '''gets the insider info of given cik number 
    Parameter:    all_df: list
                       list of all the data frame
    Return:       None
    '''        
    done = 0
    for symbol in symbols:
        all_data = []
        
        # key error handling
        try: cik = data_dict[symbol]
        except Exception as e:
            print(f"The symbol {e} is not valid, rest of the data will be saved to excel file (if available)")        
            if symbol == symbols[-1]: break
            else: continue
        all_data, headers = insiders(all_data, cik)
    
        # adding to data frame
        df = pd.DataFrame.from_records(all_data, columns=headers)
        done += 1
        print(f"Finished extracting {symbol.upper()} insider data from {start} till {end_date}.")
        print(f"Finished: {done}/{len(symbols)} symbols.")
        
        df['Purchchase'] = pd.to_numeric(df['Acquistion or Disposition'].apply(lambda x: 1 if x == 'A' else 0) * df['Number of Securities Transacted'])
        df['Sale'] = pd.to_numeric(df['Acquistion or Disposition'].apply(lambda x: 1 if x == 'D' else 0) * df['Number of Securities Transacted'])   
        
        name = 'Transaction Type'
        sell = df['Transaction Type'].str.count("S-Sale").sum()
        buy = df['Transaction Type'].str.count("P-Purchase").sum()
        
        sale = df['Acquistion or Disposition'] == 'D'    
        purch = df['Acquistion or Disposition'] == 'A'
        num_purch = len(df[purch])
        num_sale = len(df[sale])
        total_sale = int(df['Sale'].sum(skipna=True))        
        total_purch = int(df['Purchchase'].sum(skipna=True))
        
        # adding data to separate df for excel
        symbol_df = pd.DataFrame({'Symbol': symbol.upper(),
                                           '# of Purchases': num_purch,
                                           '# of Sales': num_sale,
                                           'Total Bought': f'{total_purch:,}',
                                           'Total Sold': f'{total_sale:,}',
                                           'S-Sale count': f'{sell}',
                                           'P-Purchase count': f'{buy}'},
                                            index = [1])
        
        # handling division by zero error/adding data to separate df for excel
        try:
            avg_sale = int(total_sale/num_sale)    
            avg_purch = int(total_purch/num_purch)
            ratio = round(num_purch/num_sale, 2)    # purchase to sell ratio
            
        except ZeroDivisionError as e: 
            print(f"\n{e} error for '{symbol}' there isn't much data available to calculate avg sale/purch & ratio, data will be added to excel without these metrics")
            
        else:
            symbol_df.insert(3, 'Buy/Sell Ratio', ratio)
            symbol_df.insert(6, 'Avg Shares Bought', avg_purch)
            symbol_df.insert(7, 'Avg Shares Sold', avg_sale)
            
        symbol_df.set_index('Symbol', inplace=True)    
        all_df.append(symbol_df)
    
def excel(all_df):
    '''adds the data to excel sheet, data is saved in same floder as this file
    Parameter:    all_df: list
                       list of all the data frame
    Return:       None
    '''      
    try:
        if len(extract) != 0:
            pd.concat(all_df).to_excel(extract +'.xlsx', index = True)
            print(f"Extracted the data to {extract}.xlsx\n")
    except Exception as e: print(e)
     
     
if __name__ == '__main__':
    all_df = []
    data_df(all_df)
    excel(all_df)