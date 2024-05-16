import os
import pandas as pd
import io
import base64
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render
from django.utils.safestring import mark_safe
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
from mplsoccer.pitch import Pitch
import plotly.io as pio
import plotly.graph_objects as go
import ast  
import numpy as np

def about(request):
    print('About')
    return render(request, 'about.html')

def data_return(request):
    if request.method == 'POST' and request.FILES.get('myfile'):
        myfile = request.FILES['myfile']
        fs = FileSystemStorage()
        filename = fs.save(myfile.name, myfile)
        try:
            df = pd.read_csv(fs.open(filename))
            return render_combined_charts(request, df)

        except Exception as e:
            return render(request, 'data_analysis.html', {'error_message': f"Error: {str(e)}"})

        finally:
            os.remove(fs.path(filename))
    return render(request, 'data_analysis.html')

def extract_pass(data):
    df_pass = data[data['type'] == 'Pass']
    df_pass.dropna(subset=['location', 'pass_end_location'], inplace=True)
    df_pass['location'] = df_pass['location'].apply(ast.literal_eval)
    df_pass['pass_end_location'] = df_pass['pass_end_location'].apply(ast.literal_eval)
    df_pass = df_pass[['type', 'location', 'pass_end_location',
                    'pass_outcome', 'pass_recipient', 'pass_type',
                    'play_pattern', 'player', 'under_pressure']]
    df_pass['x_start'] = df_pass['location'].apply(lambda x: x[0])
    df_pass['y_start'] = df_pass['location'].apply(lambda x: x[1])
    df_pass['x_end'] = df_pass['pass_end_location'].apply(lambda x: x[0])
    df_pass['y_end'] = df_pass['pass_end_location'].apply(lambda x: x[1])
    return df_pass

def pass_heat_one(data):
    df_team_one = data[data['team'] == data['team'].unique()[0]]
    df_pass = extract_pass(df_team_one)

    pitch = Pitch(line_zorder=2, line_color='black')
    fig, ax = pitch.grid(grid_height=0.9, title_height=0.06, axis=False,
                        endnote_height=0.04, title_space=0, endnote_space=0)
    bin_statistic = pitch.bin_statistic(df_pass.x_start, df_pass.y_start, statistic='count', bins=(8, 6), normalize=False)
    pcm = pitch.heatmap(bin_statistic, cmap='Reds', edgecolor='grey', ax=ax['pitch'])
    ax_cbar = fig.add_axes((1, 0.093, 0.03, 0.786))
    cbar = plt.colorbar(pcm, cax=ax_cbar)

    fig.suptitle("Total Pass Plot for {}".format(data['team'].unique()[0]), fontsize=16)
    plt.show()
    
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig) 
    return image_base64

def pass_heat_two(data):
    df_team_two = data[data['team'] == data['team'].unique()[1]]
    df_pass = extract_pass(df_team_two)

    pitch = Pitch(line_zorder=2, line_color='black')
    fig, ax = pitch.grid(grid_height=0.9, title_height=0.06, axis=False,
                        endnote_height=0.04, title_space=0, endnote_space=0)
    bin_statistic = pitch.bin_statistic(df_pass.x_start, df_pass.y_start, statistic='count', bins=(8, 6), normalize=False)
    pcm = pitch.heatmap(bin_statistic, cmap='Blues', edgecolor='grey', ax=ax['pitch'])
    ax_cbar = fig.add_axes((1, 0.093, 0.03, 0.786))
    cbar = plt.colorbar(pcm, cax=ax_cbar)

    fig.suptitle("Total Pass Plot for {}".format(data['team'].unique()[1]), fontsize=16)
    plt.show()
    
    
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig) 
    return image_base64

def pass_network_one(data):
    df_team_one = data[data['team'] == data['team'].unique()[0]]
    df_pass = extract_pass(df_team_one)
    
    pass_recipient_data = df_pass[['player', 'pass_recipient', 'x_start', 'y_start', 'x_end', 'y_end']].reset_index().drop('index', axis=1)
    pass_recipient_data['player'] = pass_recipient_data['player'].apply(lambda x: x.split(" ")[1])
    pass_recipient_data['pass_recipient'] = pass_recipient_data['pass_recipient'].apply(lambda x: x.split(" ")[1] if not pd.isna(x) else x)
    lines_df = pass_recipient_data.groupby(['player','pass_recipient']).x_start.count().reset_index()
    lines_df.rename({'x_start':'pass_count'},axis='columns',inplace=True)
    lines_df = lines_df[lines_df['pass_count']>0]
    scatter_df = pd.DataFrame()
    for i, name in enumerate(pass_recipient_data["player"].unique()):
        passx = pass_recipient_data.loc[pass_recipient_data["player"] == name]["x_start"].to_numpy()
        recx = pass_recipient_data.loc[pass_recipient_data["pass_recipient"] == name]["x_end"].to_numpy()
        passy = pass_recipient_data.loc[pass_recipient_data["player"] == name]["y_start"].to_numpy()
        recy = pass_recipient_data.loc[pass_recipient_data["pass_recipient"] == name]["y_end"].to_numpy()
        scatter_df.at[i, "player"] = name
        # make sure that x and y location for each circle representing the player is the average of passes and receptions
        scatter_df.at[i, "x"] = np.mean(np.concatenate([passx, recx]))
        scatter_df.at[i, "y"] = np.mean(np.concatenate([passy, recy]))
        # calculate number of passes
        scatter_df.at[i, "no"] = pass_recipient_data.loc[pass_recipient_data["player"] == name].shape[0]
    # adjust the size of a circle so that the player who made more passes
    scatter_df['marker_size'] = (scatter_df['no'] / scatter_df['no'].max() * 1500)
    
        #Drawing pitch
    pitch = Pitch(line_color='grey')
    fig, ax = pitch.grid(grid_height=0.9, title_height=0.06, axis=False,
                        endnote_height=0.04, title_space=0, endnote_space=0)
    #Scatter the location on the pitch
    pitch.scatter(scatter_df.x, scatter_df.y, s=scatter_df.marker_size, color='red', edgecolors='grey', linewidth=1, alpha=1, ax=ax["pitch"], zorder = 3)
    #annotating player name
    for i, row in scatter_df.iterrows():
        pitch.annotate(row.player, xy=(row.x, row.y), c='black', va='center', ha='center', weight = "bold", size=16, ax=ax["pitch"], zorder = 4)

    for i, row in lines_df.iterrows():
        player1 = row['player']
        player2 = row['pass_recipient']
        #take the average location of players to plot a line between them
        player1_x = scatter_df.loc[scatter_df["player"] == player1]['x'].iloc[0]
        player1_y = scatter_df.loc[scatter_df["player"] == player1]['y'].iloc[0]
        player2_x = scatter_df.loc[scatter_df["player"] == player2]['x'].iloc[0]
        player2_y = scatter_df.loc[scatter_df["player"] == player2]['y'].iloc[0]
        num_passes = row["pass_count"]
        #adjust the line width so that the more passes, the wider the line
        line_width = (num_passes / lines_df['pass_count'].max() * 10)
        #plot lines on the pitch
        pitch.lines(player1_x, player1_y, player2_x, player2_y,
                        alpha=1, lw=line_width, zorder=2, color="red", ax = ax["pitch"])

    fig.suptitle("Total Pass Plot for {}".format(data['team'].unique()[0]), fontsize=16)
    plt.show()
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig) 
    return image_base64

def pass_network_two(data):
    df_team_two = data[data['team'] == data['team'].unique()[1]]
    df_pass = extract_pass(df_team_two)

    pass_recipient_data = df_pass[['player', 'pass_recipient', 'x_start', 'y_start', 'x_end', 'y_end']].reset_index().drop('index', axis=1)
    pass_recipient_data['player'] = pass_recipient_data['player'].apply(lambda x: x.split(" ")[1])
    pass_recipient_data['pass_recipient'] = pass_recipient_data['pass_recipient'].apply(lambda x: x.split(" ")[1] if not pd.isna(x) else x)
    lines_df = pass_recipient_data.groupby(['player','pass_recipient']).x_start.count().reset_index()
    lines_df.rename({'x_start':'pass_count'},axis='columns',inplace=True)
    lines_df = lines_df[lines_df['pass_count']>0]
    scatter_df = pd.DataFrame()
    for i, name in enumerate(pass_recipient_data["player"].unique()):
        passx = pass_recipient_data.loc[pass_recipient_data["player"] == name]["x_start"].to_numpy()
        recx = pass_recipient_data.loc[pass_recipient_data["pass_recipient"] == name]["x_end"].to_numpy()
        passy = pass_recipient_data.loc[pass_recipient_data["player"] == name]["y_start"].to_numpy()
        recy = pass_recipient_data.loc[pass_recipient_data["pass_recipient"] == name]["y_end"].to_numpy()
        scatter_df.at[i, "player"] = name
        # make sure that x and y location for each circle representing the player is the average of passes and receptions
        scatter_df.at[i, "x"] = np.mean(np.concatenate([passx, recx]))
        scatter_df.at[i, "y"] = np.mean(np.concatenate([passy, recy]))
        # calculate number of passes
        scatter_df.at[i, "no"] = pass_recipient_data.loc[pass_recipient_data["player"] == name].shape[0]
    # adjust the size of a circle so that the player who made more passes
    scatter_df['marker_size'] = (scatter_df['no'] / scatter_df['no'].max() * 1500)
    
        #Drawing pitch
    pitch = Pitch(line_color='grey')
    fig, ax = pitch.grid(grid_height=0.9, title_height=0.06, axis=False,
                        endnote_height=0.04, title_space=0, endnote_space=0)
    #Scatter the location on the pitch
    pitch.scatter(scatter_df.x, scatter_df.y, s=scatter_df.marker_size, color='blue', edgecolors='grey', linewidth=1, alpha=1, ax=ax["pitch"], zorder = 3)
    #annotating player name
    for i, row in scatter_df.iterrows():
        pitch.annotate(row.player, xy=(row.x, row.y), c='black', va='center', ha='center', weight = "bold", size=16, ax=ax["pitch"], zorder = 4)

    for i, row in lines_df.iterrows():
        player1 = row['player']
        player2 = row['pass_recipient']
        #take the average location of players to plot a line between them
        player1_x = scatter_df.loc[scatter_df["player"] == player1]['x'].iloc[0]
        player1_y = scatter_df.loc[scatter_df["player"] == player1]['y'].iloc[0]
        player2_x = scatter_df.loc[scatter_df["player"] == player2]['x'].iloc[0]
        player2_y = scatter_df.loc[scatter_df["player"] == player2]['y'].iloc[0]
        num_passes = row["pass_count"]
        #adjust the line width so that the more passes, the wider the line
        line_width = (num_passes / lines_df['pass_count'].max() * 10)
        #plot lines on the pitch
        pitch.lines(player1_x, player1_y, player2_x, player2_y,
                        alpha=1, lw=line_width, zorder=2, color="blue", ax = ax["pitch"])

    fig.suptitle("Total Pass Plot for {}".format(data['team'].unique()[1]), fontsize=16)
    plt.show()
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig) 
    return image_base64




def render_combined_charts(request, data):
    chart1 = pass_heat_one(data)
    chart2 = pass_heat_two(data)
    chart3 = pass_network_one(data)
    chart4 = pass_network_two(data)


    context = {
        'chart1': chart1,
        'chart2': chart2,
        'chart3': chart3, 
        'chart4': chart4,  
 

    }
    return render(request, 'data_analysis.html', context)