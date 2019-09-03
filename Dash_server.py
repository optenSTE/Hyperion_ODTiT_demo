# -*- coding: utf-8 -*-

# Программа для демонстрации работы датчика ОДТиТ
# Отображает online-график по данным из БД
import time
import datetime
import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import plotly
import plotly.graph_objs as go
import math
import os
import pandas as pd

# ********************************************
#  Hастроечные константы
# ********************************************

# параметры dash-сервера
address, port = '127.0.0.1', 8052

# интервал обновления данных
update_interval_sec = 0.45

# ширина графика, сек
plot_width_sec = 60

tension_range = [-20, 80]

# bias for Y axe zero-calibration
max_num_of_zerocalibration_points = 10

# ********************************************
#  Глобальные переменные
# ********************************************
data = {'time': [], 'tension': []}

zerocalibration_value = 0  # сдиг показаний, применяемый к измеряемым значениям (чтобы добиться нулевого тяжения)
num_of_zerocalibration_points = 0  # количество первых измерений, которые уже были использованы для калибровки нуля


# dash-сервер
app = dash.Dash(__name__)
app.layout = html.Div(
    html.Div([
        html.Div(
            className="app-header",
            children=[
                html.Img(src='/assets/logo.png', className="app-logo"),
                html.Div(className="app-title", children="Демонстрация работы ОАИСКГН")
            ]
        ),

        dcc.Graph(id='live-update-graph', animate=False, style={'height': '90vh', 'width': '100w'}),
        dcc.Interval(
            id='interval-component',
            interval=update_interval_sec * 1000,
            n_intervals=0
        )
    ])
)
app.title = u'ОАИСКГН'


# обновление графика
@app.callback(Output('live-update-graph', 'figure'),
              [Input('interval-component', 'n_intervals')])
def update_graph_scatter(n):
    global data, zerocalibration_value, num_of_zerocalibration_points

    in_file_name = 'data_for_dash.txt'

    # обновление данных из файла
    try:
        # read new data from txt
        pd_frame = pd.read_csv(in_file_name, sep='\t')

        # del txt
        os.remove(in_file_name)

        new_X = pd_frame['Timestamp, s'] * 1000
        new_Y = pd_frame['ODTiT-7-0_Fav_N'] / 10.0

        data['time'] += new_X.tolist()
        tension_minus_zerovalue = list()
        for i, cur_tension in enumerate(new_Y.tolist()):
            # определяем калибровочный ноль по первым измерениям
            if num_of_zerocalibration_points < max_num_of_zerocalibration_points:
                zerocalibration_value = (zerocalibration_value * num_of_zerocalibration_points + cur_tension) / (
                        num_of_zerocalibration_points + 1)
                num_of_zerocalibration_points += 1
            tension_minus_zerovalue.append(cur_tension - zerocalibration_value)
        data['tension'] += tension_minus_zerovalue
    except FileNotFoundError:
        pass
    except PermissionError:
        pass

    X = data['time']
    Y = data['tension']

    # из последних измерений сформируем таблицу для графика
    traces = list()

    now = int(time.time()) * 1000
    now = max(X)+5000

    traces.append(
        plotly.graph_objs.Scatter(
            x=X,
            y=Y,
            name='Тяжение',
            mode='lines',
            line=dict(shape='spline', width=4)
        ))

    # define graph ranges
    # n_sec = .1
    # range_x = [math.floor((now - plot_width_sec * 1000) / n_sec) * n_sec, math.ceil(now / n_sec) * n_sec]
    range_x = [(now - plot_width_sec * 1000), now]

    # остальное удаляем
    for ts in X:
        if not range_x[0]<ts<range_x[1]:
            del X[0]
            del Y[0]

    range_y1 = [math.floor(min(Y) / 10.0) * 10.0, math.ceil(max(Y) / 10.0) * 10.0]
    if range_y1[0] > min(tension_range):
        range_y1[0] = min(tension_range)
    if range_y1[1] < max(tension_range):
        range_y1[1] = max(tension_range)

    # debug output of X and Y values limits
    if 1:
        print(f'ZeroCalibrationValue {zerocalibration_value}, Points: {len(X)}, X limits: {min(traces[0].x)} - {max(traces[0].x)}, Y limit: {min(traces[0].y)} - {max(traces[0].y)}, Y summ {sum(traces[0].y)}')


    return {'data': traces,
            'layout': go.Layout(
                autosize=True, title='График тяжения ОДТиТ-7-3',
                xaxis=dict(title='Время', range=range_x, type='date'),
                yaxis=dict(title='Тяжение, даН', range=range_y1, rangemode='tozero', type="linear")
    )
        }


if __name__ == "__main__":
    # update_graph_scatter(0)
    app.run_server(debug=True)
