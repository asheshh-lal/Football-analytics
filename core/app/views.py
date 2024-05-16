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

## to navigate to render page
def about(request):
    print('About')
    return render(request, 'about.html')

## function to get the data from the user and returns it
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


## function to extract pass action from the data
def extract_pass(data):
    df_pass = data[data['type'] == 'Pass']
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

def extract_shot(data):
    df_shot = data[data['type'] == 'Shot']
    df_shot['location'] = df_shot['location'].apply(ast.literal_eval)
    df_shot['shot_end_location'] = df_shot['shot_end_location'].apply(ast.literal_eval)
    df_shot = df_shot[['type', 'location', 'shot_end_location',
                    'shot_outcome']]
    df_shot[['x_start', 'y_start']] = df_shot['location'].apply(lambda x: pd.Series([x[0], x[1]]) if isinstance(x, list) and len(x) >= 2 else pd.Series([None, None]))
    # Extract first and second values of each array in shot_end_location using lambda function
    df_shot[['x_end', 'y_end']] = df_shot['shot_end_location'].apply(lambda x: pd.Series([x[0], x[1]]) if isinstance(x, list) and len(x) >= 2 else pd.Series([None, None]))
    return df_shot

## function to plot pass heat map for first team
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

    fig.suptitle("Total Pass Heatmap for {}".format(data['team'].unique()[0]), fontsize=16)
    plt.show()
    
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig) 
    return image_base64

## function to plot pass heat map for second team
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

    fig.suptitle("Total Pass Heatmap for {}".format(data['team'].unique()[1]), fontsize=16)
    plt.show()
    
    
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig) 
    return image_base64


## function to plot pass network map for second team
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

    fig.suptitle("Total Pass Network for {}".format(data['team'].unique()[0]), fontsize=16)
    plt.show()
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig) 
    return image_base64


## function to plot pass network map for second team
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

    fig.suptitle("Total Pass Network for {}".format(data['team'].unique()[1]), fontsize=16)
    plt.show()
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig) 
    return image_base64

def pass_def_att_one(data):
    df_team_one = data[data['team'] == data['team'].unique()[0]]
    df_pass = extract_pass(df_team_one)
    df_pass = df_pass[(df_pass['x_start'] < 40) & (df_pass['x_end'] > 80)]
    p = Pitch(pitch_type='statsbomb')
    fig, ax = p.draw(figsize=(12, 8))
    p.draw(ax=ax)  
    ax.set_title("Passes from defensive 3rd to attacking 3rd", fontsize=16)

    # Plot passes
    for index, row in df_pass.iterrows():
        if row['pass_outcome'] in ['Incomplete', 'Out']:
            p.scatter(x=row['x_start'], y=row['y_start'], color='white', ax=ax)
            p.scatter(x=row['x_end'], y=row['y_end'], s=300, color='red', ax=ax, marker='+')
            p.lines(xstart=row['x_start'], xend=row['x_end'], ystart=row['y_start'], yend=row['y_end'], ax=ax, linestyle='dotted') 
        else:
            p.scatter(x=row['x_start'], y=row['y_start'], color='white', ax=ax)
            p.scatter(x=row['x_end'], y=row['y_end'], color='green', ax=ax)
            p.lines(xstart=row['x_start'], xend=row['x_end'], ystart=row['y_start'], yend=row['y_end'], ax=ax, linestyle='dotted')
    
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig) 
    return image_base64

def pass_def_att_two(data):
    df_team_two = data[data['team'] == data['team'].unique()[1]]
    df_pass = extract_pass(df_team_two)
    df_pass = df_pass[(df_pass['x_start'] < 40) & (df_pass['x_end'] > 80)]
    p = Pitch(pitch_type='statsbomb')
    fig, ax = p.draw(figsize=(12, 8))
    p.draw(ax=ax)  
    ax.set_title("Passes from defensive 3rd to attacking 3rd", fontsize=16)

    # Plot passes
    for index, row in df_pass.iterrows():
        if row['pass_outcome'] in ['Incomplete', 'Out']:
            p.scatter(x=row['x_start'], y=row['y_start'], color='white', ax=ax)
            p.scatter(x=row['x_end'], y=row['y_end'], s=300, color='red', ax=ax, marker='+')
            p.lines(xstart=row['x_start'], xend=row['x_end'], ystart=row['y_start'], yend=row['y_end'], ax=ax, linestyle='dotted') 
        else:
            p.scatter(x=row['x_start'], y=row['y_start'], color='white', ax=ax)
            p.scatter(x=row['x_end'], y=row['y_end'], color='green', ax=ax)
            p.lines(xstart=row['x_start'], xend=row['x_end'], ystart=row['y_start'], yend=row['y_end'], ax=ax, linestyle='dotted')
    
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig) 
    return image_base64

def pass_mid_att_one(data):
    df_team_one = data[data['team'] == data['team'].unique()[0]]
    df_pass = extract_pass(df_team_one)
    df_pass = df_pass[(df_pass['x_start'] > 40) & (df_pass['x_end'] > 80) & (df_pass['x_start'] < 80)]
    p = Pitch(pitch_type='statsbomb')
    fig, ax = p.draw(figsize=(12, 8))
    p.draw(ax=ax)  
    ax.set_title("Passes from midfield 3rd to attacking 3rd", fontsize=16)

    # Plot passes
    for index, row in df_pass.iterrows():
        if row['pass_outcome'] in ['Incomplete', 'Out']:
            p.scatter(x=row['x_start'], y=row['y_start'], color='white', ax=ax)
            p.scatter(x=row['x_end'], y=row['y_end'], s=300, color='red', ax=ax, marker='+')
            p.lines(xstart=row['x_start'], xend=row['x_end'], ystart=row['y_start'], yend=row['y_end'], ax=ax, linestyle='dotted') 
        else:
            p.scatter(x=row['x_start'], y=row['y_start'], color='white', ax=ax)
            p.scatter(x=row['x_end'], y=row['y_end'], color='green', ax=ax)
            p.lines(xstart=row['x_start'], xend=row['x_end'], ystart=row['y_start'], yend=row['y_end'], ax=ax, linestyle='dotted')
    
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig) 
    return image_base64

def pass_mid_att_two(data):
    df_team_two = data[data['team'] == data['team'].unique()[1]]
    df_pass = extract_pass(df_team_two)
    df_pass = df_pass[(df_pass['x_start'] > 40) & (df_pass['x_end'] > 80) & (df_pass['x_start'] < 80)]
    p = Pitch(pitch_type='statsbomb')
    fig, ax = p.draw(figsize=(12, 8))
    p.draw(ax=ax)  
    ax.set_title("Passes from midfield 3rd to attacking 3rd", fontsize=16)

    # Plot passes
    for index, row in df_pass.iterrows():
        if row['pass_outcome'] in ['Incomplete', 'Out']:
            p.scatter(x=row['x_start'], y=row['y_start'], color='white', ax=ax)
            p.scatter(x=row['x_end'], y=row['y_end'], s=300, color='red', ax=ax, marker='+')
            p.lines(xstart=row['x_start'], xend=row['x_end'], ystart=row['y_start'], yend=row['y_end'], ax=ax, linestyle='dotted') 
        else:
            p.scatter(x=row['x_start'], y=row['y_start'], color='white', ax=ax)
            p.scatter(x=row['x_end'], y=row['y_end'], color='green', ax=ax)
            p.lines(xstart=row['x_start'], xend=row['x_end'], ystart=row['y_start'], yend=row['y_end'], ax=ax, linestyle='dotted')
    
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig) 
    return image_base64

def shots_one(data):
    df_shot_one = data[data['team'] == data['team'].unique()[0]]
    df_shot = extract_shot(df_shot_one)

    p = Pitch(pitch_type='statsbomb')
    fig, ax = p.draw(figsize=(12, 8))
    p.draw(ax=ax)  
    fig.suptitle("Total Pass Network for {}".format(data['team'].unique()[0]), fontsize=16)

    # Plot shots
    for index, row in df_shot.iterrows():
        if row['shot_outcome'] in ['Saved', 'Blocked', 'Off T']:       
            p.scatter(x=row['x_start'], y=row['y_start'], color='white', ax=ax)
            p.scatter(x=row['x_end'], y=row['y_end'], s=50, color='red', ax=ax, marker='+')  # Small marker size (s=50)
            p.lines(xstart=row['x_start'], xend=row['x_end'], ystart=row['y_start'], yend=row['y_end'], ax=ax, linestyle='dotted') 
        else:
            p.scatter(x=row['x_start'], y=row['y_start'], color='white', ax=ax)
            p.scatter(x=row['x_end'], y=row['y_end'], s=100, color='green', ax=ax)  # Large marker size (s=200)
            p.lines(xstart=row['x_start'], xend=row['x_end'], ystart=row['y_start'], yend=row['y_end'], ax=ax, comet=True)
            
    plt.show()  
    # Save plot to buffer and encode as base64
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig)  # Close the plot to free memory

    return image_base64

def shots_two(data):
    df_shot_two = data[data['team'] == data['team'].unique()[1]]
    df_shot = extract_shot(df_shot_two)

    p = Pitch(pitch_type='statsbomb')
    fig, ax = p.draw(figsize=(12, 8))
    p.draw(ax=ax)  
    fig.suptitle("Total Pass Network for {}".format(data['team'].unique()[1]), fontsize=16)

    # Plot shots
    for index, row in df_shot.iterrows():
        if row['shot_outcome'] in ['Saved', 'Blocked', 'Off T']:       
            p.scatter(x=row['x_start'], y=row['y_start'], color='white', ax=ax)
            p.scatter(x=row['x_end'], y=row['y_end'], s=50, color='red', ax=ax, marker='+')  # Small marker size (s=50)
            p.lines(xstart=row['x_start'], xend=row['x_end'], ystart=row['y_start'], yend=row['y_end'], ax=ax, linestyle='dotted') 
        else:
            p.scatter(x=row['x_start'], y=row['y_start'], color='white', ax=ax)
            p.scatter(x=row['x_end'], y=row['y_end'], s=100, color='green', ax=ax)  # Large marker size (s=200)
            p.lines(xstart=row['x_start'], xend=row['x_end'], ystart=row['y_start'], yend=row['y_end'], ax=ax, comet=True)
            
    plt.show()  
    # Save plot to buffer and encode as base64
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig)  # Close the plot to free memory

    return image_base64

# def def_one(data):
#     def_one = data[data['team'] == data['team'].unique()[0]]
#     defensive_actions = ['Pressure', 'Foul Committed', 'Foul Won', 'Ball Recovery', 'Block', 'Miscontrol', 'Clearance', 'Duel', 'Interception', 'Shield']
#     df_def_action = def_one[def_one['type'].isin(defensive_actions)]
#     df_def_action['player'] = df_def_action['player'].apply(lambda x: x.split(" ")[-1])
#     df_def_action[['x_start','y_start']] = pd.DataFrame(df_def_action.location.tolist(),index=df_def_action.index)
#     scatter_df = pd.DataFrame()
#     for i, name in enumerate(df_def_action["player"].unique()):
#         x = df_def_action.loc[df_def_action["player"] == name]["x_start"].to_numpy()
#         y = df_def_action.loc[df_def_action["player"] == name]["y_start"].to_numpy()
#         scatter_df.at[i, "player"] = name
#         # make sure that x and y location for each circle representing the player is the average of passes and receptions
#         scatter_df.at[i, "x"] = np.mean(x)
#         scatter_df.at[i, "y"] = np.mean(y)

#     scatter_df.head()

#     p = Pitch(pitch_type='statsbomb')
#     fig, ax = p.draw(figsize=(12, 8))
#     p.draw(ax=ax)  
#     fig.suptitle("Total Pass Network for {}".format(data['team'].unique()[1]), fontsize=16)

#     # Plot shots
#     for index, row in df_shot.iterrows():
#         if row['shot_outcome'] in ['Saved', 'Blocked', 'Off T']:       
#             p.scatter(x=row['x_start'], y=row['y_start'], color='white', ax=ax)
#             p.scatter(x=row['x_end'], y=row['y_end'], s=50, color='red', ax=ax, marker='+')  # Small marker size (s=50)
#             p.lines(xstart=row['x_start'], xend=row['x_end'], ystart=row['y_start'], yend=row['y_end'], ax=ax, linestyle='dotted') 
#         else:
#             p.scatter(x=row['x_start'], y=row['y_start'], color='white', ax=ax)
#             p.scatter(x=row['x_end'], y=row['y_end'], s=100, color='green', ax=ax)  # Large marker size (s=200)
#             p.lines(xstart=row['x_start'], xend=row['x_end'], ystart=row['y_start'], yend=row['y_end'], ax=ax, comet=True)
            
#     plt.show()  
#     # Save plot to buffer and encode as base64
#     buffer = io.BytesIO()
#     fig.savefig(buffer, format='png')
#     buffer.seek(0)
#     image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
#     plt.close(fig)  # Close the plot to free memory

#     return image_base64

def render_combined_charts(request, data):
    chart1 = pass_heat_one(data)
    chart2 = pass_heat_two(data)
    chart3 = pass_network_one(data)
    chart4 = pass_network_two(data)
    chart5 = pass_def_att_one(data)
    chart6 = pass_def_att_two(data)
    chart7 = pass_mid_att_one(data)
    chart8 = pass_mid_att_two(data)
    chart9 = shots_one(data)
    chart10 = shots_two(data)


    context = {
        'chart1': chart1,
        'chart2': chart2,
        'chart3': chart3, 
        'chart4': chart4,  
        'chart5': chart5, 
        'chart6': chart6,
        'chart7': chart7,
        'chart8': chart8,
        'chart9': chart9,  
        'chart10': chart10,  

    }
    return render(request, 'data_analysis.html', context)