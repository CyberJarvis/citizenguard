/**
 * Hazard Data Generator
 * Generates realistic dummy data for various coastal hazards
 */

// Indian Coastal Coordinates
const COASTAL_REGIONS = {
  'West Bengal': { lat: 21.8, lon: 87.8 },
  'Odisha': { lat: 19.8, lon: 85.8 },
  'Andhra Pradesh': { lat: 16.5, lon: 80.6 },
  'Tamil Nadu': { lat: 11.1, lon: 79.8 },
  'Puducherry': { lat: 11.9, lon: 79.8 },
  'Kerala': { lat: 10.5, lon: 76.2 },
  'Karnataka': { lat: 14.5, lon: 74.5 },
  'Goa': { lat: 15.3, lon: 73.9 },
  'Maharashtra': { lat: 18.5, lon: 72.8 },
  'Gujarat': { lat: 21.5, lon: 70.5 },
  'Andaman and Nicobar': { lat: 11.7, lon: 92.7 },
  'Lakshadweep': { lat: 10.5, lon: 72.6 }
};

// Tide Gauge Stations (Real locations from INCOIS)
export const TIDE_GAUGE_STATIONS = [
  { id: 'TG001', name: 'Port Blair', lat: 11.6667, lon: 92.7333, status: 'operational', region: 'Andaman and Nicobar', seaLevel: 0.45 },
  { id: 'TG002', name: 'Chennai', lat: 13.0878, lon: 80.2785, status: 'operational', region: 'Tamil Nadu', seaLevel: 0.32 },
  { id: 'TG003', name: 'Visakhapatnam', lat: 17.6868, lon: 83.2185, status: 'operational', region: 'Andhra Pradesh', seaLevel: 0.28 },
  { id: 'TG004', name: 'Paradip', lat: 20.3, lon: 86.6, status: 'operational', region: 'Odisha', seaLevel: 0.38 },
  { id: 'TG005', name: 'Mumbai', lat: 18.9217, lon: 72.8347, status: 'operational', region: 'Maharashtra', seaLevel: 0.25 },
  { id: 'TG006', name: 'Okha', lat: 22.4675, lon: 69.0772, status: 'operational', region: 'Gujarat', seaLevel: 0.42 },
  { id: 'TG007', name: 'Karwar', lat: 14.8075, lon: 74.1240, status: 'maintenance', region: 'Karnataka', seaLevel: 0.19 },
  { id: 'TG008', name: 'Kochi', lat: 9.9312, lon: 76.2673, status: 'operational', region: 'Kerala', seaLevel: 0.31 },
  { id: 'TG009', name: 'Tuticorin', lat: 8.7642, lon: 78.1348, status: 'operational', region: 'Tamil Nadu', seaLevel: 0.27 },
  { id: 'TG010', name: 'Mandapam', lat: 9.2839, lon: 79.1244, status: 'operational', region: 'Tamil Nadu', seaLevel: 0.33 },
  { id: 'TG011', name: 'Machilipatnam', lat: 16.1875, lon: 81.1389, status: 'operational', region: 'Andhra Pradesh', seaLevel: 0.36 },
  { id: 'TG012', name: 'Diamond Harbour', lat: 22.1893, lon: 88.1875, status: 'operational', region: 'West Bengal', seaLevel: 0.41 }
];

// Tsunami Buoys (Real DART-like positions)
export const TSUNAMI_BUOYS = [
  { id: 'TB001', name: 'BOB-01', lat: 15.5, lon: 85.0, status: 'active', lastUpdate: '2 min ago', depth: 4250 },
  { id: 'TB002', name: 'BOB-02', lat: 12.0, lon: 88.0, status: 'active', lastUpdate: '3 min ago', depth: 3890 },
  { id: 'TB003', name: 'BOB-03', lat: 8.5, lon: 92.5, status: 'active', lastUpdate: '1 min ago', depth: 4100 },
  { id: 'TB004', name: 'AS-01', lat: 17.0, lon: 68.0, status: 'active', lastUpdate: '4 min ago', depth: 3650 },
  { id: 'TB005', name: 'AS-02', lat: 12.5, lon: 65.5, status: 'warning', lastUpdate: '1 min ago', depth: 4320 },
  { id: 'TB006', name: 'AS-03', lat: 8.0, lon: 72.0, status: 'active', lastUpdate: '2 min ago', depth: 3970 }
];

// Generate High Wave/Swell Surge data
export function generateHighWaveData() {
  const severityLevels = ['no_threat', 'watch', 'alert', 'warning'];
  const waveData = [];

  Object.entries(COASTAL_REGIONS).forEach(([region, coords], index) => {
    // Generate 2-4 points per region
    const numPoints = 2 + Math.floor(Math.random() * 3);

    for (let i = 0; i < numPoints; i++) {
      const severity = severityLevels[Math.floor(Math.random() * severityLevels.length)];
      const waveHeight = severity === 'warning' ? 4.5 + Math.random() * 2 :
                        severity === 'alert' ? 3.0 + Math.random() * 1.5 :
                        severity === 'watch' ? 2.0 + Math.random() * 1 :
                        0.5 + Math.random() * 1.5;

      waveData.push({
        id: `HW${String(waveData.length + 1).padStart(3, '0')}`,
        location: `${region} Coast ${i + 1}`,
        region: region,
        lat: coords.lat + (Math.random() - 0.5) * 2,
        lon: coords.lon + (Math.random() - 0.5) * 1.5,
        severity: severity,
        waveHeight: parseFloat(waveHeight.toFixed(2)),
        swellPeriod: 8 + Math.random() * 6, // 8-14 seconds
        windSpeed: 15 + Math.random() * 30, // 15-45 knots
        direction: ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'][Math.floor(Math.random() * 8)],
        validUntil: new Date(Date.now() + 6 * 60 * 60 * 1000).toISOString(), // 6 hours
        issuedAt: new Date().toISOString()
      });
    }
  });

  return waveData;
}

// Generate Storm Surge data
export function generateStormSurgeData() {
  // Simulate a cyclone track approaching east coast
  const cycloneTrack = [
    { lat: 11.5, lon: 88.0, time: '2025-11-25T00:00:00Z', intensity: 'Depression' },
    { lat: 12.0, lon: 87.5, time: '2025-11-25T06:00:00Z', intensity: 'Deep Depression' },
    { lat: 13.0, lon: 86.5, time: '2025-11-25T12:00:00Z', intensity: 'Cyclonic Storm' },
    { lat: 14.5, lon: 85.0, time: '2025-11-25T18:00:00Z', intensity: 'Severe Cyclonic Storm' },
    { lat: 16.0, lon: 83.5, time: '2025-11-26T00:00:00Z', intensity: 'Very Severe Cyclonic Storm' },
    { lat: 17.5, lon: 82.0, time: '2025-11-26T06:00:00Z', intensity: 'Extremely Severe Cyclonic Storm' }
  ];

  // Generate storm surge grid data
  const surgeGrid = [];
  const centerLat = 15.0;
  const centerLon = 84.0;
  const gridSize = 50;

  for (let i = 0; i < gridSize; i++) {
    for (let j = 0; j < gridSize; j++) {
      const lat = centerLat - 5 + (i * 10 / gridSize);
      const lon = centerLon - 5 + (j * 10 / gridSize);

      // Calculate distance from cyclone center
      const distance = Math.sqrt(
        Math.pow(lat - centerLat, 2) + Math.pow(lon - centerLon, 2)
      );

      // Surge decreases with distance
      const maxSurge = 0.8;
      const surge = distance < 3 ? maxSurge * Math.exp(-distance / 2) : 0;

      if (surge > 0.05) {
        surgeGrid.push({
          lat: parseFloat(lat.toFixed(4)),
          lon: parseFloat(lon.toFixed(4)),
          surge: parseFloat(surge.toFixed(3))
        });
      }
    }
  }

  return {
    cyclone: {
      name: 'CYCLONE-2025A',
      currentPosition: cycloneTrack[cycloneTrack.length - 1],
      track: cycloneTrack,
      maxWindSpeed: 150, // kmph
      centralPressure: 960, // hPa
      category: 'ESCS'
    },
    surgeGrid: surgeGrid
  };
}

// Generate Earthquake/Tsunami threat data
export function generateSeismicData() {
  const earthquakes = [
    {
      id: 'EQ001',
      magnitude: 4.2,
      depth: 25,
      lat: 12.5,
      lon: 88.5,
      location: 'Andaman Sea',
      time: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      tsunamiThreat: 'no'
    },
    {
      id: 'EQ002',
      magnitude: 5.8,
      depth: 15,
      lat: 10.2,
      lon: 92.8,
      location: 'Nicobar Islands',
      time: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
      tsunamiThreat: 'local'
    }
  ];

  return earthquakes;
}

// Generate Rip Current Advisories
export function generateRipCurrentData() {
  const beaches = [
    'Marina Beach, Chennai',
    'Puri Beach, Odisha',
    'Juhu Beach, Mumbai',
    'Calangute Beach, Goa',
    'Kovalam Beach, Kerala',
    'Radhanagar Beach, Andaman',
    'RK Beach, Visakhapatnam',
    'Chandrabhaga Beach, Odisha'
  ];

  return beaches.map((beach, index) => {
    const severity = ['low', 'moderate', 'high'][Math.floor(Math.random() * 3)];
    const parts = beach.split(', ');

    return {
      id: `RC${String(index + 1).padStart(3, '0')}`,
      beach: parts[0],
      location: parts[1],
      lat: 10 + Math.random() * 13,
      lon: 72 + Math.random() * 20,
      severity: severity,
      currentSpeed: severity === 'high' ? 2.0 + Math.random() :
                   severity === 'moderate' ? 1.0 + Math.random() :
                   0.5 + Math.random() * 0.5,
      advisory: severity === 'high' ? 'Swimming not recommended' :
               severity === 'moderate' ? 'Swim with caution' :
               'Safe for swimming',
      validUntil: new Date(Date.now() + 12 * 60 * 60 * 1000).toISOString()
    };
  });
}

// Generate Oil Spill data
export function generateOilSpillData() {
  return [
    {
      id: 'OS001',
      type: 'crude_oil',
      lat: 19.5,
      lon: 72.0,
      area: 2.5, // sq km
      source: 'Vessel incident',
      reportedAt: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
      status: 'active',
      affectedCoast: 'Maharashtra',
      driftDirection: 'NE'
    }
  ];
}

// Generate Marine Pollution data
export function generateMarinePollutionData() {
  return [
    {
      id: 'MP001',
      type: 'algal_bloom',
      lat: 11.2,
      lon: 79.8,
      severity: 'moderate',
      area: 15, // sq km
      species: 'Red Tide',
      toxicity: 'low',
      location: 'Puducherry Coast',
      detectedAt: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString()
    },
    {
      id: 'MP002',
      type: 'plastic_accumulation',
      lat: 15.5,
      lon: 73.8,
      severity: 'high',
      area: 8,
      location: 'Goa Coast',
      detectedAt: new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString()
    }
  ];
}

// Combine all hazard data
export function getAllHazardsData() {
  return {
    tideGauges: TIDE_GAUGE_STATIONS,
    tsunamiBuoys: TSUNAMI_BUOYS,
    highWaves: generateHighWaveData(),
    stormSurge: generateStormSurgeData(),
    seismic: generateSeismicData(),
    ripCurrents: generateRipCurrentData(),
    oilSpills: generateOilSpillData(),
    marinePollution: generateMarinePollutionData(),
    lastUpdated: new Date().toISOString()
  };
}

// Simulate real-time updates
export function updateHazardData(currentData) {
  // Update tide gauge readings
  const updatedTideGauges = currentData.tideGauges.map(station => ({
    ...station,
    seaLevel: parseFloat((station.seaLevel + (Math.random() - 0.5) * 0.05).toFixed(2))
  }));

  // Update tsunami buoy status
  const updatedBuoys = currentData.tsunamiBuoys.map(buoy => {
    const minutesAgo = Math.floor(Math.random() * 5) + 1;
    return {
      ...buoy,
      lastUpdate: `${minutesAgo} min ago`
    };
  });

  return {
    ...currentData,
    tideGauges: updatedTideGauges,
    tsunamiBuoys: updatedBuoys,
    lastUpdated: new Date().toISOString()
  };
}
