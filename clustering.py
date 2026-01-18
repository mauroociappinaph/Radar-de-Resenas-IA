import os
import polars as pl
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import silhouette_score
import asyncio
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class ClusteringEngine:
    """
    Advanced clustering engine for lead segmentation using K-means.
    Groups similar businesses for targeted campaign strategies.
    """

    def __init__(self, n_clusters: int = 5, random_state: int = 42):
        """
        Initialize the clustering engine.

        Args:
            n_clusters: Number of clusters to create
            random_state: Random state for reproducibility
        """
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.kmeans = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_columns = [
            'niche_encoded',
            'city_encoded',
            'rating_normalized',
            'sentiment_score_normalized',
            'email_type_encoded'
        ]

    def _encode_categorical(self, data: pl.DataFrame, column: str, fit: bool = True) -> pl.DataFrame:
        """Encode categorical columns using LabelEncoder."""
        if column not in self.label_encoders:
            self.label_encoders[column] = LabelEncoder()

        column_values = data[column].to_list()

        if fit:
            # During fit phase: fit the encoder
            self.label_encoders[column].fit(column_values)
            encoded_values = self.label_encoders[column].transform(column_values)
        else:
            # During predict phase: handle new categories
            try:
                encoded_values = self.label_encoders[column].transform(column_values)
            except ValueError:
                # If new categories, fit again with old + new categories
                existing_categories = list(self.label_encoders[column].classes_)
                all_categories = existing_categories + list(set(column_values))
                self.label_encoders[column] = LabelEncoder()
                self.label_encoders[column].fit(all_categories)
                encoded_values = self.label_encoders[column].transform(column_values)

        return data.with_columns(pl.Series(f'{column}_encoded', encoded_values))

    def _preprocess_data(self, leads: List[Dict], fit: bool = True) -> pl.DataFrame:
        """
        Preprocess lead data for clustering.

        Args:
            leads: List of lead dictionaries
            fit: Whether to fit encoders (True for training, False for prediction)

        Returns:
            Preprocessed DataFrame ready for clustering
        """
        df = pl.DataFrame(leads)

        # Fill missing values
        df = df.with_columns([
            pl.col('rating').fill_null(0),
            pl.col('sentiment_score').fill_null(0.0),
            pl.col('sentiment_confidence').fill_null(0.0),
            pl.col('email_type').fill_null('unknown'),
            pl.col('city').fill_null('unknown'),
            pl.col('niche').fill_null('unknown')
        ])

        # Encode categorical variables
        df = self._encode_categorical(df, 'niche', fit=fit)
        df = self._encode_categorical(df, 'city', fit=fit)
        df = self._encode_categorical(df, 'email_type', fit=fit)

        # Normalize numerical features (convert to numpy for sklearn)
        if fit:
            rating_values = df['rating'].to_numpy().reshape(-1, 1)
            sentiment_values = df['sentiment_score'].to_numpy().reshape(-1, 1)

            rating_normalized = self.scaler.fit_transform(rating_values)
            sentiment_normalized = self.scaler.fit_transform(sentiment_values)
        else:
            rating_values = df['rating'].to_numpy().reshape(-1, 1)
            sentiment_values = df['sentiment_score'].to_numpy().reshape(-1, 1)

            rating_normalized = self.scaler.transform(rating_values)
            sentiment_normalized = self.scaler.transform(sentiment_values)

        df = df.with_columns([
            pl.Series('rating_normalized', rating_normalized.flatten()),
            pl.Series('sentiment_score_normalized', sentiment_normalized.flatten())
        ])

        # Select features for clustering
        feature_df = df.select(self.feature_columns)

        return feature_df

    def _find_optimal_clusters(self, data: pl.DataFrame, max_clusters: int = 10) -> int:
        """
        Find optimal number of clusters using elbow method and silhouette score.

        Args:
            data: Preprocessed data
            max_clusters: Maximum number of clusters to test

        Returns:
            Optimal number of clusters
        """
        # Convert to numpy array for sklearn
        data_array = data.to_numpy()

        distortions = []
        silhouette_scores = []

        for k in range(2, min(max_clusters + 1, data.height)):
            kmeans = KMeans(n_clusters=k, random_state=self.random_state, n_init=10)
            kmeans.fit(data_array)

            distortions.append(kmeans.inertia_)

            if data.height > k:
                silhouette_avg = silhouette_score(data_array, kmeans.labels_)
                silhouette_scores.append(silhouette_avg)
            else:
                silhouette_scores.append(-1)

        # Find elbow point (simple heuristic)
        if len(distortions) >= 3:
            # Calculate second derivative to find elbow
            second_derivatives = []
            for i in range(1, len(distortions) - 1):
                second_deriv = distortions[i-1] - 2*distortions[i] + distortions[i+1]
                second_derivatives.append(second_deriv)

            if second_derivatives:
                elbow_idx = np.argmax(second_derivatives) + 1
                optimal_k = elbow_idx + 2  # +2 because we start from k=2
            else:
                optimal_k = 3
        else:
            optimal_k = 3

        # Ensure optimal_k is reasonable
        optimal_k = max(2, min(optimal_k, data.height // 10))  # At least 2, at most len(data)/10

        print(f"📊 Optimal clusters found: {optimal_k}")
        return optimal_k

    def fit(self, leads: List[Dict]) -> None:
        """
        Fit the clustering model on lead data.

        Args:
            leads: List of lead dictionaries
        """
        print(f"🎯 Starting clustering analysis on {len(leads)} leads...")

        if len(leads) < 3:
            print("⚠️ Not enough leads for clustering. Using default single cluster.")
            self.kmeans = None
            return

        # Preprocess data
        feature_df = self._preprocess_data(leads, fit=True)

        # Find optimal number of clusters
        optimal_k = self._find_optimal_clusters(feature_df)
        self.n_clusters = optimal_k

        # Fit K-means (convert polars to numpy)
        self.kmeans = KMeans(
            n_clusters=self.n_clusters,
            random_state=self.random_state,
            n_init=10
        )
        self.kmeans.fit(feature_df.to_numpy())

        print(f"✅ Clustering model trained with {self.n_clusters} clusters")

    def predict(self, leads: List[Dict]) -> List[Dict]:
        """
        Predict cluster assignments for leads.

        Args:
            leads: List of lead dictionaries

        Returns:
            List of leads with cluster_id added
        """
        if self.kmeans is None:
            # If no model, assign all to cluster 0
            for lead in leads:
                lead['cluster_id'] = 0
            return leads

        # Preprocess data
        feature_df = self._preprocess_data(leads)

        # Predict clusters
        clusters = self.kmeans.predict(feature_df.to_numpy())

        # Add cluster_id to leads
        for lead, cluster_id in zip(leads, clusters):
            lead['cluster_id'] = int(cluster_id)

        return leads

    def fit_predict(self, leads: List[Dict]) -> List[Dict]:
        """
        Fit the model and predict cluster assignments in one step.

        Args:
            leads: List of lead dictionaries

        Returns:
            List of leads with cluster_id added
        """
        self.fit(leads)
        return self.predict(leads)

    def get_cluster_info(self) -> Dict:
        """
        Get information about the clusters.

        Returns:
            Dictionary with cluster statistics
        """
        if self.kmeans is None:
            return {"error": "No clustering model trained"}

        centroids = self.kmeans.cluster_centers_
        labels = self.kmeans.labels_

        info = {
            "n_clusters": self.n_clusters,
            "cluster_sizes": np.bincount(labels).tolist(),
            "centroids": centroids.tolist(),
            "inertia": self.kmeans.inertia_,
            "feature_importance": self._analyze_feature_importance()
        }

        return info

    def _analyze_feature_importance(self) -> Dict:
        """
        Analyze which features are most important for clustering.

        Returns:
            Dictionary with feature importance scores
        """
        if self.kmeans is None:
            return {}

        # Calculate feature importance based on centroid distances
        centroids = self.kmeans.cluster_centers_
        centroid_std = np.std(centroids, axis=0)

        importance = {}
        for i, feature in enumerate(self.feature_columns):
            importance[feature] = float(centroid_std[i])

        return importance

    def save_model(self, filepath: str) -> None:
        """
        Save the clustering model to disk.

        Args:
            filepath: Path to save the model
        """
        import joblib

        model_data = {
            'kmeans': self.kmeans,
            'scaler': self.scaler,
            'label_encoders': self.label_encoders,
            'n_clusters': self.n_clusters,
            'feature_columns': self.feature_columns
        }

        joblib.dump(model_data, filepath)
        print(f"💾 Model saved to {filepath}")

    def load_model(self, filepath: str) -> None:
        """
        Load the clustering model from disk.

        Args:
            filepath: Path to load the model from
        """
        import joblib

        model_data = joblib.load(filepath)

        self.kmeans = model_data['kmeans']
        self.scaler = model_data['scaler']
        self.label_encoders = model_data['label_encoders']
        self.n_clusters = model_data['n_clusters']
        self.feature_columns = model_data['feature_columns']

        print(f"📂 Model loaded from {filepath}")


# Global clustering engine instance
_clustering_engine = None

def get_clustering_engine(n_clusters: int = 5) -> ClusteringEngine:
    """Get or create global clustering engine instance."""
    global _clustering_engine
    if _clustering_engine is None:
        _clustering_engine = ClusteringEngine(n_clusters=n_clusters)
    return _clustering_engine


async def cluster_leads(limit: int = 100) -> None:
    """
    Cluster all enriched leads in the database.

    Args:
        limit: Maximum number of leads to cluster
    """
    print(f"🎯 Starting lead clustering process (limit: {limit})...")

    # Get enriched leads from database
    response = supabase.table("leads").select("*").eq("status", "enriched").limit(limit).execute()
    leads = response.data

    if len(leads) < 3:
        print("⚠️ Not enough leads for clustering. Skipping.")
        return

    # Initialize clustering engine
    engine = get_clustering_engine()

    # Fit and predict clusters
    clustered_leads = engine.fit_predict(leads)

    # Update database with cluster assignments
    for lead in clustered_leads:
        supabase.table("leads").update({
            "cluster_id": lead['cluster_id']
        }).eq("id", lead["id"]).execute()

    # Print cluster statistics
    cluster_info = engine.get_cluster_info()
    print(f"📊 Clustering completed:")
    print(f"   - Number of clusters: {cluster_info['n_clusters']}")
    print(f"   - Cluster sizes: {cluster_info['cluster_sizes']}")

    print("✅ All leads clustered successfully")


if __name__ == "__main__":
    # Test clustering with sample data
    asyncio.run(cluster_leads())
