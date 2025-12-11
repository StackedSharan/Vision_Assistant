import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, GeoJSON, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import mapData from '../data/map.geojson';

// Fix for default marker icon
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
    iconUrl: require('leaflet/dist/images/marker-icon.png'),
    shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

// Component to update map view when center changes
function MapUpdater({ center }) {
    const map = useMap();
    useEffect(() => {
        if (center) {
            map.setView(center, map.getZoom());
        }
    }, [center, map]);
    return null;
}

const MapComponent = ({ routeCoords, currentLocation }) => {
    const [geoJsonData, setGeoJsonData] = useState(null);

    // Default center (approximate center of the campus based on geojson)
    const defaultCenter = [13.123, 77.6205];

    useEffect(() => {
        // In a real app, we might import JSON directly or fetch it. 
        // Since we imported it, we can just set it.
        // However, if it's a file path string (due to loader), we might need to fetch.
        // But standard create-react-app imports JSON as object if extension is .json.
        // .geojson might be treated as file url. Let's assume it's the object for now, 
        // or handle the fetch if it's a URL.
        if (typeof mapData === 'string') {
            fetch(mapData)
                .then(res => res.json())
                .then(data => setGeoJsonData(data));
        } else {
            setGeoJsonData(mapData);
        }
    }, []);

    const onEachFeature = (feature, layer) => {
        if (feature.properties && feature.properties.name) {
            layer.bindPopup(feature.properties.name);
        }
    };

    // Style for the map features
    const geoJsonStyle = {
        color: "#999",
        weight: 2,
        opacity: 0.5
    };

    // Style for the navigation path
    const routeStyle = {
        color: "#4285F4", // Google Blue
        weight: 6,
        opacity: 0.9
    };

    return (
        <MapContainer
            center={defaultCenter}
            zoom={18}
            style={{ height: "100%", width: "100%", zIndex: 0 }}
            zoomControl={false} // We'll add custom controls or rely on gestures
        >
            <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            {geoJsonData && (
                <GeoJSON
                    data={geoJsonData}
                    style={geoJsonStyle}
                    onEachFeature={onEachFeature}
                />
            )}

            {routeCoords && routeCoords.length > 0 && (
                <Polyline positions={routeCoords.map(c => [c[1], c[0]])} pathOptions={routeStyle} />
            )}

            {currentLocation && (
                <Marker position={currentLocation}>
                    <Popup>You are here</Popup>
                </Marker>
            )}

            <MapUpdater center={currentLocation || defaultCenter} />
        </MapContainer>
    );
};

export default MapComponent;
