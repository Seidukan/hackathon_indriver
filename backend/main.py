from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import pandas as pd
import networkx as nx
import osmnx as ox
import geopandas as gpd
from io import StringIO
import numpy as np
from typing import List, Dict, Tuple
from sklearn.preprocessing import minmax_scale
from djikstra import get_shortest_path
import logging
from pydantic import BaseModel

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # allow all origins
    allow_credentials=True,    # allow cookies/auth headers
    allow_methods=["*"],       # allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],       # allow all headers
)

@app.get("/")
def read_root():
    return {"msg": "CORS enabled for all origins"}


# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

G = None  # Will be initialized in preprocess
base: float = 300.0
rate: float = 150.0

class RouteRequest(BaseModel):
    src_lat: float
    src_lng: float
    dst_lat: float
    dst_lng: float

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)

    a = np.sin(dphi/2.0)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2.0)**2
    return 2 * R * np.arcsin(np.sqrt(a))

def points_within_radius(df, lat_a, lng_a, radius_m=100):
    distances = haversine(lat_a, lng_a, df['lat'].values, df['lng'].values)
    logger.debug(f"Found {np.sum(distances <= radius_m)} points within {radius_m} meters")
    return df[distances <= radius_m]

def scale_to_unit(x, min_val=0, max_val=3000):
    return (x - min_val) / (max_val - min_val)

def cost_function(data: pd.DataFrame, longitude: float, latitude: float, radius_m=100) -> float:
    coef = scale_to_unit(data.shape[0])
    return 200 * (np.exp(coef))


def compute_edge_stats(matched_df: pd.DataFrame, slow_speed_thresh: float = 10.0) -> pd.DataFrame:
    logger.debug(f"Computing edge stats for {len(matched_df)} matched points")
    df = matched_df.copy()
    df['spd'] = pd.to_numeric(df['spd'], errors='coerce')
    df = df.dropna(subset=['spd'])
    
    edge_stats = df.groupby('belongs_to').agg(
        point_count=('spd', 'size'),
        unique_vehicles=('randomized_id', 'nunique'),
        mean_speed=('spd', 'mean'),
        median_speed=('spd', 'median'),
        speed_std=('spd', 'std'),
        pct_slow=('spd', lambda s: (s < slow_speed_thresh).mean())
    ).fillna(0)
    
    return edge_stats

def calculate_congestion_score(edge_stats: pd.DataFrame, w_volume: float = 0.6, 
                             w_slow: float = 0.1, w_speed: float = 0.3) -> pd.Series:
    scaled_volume = minmax_scale(np.log1p(edge_stats['unique_vehicles']))
    pct_slow = edge_stats['pct_slow'].values
    scaled_speed_reduction = 1.0 - minmax_scale(edge_stats['median_speed'])
    
    raw_score = (
        w_volume * scaled_volume +
        w_slow * pct_slow +
        w_speed * scaled_speed_reduction
    )
    
    return pd.Series(raw_score, index=edge_stats.index, name='congestion_score')

def calculate_edge_costs(G_proj: nx.MultiDiGraph, edges_df: pd.DataFrame) -> List[Dict]:
    result = []
    
    for u, v, k, data in G_proj.edges(keys=True, data=True):
        length = data.get('length', 0)
        edge_key = (u, v, k)
        
        if edge_key in edges_df.index:
            congestion_score = edges_df.loc[edge_key, 'congestion_score']
            cost = length * (1 + congestion_score)
            
            result.append({
                "u": u,
                "v": v,
                "k": k,
                "c": float(cost)
            })
    
    return result

def get_node_coordinates(G: nx.MultiDiGraph, node_id: int) -> Tuple[float, float]:
    node_data = G.nodes[node_id]
    return node_data['y'], node_data['x']

@app.post("/preprocess")
async def preprocess_data(file: UploadFile = File(...)):
    try:
        logger.debug(f"Starting preprocessing with file: {file.filename}")
        contents = await file.read()
        df = pd.read_csv(StringIO(contents.decode()))
        logger.debug(f"Successfully loaded CSV with {len(df)} rows")
        
        # Clean speed data
        df.loc[df['spd'] < 0, 'spd'] = 0
        df['spd'] = df['spd'] * 3.6
        
        # Create and store graph globally
        global G
        G = ox.graph_from_place("Astana, Kazakhstan", network_type="drive")
        G_proj = ox.project_graph(G)
        
        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df.lng, df.lat),
            crs="EPSG:4326"
        )
        gdf_proj = gdf.to_crs(G_proj.graph['crs'])
        
        # Find nearest edges
        nearest_edges, dists = ox.nearest_edges(
            G_proj,
            X=gdf_proj.geometry.x.values,
            Y=gdf_proj.geometry.y.values,
            return_dist=True
        )
        
        df['distance_to_edge'] = dists
        df['belongs_to'] = nearest_edges
        df['edge_u'], df['edge_v'], df['edge_key'] = zip(*nearest_edges)
        
        # Filter points within threshold
        threshold = 10  # meters
        matched_df = df[df['distance_to_edge'] < threshold].copy()
        
        # Create dataframe for demand calculation
        didar_df = df[df['distance_to_edge'] > threshold].copy()
        didar_df = didar_df[didar_df['spd'] < 1]

        # Calculate edge statistics and congestion scores
        edge_stats = compute_edge_stats(matched_df)
        congestion_scores = calculate_congestion_score(
            edge_stats,
            w_volume=0.6,
            w_slow=0.1,
            w_speed=0.3
        )
        
        edges_df = edge_stats.join(congestion_scores)
        edges_df.index = pd.MultiIndex.from_tuples(edges_df.index)
        
        # Calculate and add edge costs to edges_df
        edges_df['edge_cost'] = 0.0
        for u, v, k, data in G_proj.edges(keys=True, data=True):
            edge_key = (u, v, k)
            if edge_key in edges_df.index:
                length = data.get('length', 0)
                congestion_score = edges_df.loc[edge_key, 'congestion_score']
                edges_df.loc[edge_key, 'edge_cost'] = length * (1 + congestion_score)

        # Store data in app state
        app.state.edges_df = edges_df
        app.state.matched_df = matched_df
        app.state.df = df
        app.state.demand_df = didar_df

        # Calculate costs for each edge
        edge_costs = [{
            "u": u,
            "v": v,
            "k": k,
            "c": float(edges_df.loc[(u, v, k), 'edge_cost'])
        } for u, v, k in edges_df.index if (u, v, k) in edges_df.index]
        
        return JSONResponse(content={"edges": edge_costs})
        
    except Exception as e:
        logger.error(f"Error in preprocess_data: {e}")
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )

@app.post("/route")
async def calculate_route(request: RouteRequest):
    try:
        logger.debug(f"Calculating route from ({request.src_lat}, {request.src_lng}) to ({request.dst_lat}, {request.dst_lng})")
        # Get nearest nodes for source and destination
        source_node = ox.nearest_nodes(G, request.src_lng, request.src_lat)
        logger.debug(f"Found source node: {source_node}")
        dest_node = ox.nearest_nodes(G, request.dst_lng, request.dst_lat)
        
        # Get shortest path
        path = get_shortest_path(source_node, dest_node, app.state.edges_df)
        if not path:
            return JSONResponse(
                status_code=404,
                content={"error": "No path found between the given points"}
            )
        
        # Extract path nodes and calculate total distance
        nodes = [path[0].U] + [edge.V for edge in path]
        total_distance = sum(edge.C for edge in path)
        
        # Calculate average congestion score
        congestion_scores = [
            app.state.edges_df.loc[(edge.U, edge.V, edge.K), 'congestion_score']
            for edge in path
        ]
        avg_congestion = sum(congestion_scores) / len(congestion_scores)
        
        # Calculate demand at source point
        nearby_points = points_within_radius(
            app.state.demand_df,
            request.src_lat,
            request.src_lng,
            radius_m=100
        )
        demand = cost_function(nearby_points, request.src_lng, request.src_lat)
        
        # Build path coordinates
        path_coords = []
        for idx, node in enumerate(nodes):
            lat, lng = get_node_coordinates(G, node)
            point_type = "start" if idx == 0 else "end" if idx == len(nodes)-1 else "stop"
            path_coords.append({
                "lat": float(lat),
                "lng": float(lng),
                "type": point_type
            })
        
        return {
            "base": base,
            "demand": float(demand),
            "rate": rate,
            "distance": float(total_distance),
            "congestion": float(avg_congestion),
            "path": path_coords
        }
        
    except Exception as e:
        logger.error(f"Error in calculate_route: {e}")
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
