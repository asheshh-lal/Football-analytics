from django.shortcuts import render
from .forms import UploadCSVForm, PlayerChoiceForm

# TO DO:
# - remove NaN values
# - design changes, make player selection divided into two teams, consider another parameter team to filter that along with players 
# - fonts and other misc items

def upload_csv(request):
    if request.method == 'POST':
        if 'csv_file' in request.FILES:
            form = UploadCSVForm(request.POST, request.FILES)
            if form.is_valid():
                player_choices = form.get_player_choices()
                choice_form = PlayerChoiceForm(player_choices=player_choices)
                return render(request, 'player_choice.html', {'form': choice_form})
        else:
            player_choices = request.POST.getlist('players')
            choice_form = PlayerChoiceForm(request.POST, player_choices=[(choice, choice) for choice in player_choices])
            if choice_form.is_valid():
                selected_players = choice_form.cleaned_data['players']
                return render(request, 'selection_result.html', {'selected_players': selected_players})
    else:
        form = UploadCSVForm()
    return render(request, 'upload_csv.html', {'form': form})
