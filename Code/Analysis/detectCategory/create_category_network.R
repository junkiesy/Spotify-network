library(igraph)

# Read the CSV file
data <- read.csv("combined_artist_details_extended_with_categories.csv", stringsAsFactors = FALSE)

# Parse categories (handles semicolon or comma separated)
parse_cats <- function(s) {
  if (is.na(s) || s == "") return(character(0))
  trimws(unlist(strsplit(s, "[;,]")))
}

# Create edge list: connect artists sharing at least one category
edges <- list()
n <- nrow(data)

for (i in 1:(n-1)) {
  cats_i <- parse_cats(data$detected.category[i])
  if (length(cats_i) == 0) next
  
  for (j in (i+1):n) {
    cats_j <- parse_cats(data$detected.category[j])
    if (length(intersect(cats_i, cats_j)) > 0) {
      edges[[length(edges)+1]] <- c(data$name[i], data$name[j])
    }
  }
}

# Create graph
edges_df <- do.call(rbind, edges)
g <- graph_from_data_frame(edges_df, directed = FALSE)

# Print stats
cat("Nodes:", vcount(g), "| Edges:", ecount(g), "| Density:", round(graph.density(g), 4), "\n")

# Plot
plot(g, vertex.label = NA, vertex.size = 3, edge.width = 0.5, 
     layout = layout_with_fr(g), main = "Artist Network by Shared Categories")

