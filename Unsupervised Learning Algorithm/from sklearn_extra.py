from sklearn_extra.cluster import KMedoids
from sklearn.datasets import make_blobs
import matplotlib.pyplot as plt

# Create dataset
X, _ = make_blobs(
    n_samples=300,
    centers=3,
    random_state=42
)

# Create model
kmedoids = KMedoids(
    n_clusters=3,
    random_state=42
)

# Train
kmedoids.fit(X)

# Labels
labels = kmedoids.labels_

# Medoids
medoids = kmedoids.cluster_centers_

# Plot
plt.scatter(X[:,0], X[:,1], c=labels)
plt.scatter(
    medoids[:,0],
    medoids[:,1],
    color='red',
    marker='X',
    s=200
)
plt.title("K-Medoids Clustering")
plt.show()
