
import dash
import numpy as np
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html

from geopy.distance import vincenty
from datetime import datetime as dt
import dash_table as dtt
import pandas as pd
import plotly.graph_objs as go
app=dash.Dash()


df_mess_train = pd.read_csv('https://raw.githubusercontent.com/osans-tel/Geoloc/master/mess_train_list.csv')
df_mess_test = pd.read_csv('https://raw.githubusercontent.com/osans-tel/Geoloc/master/mess_test_list.csv')
pos_train = pd.read_csv('https://raw.githubusercontent.com/osans-tel/Geoloc/master/pos_train_list.csv')

def vincenty_vec(vec_coord):
    vin_vec_dist = np.zeros(vec_coord.shape[0])
    if vec_coord.shape[1] != 4:
        print('ERROR: Bad number of columns (shall be = 4)')
    else:
        vin_vec_dist = [vincenty(vec_coord[m,0:2], vec_coord[m,2:]).meters for m in range(vec_coord.shape[0])]
    return vin_vec_dist

def Eval_geoloc(y_train_lat , y_train_lng, y_pred_lat, y_pred_lng):
    vec_coord = np.array([y_train_lat , y_train_lng, y_pred_lat, y_pred_lng])
    err_vec = vincenty_vec(np.transpose(vec_coord))
    return err_vec


pred = pd.read_csv('predictionTrain.csv')
df = df_mess_train.merge(pos_train, how='left', left_index=True,right_index=True)
df = df.merge(pred,how='left',on='messid')
print(df.columns)
df['error_distance']=Eval_geoloc( df['lat'], df['lng'], df['pred_lat'], df['pred_lng'])
df['error_copy']=df['error_distance']
did_insight=df.groupby(by='did').agg({'error_distance':'mean','error_copy':'std'}).reset_index(drop=False)

# On enleve les valeurs abérente pour la visualisation
df = df.drop(df[(df.bs_lng >55) ].index)
# Récuperation des bsid sur le jeu de train
basepos = df_mess_train[['bsid','bs_lat','bs_lng']] \
    .groupby(by='bsid') \
    .agg({'bs_lat':'mean','bs_lng':'mean'}) \
    .sort_index() \
    .reset_index(drop=False)
#Récuperation des bsid sur le jeu de test
basepos2 = df_mess_test[['bsid','bs_lat','bs_lng']] \
    .groupby(by='bsid') \
    .agg({'bs_lat':'mean','bs_lng':'mean'}) \
    .sort_index() \
    .reset_index(drop=False)

bsid_tab=basepos.append(basepos2, ignore_index=True)
bsid_tab['bsid']=pd.to_numeric(bsid_tab.bsid.values)
bsid_tab.drop_duplicates(subset='bsid',inplace=True)
bsid_tab.reset_index(drop=False)
print(bsid_tab.head())
bsid_tab.describe()


# fonction et application pour la visualisation
def getdid(dff):
    did=[]
    for val in dff.did.unique():
        tmp={}
        tmp['label']=val
        tmp['value']=val
        did.append(tmp)

    return did
df['time']=pd.to_datetime(df.time_ux, unit='ms')
df['text']=" Date "+df["time"].map(str)+" Message ID " + df["messid"].astype(str)


colorscale=[
    'rgb(237,187,153)','rgb(245,203,167)','rgb(250,215,160)','rgb(249,231,156)','rgb(171,235,198)','rgb(165,223,191)',
    'rgb(162,217,206)','rgb(163,228,215)','rgb(174,214,241)','rgb(169,204,227)','rgb(210,180,222)','rgb(255,189,226)',
    'rgb(245,188,177)','rgb(230,176,170)','rgb(39,55,70)','rgb(46,64,83)','rgb(112,123,124)','rgb(131,145,146)',
    'rgb(186,74,0)','rgb(202,111,30)','rgb(214,137,16)','rgb(212,172,15)','rgb(40,180,99)','rgb(34,153,84)',
    'rgb(19,141,117)','rgb(23,165,13)','rgb(46,134,193)','rgb(36,113,163)','rgb(125,60,152)','rgb(136,78,160)',
    'rgb(203,67,53)','rgb(192,57,43)'
]
print(len(colorscale))

mapbox_access_token = 'pk.eyJ1IjoiY2h1emUiLCJhIjoiY2pxMHRsY3IzMG9lMjQ4cWprZWJkZTBxMiJ9.gKc50IpMQM2e4skq2NskHw'
app.layout = html.Div([
    html.Link(href='https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css',rel='stylesheet'),
    html.Div(className="row",children=[
        html.Div(className="col-sm-12",children=[
            dcc.Graph(id='visualisation'),
            html.Div(className="row",children=[
                html.Div(className="col-sm-5",children=[
                    html.H2("Device ID"),
                    dcc.Dropdown(
                        id='devicesID',
                        options=getdid(df),
                        multi=True,
                        value=df.did[0]
                    ),
                    html.Div([
                    ],id='test'),
                    html.P('Pour mettre à jour le second graphe clicker sur un point sur la carte de positionnement des devices')
                ]),
                html.Div(className="col-sm-7",children=[
                    dcc.Graph(id='visualisation2'),
                ])

            ]),
        ]),

    ])
])

#Maj du graph principale
@app.callback(
    dash.dependencies.Output('visualisation', 'figure'),
    [Input('devicesID','value')])
def update_vis(DID):
    # requettage sur table des devices à afficher sur une période choisie
    q=""
    if type(DID)==list:
        for device in DID[:-1]:
            q+=" did =='"+str(device)+"' or "
        q+="did =='"+str(DID[-1])+"'"
    else:
        q+="did =='"+str(DID)+"'"
    devicefil = df.query(q)


    selection=devicefil

    # mise en conformite du device ID
    if type(DID)!=list:
        valnum=DID
        DID=[]
        DID.append(valnum)

    # display des bases de geolocalisation
    traces=[]

    # display des devices
    for deviceID in DID:
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

    # Design
    layout = dict(
        title = 'Positionnement des devices',
        showlegend = True,
        dragmode='lasso',
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

# Maj du second graph via message id
@app.callback(
    dash.dependencies.Output('visualisation2', 'figure'),
    [Input('visualisation', 'selectedData')])
def update_vis2(hoverData):
    try:
        q=""
        for messid in hoverData['points'][:-1]:
            q+=" messid =='"+str(messid['text'].split(' ')[-1])+"' or "
        q+="messid =='"+str(hoverData['points'][-1]['text'].split(' ')[-1])+"'"
        hover=hoverData['points'][0]["text"].split(' ')[-1]
        #q="messid =='"+str(hover)+"'"
        messidfil = df.query(q)
        print(messidfil.columns)
        traces = []
        traces.append(go.Scattermapbox(
            lat=messidfil.bs_lat.values,
            lon=messidfil.bs_lng.values,
            hoverinfo='none',
            mode='markers',
            name="Stations",
            opacity=0.7,
            marker = dict(
                symbol="information"
            ),
            text=basepos.index.values
        ))
        print(messidfil)
        messidfil =messidfil.groupby(by='messid').agg({'lat':'mean', 'lng':'mean', 'pred_lat':'mean', 'pred_lng':'mean'}).reset_index(drop=False)
        print(messidfil)
        ind=0
        for row in messidfil.values:
            print(row)
            if ind>=len(colorscale):
                break
            traces.append(go.Scattermapbox(
                lat=[row[1]],
                lon=[row[2]],
                name=row[0],
                mode='markers',
                hoverinfo='none',
                opacity=1,
                marker = dict(
                    size = 10,
                    color= colorscale[ind]
                ),
                legendgroup= row[0]
            ))

            traces.append(go.Scattermapbox(
                lat=[row[3]],
                lon=[row[4]],
                mode='markers',
                name=row[0],
                showlegend=False,
                opacity=1,
                marker = dict(
                    size=20,
                    color= colorscale[ind]
                ),
                legendgroup= row[0]
            ))
            ind+=1

        # Design
        layout = dict(
            title = 'messid = '+str(hover),
            showlegend = True,
            mapbox=dict(
                accesstoken=mapbox_access_token,
                bearing=0,
                center=dict(
                    lat=np.mean(messidfil.lat.values),
                    lon=np.mean(messidfil.lng.values)
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




# Test des composants ajoutés
@app.callback(
    Output('test', 'children'),
    [Input('devicesID','value')]
)
def test(typeD):
    q=""
    if type(typeD)==list:
        for device in typeD[:-1]:
            q+=" did =='"+str(device)+"' or "
        q+="did =='"+str(typeD[-1])+"'"
    else:
        q+="did =='"+str(typeD)+"'"
    rq=did_insight.query(q)
    bodytab=[]
    for row in rq.values:
        bodytab.append(html.Tr([
            html.Th([row[0]]),
            html.Th([row[1]]),
            html.Th([row[2]]),
        ]))
        print(row)
    madiv=html.Table([
        html.Thead([
            html.Tr([
                html.Th(["Device ID"]),
                html.Th(["Erreur moyenne"]),
                html.Th(["Variance de l'erreur"]),
            ])
        ]),
        html.Tbody(children=bodytab)
    ],className="table table-striped")



    return [madiv]



if __name__ == '__main__':

    app.run_server( port=8080, debug=True)