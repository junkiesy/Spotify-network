library(readr)


my_top_artists_matin <- read_csv("C:/Users/CJSch/Documents/COSC421/Project/combineArtists/my_top_artists_matin.csv")
my_top_artists_ishaan <- read_csv("C:/Users/CJSch/Documents/COSC421/Project/combineArtists/my_top_artists_ishaan.csv")
my_top_artists_charlie <- read_csv("C:/Users/CJSch/Documents/COSC421/Project/combineArtists/my_top_artists_charlie.csv")

# Combine into a single data frame
all_data <- rbind(my_top_artists_matin, my_top_artists_ishaan, my_top_artists_charlie)

# Remove exact duplicate rows first (optional but helpful)
all_data <- unique(all_data)

# Merge rows with identical IDs and combine 'user' values
library(dplyr)

merged <- all_data %>%
  group_by(id) %>%
  summarise(
    name   = first(name),
    genres = first(genres),
    user   = paste(unique(user), collapse = ", ")
  ) %>%
  ungroup()

# View result
print(merged)


write_csv(merged, "combined_artists.csv")
