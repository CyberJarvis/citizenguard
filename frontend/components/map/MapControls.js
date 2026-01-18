'use client';

import React from 'react';
import {
  Layers,
  RefreshCw,
  Bell,
  BellOff,
  Map,
  Satellite,
  Mountain,
  Droplets,
  Thermometer,
  ChevronDown,
  X,
  CloudLightning,
  Waves,
  Navigation,
  Activity,
  Globe,
  Sun,
  Anchor,
} from 'lucide-react';

/**
 * MapControls - Top-left control panel
 * Handles layers, filters, and map style switching
 */
export function MapControls({
  mapStyle = 'dark',
  onMapStyleChange = () => {},
  showHeatmap = true,
  onToggleHeatmap = () => {},
  showClusters = true,
  onToggleClusters = () => {},
  showCyclone = true,
  onToggleCyclone = () => {},
  showSurge = true,
  onToggleSurge = () => {},
  showOceanCurrents = true,
  onToggleOceanCurrents = () => {},
  showWaveHeight = true,
  onToggleWaveHeight = () => {},
  hasCyclone = false,
  showDemoCyclone = false,
  onToggleDemoCyclone = () => {},
  heatmapOpacity = 0.7,
  onHeatmapOpacityChange = () => {},
  notificationsEnabled = false,
  onToggleNotifications = () => {},
  isRefreshing = false,
  onRefresh = () => {},
  isExpanded = false,
  onToggleExpand = () => {},
}) {
  const mapStyles = [
    { id: 'esriOcean', name: 'Ocean', icon: Anchor, description: 'ESRI Ocean Basemap' },
    { id: 'esriOceanRef', name: 'Ocean+', icon: Waves, description: 'ESRI Ocean with Labels' },
    { id: 'dark', name: 'Dark', icon: Map, description: 'Dark Mode' },
    { id: 'satellite', name: 'Satellite', icon: Satellite, description: 'ESRI Satellite' },
    { id: 'natGeo', name: 'NatGeo', icon: Globe, description: 'National Geographic' },
    { id: 'physical', name: 'Physical', icon: Mountain, description: 'Physical Terrain' },
    { id: 'terrain', name: 'Terrain', icon: Mountain, description: 'Topographic' },
    { id: 'light', name: 'Light', icon: Sun, description: 'Light Mode' },
  ];

  return (
    <div className="absolute top-4 left-4 z-[1000] flex flex-col gap-3">
      {/* Main Control Panel */}
      <div className="glass-panel p-2">
        <div className="flex items-center gap-2">
          {/* Layers Toggle Button */}
          <button
            onClick={onToggleExpand}
            className={`map-control-btn ${isExpanded ? 'active' : ''}`}
            title="Map Layers"
          >
            <Layers className="w-5 h-5" />
          </button>

          {/* Refresh Button */}
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="map-control-btn"
            title="Refresh Data"
          >
            <RefreshCw className={`w-5 h-5 ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>

          {/* Notifications Toggle */}
          <button
            onClick={onToggleNotifications}
            className={`map-control-btn ${notificationsEnabled ? 'active' : ''}`}
            title={notificationsEnabled ? 'Disable Notifications' : 'Enable Notifications'}
          >
            {notificationsEnabled ? (
              <Bell className="w-5 h-5" />
            ) : (
              <BellOff className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>

      {/* Expanded Panel - Layers & Settings */}
      {isExpanded && (
        <div className="glass-panel-dark p-4 w-64 animate-in slide-in-from-top-2 duration-200">
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-white">Map Settings</h3>
            <button
              onClick={onToggleExpand}
              className="p-1 rounded-lg hover:bg-slate-700/50 text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Map Style Selection */}
          <div className="mb-5">
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
              Base Map
            </p>
            <div className="grid grid-cols-4 gap-1.5">
              {mapStyles.map((style) => {
                const Icon = style.icon;
                const isActive = mapStyle === style.id;
                const isOcean = style.id.startsWith('esri');
                return (
                  <button
                    key={style.id}
                    onClick={() => onMapStyleChange(style.id)}
                    className={`flex flex-col items-center gap-0.5 p-1.5 rounded-lg transition-all ${
                      isActive
                        ? isOcean
                          ? 'bg-blue-500/20 border border-blue-500/50 text-blue-400'
                          : 'bg-cyan-500/20 border border-cyan-500/50 text-cyan-400'
                        : 'hover:bg-slate-700/50 text-slate-400 hover:text-white border border-transparent'
                    }`}
                    title={style.description}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span className="text-[9px] font-medium leading-tight">{style.name}</span>
                  </button>
                );
              })}
            </div>
            <p className="text-[10px] text-slate-500 mt-2 text-center">
              Ocean & Ocean+ use ESRI marine basemaps
            </p>
          </div>

          {/* Layer Toggles */}
          <div className="mb-5">
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
              Layers
            </p>
            <div className="space-y-2">
              {/* Heatmap Toggle */}
              <label className="flex items-center gap-3 cursor-pointer group">
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={showHeatmap}
                    onChange={onToggleHeatmap}
                    className="sr-only"
                  />
                  <div
                    className={`w-10 h-5 rounded-full transition-colors ${
                      showHeatmap ? 'bg-cyan-500' : 'bg-slate-600'
                    }`}
                  >
                    <div
                      className={`w-4 h-4 rounded-full bg-white shadow-lg transform transition-transform ${
                        showHeatmap ? 'translate-x-5' : 'translate-x-0.5'
                      } translate-y-0.5`}
                    />
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Thermometer className="w-4 h-4 text-slate-400 group-hover:text-white transition-colors" />
                  <span className="text-sm text-slate-300 group-hover:text-white transition-colors">
                    Heatmap
                  </span>
                </div>
              </label>

              {/* Clusters Toggle */}
              <label className="flex items-center gap-3 cursor-pointer group">
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={showClusters}
                    onChange={onToggleClusters}
                    className="sr-only"
                  />
                  <div
                    className={`w-10 h-5 rounded-full transition-colors ${
                      showClusters ? 'bg-cyan-500' : 'bg-slate-600'
                    }`}
                  >
                    <div
                      className={`w-4 h-4 rounded-full bg-white shadow-lg transform transition-transform ${
                        showClusters ? 'translate-x-5' : 'translate-x-0.5'
                      } translate-y-0.5`}
                    />
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Droplets className="w-4 h-4 text-slate-400 group-hover:text-white transition-colors" />
                  <span className="text-sm text-slate-300 group-hover:text-white transition-colors">
                    Report Clusters
                  </span>
                </div>
              </label>

              {/* Cyclone Toggle */}
              <label className="flex items-center gap-3 cursor-pointer group">
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={showCyclone}
                    onChange={onToggleCyclone}
                    className="sr-only"
                  />
                  <div
                    className={`w-10 h-5 rounded-full transition-colors ${
                      showCyclone ? 'bg-purple-500' : 'bg-slate-600'
                    }`}
                  >
                    <div
                      className={`w-4 h-4 rounded-full bg-white shadow-lg transform transition-transform ${
                        showCyclone ? 'translate-x-5' : 'translate-x-0.5'
                      } translate-y-0.5`}
                    />
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <CloudLightning className={`w-4 h-4 ${hasCyclone ? 'text-purple-400 animate-pulse' : 'text-slate-400'} group-hover:text-white transition-colors`} />
                  <span className="text-sm text-slate-300 group-hover:text-white transition-colors">
                    Cyclone Track
                  </span>
                  {hasCyclone && (
                    <span className="text-[10px] px-1.5 py-0.5 bg-purple-500/30 text-purple-300 rounded-full">
                      ACTIVE
                    </span>
                  )}
                </div>
              </label>

              {/* Storm Surge Toggle */}
              <label className="flex items-center gap-3 cursor-pointer group">
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={showSurge}
                    onChange={onToggleSurge}
                    className="sr-only"
                  />
                  <div
                    className={`w-10 h-5 rounded-full transition-colors ${
                      showSurge ? 'bg-orange-500' : 'bg-slate-600'
                    }`}
                  >
                    <div
                      className={`w-4 h-4 rounded-full bg-white shadow-lg transform transition-transform ${
                        showSurge ? 'translate-x-5' : 'translate-x-0.5'
                      } translate-y-0.5`}
                    />
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Waves className="w-4 h-4 text-slate-400 group-hover:text-white transition-colors" />
                  <span className="text-sm text-slate-300 group-hover:text-white transition-colors">
                    Storm Surge
                  </span>
                </div>
              </label>

              {/* Ocean Currents Toggle */}
              <label className="flex items-center gap-3 cursor-pointer group">
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={showOceanCurrents}
                    onChange={onToggleOceanCurrents}
                    className="sr-only"
                  />
                  <div
                    className={`w-10 h-5 rounded-full transition-colors ${
                      showOceanCurrents ? 'bg-blue-500' : 'bg-slate-600'
                    }`}
                  >
                    <div
                      className={`w-4 h-4 rounded-full bg-white shadow-lg transform transition-transform ${
                        showOceanCurrents ? 'translate-x-5' : 'translate-x-0.5'
                      } translate-y-0.5`}
                    />
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Navigation className="w-4 h-4 text-blue-400 group-hover:text-white transition-colors" />
                  <span className="text-sm text-slate-300 group-hover:text-white transition-colors">
                    Ocean Currents
                  </span>
                </div>
              </label>

              {/* Wave Height Toggle */}
              <label className="flex items-center gap-3 cursor-pointer group">
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={showWaveHeight}
                    onChange={onToggleWaveHeight}
                    className="sr-only"
                  />
                  <div
                    className={`w-10 h-5 rounded-full transition-colors ${
                      showWaveHeight ? 'bg-teal-500' : 'bg-slate-600'
                    }`}
                  >
                    <div
                      className={`w-4 h-4 rounded-full bg-white shadow-lg transform transition-transform ${
                        showWaveHeight ? 'translate-x-5' : 'translate-x-0.5'
                      } translate-y-0.5`}
                    />
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-teal-400 group-hover:text-white transition-colors" />
                  <span className="text-sm text-slate-300 group-hover:text-white transition-colors">
                    Wave Height
                  </span>
                </div>
              </label>
            </div>
          </div>

          {/* Demo Cyclone Section */}
          <div className="mb-5 pt-3 border-t border-slate-700/50">
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
              Testing
            </p>
            <label className="flex items-center gap-3 cursor-pointer group">
              <div className="relative">
                <input
                  type="checkbox"
                  checked={showDemoCyclone}
                  onChange={onToggleDemoCyclone}
                  className="sr-only"
                />
                <div
                  className={`w-10 h-5 rounded-full transition-colors ${
                    showDemoCyclone ? 'bg-yellow-500' : 'bg-slate-600'
                  }`}
                >
                  <div
                    className={`w-4 h-4 rounded-full bg-white shadow-lg transform transition-transform ${
                      showDemoCyclone ? 'translate-x-5' : 'translate-x-0.5'
                    } translate-y-0.5`}
                  />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <CloudLightning className="w-4 h-4 text-yellow-400 group-hover:text-yellow-300 transition-colors" />
                <span className="text-sm text-slate-300 group-hover:text-white transition-colors">
                  Demo Cyclone
                </span>
              </div>
            </label>
            <p className="text-[10px] text-slate-500 mt-1.5 ml-[52px]">
              {showDemoCyclone
                ? 'Showing demo cyclone in Bay of Bengal'
                : 'Enable to show demo cyclone for testing'
              }
            </p>
          </div>

          {/* Heatmap Opacity Slider */}
          {showHeatmap && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Heatmap Intensity
                </p>
                <span className="text-xs text-slate-500">
                  {Math.round(heatmapOpacity * 100)}%
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={heatmapOpacity * 100}
                onChange={(e) => onHeatmapOpacityChange(Number(e.target.value) / 100)}
                className="heatmap-slider w-full"
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default MapControls;
