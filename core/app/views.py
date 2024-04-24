from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from scipy import stats

import csv
import pandas as pd


def home(request):
    print('Home')
    return render(request, 'home.html')


def about(request):
    print('About')
    return render(request, 'about.html')


def data_analysis(request):
    print('Data analysis')
    if request.method == 'POST' and request.FILES['myfile']:
        myfile = request.FILES['myfile']

        fs = FileSystemStorage()
        filename = fs.save(myfile.name, myfile)

        try:
            df = pd.read_csv(fs.open(filename))

            return render(request, 'data_analysis.html',
                          {'result_present': True,
                           'results': {'r_table': "",  # Replace with your result
                                       'p_table': ""},  # Replace with your result
                           'df': df.to_html()})

        except Exception as e:
            # Handle any exceptions, such as incorrect file format
            return render(request, 'data_analysis.html',
                          {'result_present': False,
                           'error_message': f"Error: {str(e)}"})

    return render(request, 'data_analysis.html')











# from django.shortcuts import render
# from django.utils.safestring import mark_safe
# import pandas as pd
# from mplsoccer import Pitch
# from pathlib import Path
# from django.contrib.staticfiles.storage import staticfiles_storage



# def load_data(file_path):
#     print("File path:", file_path)  # Print the file path
#     try:
#         df = pd.read_csv(file_path)
#         return df
#     except FileNotFoundError as e:
#         print("File not found:", e)  
#         return None
#     except Exception as e:
#         print("Error:", e)  
#         return None


# def chart_1(df):
#     if df is not None and 'type' in df.columns and 'team' in df.columns:
#         df_pass = df[(df['type'] == 'Pass') & (df['team'] == 'France')]

#          # Extracting start and end locations
#         df_pass['x_start'] = df_pass['location'].apply(lambda x: x[0])
#         df_pass['y_start'] = df_pass['location'].apply(lambda x: x[1])
#         df_pass['x_end'] = df_pass['pass_end_location'].apply(lambda x: x[0])
#         df_pass['y_end'] = df_pass['pass_end_location'].apply(lambda x: x[1])

#         p = Pitch(pitch_type='statsbomb')

#         fig = p.draw(figsize=(12, 8))
#         ax.set_title("Total Pass Plot", fontsize=16)       

#         chart = fig.to_html(full_html=False, include_plotlyjs=False)
#         return chart
#     else:
#         return None


# from django.templatetags.static import static


# def render_combined_charts(request):
#     file_path = staticfiles_storage.url('admin\match.csv')
#     df = load_data(file_path)

#     if df is not None:
#         chart = chart_1(df)
#         if chart is not None:
#             context = {'chart': chart}
#             return render(request, 'app/chart1.html', context)
#         else:
#             return render(request, 'app/error2.html', {'message': 'Chart data not available'})
#     else:
#         return render(request, 'app/error.html', {'message': 'File not found'})
