import { useEffect, useMemo } from 'react'
import L from 'leaflet'
import { MapContainer, Marker, TileLayer, useMap } from 'react-leaflet'
import { demoFarmLocations } from '../fixtures/demo'
import type { FarmLocation } from '../types/domain'

function MapFocus({ farm }: { farm: FarmLocation }) {
  const map = useMap()
  useEffect(() => {
    map.setView([farm.latitude, farm.longitude], 8, { animate: true })
  }, [farm.latitude, farm.longitude, map])
  return null
}

export function FarmMap({
  farm,
  onSelect,
}: {
  farm: FarmLocation
  onSelect: (farmId: string) => void
}) {
  const markerIcon = useMemo(() => L.divIcon({
    className: 'hinge-map-marker',
    html: '<span></span>',
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  }), [])

  return (
    <div className="map-wrap" aria-label="Interactive synthetic farm location map">
      <MapContainer center={[farm.latitude, farm.longitude]} zoom={8} scrollWheelZoom={false}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapFocus farm={farm} />
        {demoFarmLocations.map((location) => (
          <Marker
            key={location.id}
            position={[location.latitude, location.longitude]}
            icon={markerIcon}
            eventHandlers={{ click: () => onSelect(location.id) }}
          />
        ))}
      </MapContainer>
      <div className="map-attribution-note">Map tiles © OpenStreetMap contributors · Farm points are synthetic</div>
    </div>
  )
}
