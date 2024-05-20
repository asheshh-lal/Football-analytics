from django import forms
import pandas as pd

class UploadCSVForm(forms.Form):
    csv_file = forms.FileField()

    def get_player_choices(self):
        csv_file = self.cleaned_data['csv_file']
        data = pd.read_csv(csv_file)
        players = data['player'].unique()
        choices = [(player, player) for player in players]
        return choices

class PlayerChoiceForm(forms.Form):
    players = forms.MultipleChoiceField(choices=[], widget=forms.CheckboxSelectMultiple)
    
    def __init__(self, *args, **kwargs):
        player_choices = kwargs.pop('player_choices', [])
        super(PlayerChoiceForm, self).__init__(*args, **kwargs)
        self.fields['players'].choices = player_choices
