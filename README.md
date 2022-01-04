# Fundamental-Trading-Strategies
This dash-app gives a brief overview over several trading strategies based on research papers. Analyzed are all companies that handed in their annual statement to the SEC. For every strategy the main findings and the investment strategy are explained as well as long and short positions based on that strategy.

- [Downloading the data](#downloading-the-data)
- [Editing the data](#editing-the-data)
- [Strategies](#strategies)
- [Requirements](#requirements)

## Downloading the data

All the data is public available at the [SEC website](https://www.sec.gov/dera/data/financial-statement-data-sets.html). Due to the size of these datasets it is not possible to upload that data to GitHub. The users is adviced to look into that data and download it hisself. Save the downloaded datasets into the data folder. Additionally, a mapping between cik number and company ticker should be [downloaded](https://www.sec.gov/file/company-tickers) and saved in the data folder.

## Editing the data

The data as it comes is not ready to be used in any trading strategy. Several changes and edits have to be made. The SEC database offers various parts of the financial and cashflow statements and balance sheet. The used items are declared on top of the code in the list *tags*. Additionally the last 16 quarters and the last full year have to be declared on top. The document includes two types of output: annual and querterly data. In both cases, the ticker data has do be loaded first.

### Creating ticker data

To map every cik to a company ticker later on, the ticker data has to be loaded. Download the data from that [link](https://www.sec.gov/file/company-tickers) and save into the data folder. Some companies like holdings have several tickers. To prevent doubling these datasets and loading the stock returns several times later on, the duplicates have to be dropped.

### Creating annual data

The data can be downloaded directely from the [SEC website](https://www.sec.gov/dera/data/financial-statement-data-sets.html). It is recommended to download the last 19 quarters. The code then reads in the *sub* and *num* files of each quarter. As mentioned before, a couple of changes and steps have to be performed.

1) The sub file works as a mapping file. It includes information about the companies name, SIC-group, zip and so on. The form column gives information about the type of the statement the information is coming from. To get annual data, this columns has to be set to *10-K*. The column *adsh* includes a code connecting the *num* and *sub* files. It contains unique information about the company and form  (p.e. every company in every year has an unique code).
2) Exploring the data, some inconveniences can be found. Normally, every company should only hand in one annual statement per year. Analyzing the data it can be found that some companies handed in their 10-K file more often. to avoid duplicates, you should only keep the newest version based on the columns filed and accepted.
3) On the cik code map the company ticker.
4) The next step is editting the *num* file. The *num* file includes the actual values of the statements and the *tag* column gives information about the part of the statement. Depending on the quarter, the file also gives information about the last year and last quarters value. These information are not wanted and therefor have to be dropped. We achieve that by grouping the data on the *adsh* and *tag* columns and only keeping the latest date. 
5) Merge *num* and *sub* files on the *adsh* column to get whole database for that year.
7) Lastly, some companies (based on the cik) have more than one annual statement (p.e. after a merger). As there is no way to conclude which statement is the actual statement of the mother company, both statements are dropped.
8) Create a database with all the tags in the columns by pivoting the column *tag*.
9) Due to the size of the final annual database it has to be saved as a gzip file.

### Creating quarterly data
The same steps as mentioned aboved for the annual data have to be performed. Additionally, the following changes have to be made: \
Step 1: Instead of only loading *10-K* data, *10-Q* data also have to be included.\
Step 5: \
Step 8: The *num* file does not contain information about Q4 for some companies (p.e. see Facebook), instead it only gives the full year value in that quarter. Therefore, the Q4 value has to be calculated manually. To do so, the values from Q1 to Q3 have to be substracted from the full year value.

### Creating stock returns
For strategies like Momentum the stock return for each company is needed. For doing so we load the annual statement data and extract all companies that handed in an annual report for the last year. For all of these companies the stock returns are downloaded from yahoo finance and saved into a DataFrame.

## Strategies
Seven different strategies are introduced in the app. All of them are based on research papers and have proven to generate profits in the past. 

### Piotroski's F-Score
This strategy trades on high book to market companies and creates a score based on profitability, capital structure and efficiency measures. Companies with a high score get a long position, low scores are shorted. Perform the followin steps:
1) Load the annual SEC financial data.
2) Create the book to market ratio and only keep the top 5 quantile. The book to market ratio is calculated by shareholder's (stockholder's) equity / market capitalization, where market cap = stock price \* number shares outstanding. Only companies that handed in all these information can be included (approx. 3000). Additionally, I only kept companies that handed in at least annual statements, as many of the following measures include comparisons to the previous year. To create the ratio, the financial and stock price databases are merged. Some of the 3000 companies do not have a Yahoo Finance stock price and therefore cannot be used (the number of companies now is approx. 2750). Taking the top 5 quantile leaves us with 500 companies. 

### Momentum
This strategy is based on past stock returns of the companies. It goes long on companies which performed good in the past and shorts companies with bad performance in the past. After loading the data, the following steps have to be performed:
1) Yahoo Finance offers the daily close price. In order to make the strategy work, the prices have to be chanaged to daily returns.
2) Out of the daily returns calculate the monthly return.
3) We chose a 12 month lookback period, which means the last 12 month create the momentum signal. It has been showed that the period should be inbetween 3 and 12 month.
4) The paper indicates that the intermediate-term momentum works best, when the dataset is unbiased from recent returns. Therefore remove the latest month
5) To decide which companies to long and short, we are ranking the companies based on the average monthly return in the last 12 month. We go long in the best decile and short the worst decile.

### Accruals Anatomy
This strategy compares the quality of the earnings for each company. If the earnings are driven by accruals, go short, if they are driven by cash, go long. The accruals are calculated as followed:
<img src="img/accruals.png?raw=true"/>
Unfortunately, the SEC has no equivalent to the STD column and therefore it was ignored (if you found one, please let me know). The following steps are performed:
1) Load the annual financial SEC database.
2) Create the delta columns for assets, liabilities, cash and taxes.
3) For every company keep the latest statement. That statement should be handed in in the last two years, else the company is ignored.
4) Only keep companies that filled in all the needed tags from above. That brings it down to approx. 1400 companies.
5) Calculate the accruals with the formular given above.
6) Calculate income rate (Operating Income/ Average Total Assets last two years), accrual component (Accrual/ Avg Assets) and cash component (income rate-accrual component)
7) Create Signal based on cash component. Long the top 10 stocks and short the worst 10 stops.

### Betting against Beta
This strategy shorts companies with betas over the median beta and longs companies below the median. 
Steps:
1) To calculate the beta of a stock, a market return is needed. I chose the Wilshere 5000 (Yahoo Finance: ^W5000) as it covers most of the American market. 
2) Load and calculate the stock return for each company.
3) Calculate the beta for each company by dividing the covariance of the stock with the market by the markets variance ([see here for more information on beta](https://www.investopedia.com/terms/b/beta.asp)).
4) Create the long and short signals explained above.

### Equity Pairs
This strategy takes the stock returns of the companies and finds the most correlated companies to each stock. Following the hypothesis that correlated stocks should have similar returns, it goes long on stocks that underperformed the 50 most correlated companies and shorts stocks that overperformed. A correction of the divergence is assumed. The following steps are needed:
1) Load stock data from Yahoo Finance and calculate monthly returns.
2) Calculate the correlation between the returns and for each company select the 50 most correlated companies.
3) Calculate the expected return for the last month for each stock by taking the average of the return of the 50 companies from step 2)
4) Calculate the difference between the actual return and expected return.
5) Create deciles based on the difference. Long the underperforming stocks, which means the worst decile and short the best decile. 

## Requirements

```
pip install -r requirements.txt

```
