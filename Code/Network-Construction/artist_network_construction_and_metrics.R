library(tidyverse)
library(igraph)

path <- "C:/Users/matin/Downloads/"

top_artists <- read.csv(file.path(path, "merged_top_artists.csv"),
    stringsAsFactors = FALSE
)

collab_edges <- read.csv(file.path(path, "artist_collaborators_network.csv"),
    stringsAsFactors = FALSE
)

top_with_collabs <- read.csv(file.path(path, "merged_top_artists_with_collaborators.csv"),
    stringsAsFactors = FALSE
)


artist_nodes <- top_artists %>%
    rename(artist = name) %>%
    distinct(artist, id, genres)


edges_filtered <- collab_edges %>%
    filter(primary_artist %in% artist_nodes$artist &
        collaborator_name %in% artist_nodes$artist) %>%
    transmute(
        from = primary_artist,
        to = collaborator_name
    )

g <- graph_from_data_frame(
    d = edges_filtered,
    directed = FALSE,
    vertices = artist_nodes
)

g

# Color by genre

library(stringr)


V(g)$main_genre <- str_trim(str_extract(V(g)$genres, "^[^,]+"))


rap_family <- c(
    "rap", "trap", "grime", "melodic rap", "uk drill",
    "brooklyn drill", "rage rap", "chicago drill",
    "southern hip hop", "moroccan rap", "hip hop",
    "jazz rap", "alternative hip hop", "east coast hip hop", "hiphop"
)

pop_family <- c(
    "r&b", "dark r&b", "soft pop", "pop", "dance pop",
    "bedroom pop", "art pop", "french pop"
)

rock_family <- c(
    "rock", "alt", "alternative metal", "classic rock", "post-grunge",
    "grunge", "progressive rock", "progressive metal", "post-hardcore",
    "britpop", "post-punk", "surf rock", "midwest emo"
)

indie_family <- c(
    "indie", "dream pop", "indie rock", "lo-fi indie",
    "indie folk", "jangle pop", "post-rock", "slowcore"
)

electronic_family <- c(
    "edm", "downtempo", "breakcore", "idm", "vaporwave",
    "witch house", "hyperpop"
)

world_family <- c("afrobeats")

jazzclassical_family <- c("jazz", "classical", "folk", "vocal")

other_family <- c("neo-psychedelic", "new age", "anime", "midwest")


genre_colors <- rep("grey50", length(V(g)$main_genre))

genre_colors[V(g)$main_genre %in% rap_family] <- "red"
genre_colors[V(g)$main_genre %in% pop_family] <- "pink"
genre_colors[V(g)$main_genre %in% rock_family] <- "blue"
genre_colors[V(g)$main_genre %in% indie_family] <- "forestgreen"
genre_colors[V(g)$main_genre %in% electronic_family] <- "purple"
genre_colors[V(g)$main_genre %in% jazzclassical_family] <- "brown"
genre_colors[V(g)$main_genre %in% world_family] <- "orange"
genre_colors[V(g)$main_genre %in% other_family] <- "grey70"

V(g)$color <- genre_colors


set.seed(123)
plot(
    g,
    vertex.size  = 3,
    vertex.label = NA,
    edge.color   = adjustcolor("grey75", alpha.f = 0.5),
    vertex.color = V(g)$color,
    layout       = layout_with_fr(g),
    main         = "Artist Collaboration Network (Genre Families)"
)


legend(
    "topleft",
    legend = c(
        "Rap/Hip-Hop", "Pop/R&B", "Rock/Metal", "Indie/Alt",
        "Electronic", "Jazz/Classical/Folk", "World", "Other"
    ),
    col = c(
        "red", "pink", "blue", "forestgreen",
        "purple", "brown", "orange", "grey70"
    ),
    pch = 19,
    pt.cex = 1,
    bty = "n",
    cex = 0.8,
    title = "Genre Families"
)

# CENTRALITY METRICS -----------------------------------------


deg <- degree(g)
betw <- betweenness(g, directed = FALSE, normalized = TRUE)

centrality_df <- data.frame(
    artist      = V(g)$name,
    main_genre  = V(g)$main_genre,
    degree      = deg,
    betweenness = betw
)


top_degree <- centrality_df %>%
    arrange(desc(degree)) %>%
    slice_head(n = 10)

top_degree


top_betw <- centrality_df %>%
    arrange(desc(betweenness)) %>%
    slice_head(n = 10)

top_betw

# NETWORK-LEVEL METRICS -------------------------------------


global_clust <- transitivity(g, type = "global")
global_clust


V(g)$local_clust <- transitivity(g, type = "local", isolates = "zero")

gc <- components(g)
g_gc <- induced_subgraph(g, which(gc$membership == which.max(gc$csize)))

avg_path_len <- mean_distance(g_gc, directed = FALSE)
avg_path_len

# COMMUNITY DETECTION ---------------------------------------

set.seed(123)
louvain <- cluster_louvain(g)
V(g)$community <- membership(louvain)

# Size of each community
community_sizes <- sizes(louvain)
community_sizes

# Genre breakdown inside each community
community_genres <- data.frame(
    community  = V(g)$community,
    main_genre = V(g)$main_genre
) %>%
    filter(!is.na(main_genre)) %>%
    count(community, main_genre, sort = TRUE)

community_genres
