

path <- "C:/Users/matin/Downloads/"

# Read your files
top <- read.csv(file.path(path, "merged_top_artists.csv"),
                stringsAsFactors = FALSE)

collab <- read.csv(file.path(path, "artist_collaborators_network.csv"),
                   stringsAsFactors = FALSE)



valid_edges <- collab[
  collab$primary_artist %in% top$name &
    collab$collaborator_name %in% top$name,
]




collab_list <- aggregate(
  collaborator_name ~ primary_artist,
  data = valid_edges,
  FUN = function(x) paste(unique(x), collapse = ", ")
)

# Rename columns to match for merge
names(collab_list) <- c("name", "collaborators")

final <- merge(
  top,
  collab_list,
  by = "name",
  all.x = TRUE  # keep all artists in merged_top_artists
)


wanted_cols <- c("name", "id", "genres")
wanted_cols <- intersect(wanted_cols, names(final))  # safety
final <- final[, c(wanted_cols, setdiff(names(final), wanted_cols))]



write.csv(
  final,
  file.path(path, "merged_top_artists_with_collaborators.csv"),
  row.names = FALSE
)


