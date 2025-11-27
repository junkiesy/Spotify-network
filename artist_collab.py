
import os
import time
import csv
import requests
from typing import List, Dict, Set, Tuple
from dotenv import load_dotenv

# --------------------------------------------------------------------
# Config
# --------------------------------------------------------------------
load_dotenv()

CLIENT_ID = ""
CLIENT_SECRET = ""

if not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in environment or .env")

TOKEN_URL = "https://accounts.spotify.com/api/token"
BASE_URL = "https://api.spotify.com/v1"

REQUEST_SLEEP_SECONDS = 0.05  # 50 ms between requests
MAX_ALBUMS_PER_ARTIST = 300   # limit of 300 album/single releases per artist

INPUT_CSV = "merged_top_artists.csv"
OUTPUT_CSV = "artist_collaborators_network.csv"


# --------------------------------------------------------------------
# Auth + request helper
# --------------------------------------------------------------------
def get_access_token() -> str:
    """Client credentials grant. Returns a Bearer token."""
    resp = requests.post(
        TOKEN_URL,
        data={"grant_type": "client_credentials"},
        auth=(CLIENT_ID, CLIENT_SECRET),
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["access_token"]


def spotify_get(
    url: str,
    params: Dict = None,
    token: str = None,
    max_retries: int = 5
) -> Dict:
    """
    Wrapper around GET that:
    - Adds Authorization header
    - Handles 429 rate limits with Retry-After
    - Retries a few times for safety
    """
    if token is None:
        token = get_access_token()

    headers = {"Authorization": f"Bearer {token}"}

    for attempt in range(max_retries):
        time.sleep(REQUEST_SLEEP_SECONDS)
        r = requests.get(url, headers=headers, params=params, timeout=15)

        if r.status_code == 429:
            retry_after = int(r.headers.get("Retry-After", "1"))
            print(f"[RATE LIMIT] 429 received. Sleeping for {retry_after} seconds...")
            time.sleep(retry_after)
            continue

        r.raise_for_status()
        return r.json()

    # If we got here, something went wrong repeatedly
    r.raise_for_status()


# --------------------------------------------------------------------
# Core helpers
# --------------------------------------------------------------------
def get_artist_albums_albums_and_singles(
    artist_id: str,
    token: str,
    per_page: int = 50,
    market: str = "US",
    max_albums: int = MAX_ALBUMS_PER_ARTIST,
) -> List[Dict]:
    """
    Fetch up to `max_albums` releases for the artist that are only:
      - album
      - single
    Excludes compilation and appears_on.
    """
    url = f"{BASE_URL}/artists/{artist_id}/albums"
    params = {
        "include_groups": "album,single",   # only album + single
        "limit": per_page,
        "offset": 0,
        "market": market,
    }

    all_items: List[Dict] = []
    seen_album_ids: Set[str] = set()

    while True:
        data = spotify_get(url, params=params, token=token)
        items = data.get("items", [])
        if not items:
            break

        for alb in items:
            alb_id = alb["id"]
            if alb_id not in seen_album_ids:
                seen_album_ids.add(alb_id)
                all_items.append(alb)

                if len(all_items) >= max_albums:
                    print(
                        f"  Reached max albums per artist ({max_albums}). "
                        f"Stopping album fetch for this artist."
                    )
                    return all_items

        print(
            f"  Fetched {len(items)} albums/singles this page "
            f"(total unique so far: {len(all_items)})"
        )

        if not data.get("next"):
            break

        params["offset"] += per_page

    return all_items


def get_all_album_tracks(
    album_id: str,
    token: str,
    per_page: int = 50,
    market: str = "US"
) -> List[Dict]:
    """
    Fetch **all** tracks for an album using pagination.
    """
    url = f"{BASE_URL}/albums/{album_id}/tracks"
    params = {
        "limit": per_page,
        "offset": 0,
        "market": market,
    }

    tracks: List[Dict] = []

    while True:
        data = spotify_get(url, params=params, token=token)
        items = data.get("items", [])
        if not items:
            break

        tracks.extend(items)

        if not data.get("next"):
            break

        params["offset"] += per_page

    return tracks


def extract_collaborators_from_tracks(
    tracks: List[Dict],
    primary_artist_id: str
) -> Set[Tuple[str, str]]:
    """
    From track objects, find all (artist_id, artist_name) that appear with primary_artist_id.
    """
    collaborators: Set[Tuple[str, str]] = set()

    for t in tracks:
        artists = t.get("artists", [])
        artist_ids = {a["id"] for a in artists if a.get("id")}
        if primary_artist_id not in artist_ids:
            # Track doesn't actually feature the primary artist → skip
            continue

        for a in artists:
            aid = a.get("id")
            if not aid or aid == primary_artist_id:
                continue
            collaborators.add((aid, a["name"]))

    return collaborators


def get_collaborators_for_artist_id(
    artist_name: str,
    artist_id: str,
    token: str
) -> List[Dict]:
    """
    Get collaborators for a given artist (by ID), using up to MAX_ALBUMS_PER_ARTIST album+single releases.
    """
    print(f"\n=== Processing artist: {artist_name} ({artist_id}) ===")
    albums = get_artist_albums_albums_and_singles(artist_id, token)
    print(
        f"Total album+single releases used for {artist_name}: "
        f"{len(albums)} (limit {MAX_ALBUMS_PER_ARTIST})"
    )

    all_tracks: List[Dict] = []

    for idx, alb in enumerate(albums, start=1):
        alb_id = alb["id"]
        alb_name = alb.get("name", "Unknown album")

        tracks = get_all_album_tracks(alb_id, token)
        print(f"    [{idx}/{len(albums)}] Album/Single '{alb_name}' → {len(tracks)} tracks")

        all_tracks.extend(tracks)

    print(f"  Total tracks collected for {artist_name}: {len(all_tracks)}")

    collab_set = extract_collaborators_from_tracks(all_tracks, artist_id)
    print(f"  Found {len(collab_set)} unique collaborators for {artist_name}.")

    collab_list = [
        {
            "primary_artist": artist_name,
            "primary_artist_id": artist_id,
            "collaborator_id": cid,
            "collaborator_name": cname,
        }
        for (cid, cname) in sorted(collab_set, key=lambda x: x[1].lower())
    ]
    return collab_list


# --------------------------------------------------------------------
# CSV helpers (crash-safe / resumable)
# --------------------------------------------------------------------
def load_already_processed_artists(output_csv: str) -> Set[str]:
    """
    Look at the existing OUTPUT_CSV and return a set of primary_artist_id
    that are already present, so we can skip them on reruns.
    """
    if not os.path.exists(output_csv):
        return set()

    processed: Set[str] = set()
    with open(output_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            artist_id = row.get("primary_artist_id")
            if artist_id:
                processed.add(artist_id)
    return processed


def append_collaborators_to_csv(
    collaborators: List[Dict],
    output_csv: str
) -> None:
    """
    Append collaborator rows to the output CSV.
    Writes header if file doesn't exist yet.
    """
    if not collaborators:
        print("  No collaborators to write for this artist.")
        return

    file_exists = os.path.exists(output_csv)
    fieldnames = list(collaborators[0].keys())

    with open(output_csv, "a" if file_exists else "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(collaborators)

    print(f"  Wrote {len(collaborators)} rows to {output_csv}")


def load_artists_from_input(input_csv: str) -> List[Tuple[str, str]]:
    """
    Read merged_top_artists.csv and return a list of (name, id).
    Assumes the CSV has columns 'name' and 'id'.
    """
    artists: List[Tuple[str, str]] = []
    with open(input_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("name")
            artist_id = row.get("id")
            if not name or not artist_id:
                continue
            artists.append((name, artist_id))
    return artists


# --------------------------------------------------------------------
# Main pipeline
# --------------------------------------------------------------------
def main():
    if not os.path.exists(INPUT_CSV):
        raise FileNotFoundError(f"Input CSV not found: {INPUT_CSV}")

    # Load full artist list from input
    artists = load_artists_from_input(INPUT_CSV)
    total_artists = len(artists)
    print(f"Loaded {total_artists} artists from {INPUT_CSV}")

    # Load all already processed artists from output
    processed_ids = load_already_processed_artists(OUTPUT_CSV)
    processed_count = len(processed_ids)

    # Compute how many in the input are already done
    already_done_in_input = [a for a in artists if a[1] in processed_ids]
    remaining_artists = [a for a in artists if a[1] not in processed_ids]

    remaining_count = len(remaining_artists)

    # Find the first artist we still need to process (by input order)
    first_unprocessed_idx = None
    first_unprocessed_artist = None
    for idx, (name, artist_id) in enumerate(artists, start=1):
        if artist_id not in processed_ids:
            first_unprocessed_idx = idx
            first_unprocessed_artist = (name, artist_id)
            break

    print(f"Artists with data already in {OUTPUT_CSV}: {processed_count}")
    print(f"Of those, {len(already_done_in_input)} are present in the current input list.")
    print(f"Remaining to process (from this input CSV): {remaining_count}")

    if first_unprocessed_artist:
        fname, fid = first_unprocessed_artist
        print(
            f"First unprocessed artist in input order: #{first_unprocessed_idx} "
            f"- {fname} ({fid})"
        )
    else:
        print("All artists in the input CSV appear to be processed already.")
        # You could return early here if you want:
        # return

    # Now actually call Spotify
    token = get_access_token()

    for idx, (name, artist_id) in enumerate(artists, start=1):
        if artist_id in processed_ids:
            print(f"\n[{idx}/{total_artists}] Skipping already processed artist: {name} ({artist_id})")
            continue

        print(f"\n[{idx}/{total_artists}] Starting artist: {name} ({artist_id})")

        try:
            collabs = get_collaborators_for_artist_id(name, artist_id, token)
            append_collaborators_to_csv(collabs, OUTPUT_CSV)
            processed_ids.add(artist_id)
        except KeyboardInterrupt:
            print("\nInterrupted by user (Ctrl+C). Progress so far is saved in the CSV.")
            break
        except Exception as e:
            # Don't crash the whole run on one bad artist
            print(f"  ERROR while processing {name} ({artist_id}): {e}")
            # Optional: log to separate file, but don't stop the pipeline


if __name__ == "__main__":
    main()