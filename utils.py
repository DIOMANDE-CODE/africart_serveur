from math import radians, cos, sin, asin, sqrt


def calculer_distance_gps(lat1, lon1, lat2, lon2):
    """Calcule la distance en mètres entre deux points GPS"""
    if None in [lat1, lon1, lat2, lon2]:
        return float("inf")
    lon1, lat1, lon2, lat2 = map(
        radians, [float(lon1), float(lat1), float(lon2), float(lat2)]
    )
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * asin(sqrt(a)) * 6371000
