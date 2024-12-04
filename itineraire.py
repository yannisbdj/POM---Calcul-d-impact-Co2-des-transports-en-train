import requests
import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point
from http import HTTPStatus
from geopy.distance import geodesic
import concurrent.futures
import functools
import time

train_t = "1"
train_s = "full"

@functools.lru_cache(maxsize=None)
def obtenir_coords_gare(nom_gare):
    start_time = time.time()
    url = f"https://public.opendatasoft.com/api/records/1.0/search/?dataset=europe-railway-station&q=\"{nom_gare}\"&rows=1"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['nhits'] > 0:
            record = data['records'][0]['fields']
            coords = record['geo_point_2d']
            end_time = time.time()
            print(f"obtenir_coords_gare({nom_gare}) a pris {end_time - start_time:.2f} secondes")
            return coords
        else:
            print(f"Aucune gare trouvée pour {nom_gare}")
    else:
        print(f"Erreur lors de la récupération des coordonnées de la gare : {response.status_code}")
    
    end_time = time.time()
    print(f"obtenir_coords_gare({nom_gare}) a pris {end_time - start_time:.2f} secondes (échec)")
    return None

def find_train(tag1, tag2):
    start_time = time.time()
    url = (
        f"https://signal.eu.org/osm/eu/route/v1/train/{tag1[1]},{tag1[0]};{tag2[1]},{tag2[0]}?overview="
        + train_s
        + "&geometries=geojson"
    )
    response = requests.get(url)
    if response.status_code == HTTPStatus.OK:
        train_dist = response.json()["routes"][0]["distance"] / 1e3  # km
        gdf = gpd.GeoSeries(
            LineString(response.json()["routes"][0]["geometry"]["coordinates"]),
            crs="epsg:4326",
        )
        end_time = time.time()
        print(f"find_train({tag1}, {tag2}) a pris {end_time - start_time:.2f} secondes")
        return gdf, True, train_dist
    else:
        print(f"Erreur lors de la récupération de l'itinéraire : {response.status_code}, {response.text}")
    
    end_time = time.time()
    print(f"find_train({tag1}, {tag2}) a pris {end_time - start_time:.2f} secondes (échec)")
    return pd.DataFrame(), False, 0

def calculer_pourcentages_par_pays(gdf, frontières):
    start_time = time.time()
    distances_par_pays = {}
    total_distance = 0
    
    points = list(gdf.geometry[0].coords)
    pays_points = [frontières[frontières.contains(Point(coord))]['name'].values[0] for coord in points]
    
    for i in range(len(points) - 1):
        point1 = points[i]
        point2 = points[i + 1]
        lat1, lon1 = point1[1], point1[0]
        lat2, lon2 = point2[1], point2[0]
        
        distance = geodesic((lat1, lon1), (lat2, lon2)).kilometers
        total_distance += distance
        
        pays1 = pays_points[i]
        pays2 = pays_points[i + 1]
        
        pays = pays1 if pays1 == pays2 else pays1
        
        if pays in distances_par_pays:
            distances_par_pays[pays] += distance
        else:
            distances_par_pays[pays] = distance

    pourcentages_par_pays = {pays: (distance / total_distance) * 100 for pays, distance in distances_par_pays.items()}
    end_time = time.time()
    print(f"calculer_pourcentages_par_pays a pris {end_time - start_time:.2f} secondes")
    return pourcentages_par_pays, total_distance


frontières = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))

def calculer_emissions(distance, facteur_emission):
    start_time = time.time()
    emissions = distance * facteur_emission  # en kg de CO2
    end_time = time.time()
    print(f"calculer_emissions a pris {end_time - start_time:.2f} secondes")
    return emissions

def analyser_itineraires_depart_arrivee(depart, arrivee):
    start_time = time.time()
    depart_coords = obtenir_coords_gare(depart)
    arrivee_coords = obtenir_coords_gare(arrivee)

    if not depart_coords or not arrivee_coords:
        print(f"Impossible de récupérer les coordonnées pour {depart} ou {arrivee}")
        end_time = time.time()
        print(f"analyser_itineraires_depart_arrivee({depart}, {arrivee}) a pris {end_time - start_time:.2f} secondes (échec)")
        return {
            'destination': arrivee,
            'depart': depart,
            'distance': 'Échec',
            'co2': 'Échec'
        }

    gdf, train, train_dist = find_train(depart_coords, arrivee_coords)

    if train:
        pourcentages_par_pays, total_distance = calculer_pourcentages_par_pays(gdf, frontières)
        total_emissions = 0

        for pays, pourcentage in pourcentages_par_pays.items():
            distance_pays = (pourcentage / 100) * total_distance
            facteur_emission = facteurs_emission.get(pays, 0.5)
            emissions_pays = calculer_emissions(distance_pays, facteur_emission)
            total_emissions += emissions_pays

        end_time = time.time()
        print(f"analyser_itineraires_depart_arrivee({depart}, {arrivee}) a pris {end_time - start_time:.2f} secondes")
        return {
            'destination': arrivee,
            'depart': depart,
            'distance': total_distance,
            'co2': total_emissions
        }
    else:
        end_time = time.time()
        print(f"analyser_itineraires_depart_arrivee({depart}, {arrivee}) a pris {end_time - start_time:.2f} secondes (échec)")
        return {
            'destination': arrivee,
            'depart': depart,
            'distance': 'Échec',
            'co2': 'Échec'
        }

def analyser_itineraires_parallel(depart_values, destination_values):
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(analyser_itineraires_depart_arrivee, depart_values[f'-DEPART{i}-'], destination): (i, destination)
                   for i in range(len(depart_values))
                   for destination in destination_values}
        resultats = [future.result() for future in concurrent.futures.as_completed(futures)]
    end_time = time.time()
    print(f"analyser_itineraires_parallel a pris {end_time - start_time:.2f} secondes")
    
    co2_results = []
    distance_results = []
    
    for resultat in resultats:
        co2_results.append({
            'destination': resultat['destination'],
            'depart': resultat['depart'],
            'co2': resultat['co2']
        })
        distance_results.append({
            'destination': resultat['destination'],
            'depart': resultat['depart'],
            'distance': resultat['distance']
        })
    
    return co2_results, distance_results

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
