from model.recommender import compute_recommendations

def get_recommendations(movie):
    results = compute_recommendations(movie)

    if not results:
        return {"error": "Movie not found"}

    return {"recommendations": results}