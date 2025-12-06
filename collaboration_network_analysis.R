library(igraph)
library(readr)

# Load data
collab_edges <- read_csv("collaboration_details.csv")
artist_data <- read_csv("detectCategory/combined_artist_details_extended_with_categories.csv")


edges <- data.frame(
  from = collab_edges$`Artist 1`,
  to = collab_edges$`Artist 2`,
  weight = collab_edges$`Number of Collaborations`,
  stringsAsFactors = FALSE
)

artist_names <- artist_data$name
edges <- edges[edges$from %in% artist_names & edges$to %in% artist_names, ]


vertices_df <- artist_data[, c("name", setdiff(names(artist_data), "name"))]


collab_graph <- graph_from_data_frame(edges, directed = FALSE, vertices = vertices_df)


cat("Network Statistics:\n")
cat("Nodes:", vcount(collab_graph), "\n")
cat("Edges:", ecount(collab_graph), "\n")
cat("Density:", round(graph.density(collab_graph), 4), "\n\n")

# ============================================================================
# Research Question 1: Which artists are most central?
# ============================================================================

cat("=== Research Question 1: Most Central Artists ===\n\n")


degree_centrality <- degree(collab_graph)
betweenness_centrality <- betweenness(collab_graph)
closeness_centrality <- closeness(collab_graph)

# Top 10 by degree
top_degree <- sort(degree_centrality, decreasing = TRUE)[1:10]
cat("Top 10 Artists by Degree (Number of Collaborations):\n")
for (i in 1:length(top_degree)) {
  cat(sprintf("%d. %s: %d collaborations\n", i, names(top_degree)[i], top_degree[i]))
}

cat("\nTop 10 Artists by Betweenness (Bridge Artists):\n")
top_between <- sort(betweenness_centrality, decreasing = TRUE)[1:10]
for (i in 1:length(top_between)) {
  cat(sprintf("%d. %s: %.2f\n", i, names(top_between)[i], top_between[i]))
}

# Plot network with size by degree
plot(collab_graph,
  vertex.size = sqrt(degree_centrality) * 2,
  vertex.label = ifelse(degree_centrality >= quantile(degree_centrality, 0.9), V(collab_graph)$name, NA),
  vertex.label.cex = 0.5,
  vertex.label.color = "black",
  edge.width = E(collab_graph)$weight * 0.3,
  layout = layout_with_fr(collab_graph),
  main = "Collaboration Network - Node Size = Degree Centrality"
)

# ============================================================================
# Research Question 2: How do genres/categories shape clustering?
# ============================================================================

cat("\n=== Research Question 2: Genre/Category Clustering ===\n\n")

parse_categories <- function(cat_string) {
  if (is.na(cat_string) || cat_string == "") {
    return(character(0))
  }
  cats <- trimws(unlist(strsplit(cat_string, "[;,]")))
  cats <- cats[cats != ""]
  return(cats)
}

V(collab_graph)$primary_category <- sapply(V(collab_graph)$`detected category`, function(x) {
  cats <- parse_categories(x)
  if (length(cats) > 0) {
    return(cats[1])
  } else {
    return("Unknown")
  }
})

# Community detection
communities <- cluster_louvain(collab_graph)
V(collab_graph)$community <- communities$membership


cat("Category distribution in top 5 communities:\n")
top_communities <- sort(table(communities$membership), decreasing = TRUE)[1:5]
for (comm_id in as.numeric(names(top_communities))) {
  comm_artists <- V(collab_graph)[communities$membership == comm_id]
  comm_categories <- table(V(collab_graph)$primary_category[comm_artists])
  cat(sprintf("\nCommunity %d (%d artists):\n", comm_id, length(comm_artists)))
  print(sort(comm_categories, decreasing = TRUE)[1:5])
}

category_colors <- rainbow(length(unique(V(collab_graph)$primary_category)))
names(category_colors) <- unique(V(collab_graph)$primary_category)
V(collab_graph)$color <- category_colors[V(collab_graph)$primary_category]

plot(collab_graph,
  vertex.size = 3,
  vertex.label = NA,
  vertex.color = V(collab_graph)$color,
  edge.width = 0.5,
  layout = layout_with_fr(collab_graph),
  main = "Collaboration Network - Colored by Primary Category"
)

# ============================================================================
# Research Question 3: Do certain genres act as collaboration hubs?
# ============================================================================

cat("\n=== Research Question 3: Genre Collaboration Hubs ===\n\n")


category_degrees <- aggregate(degree_centrality,
  by = list(category = V(collab_graph)$primary_category),
  FUN = mean
)
category_degrees <- category_degrees[order(category_degrees$x, decreasing = TRUE), ]

cat("Average Collaborations per Artist by Category:\n")
print(category_degrees)


category_counts <- table(V(collab_graph)$primary_category)
cat("\nNumber of Artists per Category:\n")
print(sort(category_counts, decreasing = TRUE))

category_total_degree <- aggregate(degree_centrality,
  by = list(category = V(collab_graph)$primary_category),
  FUN = sum
)
category_total_degree <- category_total_degree[order(category_total_degree$x, decreasing = TRUE), ]

cat("\nTotal Collaborations per Category:\n")
print(category_total_degree)

# ============================================================================
# Research Question 4: Are popular artists also most connected?
# ============================================================================

cat("\n=== Research Question 4: Popularity vs Connectivity ===\n\n")

V(collab_graph)$popularity <- as.numeric(V(collab_graph)$popularity)
V(collab_graph)$followers <- as.numeric(V(collab_graph)$followers)

cor_pop_degree <- cor(V(collab_graph)$popularity, degree_centrality, use = "complete.obs")
cor_followers_degree <- cor(V(collab_graph)$followers, degree_centrality, use = "complete.obs")

cat(sprintf("Correlation between Popularity and Degree: %.3f\n", cor_pop_degree))
cat(sprintf("Correlation between Followers and Degree: %.3f\n", cor_followers_degree))


top_popular <- V(collab_graph)$name[order(V(collab_graph)$popularity, decreasing = TRUE)[1:10]]
top_connected <- names(sort(degree_centrality, decreasing = TRUE)[1:10])

cat("\nTop 10 by Popularity:\n")
print(top_popular)
cat("\nTop 10 by Collaborations:\n")
print(top_connected)
cat("\nOverlap:", length(intersect(top_popular, top_connected)), "artists\n")

plot(V(collab_graph)$popularity, degree_centrality,
  xlab = "Popularity", ylab = "Number of Collaborations",
  main = "Popularity vs Collaboration Count",
  pch = 19, cex = 0.5
)
abline(lm(degree_centrality ~ V(collab_graph)$popularity), col = "red")

# ============================================================================
# Research Question 5: How similar are individual music tastes?
# ============================================================================

cat("\n=== Research Question 5: Individual Taste Similarity ===\n\n")


get_users <- function(user_string) {
  if (is.na(user_string) || user_string == "") {
    return(character(0))
  }
  users <- trimws(unlist(strsplit(user_string, "[,;]")))
  return(users)
}


user_artists <- list()
for (i in 1:length(V(collab_graph))) {
  users <- get_users(V(collab_graph)$user[i])
  artist_name <- V(collab_graph)$name[i]
  for (u in users) {
    if (!u %in% names(user_artists)) {
      user_artists[[u]] <- character(0)
    }
    user_artists[[u]] <- c(user_artists[[u]], artist_name)
  }
}

users <- names(user_artists)
similarity_matrix <- matrix(0, nrow = length(users), ncol = length(users))
rownames(similarity_matrix) <- users
colnames(similarity_matrix) <- users

for (i in 1:length(users)) {
  for (j in 1:length(users)) {
    if (i != j) {
      shared <- length(intersect(user_artists[[users[i]]], user_artists[[users[j]]]))
      total <- length(union(user_artists[[users[i]]], user_artists[[users[j]]]))
      similarity_matrix[i, j] <- ifelse(total > 0, shared / total, 0)
    }
  }
}

cat("Shared Artist Similarity (Jaccard):\n")
print(round(similarity_matrix, 3))


cat("\nShared Collaborations:\n")
for (i in 1:(length(users) - 1)) {
  for (j in (i + 1):length(users)) {
    user1_artists <- user_artists[[users[i]]]
    user2_artists <- user_artists[[users[j]]]

    shared_collabs <- 0
    for (k in 1:nrow(edges)) {
      if ((edges$from[k] %in% user1_artists && edges$to[k] %in% user2_artists) ||
        (edges$to[k] %in% user1_artists && edges$from[k] %in% user2_artists)) {
        shared_collabs <- shared_collabs + 1
      }
    }
    cat(sprintf("%s - %s: %d shared collaborations\n", users[i], users[j], shared_collabs))
  }
}


cat("\nCategory Overlap:\n")
for (i in 1:(length(users) - 1)) {
  for (j in (i + 1):length(users)) {
    user1_artists <- user_artists[[users[i]]]
    user2_artists <- user_artists[[users[j]]]

    user1_cats <- unique(unlist(sapply(user1_artists, function(a) {
      idx <- which(V(collab_graph)$name == a)
      if (length(idx) > 0) parse_categories(V(collab_graph)$`detected category`[idx]) else character(0)
    })))

    user2_cats <- unique(unlist(sapply(user2_artists, function(a) {
      idx <- which(V(collab_graph)$name == a)
      if (length(idx) > 0) parse_categories(V(collab_graph)$`detected category`[idx]) else character(0)
    })))

    shared_cats <- intersect(user1_cats, user2_cats)
    cat(sprintf(
      "%s - %s: %d shared categories (%s)\n",
      users[i], users[j], length(shared_cats),
      paste(shared_cats, collapse = ", ")
    ))
  }
}


user_colors <- c("I" = "red", "M" = "blue", "C" = "green")
V(collab_graph)$user_color <- sapply(V(collab_graph)$user, function(u) {
  users <- get_users(u)
  if (length(users) == 1) {
    return(user_colors[users[1]])
  } else {
    return("purple")
  }
})

plot(collab_graph,
  vertex.size = 3,
  vertex.label = NA,
  vertex.color = V(collab_graph)$user_color,
  edge.width = 0.5,
  layout = layout_with_fr(collab_graph),
  main = "Collaboration Network - Colored by User (I=red, M=blue, C=green, Multiple=purple)"
)

cat("\n=== Analysis Complete ===\n")
