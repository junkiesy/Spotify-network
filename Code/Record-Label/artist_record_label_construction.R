# -----------------------------------------------------------
# Record Label Collaboration Analysis (label-only)
# -----------------------------------------------------------

library(tidyverse)
library(igraph)
library(stringr)

# 1) Load and clean data ------------------------------------

path <- "C:/Users/matin/Downloads/"

df <- read.csv(file.path(path, "data_with_labels.csv"),
    stringsAsFactors = FALSE
)

df <- df %>%
    rename(
        artist        = name,
        artist_id     = id.x,
        collaborators = collaborators,
        popularity    = popularity,
        followers     = followers,
        user_code     = user,
        record_label  = record_label,
        genre_full    = genre
    ) %>%
    mutate(
        main_label = str_trim(str_extract(record_label, "^[^,]+"))
    )

# 2) Build artist–artist edges from collaborators ------------

edges <- df %>%
    filter(collaborators != "") %>%
    separate_rows(collaborators, sep = ",") %>%
    mutate(collaborators = str_trim(collaborators))

# Keep edges where collaborator exists in our dataset
edges_filtered <- edges %>%
    filter(collaborators %in% df$artist) %>%
    distinct(artist, collaborators) %>%
    rename(from = artist, to = collaborators)

# 3) Attach labels to ends of each edge ----------------------

edge_label <- edges_filtered %>%
    left_join(df %>% select(artist, main_label),
        by = c("from" = "artist")
    ) %>%
    rename(label_from = main_label) %>%
    left_join(df %>% select(artist, main_label),
        by = c("to" = "artist")
    ) %>%
    rename(label_to = main_label) %>%
    mutate(
        same_label = !is.na(label_from) & !is.na(label_to) &
            label_from == label_to
    )

# 4) Overall within-label vs cross-label summary -------------

label_summary <- edge_label %>%
    summarise(
        total_edges       = n(),
        same_label_edges  = sum(same_label, na.rm = TRUE),
        cross_label_edges = total_edges - same_label_edges,
        prop_same_label   = same_label_edges / total_edges
    )

label_summary

# 5) Bar plot: within-label vs cross-label -------------------

label_summary_long <- label_summary %>%
    select(same_label_edges, cross_label_edges) %>%
    pivot_longer(everything(),
        names_to = "type",
        values_to = "n"
    ) %>%
    mutate(
        type = recode(type,
            same_label_edges  = "Within-label collaborations",
            cross_label_edges = "Cross-label collaborations"
        )
    )

ggplot(label_summary_long, aes(x = type, y = n)) +
    geom_col() +
    labs(
        x = NULL,
        y = "Number of collaborations",
        title = "Within-label vs cross-label collaborations"
    ) +
    theme_minimal()

# 6) Build label–label edges (meta-network) ------------------

label_edges <- edge_label %>%
    filter(!is.na(label_from), !is.na(label_to)) %>%
    # Uncomment the next line if you want ONLY cross-label ties:
    # filter(label_from != label_to) %>%
    count(label_from, label_to, name = "weight")

g_labels <- graph_from_data_frame(label_edges,
    directed = FALSE
)

g_labels

# 7) Label-level metrics -------------------------------------

# Basic size
num_labels <- vcount(g_labels)
num_label_edges <- ecount(g_labels)

num_labels
num_label_edges

# Degree centrality for labels
label_deg <- sort(degree(g_labels), decreasing = TRUE)
label_deg[1:10]

# Average degree
mean_deg <- mean(degree(g_labels))
mean_deg

# Global clustering coefficient at label level
label_clust <- transitivity(g_labels, type = "global")
label_clust

# Components (how many label clusters)
label_comp <- components(g_labels)
label_comp$no # number of components
max(label_comp$csize) # size of largest component

# 8) Plot full label–label network (dense, but complete) -----

set.seed(123)

V(g_labels)$deg <- degree(g_labels)
V(g_labels)$size <- 5 + 2 * log1p(V(g_labels)$deg)
E(g_labels)$width <- 1 + log1p(E(g_labels)$weight)

plot(
    g_labels,
    layout = layout_with_fr(g_labels),
    vertex.size = V(g_labels)$size,
    vertex.label = V(g_labels)$name,
    vertex.label.cex = 0.6,
    vertex.label.color = "black",
    vertex.color = "lightblue",
    edge.width = E(g_labels)$width,
    edge.color = adjustcolor("grey60", alpha.f = 0.7),
    main = "Record Label Collaboration Network"
)

# 9) Cleaner graph: only high-degree labels ------------------

deg_threshold <- 20 # change this if you want more/less labels

g_labels_sub <- induced_subgraph(g_labels, V(g_labels)$deg >= deg_threshold)

set.seed(123)
plot(
    g_labels_sub,
    layout = layout_with_fr(g_labels_sub),
    vertex.size = 5 + 2 * log1p(degree(g_labels_sub)),
    vertex.label = V(g_labels_sub)$name,
    vertex.label.cex = 0.7,
    vertex.label.color = "black",
    vertex.color = "lightblue",
    edge.width = 1 + log1p(E(g_labels_sub)$weight),
    edge.color = adjustcolor("grey60", alpha.f = 0.7),
    main = "Record Label Collaboration Network (Top Labels Only)"
)

# 10) Cleaner graph: only strong label ties ------------------

weight_threshold <- 3 # keep label pairs with >= 3 artist collabs

strong_label_edges <- label_edges %>%
    filter(weight >= weight_threshold)

g_labels_strong <- graph_from_data_frame(strong_label_edges,
    directed = FALSE
)

set.seed(123)
plot(
    g_labels_strong,
    layout = layout_with_fr(g_labels_strong),
    vertex.size = 5 + 2 * log1p(degree(g_labels_strong)),
    vertex.label = V(g_labels_strong)$name,
    vertex.label.cex = 0.7,
    vertex.label.color = "black",
    vertex.color = "lightblue",
    edge.width = 1 + log1p(E(g_labels_strong)$weight),
    edge.color = adjustcolor("grey60", alpha.f = 0.7),
    main = "Record Label Collaboration Network (Edges ≥ 3 Collaborations)"
)

# 11) Top collaborating label pairs --------------------------

top_label_pairs <- label_edges %>%
    arrange(desc(weight)) %>%
    head(10)

top_label_pairs
