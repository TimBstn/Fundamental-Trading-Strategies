# Fundamental-Trading-Strategies
This dash-app gives a brief overview over several trading strategies based on research papers. Analyzed are all companies that handed in their annual statement to the SEC. For every strategy the main findings and the investment strategy are explained as well as long and short positions based on that strategy.

- [Downloading the data](#downloading-the-data)
- [Editing the data](#editing-the-data)

## Downloading the data

All the data is public available at the [SEC website](https://www.sec.gov/dera/data/financial-statement-data-sets.html). Due to the size of these datasets it is not possible to upload that data to GitHub. The users is adviced to look into that data and download it hisself. Save the downloaded datasets into the data folder. Additionally, a mapping between cik number and company ticker should be [downloaded](https://www.sec.gov/file/company-tickers) and saved in the data folder.

## Editing the data

The data as it comes is not ready to be used in any trading strategy. Several changes and edits have to be made. The SEC database offers various parts of the financial and cashflow statements and balance sheet. The used items are declared on top of the code in the list *tags*. Additionally the last 16 quarters and the last full year have to be declared on top. The document includes two types of output: annual and querterly data. In both cases, the ticker data has do be loaded first.

### Creating ticker data

To map every cik to a company ticker later on, the ticker data has to be loaded. Download the data from that [link](https://www.sec.gov/file/company-tickers) and save into the data folder. Some companies like holdings have several tickers. To prevent doubling these datasets and loading the stock returns several times later on, the duplicates have to be dropped.

### Creating annual data

The data can be downloaded directely from the [SEC website](https://www.sec.gov/dera/data/financial-statement-data-sets.html). It is recommended to download the last 19 quarters. The code then reads in the *sub* and *num* files of each quarter. As mentioned before, a couple of changes have to be performed.

1) The sub file works as a mapping file. It includes information about the companies name, SIC-group, zip and so on. The form column gives information about the type of the statement the information is coming from. To get annual data, this columns has to be set to *10-K*.
