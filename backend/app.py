import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, request, jsonify
from flask_cors import CORS
from model.recommender import get_recommendations, get_all_titles
import requests

app = Flask(__name__)
CORS(app)

# ==============================
# TMDB CONFIG
# ==============================
API_KEY = "29079babcf7421fdad77eb958f4c4243"

# ==============================
# SAFE REQUEST (RETRY LOGIC)
# ==============================
def safe_request(url):
    for _ in range(3):
        try:
            response = requests.get(url, verify=False, timeout=5)
            return response.json()
        except:
            continue
    return {}

# ==============================
# HOME ROUTE
# ==============================
@app.route('/')
def home_page():
    return "Movie Recommender API is running"


# ==============================
# RECOMMENDATION ROUTE
# ==============================
@app.route('/recommend', methods=['POST'])
def recommend():
    try:
        data = request.json
        movie = data.get("movie")
        mood = data.get("mood")

        if not movie or not mood:
            return jsonify({"error": "Missing movie or mood"}), 400

        results = get_recommendations(movie, mood)

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==============================
# TRENDING MOVIES
# ==============================
@app.route('/trending', methods=['GET'])
def trending():
    try:
        url = f"https://api.themoviedb.org/3/trending/movie/week?api_key={API_KEY}"
        data = safe_request(url)

        if "results" not in data:
            return jsonify([])

        movies = []
        for m in data.get('results', [])[:6]:
            movies.append({
                "title": m.get('title'),
                "overview": m.get('overview'),
                "rating": m.get('vote_average'),
                "poster": f"https://image.tmdb.org/t/p/w500{m.get('poster_path')}" if m.get('poster_path') else ""
            })

        return jsonify(movies)

    except Exception as e:
        print("TRENDING ERROR:", e)
        return jsonify([])


# ==============================
# COMBINED HOME API
# ==============================
@app.route('/home', methods=['POST'])
def home():
    try:
        data = request.json
        movie = data.get("movie")
        mood = data.get("mood")

        recommendations = get_recommendations(movie, mood)

        url = f"https://api.themoviedb.org/3/trending/movie/week?api_key={API_KEY}"
        tmdb_data = safe_request(url)

        trending = []
        for m in tmdb_data.get('results', [])[:6]:
            trending.append({
                "title": m.get('title'),
                "poster": f"https://image.tmdb.org/t/p/w500{m.get('poster_path')}" if m.get('poster_path') else "",
                "rating": m.get('vote_average'),
                "overview": m.get('overview')
            })

        return jsonify({
            "recommended": recommendations,
            "trending": trending
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==============================
# 🔥 SEARCH ROUTE (AUTOCOMPLETE)
# ==============================
@app.route('/search')
def search():
    query = request.args.get('q', '').lower()

    if not query:
        return jsonify([])

    titles = get_all_titles()

    results = [t for t in titles if query in t.lower()][:10]

    return jsonify(results)


# ==============================
# RUN SERVER (ONLY THIS INSIDE MAIN)
# ==============================
if __name__ == "__main__":
    app.run(debug=True)