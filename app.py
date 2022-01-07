# standard libraries
import pandas as pd

# dash and plotly
import dash
from dash import dcc
from dash import html
from dash.dependencies import State, Input, Output
import dash_bootstrap_components as dbc
from dash import dash_table


# css for pictograms
FONT_AWESOME = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css"

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, FONT_AWESOME],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
    ],
)

app.title = "Research based Stock Trading Strategies"

# This is for gunicorn
server = app.server

# Side panel

# side panel header
portfolio_dropdown_text = html.P(
    id="header-strategy",
    children=["Trading", html.Br(), " Strategy"],
)

# button group for trading strategies

button_group = html.Div(
    [
        dbc.RadioItems(
            id="radios",
            inputClassName="btn-check",
            labelClassName="btn btn-outline-primary",
            labelCheckedClassName="active",
            options=[
                {"label": "Piotroski F-Score", "value": 'f_score'},
                {"label": "PEAD", "value": 'pead'},
                {"label": "Momentum", "value": 'momentum'},
                {"label": "G-Score", "value": 'g_score'},
                {"label": "Accruals Anatomy", "value": 'accruals'},
                {"label": "Betting against Beta", "value": 'beta'},
                {"label": "Equity Pairs", "value": 'pairs'},
            ],
            value='f_score',
        ),
        html.Div(id="output"),
    ],
    className="radio-group",
)

info = html.Div(
    id='info',
    children=[
        dcc.Markdown(
            "All strategies are performed on companies based in the US handing in annual data to the [SEC](https://www.sec.gov/dera/data/financial-statement-data-sets.html)."
        )
    ]
)

# bringing the side panel together
side_panel_layout = html.Div(
    id="panel-side",
    children=[
        portfolio_dropdown_text,
        button_group,
        info,
    ],
)

# main panel

explanation = html.Div(
    children=[
        dcc.Markdown(
            children="",
            id='explanation-text'
        )
    ],
    className="six columns",
    id='explanation',
)

stocks_header = html.Div(
    dcc.Markdown(
        "# Investments"
    ),
    id='stocks-header'
)

long_header = html.Div(
    dcc.Markdown(
        "Long"
    ),
    id='long-header'
)

long_stocks = html.Div(
    id='long-stocks',
    style={
        'margin-top': '-30px'
    }
)

short_header = html.Div(
    dcc.Markdown(
        "Short"
    ),
    id='short-header'
)

short_stocks = html.Div(
    id='short-stocks',
    style={
        'margin-top': '-30px'
    }
)

long_short = html.Div(
    [
        stocks_header,
        long_header,
        long_stocks,
        short_header,
        short_stocks
    ],
    className="six columns",
    id='long-short',
)

book = html.Div([
    explanation,
    long_short
],
    className='row',
    id='book-text'
)

# bringing the main panel together
main_panel_layout = html.Div(
    id="panel-upper-lower",
    style={
        'background-image': 'url("assets/book2.png")',
        'background-repeat': 'no-repeat',
        'background-position': 'center',
        'background-size': '90%'

    },
    children=[
        book
    ],
)

# bringing everything together, creating store-divs for used data
root_layout = html.Div(
    id="root",
    children=[
        dcc.Store(
            id="store-data",
            data={}
        ),
        dcc.Store(
            id="store-backtests-stats",
            data={}
        ),
        dcc.Store(
            id="store-backtests-prices",
            data={}
        ),
        dcc.Store(
            id="store-backtests-weights",
            data={}
        ),
        side_panel_layout,
        main_panel_layout,
    ],
)

# creating the app
app.layout = root_layout


def create_signal_df(df, signal):
    """
    :param signal: Long or Short Signal
    :return: Returns a DataFrame with all the stocks that have the given signal in df.
    """

    # filter for signal
    df = df[df.loc[:, 'Signal'] == signal]

    # cut into 4 columns
    df['Header'] = pd.qcut(df.index, 8, labels=False)

    # create DataFrame with these 4 columns
    list_dict = {}
    for i in range(8):
        list_nr = df.loc[:, 'Stock'][df.loc[:, 'Header'] == i].to_list()
        list_dict[i] = list_nr
    df_signal = pd.DataFrame.from_dict(list_dict, orient='index').T
    return df_signal


# Callbacks
@app.callback(
    [
        Output('explanation-text', 'children'),
        Output('long-stocks', 'children'),
        Output('short-stocks', 'children')
    ],
    [
        Input('radios', 'value')
    ]

)
def create_explanation(strategy):
    """
    :return: starting with clicking the Calculate button, the function returns the price data for the selected stocks
    and saves it into the price-store
    """

    long_df = pd.DataFrame()
    short_df = pd.DataFrame()
    if strategy == "f_score":
        text = """
# Description Strategy

## Hypothesis
- Market does not fully incorporate historical financial information into prices in a timely manner
- Average high book to market firms (value stocks) are financially distressed resulting in declining margins, profits, cash flows
- Financial variables that reflect changes in these economic conditions should be useful in predicting future firm performance
- Annual plus in return of 7.5%  by picking these companies
- Combining with short strategy: 23%  annual return between 1976 and 1996

## Strategy
- Trade on high book to market companies (top 5 quantile) 
- Create score based on profitability, capital structure and and efficiency measures
- Long companies with high score, short companies with low score

## More Information
- [Go to the research paper](https://www.ivey.uwo.ca/media/3775523/value_investing_the_use_of_historical_financial_statement_information.pdf)
        """

        df = pd.read_excel('./data/f_score.xlsx')
        long_df = create_signal_df(df, 'Long')
        short_df = create_signal_df(df, 'Short')

    elif strategy == "pead":
        text = """
# Description Strategy

## Hypothesis
- The predictability of abnormal returns based on information contained in past earnings announcements is a statistically and economically significant anomaly
- Stock prices do not instantaneously adjust to information in earnings announcements
- The investor irrationality and information processing cost explanations imply that the market’s earnings expectations differ from the true process generating earnings, thus creating a direct link between estimated unexpected earnings and future abnormal returns
- The return to an equally weighted portfolio consisting of long positions in extreme good news announcers and short positions in extreme bad news announcers earns +4.19% average estimated abnormal return over the 60- day post-announcement period

## Strategy
- Calculate Standardized Unexpected Earnings (SUE) 
- Go long on top decile and short on worst decile 


## More Information
- [Go to the research paper](https://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.52.7343&rep=rep1&type=pdf)
        """

        df = pd.read_excel('./data/pead.xlsx')
        long_df = create_signal_df(df, 'Long')
        short_df = create_signal_df(df, 'Short')

    elif strategy == "momentum":
        text = """
# Description Strategy

## Hypothesis
- Momentum is the total return of a stock (including dividends) over the last n month
- There is a tendency of rising stock prices to rise further and falling stock prices to fall further
- Investors underreact to information and overreact to past information with a delay, perhaps due to positive feedback trading
- The returns of a zero cost portfolio (long past winners and short losers) made money in every five year period since 1940

## Strategy
- Run the intermediate momentum strategy: lookback period between 3 and 12 month
- Here: n = 12 month and hold for 3 month
- Long the top decile and short the worst decile in that period

## More Information
- [Go to the research paper](https://deliverypdf.ssrn.com/delivery.php?ID=632004121085073100115087024069069031054009008003061029091074107104122068026117034014017031032084099086006072121009072074002043069108113001082103007103097103040012040090008029082064089105070065087095095103005064114090110124082012067029088105069&EXT=pdf&INDEX=TRUE)
        """

        df = pd.read_excel('./data/momentum.xlsx')
        long_df = create_signal_df(df, 'Long')
        short_df = create_signal_df(df, 'Short')

    elif strategy == "g_score":
        text = """
# Description Strategy

## Hypothesis
- Strong firms are more likely to beat earnings forecasts and earn positive abnormal returns around future earnings announcements
- The market ignores the implications of growth fundamentals for future performance
- The stock market is unable to draw the correlation between current growth fundamentals and future fundamentals

## Strategy
- Trade on low book to market firms (growth stocks)
- Create score based on profitability, variability of performance and spending intensity measures
- Compare to companies in the same industry
- Long companies with high score compared to industry, short companies with low score

## More Information
- [Go to the research paper](https://deliverypdf.ssrn.com/delivery.php?ID=450091020087106088092064079103099112059038009000020002096087018066103080094006116027119013052038049022008091078116124006117126036087003041008089004118122018124005002064071001122012092112096095080085091087000100005007018079108110012103087093001101&EXT=pdf&INDEX=TRUE)
            """

        df = pd.read_excel('./data/g_score.xlsx')
        long_df = create_signal_df(df, 'Long')
        short_df = create_signal_df(df, 'Short')

    elif strategy == "accruals":
        text = """
# Description Strategy

## Hypothesis
- Stock prices act as if investors fixate on earnings
- Investors fail to reflect fully information contained in the accrual and cash flow components of current earnings
- They first realize when this split impacts future earnings
- Earnings attributable to the accrual component of the earnings exhibits lower persistence than earnings attributable to cash flow
- Firms with relatively high (low) levels of accruals experience negative (positive) future abnormal returns 

## Strategy
- Go long where the positive earnings surprise is driven by cash
- Go short where the positive earnings surprise is driven by accruals
- Rank companies based on accruals to assets component and categorize into deciles
- Short the first and long the last decile
 
## More Information
- [Go to the research paper](https://www.wm.edu/offices/auxiliary/osher/course-info/classnotes/shanesloan1996tar1.pdf)
        """

        df = pd.read_excel('./data/accruals.xlsx')
        long_df = create_signal_df(df, 'Long')
        short_df = create_signal_df(df, 'Short')

    elif strategy == "beta":
        text = """
# Description Strategy

## Hypothesis
- Sensitivity of each company to the systematic risk (market risk) is known as beta
- Companies with high beta are known as aggressive (growth stocks)
- Companies with low beta are known as defensive (low growth stocks)
- Alphas and sharpe ratios are monotonically declining in beta in each asset class
- Risky high-beta assets require lower risk-adjusted returns than low-beta assets, which require leverage

## Strategy
- Long low beta stocks (under median), short high beta stocks (above median)
- Rebalance every month



## More Information
- [Go to the research paper](https://pages.stern.nyu.edu/~lpederse/papers/BettingAgainstBeta.pdf)
        """

        df = pd.read_excel('./data/beta.xlsx')
        long_df = create_signal_df(df, 'Long')
        short_df = create_signal_df(df, 'Short')

    elif strategy == "pairs":
        text = """
# Description Strategy

## Hypothesis
- The trader profits from the correction of the divergence between two similar stocks
- Historical return correlations between pairs can lead to future information on the stocks performance
- When a firm and its peer deviate in stock prices, there is likely news related to the fundamentals of the pair and it takes time for the news to disseminate to the pair

## Strategy
- Identify pairs, which are trading instruments that show high correlations, i.e., the price of one moves in the same direction as the other
- Look for divergence in prices between a pair 
- When a divergence is noticed, take the opposite positions for instruments in a pair
- Therefore, traders take long positions for underperforming stocks and short positions for overperforming stocks


## More Information
- [Go to the research paper](http://www.pbcsf.tsinghua.edu.cn/research/chenzhuo/paper/1.3.Empirical%20Investigation%20of%20an%20Equity%20Pairs%20Trading%20Strategy.pdf)
        """

        df = pd.read_excel('./data/equity_pairs.xlsx')
        long_df = create_signal_df(df, 'Long')
        short_df = create_signal_df(df, 'Short')
    else:
        text = 'error'
        long_df = pd.DataFrame()
        short_df = pd.DataFrame()

    long = dash_table.DataTable(
        id='table_long',
        columns=[{"name": '', "id": i} for i in long_df.columns],
        data=long_df.to_dict('records'),
        style_table={'width': '100%',
                     'height': '250px',
                     'overflow': 'scroll',
                     'padding': '0px 10px 0px 00px',
                     },
        style_header={'display': 'none'},
        style_data={'border': 'none'},
        style_cell={'background-color': 'transparent'},
        page_size=1000
    )

    short = dash_table.DataTable(
        id='table_long',
        columns=[{"name": '', "id": i} for i in short_df.columns],
        data=short_df.to_dict('records'),
        style_table={'width': '100%',
                     'height': '250px',
                     'overflow': 'scroll',
                     'padding': '0px 10px 0px 00px',
                     'paging': False
                     },
        style_header={'display': 'none'},
        style_data={'border': 'none'},
        style_cell={'background-color': 'transparent'},
        page_size=1000
    )
    return [text, long, short]


if __name__ == "__main__":
    app.run_server(debug=False)
app.scripts.config.serve_locally = True
