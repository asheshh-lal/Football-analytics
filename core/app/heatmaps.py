from django.shortcuts import render
import io
import base64
import matplotlib.pyplot as plt
from mplsoccer import Pitch, Sbopen
from .forms import UploadCSVForm, TeamChoiceForm
import pandas as pd
import ast

# function to upload csv and extract team names

def upload_team_csv(request):
    if request.method == 'POST':
        if 'csv_file' in request.FILES:
            # Handle file upload
            form = UploadCSVForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = request.FILES['csv_file']
                data = pd.read_csv(csv_file)
                request.session['csv_data'] = data.to_dict('records')

                # Create unique team choices
                unique_teams = data['team'].unique()
                team_choices = [(team, team) for team in unique_teams]

                # Initialize player choice form
                choice_form = TeamChoiceForm(team_choices=team_choices)
                return render(request, 'team_choice.html', {'form': choice_form})
            else:
                return HttpResponseBadRequest("Invalid form submission")
        else:
            # Handle player selection
            csv_data = request.session.get('csv_data', [])
            
            if not csv_data:
                return HttpResponseBadRequest("No CSV data found in session")

            data = pd.DataFrame(csv_data)
            # Create unique team choices
            unique_teams = data['team'].unique()
            team_choices = [(team, team) for team in unique_teams]

            choice_form = TeamChoiceForm(request.POST, team_choices=team_choices)
            if choice_form.is_valid():
                selected_team = choice_form.cleaned_data['team']
                selected_rows = data[data['team'] == selected_team]

                # Store the selected rows and columns in session
                request.session['selected_rows'] = selected_rows.to_dict('records')
                request.session['columns'] = list(data.columns)
                return render_heatmaps(request,selected_rows)
            else:
                return render(request, 'team_choice.html', {'form': choice_form})
    else:
        form = UploadCSVForm()
    
    return render(request, 'upload_csv.html', {'form': form})

## function to extract pass action from the data
def extract_pass(data):
    # Function to safely parse the location fields
    def parse_location(location):
        if isinstance(location, str):
            return ast.literal_eval(location)
        return location

    df_pass = data[data['type'] == 'Pass']
    df_pass['location'] = df_pass['location'].apply(parse_location)
    df_pass['pass_end_location'] = df_pass['pass_end_location'].apply(parse_location)
    df_pass = df_pass[['type', 'location', 'pass_end_location',
                    'pass_outcome', 'pass_recipient', 'pass_type',
                    'play_pattern', 'player', 'under_pressure']]
    df_pass['x_start'] = df_pass['location'].apply(lambda x: x[0])
    df_pass['y_start'] = df_pass['location'].apply(lambda x: x[1])
    df_pass['x_end'] = df_pass['pass_end_location'].apply(lambda x: x[0])
    df_pass['y_end'] = df_pass['pass_end_location'].apply(lambda x: x[1])
    return df_pass

## function to plot the heat maps 

def generate_player_heatmap_grid(df):
    team_passes = df[(df.type == 'Pass') & 
                     (df.pass_type != "Throw-in")]
    team_passes = extract_pass(team_passes)
    team_passes = team_passes[['x_start', 'y_start', 'x_end', 'y_end', 'player', 'pass_outcome']]
    
    player_names = team_passes['player'].unique()    
    pitch = Pitch(line_color='white', pitch_color='#02540b')
    fig, axs = pitch.grid(ncols=4, nrows=4, grid_height=0.85, title_height=0.06, 
                          axis=False, endnote_height=0.04, title_space=0.04, endnote_space=0.01, 
                          space=0.2)
    plt.figure(figsize=(14, 10))
    
    for name, ax in zip(player_names, axs['pitch'].flat[:len(player_names)]):
        player_df = team_passes[team_passes["player"] == name]
        ax.text(60, -10, name.split()[-1], ha='center', va='center', fontsize=14)
        pitch.kdeplot(
            x=player_df['x_start'],
            y=player_df['y_start'],
            fill=True,
            shade_lowest=False,
            alpha=.5,
            n_levels=10,
            cmap='plasma',
            ax=ax
        )    
    for ax in axs['pitch'].flat[len(player_names):]:
        fig.delaxes(ax)
    
    axs['title'].text(0.5, 0.5, df['team'].unique()[0] + " Heatmaps", ha='center', va='center', fontsize=20)    
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig)
    
    return image_base64

def render_heatmaps(request, df):
    heatmap = generate_player_heatmap_grid(df)
    context = {
        'chart': heatmap,
        # 'team_name': team_name
    }
    return render(request, 'heatmap.html', context)
