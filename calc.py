import os
import pandas as pd
from pandas import DataFrame
from datetime import datetime, timedelta, date
from sqlalchemy import create_engine, select, MetaData, Table, func, and_, update


class CalcService:
    def __init__(self):
        self.config = get_config()
        self.engine_pbactual = self.config['DB_PBACTUAL']
        self.engine_replica = self.config['DB_MARGIN_REPLICA']
        self.books = self.get_all_books()

    @property
    def tn2(self):
        return self.get_last_businessdate(self.get_last_businessdate(date.today()))

    def get_fx(self, ccy, date):
        '''
            return the ccy/USD rate
            return all pairs if ccy = 'all'
        '''
        fx = self.matador_api.get_fx_rates(date).rjson()
        if ccy == 'all':
            return fx
        elif ccy == 'USD':
            return 1
        else:
            return [r['rate'] for r in fx if r['pair'] == f'{ccy}/USD'][0]

    def get_last_businessdate(self, day):
        if day.weekday() == 0:
            last_businessdate = day - timedelta(days=3)
        else:
            last_businessdate = day - timedelta(days=1)
        return last_businessdate

    def get_all_books(self):
        books_list = pd.read_sql_query(f"select distinct book from margin_replica_adjusted",
                                       con=self.engine_replica)['book'].sort_values().to_list()
        return [{'label': book, 'value': book} for book in books_list]

    def get_book_hist(self, book):
        sql = f"select * from margin_replica_adjusted where book='{book}'"
        df = pd.read_sql_query(sql, con=self.engine_replica)
        df['margin'] = df['margin'] + df['adjustment']
        df = df[['businessdate', 'margin', 'gmv']].groupby(by=['businessdate'], as_index=False).sum()
        df['margin rate'] = df['margin'] / df['gmv']
        df.drop(df.tail(1).index, inplace=True)
        return df[['businessdate', 'margin rate']]

    def reporting(self, businessdate, ccy='GBP'):
        fx = self.get_fx(ccy, businessdate)
        df = pd.read_sql_query(
            f"select * from margin_replica_adjusted where businessdate='{businessdate}'", con=self.engine_replica)

        df['margin_adjusted'] = df['margin'] + df['adjustment']
        df_books = pd.pivot_table(df[['book', 'margin_adjusted', 'pb']],
                                  values='margin_adjusted', columns='pb', index='book').fillna(0)
        df_books = df_books.reset_index(drop=False)
        df_books.columns.name = None
        df_books['Total Margin'] = df_books['GS'] + df_books['JPM'] + df_books['NOMURA'] + df_books['ABN']

        df_gmv = pd.pivot_table(df[['book', 'gmv', 'pb']], values='gmv', columns='pb', index='book').fillna(0)
        df_gmv = df_gmv.reset_index(drop=False)
        df_gmv.columns.name = None
        df_gmv['Total GMV'] = df_gmv['GS'] + df_gmv['JPM'] + df_gmv['NOMURA'] + df_gmv['ABN']

        df_all = pd.merge(df_books, df_gmv[['book', 'Total GMV']], on='book')
        df_all['Margin Rate'] = df_all['Total Margin'] / df_all['Total GMV']

        for col in ['GS', 'JPM', 'NOMURA', 'ABN', 'Total Margin', 'Total GMV']:
            df_all[col] = df_all[col] / fx

        df_summary = df_all[df_all['book'].isin(['Total', 'MIPL', 'MIPUS'])].reset_index(drop=True)
        df_details = df_all[~df_all['book'].isin(['Total', 'MIPL', 'MIPUS'])].reset_index(drop=True)
        df_details = df_details.sort_values(by='Total Margin', ascending=False)
        df_details = df_details[df_details['Total Margin'] != 0]

        tem = pd.read_sql_query(
            f"select * from pbactualmargin where date='{businessdate}' AND entity='Prop' ", con=self.engine_pbactual)
        df_pbactual = tem[['pb', 'marginvalue']].rename(columns={'marginvalue': 'pb actual margin'})
        df_pbactual['pb'] = df_pbactual['pb'].str.upper()
        df_pbactual = df_pbactual[df_pbactual['pb'].isin(['GS', 'JPM', 'NOMURA', 'ABN'])]

        df_tem = df_summary.loc[df_summary['book'] == 'Total'].reset_index(drop=True)
        df_tem = DataFrame(df_tem.drop(columns=['book', 'Total GMV', 'Total Margin', 'Margin Rate']).T).reset_index(
            drop=False).rename(columns={'index': 'pb', 0: 'margin replication'})
        df_pbactual = pd.merge(df_pbactual, df_tem, on='pb')
        df_pbactual = df_pbactual.append(df_pbactual.sum(numeric_only=True), ignore_index=True).fillna('Total')
        df_pbactual['deviation'] = (df_pbactual['pb actual margin'] -
                                    df_pbactual['margin replication']) / df_pbactual['pb actual margin']
        df_pbactual['deviation'] = df_pbactual['deviation'].abs()

        return df_summary, df_details, df_pbactual
