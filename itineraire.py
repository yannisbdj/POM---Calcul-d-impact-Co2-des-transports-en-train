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
        f"https://signal.eu.org/osm/eu/route/v1/train/{tag1[0]},{tag1[1]};{tag2[0]},{tag2[1]}?overview="
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

def analyser_itineraires_depart_arrivee(depart, arrivee):
    # Obtenir les coordonnées des villes
    depart_coords = (depart[1], depart[0])  # (longitude, latitude)
    arrivee_coords = (arrivee[1], arrivee[0])  # (longitude, latitude)

    # Trouver l'itinéraire en train
    gdf, train, train_dist = find_train(depart_coords, arrivee_coords)

    if train:
        # Calculer les pourcentages par pays
        pourcentages_par_pays, total_distance = calculer_pourcentages_par_pays(gdf, frontières)
        resultats = f"Pourcentage de voyage effectué dans chaque pays :\n"
        for pays, pourcentage in pourcentages_par_pays.items():
            resultats += f"{pays}: {pourcentage:.2f}%\n"
        resultats += f"Distance totale : {total_distance:.2f} km"
        return resultats
    else:
        return "Échec de la récupération de l'itinéraire."

# Dictionnaire des capitales européennes avec leurs coordonnées
capitales_coordinates = {
    "Amsterdam": (52.3676, 4.9041),
    "Andorra la Vella": (42.5078, 1.5211),
    "Athens": (37.9838, 23.7275),
    "Belgrade": (44.7866, 20.4489),
    "Berlin": (52.52, 13.41),
    "Bern": (46.9481, 7.4474),
    "Bratislava": (48.1486, 17.1077),
    "Brussels": (50.8503, 4.3517),
    "Bucharest": (44.4268, 26.1025),
    "Budapest": (47.4979, 19.0402),
    "Chisinau": (47.0105, 28.8638),
    "Copenhagen": (55.6761, 12.5683),
    "Dublin": (53.3498, -6.2603),
    "Helsinki": (60.1695, 24.9355),
    "Kiev": (50.4501, 30.5234),
    "Lisbon": (38.7223, -9.1393),
    "Ljubljana": (46.0569, 14.5058),
    "London": (51.5074, -0.1278),
    "Luxembourg": (49.6117, 6.13),
    "Madrid": (40.4168, -3.7038),
    "Minsk": (53.9, 27.5667),
    "Monaco": (43.7384, 7.4246),
    "Moscow": (55.7558, 37.6173),
    "Oslo": (59.9139, 10.7522),
    "Paris": (48.8566, 2.3522),
    "Podgorica": (42.441, 19.2636),
    "Prague": (50.0755, 14.4378),
    "Reykjavik": (64.1355, -21.8954),
    "Riga": (56.9496, 24.1052),
    "Rome": (41.9028, 12.4964),
    "San Marino": (43.9424, 12.4578),
    "Sarajevo": (43.8563, 18.4131),
    "Skopje": (41.9981, 21.4254),
    "Sofia": (42.6977, 23.3219),
    "Stockholm": (59.3293, 18.0686),
    "Tallinn": (59.437, 24.7535),
    "Tirana": (41.3275, 19.8189),
    "Vaduz": (47.141, 9.5209),
    "Valletta": (35.8989, 14.5146),
    "Vienna": (48.2082, 16.3738),
    "Vilnius": (54.6872, 25.2797),
    "Warsaw": (52.2297, 21.0122),
    "Zagreb": (45.815, 15.9819)
}

#print(analyser_itineraires_depart_arrivee(capitales_coordinates["Berlin"],capitales_coordinates["Prague"]))