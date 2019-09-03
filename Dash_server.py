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

import pandas as pd

# ********************************************
#  Hастроечные константы
# ********************************************

# параметры web-сервера
address, port = '127.0.0.1', 8052
# интервал обновления данных
update_interval_sec = 0.2
# ширина графика
plot_width_sec = 60
tension_range = [-20, 80]
max_num_of_zerocalibration_points = 10
# ********************************************
#  Глобальные переменные
# ********************************************
data = {'time': [], 'tension': []}

zerocalibration_value = 0  # сдиг показаний, применяемый к измеряемым значениям (чтобы добиться нулевого тяжения)
num_of_zerocalibration_points = 0  # количество первых измерений, которые будут использованы для калибровки нуля

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


# обновление графика
@app.callback(Output('live-update-graph', 'figure'),
              [Input('interval-component', 'n_intervals')])
def update_graph_scatter(n):
    global data, zerocalibration_value, num_of_zerocalibration_points, last_temperature

    in_file_name = datetime.datetime.utcnow().strftime('%Y%m%d%H_avg.txt')

    pd_frame = pd.read_csv(in_file_name, sep='\t')
    with open(in_file_name, 'r') as file:
        in_file_content = file.readlines()

    for cur_line in in_file_content[1:]:
        cur_measurements = cur_line.split('\t')
        cur_time = float(cur_measurements[0]) * 1000.0
        cur_temperature = float(cur_measurements[2])
        cur_tension = float(cur_measurements[4]) / 10.0

        # определяем калибровочный ноль по первым измерениям
        if num_of_zerocalibration_points < max_num_of_zerocalibration_points:
            zerocalibration_value = (zerocalibration_value * num_of_zerocalibration_points + cur_tension) / (
                        num_of_zerocalibration_points + 1)
            num_of_zerocalibration_points += 1

        cur_tension -= zerocalibration_value

        if time not in data:
            data['time'].append(cur_time)
            data['tension'].append(cur_tension)

    X = data['time']
    Y = data['tension']


    # данные графика
    now = time.time() * 1000
    for i, timestamp in enumerate(X):
        if timestamp < (now - 10000):
            del X[i]
            del Y[i]

    X = pd_frame['Timestamp, s']*1000
    Y = pd_frame['ODTiT-7-0_Fav_N']/10.0

    # из последних измерений сформируем таблицу для графика
    traces = list()
    points_on_plot = int(plot_width_sec / update_interval_sec)

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

    if 0:
        traces.append(
            plotly.graph_objs.Scatter(
                x=X,
                y=Y2,
                yaxis='y2',
                name='Изгиб',
                mode='lines', #markers
                line=dict(shape='spline', width=0.5)
            )
        )

    n_sec = .1
    range_x = [math.floor((now - plot_width_sec * 1000) / n_sec) * n_sec, math.ceil(now / n_sec) * n_sec]
    range_x = [(now - plot_width_sec * 1000), now]
    range_y1 = [math.floor(min(Y) / 10.0) * 10.0, math.ceil(max(Y) / 10.0) * 10.0]
    if range_y1[0] > min(tension_range):
        range_y1[0] = min(tension_range)
    if range_y1[1] < max(tension_range):
        range_y1[1] = max(tension_range)

    # debug output of X and Y values limits
    if 0:
        print(f'X axe: {min(traces[0].x)} - {max(traces[0].x)}, Y axe: {min(traces[0].y)} - {max(traces[0].y)}')
        for i, x_value in enumerate(traces[0].x[1:]):
            if x_value < traces[0].x[i-1]:
                print('Error in X values')


    return {'data': traces,
            'layout': go.Layout(
                autosize=True, title='График тяжения ОДТиТ-7-3',
                # xaxis=dict(title='Время', type='date'),
                xaxis=dict(title='Время', range=range_x, type='date'),
                yaxis=dict(title='Тяжение, даН', range=range_y1, rangemode='tozero', type="linear")
    )
        }


if __name__ == "__main__":
    update_graph_scatter(0)
    app.run_server(debug=True)
