import pandas as pd
import numpy as np
import yfinance as yf


def book_to_market():
    """
    Calculates the book to market ratio (shareholders equity/ market cap) for every company based on the latest
    stock price and annual financial statement.
    :return: DataFrame with ratio for each company.
    """

    # load data
    df_prices = pd.read_parquet('./data/stock_returns.parquet.gzip')
    df_financials = pd.read_parquet("./data/financial_statements_annual.parquet.gzip")

    # price data
    # only keep latest date
    df_prices = df_prices[-1:]

    # transpose and rename column and index
    df_prices = df_prices.T
    df_prices.index.name = 'Stock'
    df_prices.columns = ['stock_value']

    # financial data
    # only keep needed measures for the ratio
    df_financials = df_financials[['year', 'cik', 'ticker', 'StockholdersEquity',
                                   'WeightedAverageNumberOfSharesOutstandingBasic']]

    # only keep companies with at least 2 annual statements
    df_financials = df_financials.groupby('cik').filter(lambda x: len(x) > 2)

    # for every company keep the latest values
    df_financials = df_financials.sort_values('year', ascending=False).drop_duplicates('cik').sort_index()

    # only keep companies that filled all the needed tags
    df_financials = df_financials.dropna()

    # only keep companies that handed in their annual report in the last 2 years
    df_financials = df_financials[df_financials.loc[:, 'year'] >= df_financials['year'].max() - 1]

    # merge financial and stock return data
    df_financials = df_financials.merge(df_prices, left_on='ticker', right_index=True, how='left')
    df_financials = df_financials.dropna()

    # create book to market ratio
    df_financials['book_to_market'] = df_financials['StockholdersEquity'] / \
                                      (df_financials['WeightedAverageNumberOfSharesOutstandingBasic'] * df_financials[
                                          'stock_value'])
    df_financials.index = df_financials['ticker']
    df_financials.index.name = 'Stock'
    df_financials = df_financials[['book_to_market']]
    return df_financials


def f_score():
    """
    Creates the data for the F-Score strategy.
    Steps:
    1) Load financial data
    2) Get Book to Market ratio
    3) Only keep top 5 quantile of book to market companies
    4) Calculate Scores + final score
    5) Keep latest annual statement for each company
    6) Only keep companies that have at least 5 measures
    7) Create signal
    :return: DataFrame indicating which stocks to long and short
    """

    # load data
    df_financials = pd.read_parquet("./data/financial_statements_annual.parquet.gzip")

    # create book to market ratio
    btm = book_to_market()

    # keep top 5 quantile
    btm['quantile_rank'] = pd.qcut(btm['book_to_market'], 5, labels=False)
    btm = btm[btm.loc[:, 'quantile_rank'] == 4]

    # keep companies in top 5 quantile in financial DataFrame
    df_financials = df_financials.merge(btm, how='inner', left_on='ticker', right_index=True)

    # Get assets beginning of the year and avg last 2 years
    df_financials['assets_beginning'] = df_financials.groupby('cik', sort=False)['Assets'].apply(
        lambda x: (x.shift())).to_numpy()
    df_financials['assets_avg'] = df_financials.groupby('cik', sort=False)['Assets'].apply(
        lambda x: ((x+x.shift())/2)).to_numpy()
    # first year for every company --> keep assets of that year
    df_financials['assets_avg'] = df_financials['assets_avg'].fillna(df_financials['Assets'])

    # score 1 - RoA
    df_financials['RoA'] = df_financials['OperatingIncomeLoss']/df_financials['assets_beginning']
    df_financials['score_1'] = np.where(df_financials['RoA'] > 0, 1, 0)

    # score 2 - CFO
    df_financials['CFO'] = df_financials['NetCashProvidedByUsedInOperatingActivities']/df_financials['assets_beginning']
    df_financials['score_2'] = np.where(df_financials['CFO'] > 0, 1, 0)

    # score 3 - delta RoA
    df_financials['delta_RoA'] = df_financials.groupby('cik', sort=False)['RoA'].apply(
        lambda x: (x.shift())).to_numpy()
    df_financials['score_3'] = np.where(df_financials['delta_RoA'] > 0, 1, 0)

    # score 4 - Accruals
    df_financials['accrual'] = df_financials['RoA']-df_financials['CFO']
    df_financials['score_4'] = np.where(df_financials['accrual'] < 0, 1, 0)

    # score 5 - delta Leverage
    df_financials['noncurrent_liab'] = df_financials['Liabilities']-df_financials['LiabilitiesCurrent']
    df_financials['noncurrent_liab'] = df_financials['noncurrent_liab'].fillna(df_financials['OtherLiabilitiesNoncurrent'])
    df_financials['leverage'] = df_financials['noncurrent_liab']/df_financials['assets_avg']
    df_financials['delta_leverage'] = df_financials.groupby('cik', sort=False)['leverage'].apply(
        lambda x: (x-x.shift())).to_numpy()
    df_financials['score_5'] = np.where(df_financials['delta_leverage'] < 0, 1, 0)

    # score 6 - delta liquid
    df_financials['current_ratio'] = df_financials['AssetsCurrent']/df_financials['LiabilitiesCurrent']
    df_financials['delta_liquid'] = df_financials.groupby('cik', sort=False)['current_ratio'].apply(
        lambda x: (x-x.shift())).to_numpy()
    df_financials['score_6'] = np.where(df_financials['delta_liquid'] > 0, 1, 0)

    # score 7 - Equity-offer
    df_financials['delta_equity'] = df_financials.groupby('cik', sort=False)['WeightedAverageNumberOfSharesOutstandingBasic'].apply(
        lambda x: (x - x.shift())).to_numpy()
    df_financials['score_7'] = np.where(df_financials['delta_equity'] > 0, 0, 1)

    # score 8 - delta margin
    df_financials['Revenues'] = df_financials['Revenues'].fillna(df_financials['RevenueFromContractWithCustomerExcludingAssessedTax'])
    df_financials['gross_profit'] = df_financials['Revenues']-df_financials['CostOfGoodsAndServicesSold']
    df_financials['gross_profit'] = df_financials['gross_profit'].fillna(df_financials['Revenues']-df_financials['CostOfRevenue'])
    df_financials['gross_margin'] = df_financials['gross_profit']/df_financials['Revenues']
    df_financials['delta_gross_margin'] = df_financials.groupby('cik', sort=False)['gross_margin'].apply(
        lambda x: (x-x.shift())).to_numpy()
    df_financials['score_8'] = np.where(df_financials['delta_gross_margin'] > 0, 1, 0)

    # score 9 - delta turn
    df_financials['turnover_ratio'] = df_financials['Revenues'] / df_financials[
        'assets_beginning']
    df_financials['delta_turnover'] = df_financials.groupby('cik', sort=False)['turnover_ratio'].apply(
        lambda x: (x - x.shift())).to_numpy()
    df_financials['score_9'] = np.where(df_financials['delta_turnover'] > 0, 1, 0)

    # for every company keep the latest values
    df_financials = df_financials.sort_values('year', ascending=False).drop_duplicates('cik').sort_index()

    # count number of missing values and remove big numbers
    df_financials['missing_values'] = df_financials[['RoA', 'CFO', 'delta_RoA', 'accrual', 'delta_leverage',
                                                     'delta_liquid', 'delta_gross_margin', 'delta_turnover',
                                                     'delta_equity']].isnull().sum(axis=1)
    df_financials = df_financials[df_financials.loc[:, 'missing_values'] < 5]

    # final score
    df_financials['score'] = df_financials['score_1']+df_financials['score_2']+df_financials['score_3']+\
                             df_financials['score_4']+df_financials['score_5']+df_financials['score_6']+\
                             df_financials['score_7']+df_financials['score_8']+df_financials['score_9']

    # create signal
    df_financials['Signal'] = np.where(df_financials['score'] >= 7, 'Long',
                                       np.where(df_financials['score'] <= 2, 'Short', np.nan))
    df_financials = df_financials[df_financials.loc[:, 'Signal'].isin(['Long', 'Short'])]
    df_financials.index = df_financials['ticker']
    df_financials.index.name = 'Stock'
    df_financials = df_financials['Signal']

    df_financials.to_excel('./data/f_score.xlsx')
    return df_financials


def pead():
    """
    Creates the data for the Post Earnings Announcement Drift strategy
    Steps:
    1) Load SEC annual financial data and only keep companies which report EPS
    2) Only keep companies that have at least 3 annual statements
    3) Calculate the expected returns by taking the mean of the last 4 years
    4) For every company keep the latest annual statement and merge with expected value
    5) Calculate unexpected earnings
    6) Calculate standardized unexpected earnings
    7) Create ranking and signal
    :return: DataFrame indicating which stocks to long and short
    """
    # load data
    df = pd.read_parquet("./data/financial_statements_annual.parquet.gzip")

    # set stock as index
    df.index = df['ticker']
    df.index.name = 'Stock'

    # only keep needed columns
    df = df[['cik', 'year', 'ticker', 'EarningsPerShareBasic']]

    # get rid of companies without earnings per share
    df = df.dropna(subset=['EarningsPerShareBasic'])

    # only keep companies with at least 3 annual statements
    df = df.groupby('cik').filter(lambda x: len(x) > 3)

    # for every company get the previous 4 years mean and std
    df['count'] = df.groupby('cik').cumcount(ascending=False)
    last_4_df = df[(df.loc[:, 'count'] <= 4) & (df.loc[:, 'count'] > 0)]
    last_4_df = last_4_df.groupby('ticker')['EarningsPerShareBasic'].agg(['mean', 'std'])

    # for every company keep the latest values
    df = df.sort_values('year', ascending=False).drop_duplicates('cik').sort_index()

    # join average and DataFrame
    df = df.merge(last_4_df, left_index=True, right_index=True, how='left')

    # calculate unexpected earnings
    df['unexpected_earnings'] = df['EarningsPerShareBasic']-df['mean']

    # calculate standardized unexpected earnings
    df['sue'] = df['unexpected_earnings']/df['std']

    # create rank
    df['decile_rank'] = pd.qcut(df['sue'], 10, labels=False)

    # filter for winners and losers and rename
    df = df[df.loc[:, 'decile_rank'].isin([0, 9])]
    df['Signal'] = np.where(df['decile_rank'] == 0, 'Short', 'Long')
    df = df[['Signal']]
    df.index.name = 'Stock'
    df.to_excel('./data/pead.xlsx')
    return df


def momentum(lookback_period=12):
    """
    Creates the data for the momentum strategy.
    Steps:
    1) load stock price data
    2) create daily return
    3) calculate monthly return
    4) for strategy with lookback period = 12 only keep last 12 month
    5) Remove latest month
    6) calculate average return over last 12 month
    7) Create rank and keep first and last decile
    :param lookback_period: lookback period for momentum strategy
    :return: DataFrame indicating which stocks to long and short
    """

    # load data
    df = pd.read_parquet('./data/stock_returns.parquet.gzip')

    # drop columns with all #NA and last rows #NA --> not tradeable anymore
    df = df.dropna(axis=1, how='all')
    df = df.dropna(axis=1, subset=[df.index[-5]], how='all')

    # daily return
    df = df.pct_change()

    # monthly return
    df = df.resample('M').agg(lambda x: (x + 1).prod() - 1)

    # keep last 12 month
    df = df.tail(n=lookback_period)

    # remove last month
    df = df[:-1]

    # get average
    df = df.mean(axis=0).to_frame('avg_return')

    # create rank
    df['decile_rank'] = pd.qcut(df['avg_return'], 10, labels=False)

    # filter for winners and losers and rename
    df = df[df.loc[:, 'decile_rank'].isin([0, 9])]
    df['Signal'] = np.where(df['decile_rank'] == 0, 'Short', 'Long')
    df = df[['Signal']]
    df.index.name = 'Stock'
    df.to_excel('./data/momentum.xlsx')
    return df


def g_score():
    """
    Creates the data for the G-Score strategy
    Steps:
    1) Load annual SEC data
    2) Load book to market ratios and only keep lowest quantile
    3) Calculate scores
    4) Create 2-digit-SIC code
    5) Only keep industries with at least 4 companies in it
    6) Calculate final score
    7) Create signal
    :return: DataFrame indicating which stocks to long and short
    """

    # load data
    df = pd.read_parquet("./data/financial_statements_annual.parquet.gzip")

    # create book to market ratio
    btm = book_to_market()

    # keep last quantile
    btm['quantile_rank'] = pd.qcut(btm['book_to_market'], 5, labels=False)
    btm = btm[btm.loc[:, 'quantile_rank'] == 0]

    # keep companies in lowest quantile in financial DataFrame
    df = df.merge(btm, how='inner', left_on='ticker', right_index=True)

    # create sic 2 digit code
    df['sic'] = df['sic'].astype(int).astype(str)
    df['sic'] = df['sic'].apply(lambda x: '{0:0>4}'.format(x))
    df['sic_2_digits'] = df['sic'].str[:2]

    # calculate avg assets last two years
    df['assets_avg'] = df.groupby('cik', sort=False)['Assets'].apply(
        lambda x: ((x+x.shift())/2)).to_numpy()
    # first year for every company --> keep assets of that year
    df['assets_avg'] = df['assets_avg'].fillna(df['Assets'])

    # calculate avg assets last two years
    df['assets_begin'] = df.groupby('cik', sort=False)['Assets'].apply(
        lambda x: (x.shift())).to_numpy()

    # calculate RoA
    df['RoA'] = df['OperatingIncomeLoss']/df['assets_avg']

    # calculate RoA std per company
    df['RoA_var'] = df.groupby('cik')['RoA'].transform('std')

    # calculate CFO
    df['CFO'] = df['NetCashProvidedByUsedInOperatingActivities']/df['assets_avg']

    # calculate sales (revenue) growth per company
    df['Revenues'] = df['Revenues'].fillna(df['RevenueFromContractWithCustomerExcludingAssessedTax'])
    df['Sales_growth'] = df.groupby('cik')['Revenues'].pct_change()
    df['Sales_growth_var'] = df.groupby('cik')['Sales_growth'].transform('std')

    # for every company keep the latest values
    df = df.sort_values('year', ascending=False).drop_duplicates('cik').sort_index()

    # only keep industries with at least 4 companies
    df = df.groupby('sic_2_digits').filter(lambda x: len(x) > 4)

    # score 1 - RoA
    df['RoA_median_industry'] = df.groupby('sic_2_digits')['RoA'].transform('median')
    df['score_1'] = np.where(df['RoA'] > df['RoA_median_industry'], 1, 0)

    # score 2 - CFO
    df['CFO_median_industry'] = df.groupby('sic_2_digits')['CFO'].transform('median')
    df['score_2'] = np.where(df['CFO'] > df['CFO_median_industry'], 1, 0)

    # score 3 - Accruals
    df['accrual'] = df['RoA']-df['CFO']
    df['score_3'] = np.where(df['CFO'] > df['RoA'], 1, 0)

    # score 4 - Variance RoA
    df['RoA_std_median_industry'] = df.groupby('sic_2_digits')['RoA_var'].transform('median')
    df['score_4'] = np.where(df['RoA_var'] < df['RoA_std_median_industry'], 1, 0)

    # score 5 - Variance Sales Growth
    df['Sales_growth_var_industry'] = df.groupby('sic_2_digits')['Sales_growth_var'].transform('median')
    df['score_5'] = np.where(df['Sales_growth_var'] < df['Sales_growth_var_industry'], 1, 0)

    # score 6 - R&D intensity
    df['RaD_intensity'] = df['ResearchAndDevelopmentExpense']/df['assets_begin']
    df['RaD_median_industry'] = df.groupby('sic_2_digits')['RaD_intensity'].transform('median')
    df['score_6'] = np.where(df['RaD_intensity'] > df['RaD_median_industry'], 1, 0)

    # score 7 - capital expenditure intensity
    df['capex'] = df['PaymentsToAcquirePropertyPlantAndEquipment']/df['assets_begin']
    df['capex_median_industry'] = df.groupby('sic_2_digits')['capex'].transform('median')
    df['score_7'] = np.where(df['capex'] > df['capex_median_industry'], 1, 0)

    # score 8 - advertising expense intensity
    df['ads'] = df['SellingGeneralAndAdministrativeExpense']/df['assets_begin']
    df['ads_median_industry'] = df.groupby('sic_2_digits')['ads'].transform('median')
    df['score_8'] = np.where(df['ads'] > df['ads_median_industry'], 1, 0)

    # count number of missing values and remove big numbers
    df['missing_values'] = df[['RoA', 'CFO', 'accrual', 'RoA_var', 'Sales_growth_var',
                               'RaD_intensity', 'capex', 'ads']].isnull().sum(axis=1)
    df = df[df.loc[:, 'missing_values'] < 4]

    # final score
    df['score'] = df['score_1']+df['score_2']+df['score_3']+df['score_4']+df['score_5']+df['score_6']+\
                  df['score_7']+df['score_8']

    # create signal
    df['Signal'] = np.where(df['score'] >= 6, 'Long', np.where(df['score'] <= 2, 'Short', np.nan))
    df = df[df.loc[:, 'Signal'].isin(['Long', 'Short'])]
    df.index = df['ticker']
    df.index.name = 'Stock'
    df = df['Signal']

    df.to_excel('./data/g_score.xlsx')
    return df


def accrual_anatomy():
    """
    Creates the data for the accrual anatomy strategy
    Steps:
    1) load annual financial statement data
    2) Create delta columns
    3) Create average assets column
    4) For every company keep the latest statement
    5) Only keep companies with latest statements in the last 2 years
    6) Only keep companies that filled in all the needed tags
    7) Calculate accruals
    8) Calculate income rate, cash rate, accrual rate
    9) Create Signal based on cash component
    :return: DataFrame indicating which stocks to long and short
    """

    # load data
    df = pd.read_parquet("./data/financial_statements_annual.parquet.gzip")

    # create delta columns
    df = df.sort_values(['year', 'cik']).reset_index(drop=True)
    df['Delta_Assets'] = df.groupby('cik', sort=False)['AssetsCurrent'].apply(
        lambda x: x - x.shift()).to_numpy()
    df['Delta_Cash'] = df.groupby('cik', sort=False)['CashAndCashEquivalentsAtCarryingValue'].apply(
        lambda x: x - x.shift()).to_numpy()
    df['Delta_Liab'] = df.groupby('cik', sort=False)['LiabilitiesCurrent'].apply(
        lambda x: x - x.shift()).to_numpy()
    df['Delta_Taxes'] = df.groupby('cik', sort=False)['IncomeTaxesPaid'].apply(
        lambda x: x - x.shift()).to_numpy()

    # Create assets AVG column
    df['AVG_Assets'] = df.groupby('cik', sort=False)['Assets'].apply(
        lambda x: (x + x.shift()) / 2).to_numpy()

    # keep needed columns
    df = df[['year', 'cik', 'name', 'ticker', 'Delta_Assets', 'Delta_Cash', 'Delta_Liab', 'Delta_Taxes',
             'DepreciationDepletionAndAmortization', 'AVG_Assets', 'OperatingIncomeLoss']]

    # for every company keep the latest values
    df = df.sort_values('year', ascending=False).drop_duplicates('cik').sort_index()

    # only keep companies that filled all the needed tags
    df = df.dropna()

    # only keep companies that handed in their annual report in the last 2 years
    df = df[df.loc[:, 'year'] >= df['year'].max() - 1]

    # calculate accrual
    df['Accrual'] = df['Delta_Assets'] - df['Delta_Cash'] - (df['Delta_Liab'] - df['Delta_Taxes']) - \
                    df['DepreciationDepletionAndAmortization']
    df['Income_Rate'] = df['OperatingIncomeLoss'] / df['AVG_Assets']
    df['Accrual_Component'] = df['Accrual'] / df['AVG_Assets']
    df['Cash_Component'] = df['Income_Rate'] - df['Accrual_Component']

    # create rank
    df['decile_rank'] = pd.qcut(df['Cash_Component'], 10, labels=False)

    # filter for winners and losers and rename
    df = df[df.loc[:, 'decile_rank'].isin([0, 9])]
    df['Signal'] = np.where(df['decile_rank'] == 0, 'Short', 'Long')
    df.index = df['ticker']
    df = df[['Signal']]
    df.index.name = 'Stock'
    df.to_excel('./data/accruals.xlsx')
    return df


def betting_against_beta(start_date):
    """
    Creates the data for the betting against beta strategy.
    Steps:
    1) Load the Wilshere 5000 data as market index and calculate return
    2) Load stock data and calculate return
    3) Calculate beta by dividing covariance from stock and market by variance from market
    4) Create long and short signals: long --> stock over median, short --> stock under median
    :param start_date: Date to pull Wilshere 5000 data from
    :return: DataFrame indicating which stocks to long and short
    """

    # market data
    tick = yf.Ticker('^W5000')
    wilshere5000 = tick.history(start=start_date)
    wilshere5000 = wilshere5000.pct_change()
    var_market = wilshere5000['Close'].var()

    # load data
    df = pd.read_parquet('./data/stock_returns.parquet.gzip')

    # drop columns with all #NA and last rows #NA --> not tradeable anymore
    df = df.dropna(axis=1, how='all')
    df = df.dropna(axis=1, subset=[df.index[-5]], how='all')

    # daily return
    df = df.pct_change()

    # calculate beta for each stock
    beta = pd.Series({symbol: wilshere5000['Close'].cov(df[symbol]) for symbol in df}) / var_market
    beta = beta.to_frame('beta')

    # create signal
    median = beta['beta'].median()
    beta['Signal'] = np.where(beta['beta'] >= median, 'Short', 'Long')
    beta = beta[['Signal']]
    beta.index.name = 'Stock'
    beta.to_excel('./data/beta.xlsx')
    return beta


def equity_pairs():
    """
    Creates the data for the equity pairs strategy.
    Steps:
    1) load stock price data
    2) create daily return
    3) calculate monthly return
    4) Calculate the correlation between the stocks and keep top 50 for every stock
    5) Calculate expected return by taking average return of 50 stocks with highest correlation
    6) Take the difference between actual and expected return for every stock
    7) Create decile and short biggest positive difference and long biggest negative difference
    :return: DataFrame indicating which stocks to long and short
    """
    # load data
    df = pd.read_parquet('./data/stock_returns.parquet.gzip')

    # drop columns with all #NA and last rows #NA --> not tradeable anymore
    df = df.dropna(axis=1, how='all')
    df = df.dropna(axis=1, subset=[df.index[-5]], how='all')

    # daily return
    df = df.pct_change()

    # monthly return
    df = df.resample('M').agg(lambda x: (x + 1).prod() - 1)

    # calculate correlation
    corr = df.corr()
    corr = corr.unstack().reset_index()
    corr.columns = ['stock1', 'stock2', 'correlation']
    # delete correlation from stock with itself
    corr = corr[corr['stock1'] != corr['stock2']]
    # only keep top 50
    corr['rank'] = corr.groupby(['stock1'])['correlation'].rank(ascending=False)
    corr = corr[corr.loc[:, 'rank'] <= 50]

    # drop last month
    df = df[:-1]

    # keep last full month
    last_month = df.tail(n=1).T
    last_month.columns = ['exp_return']
    last_month.index.name = 'stock'

    # merge correlation with last month and calculate average return
    corr = corr.merge(last_month, left_on='stock2', right_index=True, how='left')
    corr = corr.groupby(['stock1'])['exp_return'].mean().to_frame()

    # merge actual return last month and calculate difference
    last_month.columns = ['actual_return']
    corr = corr.merge(last_month, left_on='stock1', right_index=True, how='left')
    corr['difference'] = corr['actual_return'] - corr['exp_return']
    corr['decile_rank'] = pd.qcut(corr['difference'], 10, labels=False)

    # filter for winners and short and long
    corr = corr[corr.loc[:, 'decile_rank'].isin([0, 9])]
    corr['Signal'] = np.where(corr['decile_rank'] == 0, 'Long', 'Short')
    corr = corr[['Signal']]
    corr.index.name = 'Stock'
    corr.to_excel('./data/equity_pairs.xlsx')
    return corr


f_score()
pead()
momentum()
g_score()
accrual_anatomy()
betting_against_beta('2015-01-01')
equity_pairs()



