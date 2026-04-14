"use client";

import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Corrige o ícone padrão do Leaflet no Next.js
const icone = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
});

interface Ponto {
  lat: number;
  lng: number;
  nome: string;
}

interface Props {
  pontos: Ponto[];
}

export default function MapaAtividades({ pontos }: Props) {
  if (!pontos.length) {
    return (
      <div className="h-64 bg-zinc-100 rounded-xl flex items-center justify-center text-zinc-500">
        Nenhuma localização disponível
      </div>
    );
  }

  const centro: [number, number] = [pontos[0].lat, pontos[0].lng];

  return (
    <div className="h-72 rounded-xl overflow-hidden border border-zinc-200">
      <MapContainer center={centro} zoom={13} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        />
        {pontos.map((ponto, i) => (
          <Marker key={i} position={[ponto.lat, ponto.lng]} icon={icone}>
            <Popup>{ponto.nome}</Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
