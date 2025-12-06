import spotipy
from spotipy.oauth2 import SpotifyOAuth
import csv
import os

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://127.0.0.1:8888/callback")

# Initialize Spotify client
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope="user-top-read",
))

print("Reading artist IDs from my_top_artists_GOOD.csv...")

# Read the CSV file and store artist IDs with their genres
artist_data = {}  # id -> {name, genres}
artist_ids = []

with open("./combineArtists/combined_artists.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        artist_id = row["id"]
        artist_ids.append(artist_id)
        artist_data[artist_id] = {
            "name": row["name"],
            "genres": row["genres"],
            "user": row["user"]
        }

print(f"Found {len(artist_ids)} artists in CSV")

# Fetch artist details in batches of 50 (API limit)
print("Fetching artist details from Spotify API...")
all_artist_details = []

for i in range(0, len(artist_ids), 50):
    batch = artist_ids[i:i+50]
    print(f"Fetching batch {i//50 + 1} ({len(batch)} artists)...")
    
    # Use the /artists endpoint to get multiple artists at once
    results = sp.artists(batch)
    
    for artist in results["artists"]:
        if artist:  # Check if artist data exists
            artist_id = artist["id"]

            api_genres = artist.get("genres", [])
            
            # Get genres from CSV (comma-separated string) and split into list
            csv_genres_str = artist_data[artist_id]["genres"]
            csv_genres = [g.strip() for g in csv_genres_str.split(",")] if csv_genres_str else []
            
            # Combine both lists (API genres first, then CSV genres) and remove duplicates
            combined_genres = list(set(api_genres + csv_genres))
            # Remove empty strings
            combined_genres = [g for g in combined_genres if g]
            # Sort for consistency
            combined_genres.sort()
            
            # Convert back to comma-separated string for CSV output
            genres_str = ", ".join(combined_genres)
            all_artist_details.append({
                "id": artist_id,
                "name": artist["name"],
                "popularity": artist["popularity"],
                "followers": artist["followers"]["total"],
                "genres": genres_str,  # Use genres from original CSV
                "user": artist_data[artist_id]["user"]
            })

# Write to new CSV file
output_file = "combined_artist_details_extended.csv"
with open(output_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "name", "popularity", "followers", "genres", "user"])
    
    for artist in all_artist_details:
        writer.writerow([
            artist["id"],
            artist["name"],
            artist["popularity"],
            artist["followers"],
            artist["genres"],
            artist["user"]
        ])

print(f"Saved {len(all_artist_details)} artists with extended details to {output_file}")

