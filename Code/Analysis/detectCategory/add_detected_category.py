import csv
import sys

GENRE_MAP = {
    "Electronic": {
        "electroclash", "witch house", "new rave", "alternative dance",
        "hyperpop", "edm", "big room", "trance", "electronica", "idm",
        "breakcore", "jungle", "speedcore", "vaporwave", "chillwave",
        "downtempo", "melodic bass"
    },
    "Pop": {
        "pop", "new wave", "art pop", "hyperpop", "soft pop",
        "dance pop", "j-pop", "dream pop", "bedroom pop", "alt pop",
        "moroccan pop", "french pop", "iranian pop", "persian pop"
    },
    "Rock/Metal": {
        "art rock", "proto-punk", "rock", "gothic rock", "post-punk",
        "darkwave", "garage rock", "post-rock", "grunge", "post-grunge",
        "alternative rock", "alternative metal", "djent",
        "progressive metal", "progressive rock", "indie rock",
        "shoegaze", "nu metal", "rap metal", "classic rock",
        "hard rock", "space rock", "surf rock",
        "emo", "math rock", "midwest emo", "screamo", "post-hardcore"
    },
    "Alternative/Indie": {
        "indie", "alt", "alternative", "alternative dance",
        "alternative rock", "alternative metal",
        "indie rock", "lo-fi indie", "alternaive", "neo-psychedelic",
        "midwest emo"
    },
    "Folk": {
        "folk", "folk punk", "anti-folk", "indie folk", "georgian folk"
    },
    "Classical": {
        "chamber music", "classical", "classical piano",
        "opera", "orchestral", "requiem"
    },
    "Hip Hop/Rap": {
        "brooklyn drill", "melodic rap", "hip hop", "rap", "chicago drill",
        "drill", "g-funk", "gangster rap", "old school hip hop",
        "west coast hip hop", "rap metal",
        "east coast hip hop", "trap", "detroit hip hop",
        "southern hip hop", "brooklyn drill",
        "uk drill", "new york drill",
        "grime", "uk grime", "cloud rap", "rage rap",
        "alternative hip hop", "jazz rap",
        "boom bap", "experimental hip hop", "hiphop",
        "arabic hip hop", "moroccan rap", "latin hip hop", "latin trap"
    },
    "R&B": {
        "dark r&b", "r&b", "alternative r&b", "soul", "afro r&b"
    },
    "Jazz": {
        "cool jazz", "jazz", "swing music",
        "bebop", "hard bop", "jazz blues",
        "vocal jazz", "big band"
    },
    "Other": {
        "bhajan", "vocal", "anime", "gregorian chant",
        "new age", "christmas", "soundtrack"
    },
    "International": {
        "bhajan", "arabic hip hop", "moroccan rap", "moroccan pop", "french pop",
        "iranian pop", "persian pop", "latin hip hop", "latin trap"
    }
}

def detect_categories(genres_str):
    """
    Detect categories for an artist based on their genres.
    
    Args:
        genres_str: String of comma-separated genres
        
    Returns:
        String of comma-separated categories
    """
    if not genres_str or genres_str.strip() == "":
        return ""
    
    # Parse genres (split by comma and strip whitespace)
    genres = [genre.strip().lower() for genre in genres_str.split(",")]
    
    # Find matching categories
    detected_categories = set()
    
    for genre in genres:
        for category, genre_set in GENRE_MAP.items():
            if genre in genre_set:
                detected_categories.add(category)
    
    # Return as comma-separated string, sorted for consistency
    return "; ".join(sorted(detected_categories))


def process_csv(input_file, output_file):
    """
    Process the CSV file and add the detected_category column.
    
    Args:
        input_file: Path to input CSV file
        output_file: Path to output CSV file
    """
    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ['detected category']
        
        rows = []
        for row in reader:
            genres = row.get('genres', '')
            row['detected category'] = detect_categories(genres)
            rows.append(row)
    
    with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Processed {len(rows)} artists")
    print(f"Output written to {output_file}")


if __name__ == "__main__":
    input_file = "../artistDetails/combined_artist_details_extended.csv"
    output_file = "combined_artist_details_extended_with_categories.csv"  # New file
    
    # Allow command line arguments
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    process_csv(input_file, output_file)

