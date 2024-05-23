from django.shortcuts import render
from .forms import UploadCSVForm, PlayerChoiceForm
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
from matplotlib.lines import Line2D


# TO DO:
# - remove NaN values
# - design changes, make player selection divided into two teams, consider another parameter team to filter that along with players 
# - fonts and other misc items

def upload_csv(request):
    if request.method == 'POST':
        if 'csv_file' in request.FILES:
            # Handle file upload
            form = UploadCSVForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = request.FILES['csv_file']
                data = pd.read_csv(csv_file)
                request.session['csv_data'] = data.to_dict('records')

                # Create unique player choices
                unique_players = data[['player', 'team']].drop_duplicates()
                player_choices = [(row['player'], f"{row['player']} ({row['team']})") for _, row in unique_players.iterrows()]

                # Initialize player choice form
                choice_form = PlayerChoiceForm(player_choices=player_choices)
                return render(request, 'player_choice.html', {'form': choice_form})
            else:
                return HttpResponseBadRequest("Invalid form submission")
        else:
            # Handle player selection
            csv_data = request.session.get('csv_data', [])
            
            if not csv_data:
                return HttpResponseBadRequest("No CSV data found in session")

            data = pd.DataFrame(csv_data)
            unique_players = data[['player', 'team']].drop_duplicates()
            player_choices = [(row['player'], f"{row['player']} ({row['team']})") for _, row in unique_players.iterrows()]

            choice_form = PlayerChoiceForm(request.POST, player_choices=player_choices)
            if choice_form.is_valid():
                selected_player = choice_form.cleaned_data['player']
                selected_rows = data[data['player'] == selected_player]

                # Store the selected rows and columns in session
                request.session['selected_rows'] = selected_rows.to_dict('records')
                request.session['columns'] = list(data.columns)
                return render_combined_charts(request, selected_rows)

            else:
                form = UploadCSVForm()
                return render(request, 'player_choice.html', {'form': choice_form})
    else:
        form = UploadCSVForm()
    
    return render(request, 'upload_csv.html', {'form': form})


# def render_selection_result(request, selected_player):
#     selected_rows = request.session.get('selected_rows', pd.DataFrame())
#     # columns = selected_rows.columns.tolist()

#     try:
#         return render_combined_charts(request, selected_rows)

#     except Exception as e:
#         return render(request, 'data_analysis.html', {'error_message': f"Error: {str(e)}"})

#     return render(request, 'data_analysis.html')

## function to extract pass action from the data
def extract_pass(data):
    df_pass = data[data['type'] == 'Pass']
    df_pass['location'] = df_pass['location'].apply(ast.literal_eval)
    df_pass['pass_end_location'] = df_pass['pass_end_location'].apply(ast.literal_eval)
    df_pass = df_pass[['type', 'location', 'pass_end_location',
                    'pass_outcome', 'pass_recipient', 'pass_type',
                    'play_pattern', 'player', 'under_pressure','pass_height']]
    df_pass['x_start'] = df_pass['location'].apply(lambda x: x[0])
    df_pass['y_start'] = df_pass['location'].apply(lambda x: x[1])
    df_pass['x_end'] = df_pass['pass_end_location'].apply(lambda x: x[0])
    df_pass['y_end'] = df_pass['pass_end_location'].apply(lambda x: x[1])
    return df_pass

## function to extract defensive data
def extract_def(data):
    # Define the list of defensive actions
    defensive_actions = ['Pressure', 'Foul Committed', 'Foul Won', 'Ball Recovery', 'Block', 'Miscontrol', 'Clearance', 'Duel', 'Interception', 'Shield']

    # Filter for defensive actions
    df_def_action = data[data['type'].isin(defensive_actions)]

    # Extract the last name of the player
    df_def_action['player'] = df_def_action['player'].apply(lambda x: x.split(" ")[-1])
    
    df_def_action['location'] = df_def_action['location'].apply(ast.literal_eval)
    df_def_action['x_start'] = df_def_action['location'].apply(lambda x: x[0])
    df_def_action['y_start'] = df_def_action['location'].apply(lambda x: x[1])
    return df_def_action

## function to extract shot data
def extract_shot(data):
    # Filter for Shot type events
    df_shot = data[data['type'] == 'Shot'].copy()
    
    # Function to safely parse locations
    def parse_location(location):
        try:
            if isinstance(location, str):
                return ast.literal_eval(location)
            return location
        except (ValueError, SyntaxError):
            return [None, None]
    
    # Apply parsing function
    df_shot['location'] = df_shot['location'].apply(parse_location)
    df_shot['shot_end_location'] = df_shot['shot_end_location'].apply(parse_location)
    
    # Extract coordinates
    df_shot['x_start'] = df_shot['location'].apply(lambda x: x[0] if isinstance(x, list) and len(x) >= 2 else None)
    df_shot['y_start'] = df_shot['location'].apply(lambda x: x[1] if isinstance(x, list) and len(x) >= 2 else None)
    df_shot['x_end'] = df_shot['shot_end_location'].apply(lambda x: x[0] if isinstance(x, list) and len(x) >= 2 else None)
    df_shot['y_end'] = df_shot['shot_end_location'].apply(lambda x: x[1] if isinstance(x, list) and len(x) >= 2 else None)
    
    # Calculate distance
    df_shot['distance'] = np.ceil(np.sqrt((df_shot['x_end'] - df_shot['x_start'])**2 + (df_shot['y_end'] - df_shot['y_start'])**2))
    
    # Filter and return relevant columns
    df_shot = df_shot[['type', 'location', 'shot_end_location', 'shot_outcome', 'x_start', 'y_start', 'x_end', 'y_end', 'distance']]
    
    return df_shot

## function to extract shot data
def extract_carry(data):
    df_carry = data[data['type'] == 'Carry']

    # Function to safely parse the location fields
    def parse_location(location):
        if isinstance(location, str):
            return ast.literal_eval(location)
        return location

    # Apply the function to parse locations if they are strings
    df_carry['location'] = df_carry['location'].apply(parse_location)
    df_carry['carry_end_location'] = df_carry['carry_end_location'].apply(parse_location)

    # Extract x and y coordinates for start and end locations
    df_carry['x_start'] = df_carry['location'].apply(lambda x: x[0] if isinstance(x, list) else None)
    df_carry['y_start'] = df_carry['location'].apply(lambda x: x[1] if isinstance(x, list) else None)
    df_carry['x_end'] = df_carry['carry_end_location'].apply(lambda x: x[0] if isinstance(x, list) else None)
    df_carry['y_end'] = df_carry['carry_end_location'].apply(lambda x: x[1] if isinstance(x, list) else None)
    return df_carry

## function to extract dribble data
def extract_dribble(data):
    df_carry = data[data['type'] == 'Dribble']
    df_carry['location'] = df_carry['location'].apply(ast.literal_eval)
    df_carry['x_start'] = df_carry['location'].apply(lambda x: x[0])
    df_carry['y_start'] = df_carry['location'].apply(lambda x: x[1])
    return df_carry

## function to plot pass heat map for first team
def pass_heat_one(data):
    df_pass = extract_pass(data)
    player = data['player']
    pitch = Pitch(line_zorder=2, line_color='black')
    fig, ax = pitch.grid(grid_height=0.9, title_height=0.06, axis=False,
                         endnote_height=0.04, title_space=0, endnote_space=0)
    
    bin_statistic = pitch.bin_statistic(df_pass['x_start'], df_pass['y_start'], statistic='count', bins=(8, 6), normalize=False)
    pcm = pitch.heatmap(bin_statistic, cmap='Reds', edgecolor='grey', ax=ax['pitch'])
    
    ax_cbar = fig.add_axes((1, 0.093, 0.03, 0.786))
    cbar = plt.colorbar(pcm, cax=ax_cbar)
    
    fig.suptitle("Total Pass Heatmap for {}".format(data['player'].unique()[0]), fontsize=16)
    plt.show()
    
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig)
    
    return image_base64

## function to plot ground passes for the player
def ground_pass(data):
    df_pass = extract_pass(data)
    df_ground_pass = df_pass[df_pass['pass_height']=="Ground Pass"]
    player = data['player']
    p = Pitch(pitch_type='statsbomb')
    fig, ax = p.draw(figsize=(12, 8))
    for index, row in df_ground_pass.iterrows():
        if row['pass_outcome'] in ['Incomplete', 'Out']:       
            p.scatter(x=row['x_start'], y=row['y_start'], color='white',ax=ax)
            p.scatter(x=row['x_end'], y=row['y_end'],s=300, color='red',ax=ax,marker='+')
            p.lines(xstart=row['x_start'], xend=row['x_end'], ystart=row['y_start'], yend=row['y_end'], ax=ax,linestyle='dotted') 
        else:
            p.scatter(x=row['x_start'], y=row['y_start'], color='white',ax=ax)
            p.scatter(x=row['x_end'], y=row['y_end'],s=50 ,color='green',ax=ax)
            p.lines(xstart=row['x_start'], xend=row['x_end'], ystart=row['y_start'], yend=row['y_end'], ax=ax,linestyle='dotted')
        
    fig.suptitle("Total ground passes for {}".format(data['player'].unique()[0]), fontsize=16)
    plt.show()
    
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig)
    
    return image_base64

## function to plot low passes for the player
def low_pass(data):
    df_pass = extract_pass(data)
    df_ground_pass = df_pass[df_pass['pass_height']=="Low Pass"]
    player = data['player']
    p = Pitch(pitch_type='statsbomb')
    fig, ax = p.draw(figsize=(12, 8))
    for index, row in df_ground_pass.iterrows():
        if row['pass_outcome'] in ['Incomplete', 'Out']:       
            p.scatter(x=row['x_start'], y=row['y_start'], color='white',ax=ax)
            p.scatter(x=row['x_end'], y=row['y_end'],s=300, color='red',ax=ax,marker='+')
            p.lines(xstart=row['x_start'], xend=row['x_end'], ystart=row['y_start'], yend=row['y_end'], ax=ax,linestyle='dotted') 
        else:
            p.scatter(x=row['x_start'], y=row['y_start'], color='white',ax=ax)
            p.scatter(x=row['x_end'], y=row['y_end'], color='green',ax=ax)
            p.lines(xstart=row['x_start'], xend=row['x_end'], ystart=row['y_start'], yend=row['y_end'], ax=ax,linestyle='dotted')
        
    fig.suptitle("Total low passes for {}".format(data['player'].unique()[0]), fontsize=16)
    plt.show()
    
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig)
    
    return image_base64

## function to plot low passes for the player
def high_pass(data):
    df_pass = extract_pass(data)
    df_ground_pass = df_pass[df_pass['pass_height']=="High Pass"]
    player = data['player']
    p = Pitch(pitch_type='statsbomb')
    fig, ax = p.draw(figsize=(12, 8))
    for index, row in df_ground_pass.iterrows():
        if row['pass_outcome'] in ['Incomplete', 'Out']:       
            p.scatter(x=row['x_start'], y=row['y_start'], color='white',ax=ax)
            p.scatter(x=row['x_end'], y=row['y_end'],s=300, color='red',ax=ax,marker='+')
            p.lines(xstart=row['x_start'], xend=row['x_end'], ystart=row['y_start'], yend=row['y_end'], ax=ax,linestyle='dotted') 
        else:
            p.scatter(x=row['x_start'], y=row['y_start'], color='white',ax=ax)
            p.scatter(x=row['x_end'], y=row['y_end'], color='green',ax=ax)
            p.lines(xstart=row['x_start'], xend=row['x_end'], ystart=row['y_start'], yend=row['y_end'], ax=ax,linestyle='dotted')
        
    fig.suptitle("Total high passes for {}".format(data['player'].unique()[0]), fontsize=16)
    plt.show()
    
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig)
    
    return image_base64

## function to plot carry of the player
def player_carry(data):
    df_carry = extract_carry(data)
    player = data['player']
    p = Pitch(pitch_type='statsbomb')
    fig, ax = p.draw(figsize=(12, 8))
    ## plotting the start and end locations
    p.scatter(x=df_carry['x_start'], y=df_carry['y_start'], ax=ax)
    p.scatter(x=df_carry['x_end'], y=df_carry['y_end'], ax=ax, color='red')

    ## plotting the lines of the start and end locations
    p.lines(xstart=df_carry['x_start'], xend=df_carry['x_end'], ystart=df_carry['y_start'], yend=df_carry['y_end'], ax=ax, comet=True)

    ## setting the title        
    fig.suptitle("Total carry for {}".format(data['player'].unique()[0]), fontsize=16)
    plt.show()
    
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig)
    
    return image_base64

## function to plot carry of the player
def player_dribble(data):
    df_dribble = extract_dribble(data)
    player = data['player']
    p = Pitch(pitch_type='statsbomb')
    fig, ax = p.draw(figsize=(12, 8))
    
    # Plotting the dribbles
    for index, row in df_dribble.iterrows():
        if row['dribble_outcome'] == 'Complete':
            p.scatter(x=row['x_start'], y=row['y_start'], ax=ax, color='green', s=300, alpha=0.5)
        else:
            p.scatter(x=row['x_start'], y=row['y_start'], ax=ax, color='red', s=300, alpha=0.9)

    # Create custom legend
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label='Complete Dribble', markerfacecolor='green', markersize=10),
        Line2D([0], [0], marker='o', color='w', label='Incomplete Dribble', markerfacecolor='red', markersize=10),
    ]
    ax.legend(handles=legend_elements)

    # Adding description
    description = f"Complete dribbles: {len(df_dribble[df_dribble['dribble_outcome'] == 'Complete'])}\nIncomplete dribbles:{len(df_dribble[df_dribble['dribble_outcome'] == 'Incomplete'])}"
    ax.text(0.2, 0, description, ha='center', va='center', transform=ax.transAxes, fontsize=12)

    ## setting the title        
    fig.suptitle("Total dribbles for {}".format(data['player'].unique()[0]), fontsize=16)
    plt.show()
    
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig)
    
    return image_base64

## function to plot shot of the player
def player_shot(data):
    df_shot = extract_shot(data)
    player = data['player']
    p = Pitch(pitch_type='statsbomb')
    fig, ax = p.draw(figsize=(12, 8))
    
    # Plotting the shots
    for index, row in df_shot.iterrows():
        if row['shot_outcome'] == 'Off T':
            p.scatter(x=row['x_start'], y=row['y_start'], ax=ax, color='black', s=300, alpha=0.5)
            p.scatter(x=row['x_end'], y=row['y_end'], ax=ax, color='blue', s=300, alpha=0.5)
            p.lines(xstart=row['x_start'], xend=row['x_end'], ystart=row['y_start'], yend=row['y_end'], ax=ax, linestyle='dotted')
            ax.annotate(f"{row['distance']} yds", xy=(row['x_start'], row['y_start']), xytext=(row['x_end'], row['y_end']), textcoords='offset points', arrowprops=dict(arrowstyle='->'), xycoords='data', ha='right')
        elif row['shot_outcome'] == 'Goal':
            p.scatter(x=row['x_start'], y=row['y_start'], ax=ax, color='green', s=300, alpha=0.9)
            p.scatter(x=row['x_end'], y=row['y_end'], ax=ax, color='blue', s=300, alpha=0.5)
            p.lines(xstart=row['x_start'], xend=row['x_end'], ystart=row['y_start'], yend=row['y_end'], ax=ax, linestyle='dotted')
            ax.annotate(f"{row['distance']} yds", xy=(row['x_start'], row['y_start']), xytext=(row['x_end'], row['y_end']), textcoords='offset points', arrowprops=dict(arrowstyle='->'), xycoords='data', ha='right')
        else:
            p.scatter(x=row['x_start'], y=row['y_start'], ax=ax, color='red', s=300, alpha=0.9)
            p.scatter(x=row['x_end'], y=row['y_end'], ax=ax, color='blue', s=300, alpha=0.5)
            p.lines(xstart=row['x_start'], xend=row['x_end'], ystart=row['y_start'], yend=row['y_end'], ax=ax, linestyle='dotted')
            ax.annotate(f"{row['distance']} yds", xy=(row['x_start'], row['y_start']), xytext=(row['x_end'], row['y_end']), textcoords='offset points', arrowprops=dict(arrowstyle='->'), xycoords='data', ha='right')
    # Create custom legend
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label='Goal', markerfacecolor='green', markersize=10),
        Line2D([0], [0], marker='o', color='w', label='Blocked/OffTarget', markerfacecolor='red', markersize=10),
        Line2D([0], [0], marker='o', color='w', label='ShotEndLocation', markerfacecolor='Blue', markersize=10),

    ]
    ax.legend(handles=legend_elements)
    fig.suptitle("Total Shots for {}".format(data['player'].unique()[0]), fontsize=16)

    plt.show()
    
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig)
    
    return image_base64


def render_combined_charts(request, data):
    chart1 = pass_heat_one(data)
    chart2 = ground_pass(data)
    chart3 = low_pass(data)
    chart4 = high_pass(data)
    chart5 = player_carry(data)
    chart6 = player_dribble(data)
    chart7 = player_shot(data)

    context = {
        'chart1': chart1,
        'chart2': chart2,
        'chart3': chart3,
        'chart4': chart4,
        'chart5': chart5,
        'chart6': chart6,
        'chart7': chart7,

    }
    return render(request, 'player_data_analysis.html', context)



