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


def about(request):
    print('About')
    return render(request, 'about.html')


def data_analysis(request):
    if request.method == 'POST' and request.FILES.get('myfile'):
        myfile = request.FILES['myfile']

        fs = FileSystemStorage()
        filename = fs.save(myfile.name, myfile)

        try:
            df = pd.read_csv(fs.open(filename))
            # Create a Pitch object
            p = Pitch(pitch_type='statsbomb')

            # Plot the passes on the pitch
            fig, ax = p.draw(figsize=(12, 8))
            ax.set_title("Total Pass Plot", fontsize=16)

            # Convert the figure to a base64-encoded image
            buffer = io.BytesIO()
            fig.savefig(buffer, format='png')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            # Delete the CSV file
            os.remove(fs.path(filename))

            # Pass chart to template
            return render(request, 'data_analysis.html', {'chart': image_base64})

        except Exception as e:
            # Delete the CSV file in case of an error
            os.remove(fs.path(filename))
            return render(request, 'data_analysis.html', {'error_message': f"Error: {str(e)}"})

    return render(request, 'data_analysis.html')

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

def plot_one(data):
    fig = Figure(figsize=(8, 4))
    ax = fig.subplots()
    p = Pitch(pitch_type='statsbomb')
    p.draw(ax=ax)  

    ax.set_title("Total Pass Plot", fontsize=16)
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    plt.close(fig) 
    return image_base64  

def render_combined_charts(request, data):
    chart1 = plot_one(data)
    context = {
        'chart1': chart1 
    }
    return render(request, 'data_analysis.html', context)