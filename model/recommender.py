import pandas as pd
import warnings
import os
from rapidfuzz import process

warnings.filterwarnings("ignore")

# ================================
# LOAD DATA
# ================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

movies = pd.read_csv(os.path.join(BASE_DIR, '..', 'data', 'movies.csv'))

def get_all_titles():
    return movies['title'].dropna().unique()

ratings = pd.read_csv(os.path.join(BASE_DIR, '..', 'data', 'ratings.csv'))

movies['title'] = movies['title'].str.strip()
movies['genres'] = movies['genres'].str.replace('|', ' ', regex=False)

data = pd.merge(ratings, movies, on="movieId")

ratings_count = data.groupby('title')['rating'].count().reset_index()
ratings_count.columns = ['title', 'num_ratings']

popular_movies = ratings_count[ratings_count['num_ratings'] > 100]
data = data.merge(popular_movies, on='title')

movie_matrix = data.pivot_table(index='userId', columns='title', values='rating')
movie_matrix.columns = movie_matrix.columns.str.strip()

# ================================
# CONTENT MODEL
# ================================
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

vectorizer = CountVectorizer()
genre_matrix = vectorizer.fit_transform(movies['genres'])
cosine_sim = cosine_similarity(genre_matrix)

# ================================
# HELPERS
# ================================
def mood_score(genres, mood):
    if mood == "happy" and "Comedy" in genres:
        return 1
    elif mood == "sad" and "Drama" in genres:
        return 1
    elif mood == "thrilling" and ("Action" in genres or "Thriller" in genres):
        return 1
    return 0


def generate_explanation(genres, mood, collab, content):
    reasons = []

    if mood == "happy" and "Comedy" in genres:
        reasons.append("good for a happy mood")

    if content > 0.7:
        reasons.append("strong genre match")

    if collab > 0.5:
        reasons.append("popular among similar users")

    if "Animation" in genres:
        reasons.append("visually engaging")

    return ", ".join(reasons) if reasons else "recommended based on similarity"


def find_closest_movie(name):
    titles = movie_matrix.columns.tolist()
    match = process.extractOne(name, titles)

    if match:
        return match[0]
    return None

# ================================
# HYBRID RECOMMENDER
# ================================
def hybrid_recommendations(title, mood):
    title = title.strip()

    correct_title = find_closest_movie(title)

    if not correct_title or correct_title not in movie_matrix.columns:
        return None

    title = correct_title

    try:
        sample_movie = movie_matrix[title]
        collab_scores = movie_matrix.corrwith(sample_movie)
    except:
        return None

    collab_df = pd.DataFrame(collab_scores, columns=['collab_score'])
    collab_df.dropna(inplace=True)

    ratings_count = data.groupby('title')['rating'].count()
    collab_df['num_ratings'] = ratings_count
    collab_df = collab_df[collab_df['num_ratings'] > 100]

    idx = movies[movies['title'].str.strip() == title.strip()].index
    if len(idx) == 0:
        return None

    idx = idx[0]

    content_scores = list(enumerate(cosine_sim[idx]))
    content_df = pd.DataFrame(content_scores, columns=['movie_index', 'content_score'])
    content_df['title'] = content_df['movie_index'].apply(lambda x: movies.iloc[x]['title'])
    content_df.set_index('title', inplace=True)

    hybrid = collab_df.join(content_df[['content_score']], how='inner')
    hybrid = hybrid.merge(movies[['title', 'genres']], on='title')

    hybrid['explanation'] = hybrid.apply(
        lambda row: generate_explanation(
            row['genres'], mood, row['collab_score'], row['content_score']
        ),
        axis=1
    )

    hybrid['mood_score'] = hybrid['genres'].apply(lambda x: mood_score(x, mood))

    hybrid['final_score'] = (
        0.4 * hybrid['collab_score'] +
        0.4 * hybrid['content_score'] +
        0.2 * hybrid['mood_score']
    )

    hybrid = hybrid.sort_values('final_score', ascending=False)
    hybrid = hybrid[hybrid['title'] != title]
    hybrid = hybrid.reset_index(drop=True)

    return hybrid[['title', 'final_score', 'explanation']].head(10)

# ================================
# MAIN FUNCTION
# ================================
def get_recommendations(movie_name, mood):

    results = hybrid_recommendations(movie_name, mood)

    if results is not None and not results.empty:
        output = []

        for _, row in results.iterrows():
            output.append({
                "title": row['title'],
                "score": float(row['final_score']),
                "explanation": row['explanation']
            })

        return output

    return [{
        "title": "Movie not found in dataset",
        "score": 0,
        "explanation": "Try another movie"
    }]