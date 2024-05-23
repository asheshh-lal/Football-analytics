from django import forms
import pandas as pd

class UploadCSVForm(forms.Form):
    csv_file = forms.FileField()

class PlayerChoiceForm(forms.Form):
    player = forms.ChoiceField(choices=[])

    def __init__(self, *args, **kwargs):
        player_choices = kwargs.pop('player_choices', [])
        super(PlayerChoiceForm, self).__init__(*args, **kwargs)
        self.fields['player'].choices = player_choices


