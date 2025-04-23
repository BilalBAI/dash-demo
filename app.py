import pandas as pd
from datetime import datetime, date, timedelta

import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import dash_table
from dash_table.Format import Format, Group, Scheme, Sign
import dash_table.FormatTemplate as FormatTemplate
import plotly.graph_objs as go

from calc import CalcService

def money(decimals, sign=Sign.default):
    return Format(group=Group.yes, precision=decimals, scheme=Scheme.fixed, sign=sign)


class DashApp:
    def __init__(self):
        self.calc = CalcService()
        self.app = app = dash.Dash(__name__)
        # Dash app setup
        self.app.layout = html.Div(
            html.Div(
                [
                    html.H2('Book Hist Margin Rates', style={'color': 'white'}),
                    dcc.Dropdown(
                        id='book-hist-dropdown',
                        options=self.calc.books,
                        value='Total',
                    ),

                    dcc.Graph(
                            id='book-hist',
                            style={'backgroundColor': 'black'}
                        ),
                    html.H2('Day View', style={'color': 'white'}),
                    dcc.DatePickerSingle(
                        id='date-picker-single',
                        min_date_allowed=datetime(2020, 3, 1),
                        initial_visible_month=datetime.today()
                    ),
                    html.Button('Refresh', id='refresh', n_clicks=0),
                    html.H4('Summary', style={'color': 'white'}),
                    dash_table.DataTable(
                        id='summary',
                        columns=[
                            {
                                'id': 'book',
                                'name': 'Entity',
                                'type': 'text'
                            }, {
                                'id': 'ABN',
                                'name': 'ABN',
                                'type': 'numeric',
                                'format': money(0)
                            }, {
                                'id': 'GS',
                                'name': 'GS',
                                'type': 'numeric',
                                'format': money(0)
                            }, {
                                'id': 'NOMURA',
                                'name': 'NOMURA',
                                'type': 'numeric',
                                'format': money(0)
                            },{
                                'id': 'JPM',
                                'name': 'JPM',
                                'type': 'numeric',
                                'format': money(0)
                            },{
                                'id': 'Total Margin',
                                'name': 'Total Margin',
                                'type': 'numeric',
                                'format': money(0)
                            },{
                                'id': 'Total GMV',
                                'name': 'Total GMV',
                                'type': 'numeric',
                                'format': money(0)
                            },{
                                'id': 'Margin Rate',
                                'name': 'Margin Rate',
                                'type': 'numeric',
                                'format': FormatTemplate.percentage(2)
                            }
                        ],
                        sort_action="native",
                        sort_mode='multi',
                        style_header={
                            'backgroundColor': 'rgb(0, 0, 0)',
                            'fontSize': 15
                        },
                        style_cell={
                            'backgroundColor': 'rgb(30, 30, 30)',
                            'color': 'white',
                            'fontSize': 13
                        }
                    ),
                    dash_table.DataTable(
                        id='pbactual',
                        columns=[
                            {
                                'id': 'pb',
                                'name': 'pb',
                                'type': 'text'
                            }, {
                                'id': 'pb actual margin',
                                'name': 'pb actual margin',
                                'type': 'numeric',
                                'format': money(0)
                            }, {
                                'id': 'margin replication',
                                'name': 'margin replication',
                                'type': 'numeric',
                                'format': money(0)
                            }, {
                                'id': 'deviation',
                                'name': 'deviation',
                                'type': 'numeric',
                                'format': FormatTemplate.percentage(2)
                            }
                        ],
                        sort_action="native",
                        sort_mode='multi',
                        style_header={
                            'backgroundColor': 'rgb(0, 0, 0)',
                            'fontSize': 15
                        },
                        style_cell={
                            'backgroundColor': 'rgb(30, 30, 30)',
                            'color': 'white',
                            'fontSize': 13
                        }
                    ),
                    html.H4('Details', style={'color': 'white'}),
                    dash_table.DataTable(
                        id='details',
                        columns=[
                            {
                                'id': 'book',
                                'name': 'book',
                                'type': 'text'
                            }, {
                                'id': 'ABN',
                                'name': 'ABN',
                                'type': 'numeric',
                                'format': money(0)
                            }, {
                                'id': 'GS',
                                'name': 'GS',
                                'type': 'numeric',
                                'format': money(0)
                            }, {
                                'id': 'JPM',
                                'name': 'JPM',
                                'type': 'numeric',
                                'format': money(0)
                            },{
                                'id': 'NOMURA',
                                'name': 'NOMURA',
                                'type': 'numeric',
                                'format': money(0)
                            },{
                                'id': 'Total Margin',
                                'name': 'Total Margin',
                                'type': 'numeric',
                                'format': money(0)
                            },{
                                'id': 'Total GMV',
                                'name': 'Total GMV',
                                'type': 'numeric',
                                'format': money(0)
                            },{
                                'id': 'Margin Rate',
                                'name': 'Margin Rate',
                                'type': 'numeric',
                                'format': FormatTemplate.percentage(2)
                            }
                        ],
                        sort_action="native",
                        sort_mode='multi',
                        style_header={
                            'backgroundColor': 'rgb(0, 0, 0)',
                            'fontSize': 15
                        },
                        style_cell={
                            'backgroundColor': 'rgb(30, 30, 30)',
                            'color': 'white',
                            'fontSize': 13
                        }

                    ),

                ]
        )
        )
        @self.app.callback(
            [Output('summary', 'data'),
            Output('details', 'data'),
            Output('pbactual', 'data')],
            [Input('date-picker-single', 'date')])
        def update_output(date):
            if date is not None:
                df_summary, df_details, df_pbactual = self.calc.reporting(date)
                return df_summary.to_dict('records'), df_details.to_dict('records'), df_pbactual.to_dict('records')

        @app.callback(
            dash.dependencies.Output('book-hist', 'figure'),
            [dash.dependencies.Input('book-hist-dropdown', 'value')])
        def update_figure(value):
            if value == 'Select Book':
                fig = go.Figure(data=[go.Scatter(x=[], y=[])])
            else:
                book_hist = self.calc.get_book_hist(value)
                fig = go.Figure(data=[go.Scatter(x=book_hist['businessdate'].to_list(), y=book_hist['margin rate'].to_list())])
            fig.layout.template = 'plotly_dark'
            return fig

        @app.callback(
            [dash.dependencies.Output('date-picker-single', 'max_date_allowed'),
            dash.dependencies.Output('date-picker-single', 'date')],
            [dash.dependencies.Input('refresh', 'n_clicks')])
        def update_output(n_clicks):
            return self.calc.tn2, self.calc.tn2

    def run_server(self):
        self.app.run_server(**self.calc.config['server_config'])


if __name__ == "__main__":
    dash_app = DashApp()
    dash_app.run_server()