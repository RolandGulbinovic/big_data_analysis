import json
import pandas as pd
import os
from collections import defaultdict
from collections import Counter

# Get rid of movies that don't have assigned cast or a genre.
def clean_movies(movies):
    cleaned = []
    for movie in movies:
        cast = movie.get('cast', [])
        genres = movie.get('genres', [])
        if cast and genres:  # Only keep if both are non-empty
            cleaned.append(movie)

    return cleaned

# Get statistics about movies for each decade:
# Returns dictionary:
#   Decade:
#   top_actor - the actor that had the most movies
#   actor_count - how many movies that actor has been in
#   top_genre - most frequent genre
#   genre_movies - how many movies of that genre

def get_most_frequent_by_decade(movies):
    decade_actors = defaultdict(list)
    decade_genre = defaultdict(list)

    # Separate actors and genres by decade
    for movie in movies:
        year = movie.get('year')
        if year is None:
            continue  # skip if no year

        decade = (year // 10) * 10
        # Add cast members
        for actor in movie.get('cast', []):
            decade_actors[decade].append(actor)

        # Add directors
        for genres in movie.get('genres', []):
            decade_genre[decade].append(genres)


    result = {}
    # # Calculate the statistics of most common actors and genres and store it in result[decade]
    for decade in sorted(decade_actors.keys()):
        top_actor = Counter(decade_actors[decade]).most_common(1)[0][0]
        actor_count = Counter(decade_actors[decade]).most_common(1)[0][1]
        top_genre = Counter(decade_genre[decade]).most_common(1)[0][0]
        genre_count = Counter(decade_genre[decade]).most_common(1)[0][1]

        result[decade] = {
            'top_actor': top_actor,
            'actor_movies': actor_count,
            'top_genre': top_genre,
            'genre_movies': genre_count
        }

    return result


def print_results(data):
    print("\n Summary:")
    for decade, info in sorted(data.items()):
        print("=" * 40)
        print(f"{decade}s:")
        for key, value in info.items():
            print(f"  {key.replace('_', ' ').title()}: {value}")
        print()

# Save the results as a .json and as a .csv file
def save_summary(data):
    json_path = os.path.join('summary.json')
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Saved JSON to {json_path}")

    df = pd.DataFrame.from_dict(data, orient='index')
    df.index.name = 'decade'
    df.reset_index(inplace=True)

    csv_path = os.path.join('summary.csv')
    df.to_csv(csv_path, index=False)
    print(f"Saved CSV to {csv_path}")


def main():
    with open('data/movies.json', 'r') as f:
        movies = json.load(f)

    cleaned_movies = clean_movies(movies)

    results = get_most_frequent_by_decade(cleaned_movies)
    print_results(results)
    save_summary(results)


if __name__ == "__main__":
    main()