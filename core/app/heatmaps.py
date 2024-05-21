from django.shortcuts import render
import io
import base64
import matplotlib.pyplot as plt
from mplsoccer import Pitch, Sbopen

parser = Sbopen()

competitions = parser.competition()
competitions[competitions.competition_name == 'International - Fifa World Cup']
parser.match(competition_id=43, season_id=106)
df, df_related, df_freeze, df_tactics = parser.event(3869685)

# Define the list of valid team names
valid_team_names = ['Argentina','France']

def data_return(request):
    if request.method == "POST":
        team_name = request.POST.get('team_name', 'Argentina')  
        if team_name in valid_team_names:
            return render_heatmaps(request, df, team_name)
        else:
            error_message = "Please enter a correct team name."
            return render(request, 'heatmap.html', {'team_name': team_name, 'error_message': error_message})
    return render(request, 'heatmap.html', {'team_name': 'Argentina'})

def generate_player_heatmap_grid(df, team_name):
    team_passes = df[(df.type_name == 'Pass') & 
                     (df.team_name == team_name) & 
                     (df.sub_type_name != "Throw-in")]
    team_passes = team_passes[['x', 'y', 'end_x', 'end_y', 'player_name', 'outcome_name']]
    
    player_names = team_passes['player_name'].unique()    
    pitch = Pitch(line_color='white', pitch_color='#02540b')
    fig, axs = pitch.grid(ncols=4, nrows=4, grid_height=0.85, title_height=0.06, 
                          axis=False, endnote_height=0.04, title_space=0.04, endnote_space=0.01, 
                          space=0.2)
    plt.figure(figsize=(14, 10))
    
    for name, ax in zip(player_names, axs['pitch'].flat[:len(player_names)]):
        player_df = team_passes[team_passes["player_name"] == name]
        ax.text(60, -10, name.split()[-1], ha='center', va='center', fontsize=14)
        pitch.kdeplot(
            x=player_df['x'],
            y=player_df['y'],
            fill=True,
            shade_lowest=False,
            alpha=.5,
            n_levels=10,
            cmap='plasma',
            ax=ax
        )    
    for ax in axs['pitch'].flat[len(player_names):]:
        fig.delaxes(ax)
    
    axs['title'].text(0.5, 0.5, team_name + " Heatmaps", ha='center', va='center', fontsize=20)    
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig)
    
    return image_base64

def render_heatmaps(request, df, team_name):
    heatmap = generate_player_heatmap_grid(df, team_name)
    context = {
        'chart': heatmap,
        'team_name': team_name
    }
    return render(request, 'heatmap.html', context)
