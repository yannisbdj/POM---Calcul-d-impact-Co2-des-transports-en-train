import PySimpleGUI as sg
from itineraire import analyser_itineraires_depart_arrivee

layout = [
    [sg.Text('Départ', size=(20, 1)), sg.Text('Nombre de personnes')],
    [sg.Column([[sg.Input(key='-DEPART0-', size=(20, 1)), sg.Input('1', key='-NB_PERSONNES0-', size=(10, 1))]], key='-DEPARTS-')],
    [sg.Button('Créer un nouveau départ', key='-NOUVEAU_DEPART-')],
    [sg.Text('Destinations potentielles')],
    [sg.Input(key='-DESTINATION-', size=(20, 1)), sg.Button('Ajouter Destination', key='-AJOUTER_DEST-')],
    [sg.Listbox(values=[], size=(30, 6), key='-LIST_DEST-')],
    [sg.Button('Évaluer Itinéraires')]
]

window = sg.Window('Itinéraire en Train', layout)

depart_counter = 1
destinations = []

while True:
    event, values = window.read()
    print(f"Event: {event}, Values: {values}")  # Déboguer les événements et les valeurs
    
    if event == sg.WINDOW_CLOSED:
        break
    
    if event == '-NOUVEAU_DEPART-':
        new_depart = [[sg.Input(key=f'-DEPART{depart_counter}-', size=(20, 1)), sg.Input('1', key=f'-NB_PERSONNES{depart_counter}-', size=(10, 1))]]
        window.extend_layout(window['-DEPARTS-'], new_depart)
        depart_counter += 1
    
    if event == '-AJOUTER_DEST-':
        destination = values['-DESTINATION-']
        if destination:
            destinations.append(destination)
            window['-LIST_DEST-'].update(destinations)
            window['-DESTINATION-'].update('')  # Vider l'input
    
    if event == 'Évaluer Itinéraires':
        depart_values = {f'-DEPART{i}-': values[f'-DEPART{i}-'] for i in range(depart_counter) if values[f'-DEPART{i}-']}
        personnes_values = {f'-NB_PERSONNES{i}-': values[f'-NB_PERSONNES{i}-'] for i in range(depart_counter) if values[f'-NB_PERSONNES{i}-']}
        
        resultats = ""
        for i in range(depart_counter):
            depart_cap = values[f'-DEPART{i}-']
            for destination in destinations:
                resultats += f"Analyse de l'itinéraire de {depart_cap} à {destination}:\n"
                resultats += analyser_itineraires_depart_arrivee(depart_cap, destination) + "\n\n"
        
        sg.popup(f"Départs: {depart_values}\nNombre de personnes: {personnes_values}\nDestinations potentielles: {destinations}\n\n{resultats}")

window.close()
