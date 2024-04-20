from django.shortcuts import render
from django.shortcuts import render
from django.shortcuts import render
from django.utils.safestring import mark_safe
# import plotly.express as px
from django.db.models import Sum, F, Count
import math
import pandas as pd
# import plotly.graph_objs as go
# from plotly.subplots import make_subplots
# import seaborn as sns
# import joblib

# Create your views here.

def generate_chart1_data(request):
    file_path = "/Users/asheshlalshrestha/Desktop/Datanal/Project/Football-analytics/event/Generated Datsets/match.csv"
    
    # Check if the file path is valid
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        return render(request, 'error.html', {'message': 'File not found'})

    # Process the data as needed
    # chart_data = df.head().to_dict(orient='records')
    chart_data= df.head()

    return render(request, 'app/chart1.html', {'chart_data': chart_data})
