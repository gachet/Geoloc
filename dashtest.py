#from jupyter_plotly_dash import JupyterDash

def getdid(dff):
    did=[]
    for val in dff.did.unique():
        tmp={}
        tmp['label']=val
        tmp['value']=val
        did.append(tmp)

    return did

# Imports
import dash
import numpy as np
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
from datetime import datetime as dt
import dash_table as dtt
import pandas as pd
import plotly.graph_objs as go
import json

#app = JupyterDash('SimpleExample')
# Load and preprocess data

df_mess_train = pd.read_csv('mess_train_list.csv') # train set
df_mess_test = pd.read_csv('mess_test_list.csv') # test set
pos_train = pd.read_csv('pos_train_list.csv') # position associated to train set
print(pos_train.describe())
df_mess_train.describe()
df_mess_train['time']=pd.to_datetime(df_mess_train.time_ux, unit='ms')
df=df_mess_train.merge(pos_train, how='left', left_index=True,right_index=True)
df = df.drop(df[(df.bs_lat >55) ].index)
df['text']="Date "+df["time"].map(str)+" Message ID " + df["messid"]
basepos = df[['bsid','bs_lat','bs_lng']] \
    .groupby(by='bsid') \
    .agg({'bs_lat':'mean','bs_lng':'mean'})

app=dash.Dash()

mapbox_access_token = 'pk.eyJ1IjoiY2h1emUiLCJhIjoiY2pxMHRsY3IzMG9lMjQ4cWprZWJkZTBxMiJ9.gKc50IpMQM2e4skq2NskHw'
app.layout = html.Div([
    html.Link(href='https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css',rel='stylesheet'),
    html.Div(className="row",children=[
        html.Div(className="col-sm-10",children=[
            dcc.Graph(id='visualisation'),
            html.Div(className="row",children=[
                html.Div(className="col-sm-7",children=[
                    dcc.Graph(id='visualisation2'),
                ]),
                html.Div(className="col-sm-5",children=[
                    html.H2("Device ID"),
                    dcc.Dropdown(
                        id='devicesID',
                        options=getdid(df),
                        multi=True,
                        value=df.did[0]
                    ),
                    html.H2("Unité de temps"),
                    html.Div([
                        dcc.Slider(
                            id='timescale',
                            min=0,
                            max=3,
                            marks={0:'1ms',1:'100ms',2:'500ms',3:'1s'},
                            value=1,
                        )
                    ],style={'width':'90%'}),
                    html.H2("Type de date"),
                    dcc.RadioItems(
                        id='tdate',
                        options=[
                            {'label': 'Plage de temps', 'value': 'Range'},
                            {'label': 'Point unique', 'value': 'ptu'}
                        ],
                        value='Range',
                        labelStyle={'display':'block'}
                    ),
                    html.Div([
                    ],id='test')
                ])

            ]),


        ]),
        html.Div(className="col-sm-2",children=[



            html.Div([
                dcc.RangeSlider(
                    id='timechoice',
                    count=1,
                    min=-5,
                    max=10,
                    step=0.5,
                    value=[-3, 7]
                )
            ],id='choixslider',style={'height':'95vh','width':'100%','margin-top':'2.5vh'}),



        ])

    ])])


@app.callback(
    Output(component_id='choixslider', component_property='children'),
    [Input(component_id='tdate', component_property='value'),
     Input('devicesID','value')]
)
def range_time(typedate,typeD):
    q=""
    if type(typeD)==list:
        for device in typeD[:-1]:
            q+=" did =='"+str(device)+"' or "
        q+="did =='"+str(typeD[-1])+"'"
    else:
        q+="did =='"+str(typeD)+"'"
    rq=df.query(q)
    n = len(rq.time_ux.unique())
    mark={}
    step_dot=int(n/10.0)
    for nn in range(n):
        if nn%step_dot==0:
            print(nn)
            print(rq.time.astype(str).unique()[nn])
            mark[str(nn)]=rq.time.astype(str).unique()[nn]
    mark[n]=rq.time.astype(str).unique()[n-1]
    if typedate =='Range':
        return [dcc.RangeSlider(
            id='timechoice',
            min=0,
            max=n,
            vertical=True,
            marks=mark,
            value=[int(n*0.25),int(n*0.75)]
        )]
    return [dcc.Slider(
        id='timechoice',
        min=0,
        max=n,
        value=int(n*0.5)
    )]


@app.callback(
    dash.dependencies.Output('visualisation', 'figure'),
    [Input('timescale', 'value'),
     Input('timechoice', 'value'),
     Input('devicesID','value')])
def update_figure(time,timechoice,typeD):
    q=""
    if type(typeD)==list:
        for device in typeD[:-1]:
            q+=" did =='"+str(device)+"' or "
        q+="did =='"+str(typeD[-1])+"'"
    else:
        q+="did =='"+str(typeD)+"'"
    devicefil = df.query(q)
    traces = []

    text = list(devicefil.time_ux.unique())
    q2=""
    if type(timechoice)==list:
        timee=text[timechoice[0]:timechoice[1]]
        q2+="time_ux>="+str(min(timee))+" and time_ux<="+str(max(timee))
    else:
        timee=text[timechoice]
        q2+="time_ux=="+str((timee))
    selection=devicefil.query(q2)
    traces.append(go.Scattermapbox(
        lat=basepos.bs_lat.values,
        lon=basepos.bs_lng.values,
        mode='markers',
        name="Stations",
        opacity=0.7,
        marker = dict(
            symbol="information"
        ),
        text=basepos.index.values
    ))


    if type(typeD)!=list:
        valnum=typeD
        typeD=[]
        typeD.append(valnum)

    for deviceID in typeD:
        traces.append(go.Scattermapbox(
            lat=selection[(selection.did==deviceID)].lat.values,
            lon=selection[(selection.did==deviceID)].lng.values,
            mode='markers',
            opacity=0.7,
            marker = dict(
                size = 10,
            ),
            name=deviceID,
            text=selection[(selection.did==deviceID)].text.values,
        ))



    layout = dict(
        title = '2014 US city populations',
        showlegend = True,
        mapbox=dict(
            accesstoken=mapbox_access_token,
            bearing=0,
            center=dict(
                lat=np.mean(selection.lat.values),
                lon=np.mean(selection.lng.values)
            ),
            pitch=0,
            zoom=9
        ),
        margin={'l': 10, 'b': 10, 't': 30, 'r': 10},

    )
    return {
        'data': traces,
        'layout': layout
    }

@app.callback(
    dash.dependencies.Output('visualisation2', 'figure'),
    [Input('visualisation', 'clickData')])
def update_figure(hoverData):
    try:
        hover=hoverData['points'][0]["text"].split(' ')[-1]

        q="messid =='"+str(hover)+"'"
        devicefil = df.query(q)
        traces = []
        for deviceID in devicefil[['lat','lng','bs_lat','bs_lng','rssi','bsid']].values:
            print(deviceID)
            traces.append(go.Scattermapbox(
                showlegend=True,
                lat=[deviceID[0],deviceID[2]],
                lon=[deviceID[1],deviceID[3]],
                mode='markers+lines',
                opacity=0.7,

                marker = dict(
                    size = 10,
                ),
                text=deviceID[4],
                name=deviceID[-1],
            ))



        layout = dict(
            title = 'messid = '+str(hover),
            showlegend = True,
            mapbox=dict(
                accesstoken=mapbox_access_token,
                bearing=0,
                center=dict(
                    lat=np.mean(devicefil.lat.values),
                    lon=np.mean(devicefil.lng.values)
                ),
                pitch=0,
                zoom=12
            ),
            margin={'l': 10, 'b': 10, 't': 30, 'r': 10},

        )
        return {
            'data': traces,
            'layout': layout
        }
    except:
        return {}





@app.callback(
    Output('test', 'children'),
    [Input('timescale', 'value'),
     Input('timechoice', 'value'),
     Input('devicesID','value'),
     Input('visualisation', 'hoverData')]
)
def test(time,timechoice,typeD,hoverData):
    q=""
    if type(typeD)==list:
        for device in typeD[:-1]:
            q+=" did =='"+str(device)+"' or "
        q+="did =='"+str(typeD[-1])+"'"
    else:
        q+="did =='"+str(typeD)+"'"
    rq=df.query(q)
    text = list(rq.time_ux.unique())
    q2=""
    if type(timechoice)==list:
        timee=text[timechoice[0]:timechoice[1]]
        q2+="time_ux>="+str(min(timee))+" and time_ux<="+str(max(timee))
    else:
        timee=text[timechoice]
        q2+="time_ux=="+str((timee))
    #print(rq.query(q2))

    hover=hoverData['points'][0]["text"].split(' ')[-1]
    return [html.P(str(hover)+"    "+str(q))]


if __name__ == '__main__':

    app.run_server( port=8080, debug=True)