import spotipy
from spotipy.oauth2 import SpotifyOAuth
import csv

import os

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://127.0.0.1:8888/callback")

# Initialize Spotify client with proper scopes
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope="user-top-read user-read-recently-played",  # Added recently-played scope
))

all_artists = {}  # id -> artist obj

print("Fetching your top artists from Spotify...")

def fetch_top(time_range):
    top = sp.current_user_top_artists(limit=50, time_range=time_range)
    for a in top["items"]:
        all_artists[a["id"]] = a


#1) get all top windows
fetch_top("short_term")
fetch_top("medium_term")
fetch_top("long_term")

#2) if still less than 100, pad with artists from recently played
if len(all_artists) < 100:
    recent = sp.current_user_recently_played(limit=50)
    for item in recent["items"]:
        track = item["track"]
        for artist in track["artists"]:
            # fetch full artist details (to get genres)
            if artist["id"] not in all_artists:
                full = sp.artist(artist["id"])
                all_artists[artist["id"]] = full
            if len(all_artists) >= 100:
                break
        if len(all_artists) >= 100:
            break

#3) turn into list and cut to 100 max
artists_list = list(all_artists.values())[:100]

#4) write CSV
with open("my_top_artists.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["name", "id", "genres"])
    for a in artists_list:
        genres = ", ".join(a.get("genres", []))
        writer.writerow([a["name"], a["id"], genres])

print(f"saved {len(artists_list)} artists to my_top_artists.csv")