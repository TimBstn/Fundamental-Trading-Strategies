import pandas as pd
import numpy as np
import os
import yfinance as yf

# tags (part of statement to keep)
tags = ['AssetsCurrent', 'CashAndCashEquivalentsAtCarryingValue', 'LiabilitiesCurrent', 'Liabilities',
        'IncomeTaxesPaid', 'IncomeTaxesPaidNet', 'DepreciationDepletionAndAmortization',
        'OperatingIncomeLoss', 'Assets', 'StockholdersEquity', 'WeightedAverageNumberOfSharesOutstandingBasic',
        'NetCashProvidedByUsedInOperatingActivities', 'OtherLiabilitiesNoncurrent',
        'RevenueFromContractWithCustomerExcludingAssessedTax', 'CostOfGoodsAndServicesSold', 'CostOfRevenue',
        'EarningsPerShareBasic', 'Revenues', 'ResearchAndDevelopmentExpense', 'SellingGeneralAndAdministrativeExpense',
        'PaymentsToAcquirePropertyPlantAndEquipment']

# the quarters the final dataframe should contain
quarters = ['2017Q4', '2018Q1', '2018Q2', '2018Q3', '2018Q4', '2019Q1', '2019Q2', '2019Q3', '2019Q4',
            '2020Q1', '2020Q2', '2020Q3', '2020Q4', '2021Q1', '2021Q2', '2021Q3', '2021Q4']

# year of last annual statement
year = 2020


def create_quarterly_data(quarters, tags):
    """
    :param quarters: quarters for which financial statement should be considered
    :param tags: parts of financial statement which should be considered
    :return: returns quarterly data for all tags and quarters
    """
    # final DataFrame
    financial_statement = pd.DataFrame()

    # get ticker data
    ticker = pd.read_json('./data/ticker.txt').T
    # transform ticker
    ticker = ticker.drop(['title'], axis=1)
    ticker.columns = ['cik', 'ticker']
    ticker['cik'] = ticker['cik'].astype(str)
    # some cik's have more than one ticker
    ticker = ticker.drop_duplicates(subset='cik')

    # iterate though all the folders in data
    for folder in os.listdir('./data'):
        if folder.startswith("20"):
            print(folder)
            # import data
            sub = pd.read_csv(f"./data/{folder}/sub.txt", sep="\t", dtype={"cik": str})
            num = pd.read_csv(f"./data/{folder}/num.txt", sep="\t")

            # transform sub data
            # filter for needed columns
            cols = ['adsh', 'cik', 'name', 'sic', 'form', 'filed', 'period', 'accepted', 'fy', 'fp']
            sub = sub[cols]

            # change to datetype
            sub["accepted"] = pd.to_datetime(sub["accepted"])
            sub["period"] = pd.to_datetime(sub["period"], format="%Y%m%d")
            sub["filed"] = pd.to_datetime(sub["filed"], format="%Y%m%d")

            # filter for quarterly and annual financial data
            sub = sub[sub['form'].isin(['10-K', '10-Q'])]

            # delete duplicates --> company handed in same file in same period --> only keep newest
            sub = sub.loc[sub.sort_values(by=["filed", "accepted"], ascending=False).groupby(["cik", "period"]).cumcount() == 0]

            # drop not needed columns
            sub = sub.drop(['filed', 'period', 'accepted', 'fy', 'fp'], axis=1)

            # merge ticker and sub data
            sub = sub.merge(ticker)

            # transform num data
            # change to datetype
            num["ddate"] = pd.to_datetime(num["ddate"], format="%Y%m%d")

            # filter for needed columns
            cols_num = ['adsh', 'tag', 'ddate', 'qtrs', 'value']
            num = num[cols_num]

            # only select current date and quarter
            num = num.loc[
                num.sort_values(by=["ddate", "qtrs"], ascending=(False, True)).groupby(["adsh", "tag"]).cumcount() == 0]

            # create quarter and year column
            num['quarter'] = num['ddate'].dt.quarter
            num['year'] = num['ddate'].dt.year

            # merge num and sub data
            num = num.merge(sub)

            # append to financial statement
            financial_statement = financial_statement.append(num)

    # filter for needed tags
    financial_statement = financial_statement[financial_statement.loc[:, 'tag'].isin(tags)]
    financial_statement = financial_statement.sort_values(by='ddate')

    # create Q4 data
    for idx, row in financial_statement.iterrows():
        # when form is 10-K --> annual report --> change to quarterly
        if row['form'] == '10-K':
            # some companies only deliver full year numbers (qtrs = 4)
            if row['qtrs'] == 4:
                # filter for company and tag, select index of last 3 quarters
                idx_list = financial_statement[
                    (financial_statement.loc[:, 'ticker'] == row['ticker']) &
                    (financial_statement.loc[:, 'tag'] == row['tag'])].index.values.tolist()
                idx_position = idx_list.index(idx)
                idx_list = idx_list[idx_position - 3:idx_position]
                # subtract sum of all quarters from full year number
                financial_statement.at[idx, 'value'] = financial_statement.at[idx, 'value'] - \
                                                       financial_statement.loc[idx_list, 'value'].sum()

    # reset index
    financial_statement = financial_statement.reset_index()

    # only keep last 16 quarters
    financial_statement['year-quarter'] = financial_statement['year'].astype(str) + 'Q' + financial_statement['quarter'].astype(str)
    financial_statement = financial_statement.loc[financial_statement['year-quarter'].isin(quarters)]

    financial_statement = financial_statement.drop(['index', 'adsh', 'ddate', 'qtrs', 'form'], axis=1)
    # save as gzip file
    financial_statement.to_parquet('./data/financial_statements.parquet.gzip', compression='gzip')
    return financial_statement


def create_annual_data(tags):
    """
    :param tags: parts of financial statement which should be considered
    :return: returns annual data for all tags
    """

    # final DataFrame
    financial_statement = pd.DataFrame()

    # get ticker data
    ticker = pd.read_json('./data/ticker.txt').T
    # transform ticker
    ticker = ticker.drop(['title'], axis=1)
    ticker.columns = ['cik', 'ticker']
    ticker['cik'] = ticker['cik'].astype(str)
    # drop companies with several tickers
    ticker = ticker.drop_duplicates(subset='cik')

    # iterate though all the folders in data
    for folder in os.listdir('./data'):
        if folder.startswith("20"):
            print(folder)
            # import data
            sub = pd.read_csv(f"./data/{folder}/sub.txt", sep="\t", dtype={"cik": str})
            num = pd.read_csv(f"./data/{folder}/num.txt", sep="\t")

            # transform sub data
            # filter for needed columns
            cols = ['adsh', 'cik', 'name', 'sic', 'form', 'filed', 'period', 'accepted', 'fy', 'fp']
            sub = sub[cols]

            # change to datetype
            sub["accepted"] = pd.to_datetime(sub["accepted"])
            sub["period"] = pd.to_datetime(sub["period"], format="%Y%m%d")
            sub["filed"] = pd.to_datetime(sub["filed"], format="%Y%m%d")

            # filter for annual financial data
            sub = sub[sub['form'] == '10-K']

            # delete duplicates --> company handed in same file in same period --> only keep newest
            sub = sub.loc[sub.sort_values(by=["filed", "accepted"], ascending=False).groupby(["cik", "period"]).cumcount() == 0]

            # drop not needed columns
            sub = sub.drop(['filed', 'period', 'accepted', 'fy', 'fp'], axis=1)

            # merge ticker and sub data
            sub = sub.merge(ticker)

            # transform num data
            # change to datetype
            num["ddate"] = pd.to_datetime(num["ddate"], format="%Y%m%d")

            # filter for needed columns
            cols_num = ['tag', 'adsh', 'ddate', 'qtrs', 'value']
            num = num[cols_num]

            # only select current date and quarter
            num = num.loc[num.sort_values(by=["ddate", "qtrs"], ascending=False).groupby(["adsh", "tag"]).cumcount() == 0]

            # create year column
            num['year'] = num['ddate'].dt.year

            # merge num and sub data
            num = num.merge(sub)

            # append to financial statement
            financial_statement = financial_statement.append(num)

    # filter for needed tags
    financial_statement = financial_statement[financial_statement.loc[:, 'tag'].isin(tags)]
    financial_statement = financial_statement.sort_values(by='ddate')

    # only use firms with quarter 4 --> sign for full year
    #financial_statement = financial_statement[financial_statement.loc[:, 'qtrs'] == 4]

    # reset index
    financial_statement = financial_statement.reset_index()

    # drop not needed columns
    financial_statement = financial_statement.drop(['index', 'adsh', 'ddate', 'qtrs', 'form'], axis=1)

    # put tags into columns
    financial_statement = pd.pivot_table(financial_statement, values='value', columns=['tag'],
                                         index=['year', 'cik', 'name', 'sic', 'ticker']).reset_index()

    # some companies have 2 annual statements, for example after merger --> drop these
    financial_statement = financial_statement.drop_duplicates(subset=['cik', 'year'], keep=False)

    # income taxes replace NA's
    financial_statement['IncomeTaxesPaid'] = financial_statement['IncomeTaxesPaid'].fillna(financial_statement['IncomeTaxesPaidNet'])
    financial_statement = financial_statement.drop(['IncomeTaxesPaidNet'], axis=1)

    # save as gzip file
    financial_statement.to_parquet('./data/financial_statements_annual.parquet.gzip', compression='gzip')
    return financial_statement


def create_ticker(year):
    """
    :param year: year which should be considered
    :return: Take the annual statement data and extract the companies which handed in their annual report at the SEC
    """
    df = pd.read_parquet('./data/financial_statements_annual.parquet.gzip')
    df = df[['year', 'ticker']]
    df = df[df.loc[:, 'year'] == year]
    ticker = df['ticker'].tolist()
    return ticker


def get_stock_returns(year):
    """
    :param year: year which should be considered
    :return: for a given year, get the stock prices for the last 5 years for each company that handed in their
            annual data at the SEC
    """

    start_date = str(year-4) + '-01-01'
    ticker = create_ticker(year)

    df_prices = pd.DataFrame()

    # get price data for every stock
    for stock in ticker:
        print(stock)
        tick = yf.Ticker(stock)

        # get historical market data
        hist = tick.history(start=start_date)
        df_prices = df_prices.join(hist['Close'], how='outer', rsuffix=stock)

    df_prices.columns = ticker

    # in the case a price is missing for one stock, fill with NA
    df_prices[df_prices.loc[:, :] == ""] = np.nan

    df_prices.to_parquet('./data/stock_returns.parquet.gzip', compression='gzip')
    return df_prices


#create_annual_data(tags)
#get_stock_returns(year)
#create_quarterly_data(quarters, tags)
#df =pd.read_parquet('./data/financial_statements_annual.parquet.gzip')
#df.to_excel('annuals.xlsx')