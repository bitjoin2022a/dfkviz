from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

key_pairs = {
    "strength": "STR",  
    "agility": "AGI", 
    "endurance": "END", 
    "wisdom": "WIS", 
    "dexterity": "DEX", 
    "vitality": "VIT", 
    "intelligence": "INT", 
    "luck": "LCK"}


g_query_string = """
{
    id,
    generation,
    summons, maxSummons,
    level,
    mainClass, subClass,
    rarity,
    profession,
    statBoost1, statBoost2,
    strength, strengthGrowthP, strengthGrowthS,
    agility, agilityGrowthP, agilityGrowthS,
    endurance, enduranceGrowthP, enduranceGrowthS,
    wisdom, wisdomGrowthP, wisdomGrowthS,
    dexterity, dexterityGrowthP, dexterityGrowthS,
    vitality, vitalityGrowthP, vitalityGrowthS,
    intelligence, intelligenceGrowthP, intelligenceGrowthS,
    luck, luckGrowthP, luckGrowthS
}   
"""
g_dfk_graph_url = \
    "http://graph3.defikingdoms.com/subgraphs/name/defikingdoms/apiv5"


#### STAT COMPUTATION ####
def uncommon_plus_every_5(h, rng):
    attrs = list(key_pairs.keys())
    aa = rng.choice(attrs, 2, replace=False)
    for a in aa:
        h[a] += 1
    return h

def rare_plus_every_5(h, rng):
    attrs = list(key_pairs.keys())
    aa = rng.choice(attrs, 3, replace=False)
    for a in aa:
        h[a] += 1

    aa = rng.choice(attrs)
    h[aa] += 1
    return h

def legendary_plus_every_5(h, rng):
    attrs = list(key_pairs.keys())
    aa = rng.choice(attrs, 4, replace=False)
    h[aa[0]] += 2
    
    for a in aa[1:]:
        h[a] += 1

    aa = rng.choice(attrs)
    h[aa] += 1
    return h
    
def mythic_plus_every_5(h, rng):
    attrs = list(key_pairs.keys())
    aa = rng.choice(attrs, 6, replace=False)
    for a in aa[:3]:
        h[a] += 2
    
    for a in aa[3:]:
        h[a] += 1

    aa = rng.choice(attrs)
    h[aa] += 1
    return h

def simulate_level_up(hero_info, target_level, chosen1, chosen2, rng=None):
    if rng is None:
        rng = np.random.RandomState(42)

    attrs = key_pairs.keys()
    level_up_results = {k:[] for k in attrs}
    sampling_trails = 1000
    # print(hero_info)
    for _ in range(sampling_trails):
        l = hero_info['level']
        this_level_up_trail = {k:hero_info[k] for k in attrs}
        while l < target_level:
            for k in attrs:
                #print(h['mainClass'], a, prof_stats_1[h['mainClass']][a])
                # main attribute growth draw
                if rng.rand() * 10000 <= hero_info[k+'GrowthP']:
                    this_level_up_trail[k] += 1
                elif rng.rand() * 10000 <= hero_info[k+'GrowthS']:
                    this_level_up_trail[k] += 1
            # user chosen attribute growth
            if chosen1 in attrs:
                this_level_up_trail[chosen1] += 1
            # user chosen attribute growth-2 
            if chosen2[0] in attrs:
                if rng.rand() < 0.5:
                    this_level_up_trail[chosen2[0]] += 1
            if chosen2[1] in attrs:
                if rng.rand() < 0.5:
                    this_level_up_trail[chosen2[1]] += 1
            # rarity draw ...
            if (l+1) % 5 == 0:
                if hero_info['rarity'] == 1: #'uncommon':
                    this_level_up_trail = \
                        uncommon_plus_every_5(this_level_up_trail, rng)
                if hero_info['rarity'] == 2: #'rare':
                    this_level_up_trail = \
                        rare_plus_every_5(this_level_up_trail, rng)
                if hero_info['rarity'] == 3: #'legendary':
                    this_level_up_trail = \
                        legendary_plus_every_5(this_level_up_trail, rng)
                if hero_info['rarity'] == 4: # 'mythic':
                    this_level_up_trail = \
                        mythic_plus_every_5(this_level_up_trail, rng)
            l += 1
        # save this trail to sampling records
        for k in attrs:
            level_up_results[k].append(this_level_up_trail[k])
    return level_up_results

#### HERO DATA DOWNLOADING ####

def query_subgraph(qstr):
    transport = AIOHTTPTransport(url=g_dfk_graph_url)
    # Create a GraphQL client using the defined transport
    client = Client(transport=transport, fetch_schema_from_transport=True)
    query1 = gql(qstr)
    result = client.execute(query1)
    return result

# class HeroQuery:
#     def __init__(self):
#         self.cache = {}
#     
#     def pull_hero(self, hero_id):
#         """
#         querier: communicator to subgraph
#         """
#         if hero_id not in self.cache.keys():
#             query_string = f"""{{hero(
#                 id:{hero_id}) {g_query_string}
#             }}"""
#             self.cache[hero_id] = query_subgraph(query_string)
#         return self.cache[hero_id]
# hero_query = HeroQuery()

def pull_hero(hero_id):
    """
    querier: communicator to subgraph
    """
    query_string = f"""{{hero(
        id:{hero_id}) {g_query_string}
    }}"""
    return query_subgraph(query_string)

g_current_hero_info = None
g_current_hero_id = None
def update_bar_graph(hero_info, target_level, chosen1, chosen2a, chosen2b):
    attributes = ["STR", "AGI", "END", "WIS", "DEX", "VIT", "INT", "LCK"]
    simulated_stats = simulate_level_up(hero_info, target_level, 
        chosen1, (chosen2a, chosen2b))
    attrs = key_pairs.keys()
    for k in attrs:
        print(k, np.mean(simulated_stats[k]), np.std(simulated_stats[k]))
    
    values = []
    x = []
    y = []
    z1=[]
    z2=[]
    for k in key_pairs:
        x.append(key_pairs[k])
        y.append(np.mean(simulated_stats[k]))
        z1.append(np.min(simulated_stats[k]))
        z2.append(np.max(simulated_stats[k]))

    y = np.array(y)
    z1 = np.array(z1)
    z2 = np.array(z2)
    fig = go.Figure()
    fig.add_trace(
        go.Bar(x=attributes, y=y, error_y=dict(
            type='data',
            symmetric=False,
            array=z2-z1,
            arrayminus=y-z1)))
    fig.update_layout(
        title=dict(
            text=f"Hero Attribute Stats at Target Level {target_level}",
            xanchor='left')
    )
    
    return fig

#### WEB APP ####
app = dash.Dash(__name__)
server = app.server

app.layout = html.Div(children=[
    html.H1(children='Hero Level Up Helper'),
    html.Div([
        html.H5(children="HeroID: "),
        dcc.Input(id='heroid-input', value='0', type='text', debounce=True)
    ]),
    html.H5(children='Target Level'),
    dcc.Slider(
        id='level-slider',
        min=5,
        max=100,
        value=5,
        step=1,
        marks={i:str(i) for i in range(5, 101, 5)}
    ),
    html.H5(children="Gaia's blessing choices"),
    html.Div([
        "Bless 100%",
        dcc.Dropdown(
            id='choice-A',
            options=[{'label': i, 'value': i} for i in key_pairs.keys()],
        ),
        ], style={'width': '30%', 'display': 'inline-block'}),
    html.Div([
        "Bless 50% - 1",
        dcc.Dropdown(
            id='choice-B-1',
            options=[{'label': i, 'value': i} for i in key_pairs.keys()],
        ),
        ], style={'width': '30%', 'display': 'inline-block'}),
    html.Div([
        "Bless 50% - 2",
        dcc.Dropdown(
            id='choice-B-2',
            options=[{'label': i, 'value': i} for i in key_pairs.keys()],
        ),
        ], style={'width': '30%', 'display': 'inline-block'}),
    html.Div(id="info-div", 
        children='''
            Hero Information
        '''),
    dcc.Graph(id='stat-graph'),
    dcc.Store(id='hero-cache')
    ],
    )

# make Gaia's blessing exclusive
@app.callback(Output('choice-A', 'options'), 
    Input('choice-B-1', 'value'),
    Input('choice-B-2', 'value'))
def exc_A_B1(c1, c2):
    options=[{'label': i, 'value': i, 'disabled': i==c1 or i==c2} 
        for i in key_pairs.keys()]
    return options

@app.callback(Output('choice-B-1', 'options'), 
    Input('choice-A', 'value'),
    Input('choice-B-2', 'value'))
def exc_A_B1(c1, c2):
    options=[{'label': i, 'value': i, 'disabled': i==c1 or i==c2} 
        for i in key_pairs.keys()]
    return options

@app.callback(Output('choice-B-2', 'options'), 
    Input('choice-A', 'value'),
    Input('choice-B-1', 'value'))
def exc_A_B1(c1, c2):
    options=[{'label': i, 'value': i, 'disabled': i==c1 or i==c2} 
        for i in key_pairs.keys()]
    return options

@app.callback(
    Output('hero-cache', 'data'), 
    Input('heroid-input', 'value'),
    State('hero-cache', 'data'))
def on_hero_change(hero_id_str, hero_cache):
    hero_cache = hero_cache or {} # init to a dict

    try:
        hero_id_i = int(hero_id_str)
        if hero_id_str not in hero_cache.keys():
            hero_info = pull_hero(hero_id_i)["hero"]
            hero_cache[hero_id_str] = hero_info
    except:
        raise PreventUpdate

    hero_cache['current_id'] = hero_id_str
    return hero_cache

@app.callback(
    Output(component_id='info-div', component_property='children'),
    Input(component_id='hero-cache', component_property='data'),
    #Input(component_id='heroid-input', component_property='value'),
)
def update_hero_info(hero_cache):
    hero_info = hero_cache[hero_cache["current_id"]]
    s = html.P([
        html.H5("Hero Information"), html.Br(),
        f"Class: {hero_info['mainClass']}", html.Br(),
        f"Current level: {hero_info['level']}", html.Br(),
        f"Profession: {hero_info['profession']}", html.Br(),
        f"Rarity: {hero_info['rarity']}"
    ]) 
    return s

@app.callback(
    Output(component_id='stat-graph', component_property='figure'),
    Input(component_id='hero-cache', component_property='data'),
    Input(component_id="level-slider", component_property="value"),
    Input(component_id="choice-A", component_property="value"),
    Input(component_id="choice-B-1", component_property="value"),
    Input(component_id="choice-B-2", component_property="value")
)
def update_bar_graph_wrapper(hero_cache, target_level, ch1, ch2a, ch2b):
    hero_info = hero_cache[hero_cache["current_id"]]
    try:
        fig = update_bar_graph(hero_info, target_level, ch1, ch2a, ch2b)
        return fig
    except:
        raise PreventUpdate
        
if __name__ == "__main__":
    app.run_server(debug=True)

    # 'agility': 10, 'agilityGrowthP': 4500, 'agilityGrowthS': 1750, 
    # 'dexterity': 8, 'dexterityGrowthP': 5500, 'dexterityGrowthS': 1375, 
    # 'endurance': 15, 'enduranceGrowthP': 7700, 'enduranceGrowthS': 1525, 
    # 'intelligence': 5, 'intelligenceGrowthP': 2000, 'intelligenceGrowthS': 625, 
    # 'strength': 15, 'strengthGrowthP': 7000, 'strengthGrowthS': 1375, 
    # 'vitality': 15, 'vitalityGrowthP': 7500, 'vitalityGrowthS': 1250, 
    # 'wisdom': 8, 'wisdomGrowthP': 2500, 'wisdomGrowthS': 875}}
    # 'luck': 9, 'luckGrowthP': 3500, 'luckGrowthS': 1625, 
    # 'level': 3, 
    # 'generation': 0, 'id': '100', 
    # 'mainClass': 'Knight', 'maxSummons': 11, 'profession': 'gardening', 
    # 'rarity': 4, 'statBoost1': 'AGI', 'statBoost2': 'END', 
    # 'subClass': 'Thief', 'summons': 32, 
