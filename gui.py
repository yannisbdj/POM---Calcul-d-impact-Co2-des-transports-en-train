import PySimpleGUI as sg
import threading
from itineraire import analyser_itineraires_depart_arrivee, analyser_itineraires_parallel
import plotly.graph_objects as go
from io import BytesIO
import base64

def analyser_itineraire(depart_cap, destination, window, result_list, idx):
    result = analyser_itineraires_depart_arrivee(depart_cap, destination)
    result_list[idx] = result
    window.write_event_value('-THREAD_TERMINE-', idx)

def afficher_resultats(co2_results, distance_results, window):
    fig_co2 = create_stacked_bar_chart(co2_results, 400, 150, "Émissions de CO2 par Départ", "Emissions de CO2 (kg)")
    fig_distance = create_stacked_bar_chart(distance_results, 400, 150, "Distances par Départ", "Distance (km)")
    
    # Convert Plotly figure to PNG
    png_co2 = convert_fig_to_png(fig_co2)
    png_distance = convert_fig_to_png(fig_distance)
    
    # Display images in the GUI
    window['-IMAGE-CO2-'].update(data=png_co2)
    window['-IMAGE-DISTANCE-'].update(data=png_distance)

def create_stacked_bar_chart(data, width, height, title, xlabel):
    fig = go.Figure()
    
    destinations = {item['destination'] for item in data}
    
    for destination in destinations:
        y = []
        x = []
        text = []
        for item in data:
            if item['destination'] == destination:
                for depart, value in item.items():
                    if depart != destination:
                        y.append(destination)
                        x.append(value)
                        text.append(item['depart'])
        fig.add_trace(go.Bar(
            y=y,
            x=x,
            text=text,
            name=destination,
            orientation='h',
            textposition='inside'
        ))

    fig.update_layout(
        showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0),
        width=width,
        height=height,
        xaxis=dict(title=xlabel, showticklabels=True),
        yaxis=dict(showticklabels=True),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        barmode='stack',
        title=title
    )
    
    return fig

def convert_fig_to_png(fig):
    img_bytes = fig.to_image(format="png", engine="kaleido")
    return base64.b64encode(img_bytes).decode('utf-8')

layout = [
    [sg.Column([
        [sg.Text('Départs')],
        [sg.Text('Départ', size=(20, 1)), sg.Text('Nombre de personnes')],
        [sg.Column([[sg.Input(key='-DEPART0-', size=(20, 1)), sg.Input('1', key='-NB_PERSONNES0-', size=(10, 1))]], key='-DEPARTS-')],
        [sg.Button('Ajouter départ', key='-NOUVEAU_DEPART-')],
        [sg.Button('Retirer départ', key='-SUPPRIMER_DEPART-')],
        [sg.Text('Destinations')],
        [sg.Column([[sg.Input(key=f'-DESTINATION0-', size=(20, 1))]], key='-DESTINATIONS-')],
        [sg.Button('Ajouter destination', key='-NOUVEAU_DEST-')],
        [sg.Button('Retirer destination', key='-SUPPRIMER_DEST-')]
    ], key='-CONTROLS-')],
    [sg.VerticalSeparator()],
    [sg.Column([
        [sg.Text('Résultat')],
        [sg.Image(key='-IMAGE-CO2-', size=(400, 150))],
        [sg.Image(key='-IMAGE-DISTANCE-', size=(400, 150))],
        [sg.Button('Analyser itinéraires', key='-ANALYSER-')]
    ], key='-RESULT-', vertical_alignment='top')]
]

window = sg.Window('Itinéraire en Train', layout)

depart_counter = 1
destination_counter = 1
threads = []
result_list = []

while True:
    event, values = window.read()
    if event == sg.WINDOW_CLOSED:
        break
    
    if event == '-NOUVEAU_DEPART-':
        new_depart = [[sg.Input(key=f'-DEPART{depart_counter}-', size=(20, 1)), sg.Input('1', key=f'-NB_PERSONNES{depart_counter}-', size=(10, 1))]]
        window.extend_layout(window['-DEPARTS-'], new_depart)
        depart_counter += 1
    
    if event == '-SUPPRIMER_DEPART-' and depart_counter > 1:
        depart_counter -= 1
        window[f'-DEPART{depart_counter}-'].update(visible=False)
        window[f'-NB_PERSONNES{depart_counter}-'].update(visible=False)
    
    if event == '-NOUVEAU_DEST-':
        new_dest = [[sg.Input(key=f'-DESTINATION{destination_counter}-', size=(20, 1))]]
        window.extend_layout(window['-DESTINATIONS-'], new_dest)
        destination_counter += 1
    
    if event == '-SUPPRIMER_DEST-' and destination_counter > 1:
        destination_counter -= 1
        window[f'-DESTINATION{destination_counter}-'].update(visible=False)
    
    if event == '-ANALYSER-':
        depart_values = {f'-DEPART{i}-': values[f'-DEPART{i}-'] for i in range(depart_counter) if values[f'-DEPART{i}-']}
        destination_values = [values[f'-DESTINATION{i}-'] for i in range(destination_counter) if values[f'-DESTINATION{i}-']]
        
        result_list = [None] * (len(depart_values) * len(destination_values))
        window['-ANALYSER-'].update(disabled=True)
        
        idx = 0
        for i in range(depart_counter):
            depart_cap = values[f'-DEPART{i}-']
            for destination in destination_values:
                t = threading.Thread(target=analyser_itineraire, args=(depart_cap, destination, window, result_list, idx), daemon=True)
                threads.append(t)
                t.start()
                idx += 1
    
    if event == '-THREAD_TERMINE-':
        if all(result is not None for result in result_list):
            co2_results, distance_results = analyser_itineraires_parallel({f'-DEPART{i}-': values[f'-DEPART{i}-'] for i in range(depart_counter) if values[f'-DEPART{i}-']},
                                                                          [values[f'-DESTINATION{i}-'] for i in range(destination_counter) if values[f'-DESTINATION{i}-']])
            window['-ANALYSER-'].update(disabled=False)
            afficher_resultats(co2_results, distance_results, window)

window.close()

#pip install -U kaleido
