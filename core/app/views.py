from django.shortcuts import render
from django.shortcuts import render
from django.shortcuts import render
from django.utils.safestring import mark_safe
# import plotly.express as px
from django.db.models import Sum, F, Count
import math
import pandas as pd
import pandas as pd
from statsbombpy import sb
import numpy as np
from mplsoccer import Pitch,VerticalPitch, Sbopen, FontManager, inset_image
import plotly.express as px
import matplotlib.pyplot as plt

# Create your views here.

def load_data(request):
    file_path = "/Users/asheshlalshrestha/Desktop/Datanal/Project/Football-analytics/event/Generated Datsets/match.csv"
    
    # Check if the file path is valid
    try:
        df = pd.read_csv(file_path)
        return df
    except FileNotFoundError:
        return render(request, 'error.html', {'message': 'File not found'})
    
    
def chart_1(request):
    df = load_data(request)
    df_pass = df[(df['type'] == 'Pass') & (df['team'] == 'France')]

    # Extracting start and end locations
    df_pass['x_start'] = df_pass['location'].apply(lambda x: x[0])
    df_pass['y_start'] = df_pass['location'].apply(lambda x: x[1])
    df_pass['x_end'] = df_pass['pass_end_location'].apply(lambda x: x[0])
    df_pass['y_end'] = df_pass['pass_end_location'].apply(lambda x: x[1])
    p = Pitch(pitch_type='statsbomb')
    # ## plot for ground pass
    # fig = p.draw(figsize=(12, 8))
    # ax.set_title("Total Pass Plot", fontsize=16)
    # for index, row in df_pass.iterrows():
    #     if row['pass_outcome'] in ['Incomplete', 'Out']:       
    #         p.scatter(x=row['x_start'], y=row['y_start'], color='white',ax=ax)
    #         p.scatter(x=row['x_end'], y=row['y_end'],s=300, color='red',ax=ax,marker='+')
    #         p.lines(xstart=row['x_start'], xend=row['x_end'], ystart=row['y_start'], yend=row['y_end'], ax=ax,linestyle='dotted') 
    #     else:
    #         p.scatter(x=row['x_start'], y=row['y_start'], color='white',ax=ax)
    #         p.scatter(x=row['x_end'], y=row['y_end'], color='green',ax=ax)
    #         p.lines(xstart=row['x_start'], xend=row['x_end'], ystart=row['y_start'], yend=row['y_end'], ax=ax,linestyle='dotted')
    # chart1 = fig.to_html(full_html=False, include_plotlyjs=False)

    return df_pass

def render_combined_charts(request):
    df = chart_1(request)
    
    context = {
        'data': mark_safe(df),  
    }
    return render(request, 'app/chart1.html', context)


