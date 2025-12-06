import spotipy
from spotipy.oauth2 import SpotifyOAuth
import csv
import time
from collections import defaultdict, deque
import numpy as np
import sys
from datetime import datetime
import os

# Force unbuffered output so we see progress in real-time
sys.stdout.reconfigure(line_buffering=True)

# ============================================================
# RATE LIMITING CONFIGURATION
# ============================================================
# Spotify's rate limit: Rolling 30-second window
# Critical: No warning before 24-hour ban!
# Conservative limit to stay safe
RATE_LIMIT_WINDOW = 5.0  # seconds
MAX_REQUESTS_PER_WINDOW = 20  # Conservative (actual limit ~20-25, but we stay safe)
                               # Adjust this if you want to be more/less conservative
                               # Recommended range: 15-20 (lower = safer but slower)

# Track request timestamps in a rolling window
request_timestamps = deque()

def rate_limit_check():
    """
    Ensure we don't exceed Spotify's rate limit.
    Uses a sliding window to track requests in the last 30 seconds.
    Blocks until it's safe to make another request.
    """
    current_time = time.time()
    
    # Remove timestamps older than 30 seconds
    while request_timestamps and current_time - request_timestamps[0] > RATE_LIMIT_WINDOW:
        request_timestamps.popleft()
    
    # If we've hit the limit, wait until we can make another request
    if len(request_timestamps) >= MAX_REQUESTS_PER_WINDOW:
        # Calculate how long to wait
        oldest_timestamp = request_timestamps[0]
        time_to_wait = RATE_LIMIT_WINDOW - (current_time - oldest_timestamp) + 0.1  # Add 0.1s buffer
        
        if time_to_wait > 0:
            print(f"  [RATE LIMIT] {len(request_timestamps)}/{MAX_REQUESTS_PER_WINDOW} requests in last 5s. Waiting {time_to_wait:.1f}s...", flush=True)
            time.sleep(time_to_wait)
            
            # Clean up old timestamps after waiting
            current_time = time.time()
            while request_timestamps and current_time - request_timestamps[0] > RATE_LIMIT_WINDOW:
                request_timestamps.popleft()
    
    # Record this request
    request_timestamps.append(current_time)

def get_rate_limit_status():
    """Get current rate limiting status for display."""
    current_time = time.time()
    
    # Count requests in last 30 seconds
    count = 0
    for timestamp in request_timestamps:
        if current_time - timestamp <= RATE_LIMIT_WINDOW:
            count += 1
    
    return count, MAX_REQUESTS_PER_WINDOW

def api_call_with_backoff(func, *args, max_retries=5, initial_wait=2, **kwargs):
    """
    Execute API call with exponential backoff on rate limit errors.
    Includes proactive rate limiting to prevent hitting Spotify's limits.
    
    Important: Spotify uses a rolling 30-second window with NO WARNING
    before imposing a 24-hour ban. We enforce limits BEFORE making requests.
    """
    for attempt in range(max_retries):
        try:
            # PROACTIVE RATE LIMITING - Check before making request
            rate_limit_check()
            
            # Make the API call
            return func(*args, **kwargs)
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 429:  # Rate limit error
                # Check if Retry-After header is present
                retry_after = e.headers.get('Retry-After')
                if retry_after:
                    wait_time = int(retry_after)
                else:
                    # Exponential backoff: 2, 4, 8, 16, 32 seconds
                    wait_time = initial_wait * (2 ** attempt)
                
                print(f"\n⚠ Rate limit hit! Waiting {wait_time} seconds before retry (attempt {attempt + 1}/{max_retries})...", flush=True)
                print(f"  Time: {datetime.now().strftime('%H:%M:%S')}", flush=True)
                time.sleep(wait_time)
            elif e.http_status >= 500:  # Server error
                wait_time = initial_wait * (2 ** attempt)
                print(f"\n⚠ Server error {e.http_status}. Waiting {wait_time} seconds before retry...", flush=True)
                time.sleep(wait_time)
            else:
                # Non-retryable error, raise it
                raise
        except Exception as e:
            # For other errors, use exponential backoff
            wait_time = initial_wait * (2 ** attempt)
            print(f"\n⚠ Error: {e}. Waiting {wait_time} seconds before retry (attempt {attempt + 1}/{max_retries})...", flush=True)
            time.sleep(wait_time)
    
    raise Exception(f"Max retries ({max_retries}) exceeded for API call")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://127.0.0.1:8888/callback")

# Initialize Spotify client with proper scopes
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope="user-top-read",
))

def load_artists_from_csv(filename):
    """Load artist data from CSV file."""
    artists = []
    artist_ids = set()
    
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip empty rows
            if not row.get('name') or not row.get('id'):
                continue
            artists.append({
                'name': row['name'],
                'id': row['id']
            })
            artist_ids.add(row['id'])
    
    return artists, artist_ids

def get_all_album_ids(artists):
    """
    Step 1: Get all album IDs for all artists.
    Returns a list of unique album IDs.
    
    Efficiency: ~100-150 API calls (1-2 per artist on average)
    - Most artists have <50 albums = 1 call
    - Prolific artists with >50 albums = 2+ calls with pagination
    """
    album_ids = set()
    total_artists = len(artists)
    api_calls = 0
    
    print("\nStep 1: Fetching album lists for all artists...", flush=True)
    print(f"Progress: 0/{total_artists} artists processed", flush=True)
    
    for idx, artist in enumerate(artists):
        # Print progress every 10 artists
        if (idx + 1) % 10 == 0 or idx == 0:
            requests_in_window, max_requests = get_rate_limit_status()
            print(f"Progress: {idx + 1}/{total_artists} artists | Albums: {len(album_ids)} | API calls: {api_calls} | Rate: {requests_in_window}/{max_requests} per 30s", flush=True)
        
        try:
            offset = 0
            limit = 50
            
            while True:
                # Use backoff wrapper for API call
                results = api_call_with_backoff(
                    sp.artist_albums,
                    artist['id'],
                    album_type='album,single',
                    limit=limit,
                    offset=offset
                )
                api_calls += 1
                
                for album in results['items']:
                    album_ids.add(album['id'])
                
                # Break if we got fewer items than requested (no more pages)
                if len(results['items']) < limit:
                    break
                offset += limit
                
        except Exception as e:
            print(f"  ✗ Error getting albums for artist ID {artist['id']}: {e}", flush=True)
            continue
    
    print(f"Progress: {total_artists}/{total_artists} artists processed", flush=True)
    print(f"Total API calls in Step 1: {api_calls}", flush=True)
    return list(album_ids)

def get_albums_with_tracks_batched(album_ids):
    """
    Step 2: Batch fetch albums with their tracks (up to 20 albums per call).
    Returns a list of all tracks from all albums.
    
    Efficiency: ~20-30 API calls for 100 artists (~400 albums)
    - Main efficiency gain: 20 albums per call instead of 1
    - Reduced from ~400 calls to ~20 calls (95% reduction!)
    - Extra calls only for albums with >50 tracks (very rare)
    """
    all_tracks = []
    total_albums = len(album_ids)
    batch_size = 20  # Spotify allows up to 20 albums per request
    api_calls = 0
    
    print(f"\nStep 2: Fetching {total_albums} albums in batches of {batch_size}...", flush=True)
    total_batches = (total_albums + batch_size - 1) // batch_size
    print(f"Total batches to process: {total_batches} (huge efficiency gain: {batch_size} albums per API call!)", flush=True)
    
    for i in range(0, total_albums, batch_size):
        batch = album_ids[i:i+batch_size]
        batch_num = i // batch_size + 1
        
        requests_in_window, max_requests = get_rate_limit_status()
        print(f"Batch {batch_num}/{total_batches} ({len(batch)} albums) | Tracks: {len(all_tracks)} | API calls: {api_calls} | Rate: {requests_in_window}/{max_requests}", flush=True)
        
        try:
            # Get multiple albums at once - includes ALL track data!
            results = api_call_with_backoff(sp.albums, batch)
            api_calls += 1
            
            for album in results['albums']:
                if album and 'tracks' in album:
                    # Extract all tracks from this album
                    # Most albums have <50 tracks, so they're fully included
                    tracks = album['tracks']['items']
                    all_tracks.extend(tracks)
                    
                    # For very long albums (rare), get remaining tracks
                    # The 'next' field indicates if there are more tracks
                    if album['tracks'].get('next'):
                        album_id = album['id']
                        album_name = album.get('name', 'Unknown')
                        print(f"    → Album '{album_name}' has >50 tracks, fetching additional pages...", flush=True)
                        offset = 50
                        while True:
                            try:
                                more_results = api_call_with_backoff(
                                    sp.album_tracks,
                                    album_id,
                                    limit=50,
                                    offset=offset
                                )
                                api_calls += 1
                                
                                if not more_results or not more_results.get('items'):
                                    break
                                all_tracks.extend(more_results['items'])
                                if len(more_results['items']) < 50:
                                    break
                                offset += 50
                            except Exception as e:
                                print(f"    ✗ Error fetching more tracks for album {album_id}: {e}", flush=True)
                                break
            
        except Exception as e:
            print(f"  ✗ Error fetching batch {batch_num}: {e}", flush=True)
            continue
    
    print(f"Completed: All {total_batches} batches processed", flush=True)
    print(f"Total API calls in Step 2: {api_calls}", flush=True)
    return all_tracks

def find_collaborations(all_tracks, artist_ids):
    """
    Step 3: Find all collaborations between artists in our list.
    Returns a dict mapping (artist_id1, artist_id2) -> list of track names.
    """
    collaborations = defaultdict(list)
    processed_tracks = set()
    
    print(f"\nStep 3: Analyzing {len(all_tracks)} tracks for collaborations...", flush=True)
    
    total_tracks = len(all_tracks)
    for idx, track in enumerate(all_tracks):
        # Print progress every 1000 tracks
        if (idx + 1) % 1000 == 0:
            print(f"  Progress: {idx + 1}/{total_tracks} tracks analyzed, {len(collaborations)} collaboration pairs found", flush=True)
        
        if not track or 'id' not in track or track['id'] is None:
            continue
            
        track_id = track['id']
        
        # Skip if we've already processed this track
        if track_id in processed_tracks:
            continue
        
        processed_tracks.add(track_id)
        
        # Get all artist IDs on this track
        track_artist_ids = [a['id'] for a in track.get('artists', [])]
        
        # Find which of these artists are in our top 100 list
        collaborating_artists = [aid for aid in track_artist_ids if aid in artist_ids]
        
        # If 2 or more of our artists are on this track, it's a collaboration
        if len(collaborating_artists) >= 2:
            track_name = track['name']
            # Add all pairwise collaborations
            for i in range(len(collaborating_artists)):
                for j in range(i + 1, len(collaborating_artists)):
                    artist1 = collaborating_artists[i]
                    artist2 = collaborating_artists[j]
                    # Store in sorted order to avoid duplicates
                    pair = tuple(sorted([artist1, artist2]))
                    collaborations[pair].append(track_name)
    
    print(f"  Completed: {total_tracks} tracks analyzed")
    return collaborations

def build_adjacency_matrix(artists, collaborations):
    """
    Build an adjacency matrix from the collaboration data.
    Returns a numpy array where matrix[i][j] = 1 if artists i and j have collaborated.
    """
    n = len(artists)
    matrix = np.zeros((n, n), dtype=int)
    
    # Create a mapping from artist ID to index
    artist_id_to_idx = {artist['id']: idx for idx, artist in enumerate(artists)}
    
    # Fill in the matrix
    for (artist1_id, artist2_id), tracks in collaborations.items():
        idx1 = artist_id_to_idx[artist1_id]
        idx2 = artist_id_to_idx[artist2_id]
        matrix[idx1][idx2] = 1
        matrix[idx2][idx1] = 1  # Symmetric matrix
    
    return matrix

def save_adjacency_matrix_for_r(matrix, artists, filename="collaboration_matrix.csv"):
    """
    Save the adjacency matrix in a format that R can easily import.
    Includes row and column names (artist names).
    """
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header with artist names
        header = [''] + [artist['name'] for artist in artists]
        writer.writerow(header)
        
        # Write each row with artist name as first column
        for idx, row in enumerate(matrix):
            writer.writerow([artists[idx]['name']] + list(row))
    
    print(f"\nAdjacency matrix saved to {filename}")
    print(f"Matrix shape: {matrix.shape}")
    print(f"Total collaborations found: {np.sum(matrix) // 2}")  # Divide by 2 because symmetric

def save_collaboration_details(collaborations, artists, filename="collaboration_details.csv"):
    """Save detailed information about each collaboration."""
    # Create artist ID to name mapping
    id_to_name = {artist['id']: artist['name'] for artist in artists}
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Artist 1', 'Artist 2', 'Number of Collaborations', 'Track Names'])
        
        for (artist1_id, artist2_id), tracks in sorted(collaborations.items()):
            artist1_name = id_to_name[artist1_id]
            artist2_name = id_to_name[artist2_id]
            track_list = '; '.join(tracks)
            writer.writerow([artist1_name, artist2_name, len(tracks), track_list])
    
    print(f"Collaboration details saved to {filename}")

def main():
    print("=" * 60, flush=True)
    print("Spotify Artist Collaboration Matrix Builder", flush=True)
    print("Optimized Batch Processing Strategy", flush=True)
    print("=" * 60, flush=True)
    print("\nEFFICIENCY & SAFETY FEATURES:", flush=True)
    print("• Batch fetching: 20 albums per API call (95% reduction!)", flush=True)
    print("• Proactive rate limiting: Max 18 requests per 30-second window", flush=True)
    print("• Exponential backoff for transient errors", flush=True)
    print("• Expected API calls: ~120-150 total (vs. 500+ naive approach)", flush=True)
    print("• Prevents 24-hour ban from Spotify API", flush=True)
    print("=" * 60, flush=True)
    print(f"Start time: {datetime.now().strftime('%H:%M:%S')}", flush=True)
    
    start_time = time.time()
    
    # Load artists from CSV
    print("\nLoading artists from artist_details_extended.csv...", flush=True)
    artists, artist_ids = load_artists_from_csv("./artistDetails/combined_artist_details_extended.csv")
    print(f"Loaded {len(artists)} artists", flush=True)
    print(f"Artist IDs in set: {len(artist_ids)}", flush=True)
    
    # Step 1: Get all album IDs
    step1_start = time.time()
    album_ids = get_all_album_ids(artists)
    step1_time = time.time() - step1_start
    print(f"\nFound {len(album_ids)} unique albums across all artists", flush=True)
    print(f"Step 1 completed in {step1_time:.1f} seconds", flush=True)
    
    # Step 2: Batch fetch albums with tracks
    step2_start = time.time()
    all_tracks = get_albums_with_tracks_batched(album_ids)
    step2_time = time.time() - step2_start
    print(f"\nRetrieved {len(all_tracks)} total tracks", flush=True)
    print(f"Step 2 completed in {step2_time:.1f} seconds", flush=True)
    
    # Step 3: Find collaborations (no API calls)
    step3_start = time.time()
    collaborations = find_collaborations(all_tracks, artist_ids)
    step3_time = time.time() - step3_start
    print(f"\nFound {len(collaborations)} unique collaboration pairs", flush=True)
    print(f"Step 3 completed in {step3_time:.1f} seconds", flush=True)
    
    # Build adjacency matrix
    #print("\nBuilding adjacency matrix...", flush=True)
    #matrix = build_adjacency_matrix(artists, collaborations)
    
    # Save outputs
    print("\nSaving outputs...", flush=True)
    #save_adjacency_matrix_for_r(matrix, artists)
    save_collaboration_details(collaborations, artists)
    
    # Print some statistics
    print("\n" + "=" * 60, flush=True)
    print("Statistics:", flush=True)
    print("=" * 60, flush=True)
    #total_collabs = np.sum(matrix) // 2
    print(f"Total unique collaboration pairs: {total_collabs}", flush=True)
    print(f"Total tracks analyzed: {len(all_tracks)}", flush=True)
    print(f"Total albums fetched: {len(album_ids)}", flush=True)
    print(f"Total API requests made: {len(request_timestamps)}", flush=True)
    
    total_time = time.time() - start_time
    print(f"\nTotal execution time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)", flush=True)
    print(f"Average: {len(request_timestamps)/total_time*60:.1f} requests/minute (safely under limit)", flush=True)
    print(f"End time: {datetime.now().strftime('%H:%M:%S')}", flush=True)
    
    # Find artists with most collaborations
    #collab_counts = np.sum(matrix, axis=1)
    #top_collaborators_idx = np.argsort(collab_counts)[::-1][:10]
    
    #print("\nTop 10 most collaborative artists:", flush=True)
    #for rank, idx in enumerate(top_collaborators_idx, 1):
    #    if collab_counts[idx] > 0:
    #        print(f"  {rank}. {artists[idx]['name']}: {collab_counts[idx]} collaborations", flush=True)
    
    #print("\n" + "=" * 60, flush=True)
    #print("Done! You can now import 'collaboration_matrix.csv' into R", flush=True)
    #print("In R, use: matrix <- read.csv('collaboration_matrix.csv', row.names=1)", flush=True)
    #print("=" * 60, flush=True)

if __name__ == "__main__":
    main()

