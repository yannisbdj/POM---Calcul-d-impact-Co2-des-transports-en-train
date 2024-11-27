import requests
import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point
from http import HTTPStatus
from geopy.distance import geodesic

train_t = "1"
train_s = "full"

def find_train(tag1, tag2):
    url = (
        f"https://signal.eu.org/osm/eu/route/v1/train/{tag1[1]},{tag1[0]};{tag2[1]},{tag2[0]}?overview="
        + train_s
        + "&geometries=geojson"
    )
    print(url)
    response = requests.get(url)
    if response.status_code == HTTPStatus.OK:
        train_dist = response.json()["routes"][0]["distance"] / 1e3  # km
        gdf = gpd.GeoSeries(
            LineString(response.json()["routes"][0]["geometry"]["coordinates"]),
            crs="epsg:4326",
        )
        return gdf, True, train_dist
    else:
        print(f"Erreur lors de la récupération de l'itinéraire : {response.status_code}, {response.text}")
        return pd.DataFrame(), False, 0

def calculer_pourcentages_par_pays(gdf, frontières):
    distances_par_pays = {}
    total_distance = 0
    for i in range(len(gdf.geometry[0].coords) - 1):
        point1 = Point(gdf.geometry[0].coords[i])
        point2 = Point(gdf.geometry[0].coords[i + 1])
        lat1, lon1 = point1.y, point1.x
        lat2, lon2 = point2.y, point2.x
        
        distance = geodesic((lat1, lon1), (lat2, lon2)).kilometers
        total_distance += distance
        
        pays1 = frontières[frontières.contains(point1)]['name'].values[0]
        pays2 = frontières[frontières.contains(point2)]['name'].values[0]
        
        if pays1 == pays2:
            pays = pays1
        else:
            pays = pays1 
        
        if pays in distances_par_pays:
            distances_par_pays[pays] += distance
        else:
            distances_par_pays[pays] = distance

    pourcentages_par_pays = {pays: (distance / total_distance) * 100 for pays, distance in distances_par_pays.items()}
    
    return pourcentages_par_pays, total_distance

# Charger les frontières des pays
frontières = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))

def calculer_emissions(distance, facteur_emission):
    emissions = distance * facteur_emission  # en kg de CO2
    return emissions

def obtenir_coords_gare(nom_gare):
    url = f"https://public.opendatasoft.com/api/records/1.0/search/?dataset=europe-railway-station&q=\"{nom_gare}\"&rows=1"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['nhits'] > 0:
            record = data['records'][0]['fields']
            coords = record['geo_point_2d']
            return coords
        else:
            print(f"Aucune gare trouvée pour {nom_gare}")
            return None
    else:
        print(f"Erreur lors de la récupération des coordonnées de la gare : {response.status_code}")
        return None

def analyser_itineraires_depart_arrivee(depart, arrivee):
    # Obtenir les coordonnées des gares
    depart_coords = obtenir_coords_gare(depart)
    arrivee_coords = obtenir_coords_gare(arrivee)

    if not depart_coords or not arrivee_coords:
        return "Impossible de récupérer les coordonnées pour l'une ou l'autre des gares."

    gdf, train, train_dist = find_train(depart_coords, arrivee_coords)

    if train:
        pourcentages_par_pays, total_distance = calculer_pourcentages_par_pays(gdf, frontières)
        resultats = f"Pourcentage de voyage effectué dans chaque pays :\n"
        total_emissions = 0

        for pays, pourcentage in pourcentages_par_pays.items():
            distance_pays = (pourcentage / 100) * total_distance
            facteur_emission = facteurs_emission.get(pays, 0.5)  # Utiliser une valeur par défaut si le pays n'est pas dans le dictionnaire
            emissions_pays = calculer_emissions(distance_pays, facteur_emission)
            total_emissions += emissions_pays
            resultats += f"{pays}: {pourcentage:.2f}% de la distance, Emissions: {emissions_pays:.2f} kg CO2\n"

        resultats += f"Distance totale : {total_distance:.2f} km\n"
        resultats += f"Emissions totales de CO2 : {total_emissions:.2f} kg CO2"
        return resultats
    else:
        return "Échec de la récupération de l'itinéraire."

facteurs_emission = {
    "Corsica": 0.187,
    "Germany": 0.0668,
    "Austria": 0.0235,
    "Belgium": 0.0484,
    "Denmark": 0.114,
    "Spain": 0.0514,
    "Finland": 0.0452,
    "Greece": 0.0662,
    "Ireland": 0.0388,
    "Italy": 0.0317,
    "Luxembourg": 0.0397,
    "Norway": 0.0400,
    "Netherlands": 0.0763,
    "Portugal": 0.0615,
    "United Kingdom": 0.0750,
    "Sweden": 0.0129,
    "Switzerland": 0.00374,
    "France": 0.00369  # TGV valeur la plus élevée
}
