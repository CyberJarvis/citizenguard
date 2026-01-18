'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/ProtectedRoute';
import DashboardLayout from '@/components/DashboardLayout';
import useAuthStore from '@/context/AuthContext';
import {
  Camera,
  Upload,
  X,
  Loader2,
  MapPin,
  Waves,
  Wind,
  CloudRain,
  Anchor,
  Fish,
  Ship,
  Droplets,
  Trash2,
  RotateCcw,
  Check,
  Thermometer,
  AlertTriangle,
  ShieldCheck,
  ShieldAlert,
  Cloud,
  Compass,
  Eye,
  FileText,
  ChevronRight
} from 'lucide-react';
import toast, { Toaster } from 'react-hot-toast';
import { submitHazardReport, submitHazardReportS3, getFullEnrichment, getStorageStatus } from '@/lib/api';
import PageHeader from '@/components/PageHeader';
import { savePendingReport, isOnline } from '@/lib/offlineStorage';
import { syncPendingReports } from '@/lib/backgroundSync';
import { useS3Upload, UPLOAD_TYPES } from '@/hooks/useS3Upload';
import { InlineVoiceInput } from '@/components/InlineVoiceInput';

// Hazard types with icons
const NATURAL_HAZARDS = [
  { id: 'high_waves', label: 'High Waves', value: 'High Waves', icon: Waves },
  { id: 'rip_current', label: 'Rip Current', value: 'Rip Current', icon: Wind },
  { id: 'storm_cyclone', label: 'Storm / Cyclone', value: 'Storm Surge/Cyclone Effects', icon: CloudRain },
  { id: 'flooded_coast', label: 'Flooded Coast', value: 'Flooded Coastline', icon: Droplets },
  { id: 'beached_animal', label: 'Beached Animal', value: 'Beached Aquatic Animal', icon: Fish },
];

const HUMAN_MADE_HAZARDS = [
  { id: 'oil_spill', label: 'Oil/Chemical Spill', value: 'Oil Spill', icon: Droplets },
  { id: 'ship_wreck', label: 'Ship Wreck', value: 'Ship Wreck', icon: Ship },
  { id: 'plastic_pollution', label: 'Marine Debris', value: 'Plastic Pollution', icon: Trash2 },
  { id: 'fisher_nets', label: 'Other', value: 'Fisher Nets Entanglement', icon: Anchor },
];

function ReportHazardContent() {
  const router = useRouter();
  const { user } = useAuthStore();
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const cameraStreamRef = useRef(null);
  const fileInputRef = useRef(null);

  // Form state
  const [capturedImage, setCapturedImage] = useState(null);
  const [selectedHazard, setSelectedHazard] = useState(null);
  const [description, setDescription] = useState('');
  const [location, setLocation] = useState(null);
  const [isLoadingLocation, setIsLoadingLocation] = useState(false);

  // Voice input state
  const [isVoiceListening, setIsVoiceListening] = useState(false);
  const [voiceTranscript, setVoiceTranscript] = useState('');

  // Environmental data
  const [weather, setWeather] = useState(null);
  const [isLoadingWeather, setIsLoadingWeather] = useState(false);
  const [threatAssessment, setThreatAssessment] = useState(null);
  const [isLoadingThreat, setIsLoadingThreat] = useState(false);

  // Camera state
  const [showCameraModal, setShowCameraModal] = useState(false);
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [isCameraLoading, setIsCameraLoading] = useState(false);
  const [showCapturePreview, setShowCapturePreview] = useState(false);
  const [previewImage, setPreviewImage] = useState(null);
  const [cameraFacingMode, setCameraFacingMode] = useState('environment');

  // Submit state
  const [isSubmitting, setIsSubmitting] = useState(false);

  // S3 upload state
  const [s3Enabled, setS3Enabled] = useState(false);
  const { uploadFile, uploading: s3Uploading, progress: s3Progress } = useS3Upload();

  // Check S3 status on mount
  useEffect(() => {
    const checkS3 = async () => {
      try {
        const status = await getStorageStatus();
        setS3Enabled(status.s3_enabled);
      } catch (error) {
        console.log('S3 not available, using local storage');
      }
    };
    checkS3();
  }, []);

  useEffect(() => {
    return () => { stopCamera(); };
  }, []);

  useEffect(() => {
    if (capturedImage && !location) detectLocation();
  }, [capturedImage]);

  // ============ LOCATION ============
  const detectLocation = async () => {
    setIsLoadingLocation(true);
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const { latitude, longitude } = position.coords;
          const address = await reverseGeocode(latitude, longitude);
          setLocation({ latitude, longitude, address: address || 'Location detected', isAutoDetected: true });
          setIsLoadingLocation(false);
          toast.success('Location captured!');
          fetchWeatherData(latitude, longitude);
          fetchThreatAssessment(latitude, longitude);
        },
        () => { setIsLoadingLocation(false); toast.error('Unable to detect location'); },
        { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
      );
    } else {
      setIsLoadingLocation(false);
      toast.error('Geolocation not supported');
    }
  };

  const reverseGeocode = async (lat, lon) => {
    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&zoom=16&addressdetails=1`,
        { headers: { 'User-Agent': 'CoastGuardian/1.0', 'Accept': 'application/json' } }
      );
      if (!response.ok) return null;
      const data = await response.json();
      const addr = data.address;
      const parts = [];
      if (addr?.suburb || addr?.neighbourhood) parts.push(addr.suburb || addr.neighbourhood);
      if (addr?.city || addr?.town || addr?.village) parts.push(addr.city || addr.town || addr.village);
      if (addr?.state) parts.push(addr.state);
      return parts.length > 0 ? parts.join(', ') : null;
    } catch { return null; }
  };

  const fetchWeatherData = async (lat, lon) => {
    setIsLoadingWeather(true);
    try {
      const apiKey = process.env.NEXT_PUBLIC_WEATHER_API_KEY;
      const baseUrl = process.env.NEXT_PUBLIC_WEATHER_API_BASE_URL;
      if (!apiKey) {
        setWeather({ temp: 28, condition: 'Partly Cloudy', wind: 12, humidity: 75, cloudCover: 45 });
        return;
      }
      const response = await fetch(`${baseUrl}/current.json?key=${apiKey}&q=${lat},${lon}`);
      if (response.ok) {
        const data = await response.json();
        setWeather({
          temp: Math.round(data.current.temp_c),
          condition: data.current.condition.text,
          wind: Math.round(data.current.wind_kph),
          humidity: data.current.humidity,
          cloudCover: data.current.cloud
        });
      }
    } catch {} finally { setIsLoadingWeather(false); }
  };

  const fetchThreatAssessment = async (lat, lon) => {
    setIsLoadingThreat(true);
    try {
      const response = await getFullEnrichment(lat, lon, null);
      if (response.success) {
        // Extract marine data from environmental_snapshot
        const marine = response.environmental_snapshot?.marine || {};

        // Format tide time for display (extract just the time part)
        const tideTime = marine.tide_time ? marine.tide_time.split(' ')[1] || marine.tide_time : 'N/A';
        const tideType = marine.tide_type?.toUpperCase() || 'MID';
        const tideHeight = marine.tide_height_mt ? `${marine.tide_height_mt}m` : 'N/A';

        // Determine current and next tide based on the reported tide type
        // The API returns the next significant tide event
        const nextTideType = tideType === 'HIGH' ? 'High' : tideType === 'LOW' ? 'Low' : 'Mid';
        const currentTideType = tideType === 'HIGH' ? 'Low' : tideType === 'LOW' ? 'High' : 'Mid';

        // Wave and swell data
        const waveHeight = marine.sig_ht_mt ? `${marine.sig_ht_mt}m` : '0m';
        const swellHeight = marine.swell_ht_mt ? `${marine.swell_ht_mt}m` : '0m';
        const swellPeriod = marine.swell_period_secs ? `${marine.swell_period_secs}s` : 'N/A';
        const swellDir = marine.swell_dir_16_point || 'N/A';

        setThreatAssessment({
          level: response.threat_level || 0,
          levelName: response.threat_level_name || 'NO THREAT',
          primaryHazard: response.primary_hazard,
          classification: response.hazard_classification,
          confidence: Math.round((response.hazard_classification?.confidence || 0.9) * 100),
          analysis: response.analysis || 'No significant threats detected',
          recommendation: response.recommendation || 'Normal conditions - exercise standard coastal safety',
          hazards: {
            tsunami: response.hazard_classification?.tsunami_threat || 'NO THREAT',
            cyclone: response.hazard_classification?.cyclone_threat || 'NO THREAT',
            highWaves: response.hazard_classification?.high_waves_threat || 'NO THREAT',
            flood: response.hazard_classification?.coastal_flood_threat || 'NO THREAT',
            ripCurrent: response.hazard_classification?.rip_current_threat || 'NO THREAT'
          },
          tide: {
            current: `${currentTideType} Tide`,
            currentHeight: 'Now',
            next: `${nextTideType} Tide`,
            nextTime: tideTime,
            waveHeight: waveHeight,
            waveDirection: swellDir,
            swell: swellHeight,
            swellPeriod: swellPeriod
          }
        });
      }
    } catch {} finally { setIsLoadingThreat(false); }
  };

  // ============ CAMERA ============
  const openCameraModal = () => { setShowCameraModal(true); setTimeout(() => startCamera(), 100); };
  const closeCameraModal = () => { stopCamera(); setShowCameraModal(false); setShowCapturePreview(false); setPreviewImage(null); };

  const startCamera = async () => {
    try {
      setIsCameraLoading(true);
      stopCamera();
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: cameraFacingMode, width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        cameraStreamRef.current = stream;
        videoRef.current.onloadedmetadata = () => {
          videoRef.current.play().then(() => { setIsCameraActive(true); setIsCameraLoading(false); }).catch(() => setIsCameraLoading(false));
        };
      }
    } catch { setIsCameraLoading(false); toast.error('Unable to access camera'); }
  };

  const stopCamera = () => {
    if (cameraStreamRef.current) { cameraStreamRef.current.getTracks().forEach(track => track.stop()); cameraStreamRef.current = null; }
    if (videoRef.current) videoRef.current.srcObject = null;
    setIsCameraActive(false); setIsCameraLoading(false);
  };

  const switchCamera = () => {
    const newMode = cameraFacingMode === 'environment' ? 'user' : 'environment';
    setCameraFacingMode(newMode);
    if (isCameraActive) { stopCamera(); setTimeout(() => startCamera(), 200); }
  };

  const capturePhoto = () => {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (video.videoWidth === 0) { toast.error('Camera not ready'); return; }
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      if (!blob) { toast.error('Failed to capture'); return; }
      setPreviewImage({ blob, url: URL.createObjectURL(blob) });
      setShowCapturePreview(true);
      stopCamera();
    }, 'image/jpeg', 0.95);
  };

  const usePhoto = () => { setCapturedImage(previewImage); closeCameraModal(); toast.success('Photo added!'); };
  const retakePhoto = () => { setShowCapturePreview(false); setPreviewImage(null); startCamera(); };
  const removePhoto = () => { setCapturedImage(null); setLocation(null); setWeather(null); setThreatAssessment(null); };

  // ============ FILE UPLOAD ============
  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) { toast.error('Please select an image'); return; }
    if (file.size > 10 * 1024 * 1024) { toast.error('Max size: 10MB'); return; }
    setCapturedImage({ blob: file, url: URL.createObjectURL(file), isUploaded: true });
    toast.success('Image uploaded!');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // ============ SUBMIT ============
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!capturedImage) { toast.error('Please add a photo'); return; }
    if (!selectedHazard) { toast.error('Please select hazard type'); return; }
    if (!location) { toast.error('Location required'); return; }

    setIsSubmitting(true);

    // Check if we're online
    const online = isOnline();

    try {
      if (online) {
        // Online: Submit to server
        const category = NATURAL_HAZARDS.find(h => h.id === selectedHazard.id) ? 'natural' : 'humanMade';

        if (s3Enabled) {
          // S3 Mode: Upload image to S3 first, then submit report with URL
          toast.loading('Uploading image...', { id: 'upload' });

          try {
            // Upload image to S3
            const uploadResult = await uploadFile(capturedImage.blob, UPLOAD_TYPES.HAZARD_IMAGE);

            toast.dismiss('upload');
            toast.loading('Submitting report...', { id: 'submit' });

            // Submit report with S3 URL
            const reportData = {
              hazard_type: selectedHazard.value,
              category: category,
              latitude: location.latitude,
              longitude: location.longitude,
              address: location.address,
              description: description || '',
              weather: weather || null,
              image_url: uploadResult.publicUrl,
              voice_note_url: null, // TODO: Add voice note S3 upload
            };

            await submitHazardReportS3(reportData);
            toast.dismiss('submit');
            toast.success('Report submitted!');
            router.push('/dashboard');
          } catch (s3Error) {
            toast.dismiss('upload');
            toast.dismiss('submit');
            console.error('S3 upload failed, falling back to local:', s3Error);

            // Fallback to local upload if S3 fails
            const submitData = new FormData();
            submitData.append('hazard_type', selectedHazard.value);
            submitData.append('category', category);
            submitData.append('image', capturedImage.blob, 'hazard-photo.jpg');
            submitData.append('latitude', location.latitude);
            submitData.append('longitude', location.longitude);
            submitData.append('address', location.address);
            submitData.append('description', description || '');
            if (weather) submitData.append('weather', JSON.stringify(weather));
            if (threatAssessment) submitData.append('hazard_classification', JSON.stringify(threatAssessment.classification));

            await submitHazardReport(submitData);
            toast.success('Report submitted!');
            router.push('/dashboard');
          }
        } else {
          // Local Mode: Traditional form upload
          const submitData = new FormData();
          submitData.append('hazard_type', selectedHazard.value);
          submitData.append('category', category);
          submitData.append('image', capturedImage.blob, 'hazard-photo.jpg');
          submitData.append('latitude', location.latitude);
          submitData.append('longitude', location.longitude);
          submitData.append('address', location.address);
          submitData.append('description', description || '');
          if (weather) submitData.append('weather', JSON.stringify(weather));
          if (threatAssessment) submitData.append('hazard_classification', JSON.stringify(threatAssessment.classification));

          await submitHazardReport(submitData);
          toast.success('Report submitted!');
          router.push('/dashboard');
        }
      } else {
        // Offline: Save to IndexedDB for later sync
        // Convert image blob to base64 for storage
        const reader = new FileReader();
        reader.onloadend = async () => {
          const reportData = {
            hazard_type: selectedHazard.value,
            category: NATURAL_HAZARDS.find(h => h.id === selectedHazard.id) ? 'natural' : 'humanMade',
            photo_base64: reader.result,
            latitude: location.latitude,
            longitude: location.longitude,
            location_description: location.address,
            description: description || '',
            severity: 'medium', // Default severity
            weather: weather ? JSON.stringify(weather) : null,
            hazard_classification: threatAssessment?.classification ? JSON.stringify(threatAssessment.classification) : null,
          };

          await savePendingReport(reportData);
          toast.success('Report saved! Will submit when online.', {
            icon: '📱',
            duration: 4000,
          });
          router.push('/dashboard');
        };
        reader.readAsDataURL(capturedImage.blob);
      }
    } catch (error) {
      // If online submission fails, try to save offline
      if (online) {
        try {
          const reader = new FileReader();
          reader.onloadend = async () => {
            const reportData = {
              hazard_type: selectedHazard.value,
              category: NATURAL_HAZARDS.find(h => h.id === selectedHazard.id) ? 'natural' : 'humanMade',
              photo_base64: reader.result,
              latitude: location.latitude,
              longitude: location.longitude,
              location_description: location.address,
              description: description || '',
              severity: 'medium',
              weather: weather ? JSON.stringify(weather) : null,
              hazard_classification: threatAssessment?.classification ? JSON.stringify(threatAssessment.classification) : null,
            };

            await savePendingReport(reportData);
            toast.success('Saved offline. Will retry when connection improves.', {
              icon: '📱',
              duration: 4000,
            });
            router.push('/dashboard');
          };
          reader.readAsDataURL(capturedImage.blob);
        } catch (offlineError) {
          toast.error(error.response?.data?.detail || 'Submission failed');
        }
      } else {
        toast.error('Failed to save report');
      }
    } finally { setIsSubmitting(false); }
  };

  const getHazardStatus = (status) => {
    const s = status?.toUpperCase() || 'NO THREAT';
    if (s.includes('HIGH') || s.includes('SEVERE') || s.includes('WARNING')) {
      return { label: 'HIGH', color: 'bg-red-400' };
    }
    if (s.includes('MEDIUM') || s.includes('ALERT') || s.includes('MODERATE')) {
      return { label: 'ALERT', color: 'bg-orange-400' };
    }
    if (s.includes('LOW') || s.includes('WATCH')) {
      return { label: 'LOW', color: 'bg-yellow-400' };
    }
    return { label: 'SAFE', color: 'bg-emerald-300' };
  };

  // ============ RENDER ============
  return (
    <div className="min-h-full bg-slate-50">
      <Toaster position="top-center" />
      <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFileUpload} className="hidden" />

      {/* Main Content */}
      <div className="p-4 lg:p-6 pb-28 lg:pb-8">
        {/* Page Header - Desktop Only */}
        <PageHeader />

        {/* Mobile Header */}
        <div className="lg:hidden mb-6">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-10 h-10 bg-gradient-to-br from-[#0d4a6f] to-[#083a57] rounded-xl flex items-center justify-center shadow-lg shadow-[#0d4a6f]/20">
              <AlertTriangle className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-slate-900">Report a Hazard</h1>
              <p className="text-xs text-slate-500">Help keep your community safe</p>
            </div>
          </div>
        </div>

        {/* Main Form */}
        <form onSubmit={handleSubmit} className="max-w-6xl mx-auto">

          {/* Step Indicator - Mobile */}
          <div className="lg:hidden mb-6">
            <div className="flex items-center justify-between bg-white rounded-xl p-3 shadow-sm border border-slate-100">
              <div className={`flex items-center gap-2 ${capturedImage ? 'text-emerald-600' : 'text-[#0d4a6f]'}`}>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold ${capturedImage ? 'bg-emerald-100' : 'bg-[#e8f4fc]'}`}>
                  {capturedImage ? <Check className="w-3.5 h-3.5" /> : '1'}
                </div>
                <span className="text-xs font-medium">Photo</span>
              </div>
              <ChevronRight className="w-4 h-4 text-slate-300" />
              <div className={`flex items-center gap-2 ${selectedHazard ? 'text-emerald-600' : capturedImage ? 'text-[#0d4a6f]' : 'text-slate-400'}`}>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold ${selectedHazard ? 'bg-emerald-100' : capturedImage ? 'bg-[#e8f4fc]' : 'bg-slate-100'}`}>
                  {selectedHazard ? <Check className="w-3.5 h-3.5" /> : '2'}
                </div>
                <span className="text-xs font-medium">Type</span>
              </div>
              <ChevronRight className="w-4 h-4 text-slate-300" />
              <div className={`flex items-center gap-2 ${capturedImage && selectedHazard ? 'text-[#0d4a6f]' : 'text-slate-400'}`}>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold ${capturedImage && selectedHazard ? 'bg-[#e8f4fc]' : 'bg-slate-100'}`}>
                  3
                </div>
                <span className="text-xs font-medium">Submit</span>
              </div>
            </div>
          </div>

          {/* Two Column Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

            {/* Left Column - Photo & Location */}
            <div className="space-y-5">

              {/* Photo Upload Card */}
              <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
                <div className="p-4 sm:p-5">
                  <label className="flex items-center gap-2 text-base font-semibold text-gray-900">
                    <Camera className="w-5 h-5 text-[#0d4a6f]" />
                    Add Photo <span className="text-red-500">*</span>
                  </label>
                  <p className="text-sm text-slate-500 mt-0.5 mb-4">Take or upload a clear photo of the hazard</p>
                  {!capturedImage ? (
                    <div className="border-2 border-dashed border-slate-200 rounded-xl p-8 hover:border-[#1a6b9a] transition-colors bg-slate-50/50">
                      <div className="flex flex-col sm:flex-row justify-center gap-4">
                        <button
                          type="button"
                          onClick={openCameraModal}
                          className="flex items-center justify-center gap-3 px-6 py-4 bg-[#0d4a6f] hover:bg-[#083a57] text-white rounded-xl transition-all shadow-lg shadow-[#0d4a6f]/20"
                        >
                          <Camera className="w-5 h-5" />
                          <span className="font-medium">Take Photo</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => fileInputRef.current?.click()}
                          className="flex items-center justify-center gap-3 px-6 py-4 bg-white hover:bg-slate-50 text-slate-700 rounded-xl transition-all border-2 border-slate-200 hover:border-slate-300"
                        >
                          <Upload className="w-5 h-5" />
                          <span className="font-medium">Upload</span>
                        </button>
                      </div>
                      <p className="text-center text-xs text-slate-400 mt-4">Supports JPG, PNG up to 10MB</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <div className="relative aspect-video rounded-xl overflow-hidden bg-slate-100">
                        <img src={capturedImage.url} alt="Hazard" className="w-full h-full object-cover" />
                        <button
                          type="button"
                          onClick={removePhoto}
                          className="absolute top-3 right-3 w-8 h-8 bg-black/60 hover:bg-black/80 rounded-full flex items-center justify-center text-white backdrop-blur-sm transition-colors"
                        >
                          <X className="w-4 h-4" />
                        </button>
                        <div className="absolute bottom-3 left-3 px-2 py-1 bg-emerald-500 text-white text-xs font-medium rounded-lg flex items-center gap-1">
                          <Check className="w-3 h-3" /> Photo Added
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="w-full py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl flex items-center justify-center gap-2 text-sm font-medium transition-colors"
                      >
                        <Upload className="w-4 h-4" /> Change Photo
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Location Card */}
              {(location || isLoadingLocation) && (
                <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
                  <div className="p-4 sm:p-5">
                    {isLoadingLocation ? (
                      <div className="flex items-center gap-3 text-[#0d4a6f]">
                        <Loader2 className="w-5 h-5 animate-spin" />
                        <div>
                          <p className="text-sm font-medium">Detecting location...</p>
                          <p className="text-xs text-slate-500">Please wait</p>
                        </div>
                      </div>
                    ) : location && (
                      <div className="flex items-start gap-3">
                        <div className="w-10 h-10 bg-emerald-500 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-emerald-500/20">
                          <MapPin className="w-5 h-5 text-white" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-semibold text-emerald-600 uppercase tracking-wide flex items-center gap-1">
                            <Check className="w-3 h-3" /> Location Captured
                          </p>
                          <p className="text-sm font-medium text-gray-900 mt-0.5">{location.address}</p>
                          <p className="text-xs text-slate-500 mt-0.5">{location.latitude?.toFixed(6)}, {location.longitude?.toFixed(6)}</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Weather & Conditions Card */}
              {location && (
                <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
                  <div className="p-4 sm:p-5 border-b border-slate-100 bg-slate-50/50">
                    <p className="text-base font-semibold text-gray-900 flex items-center gap-2">
                      <Cloud className="w-5 h-5 text-[#0d4a6f]" />
                      Current Conditions
                    </p>
                  </div>

                  <div className="p-4 sm:p-5">
                    {isLoadingWeather ? (
                      <div className="flex items-center justify-center py-4">
                        <Loader2 className="w-5 h-5 text-[#0d4a6f] animate-spin mr-2" />
                        <span className="text-sm text-slate-500">Loading weather...</span>
                      </div>
                    ) : weather ? (
                      <div className="space-y-4">
                        {/* Weather Grid */}
                        <div className="grid grid-cols-4 gap-2">
                          <div className="text-center bg-slate-50 rounded-xl p-3">
                            <Thermometer className="w-5 h-5 text-red-500 mx-auto" />
                            <p className="text-base font-semibold text-gray-900 mt-1">{weather.temp}°C</p>
                            <p className="text-[10px] text-slate-500 uppercase">Temp</p>
                          </div>
                          <div className="text-center bg-slate-50 rounded-xl p-3">
                            <Wind className="w-5 h-5 text-[#1a6b9a] mx-auto" />
                            <p className="text-base font-semibold text-gray-900 mt-1">{weather.wind}</p>
                            <p className="text-[10px] text-slate-500 uppercase">km/h</p>
                          </div>
                          <div className="text-center bg-slate-50 rounded-xl p-3">
                            <Droplets className="w-5 h-5 text-cyan-500 mx-auto" />
                            <p className="text-base font-semibold text-gray-900 mt-1">{weather.humidity}%</p>
                            <p className="text-[10px] text-slate-500 uppercase">Humidity</p>
                          </div>
                          <div className="text-center bg-slate-50 rounded-xl p-3">
                            <Cloud className="w-5 h-5 text-slate-400 mx-auto" />
                            <p className="text-base font-semibold text-gray-900 mt-1">{weather.cloudCover}%</p>
                            <p className="text-[10px] text-slate-500 uppercase">Clouds</p>
                          </div>
                        </div>

                        {/* Tide & Wave Info */}
                        {threatAssessment?.tide && (
                          <div className="pt-4 border-t border-slate-100">
                            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Tide & Waves</p>
                            <div className="grid grid-cols-4 gap-2">
                              <div className="text-center">
                                <Waves className="w-4 h-4 text-[#0d4a6f] mx-auto" />
                                <p className="text-sm font-semibold text-gray-900 mt-1">{threatAssessment.tide.current}</p>
                                <p className="text-[10px] text-slate-500">{threatAssessment.tide.currentHeight}</p>
                              </div>
                              <div className="text-center">
                                <Compass className="w-4 h-4 text-[#1a6b9a] mx-auto" />
                                <p className="text-sm font-semibold text-gray-900 mt-1">{threatAssessment.tide.next}</p>
                                <p className="text-[10px] text-slate-500">{threatAssessment.tide.nextTime}</p>
                              </div>
                              <div className="text-center">
                                <Waves className="w-4 h-4 text-indigo-500 mx-auto" />
                                <p className="text-sm font-semibold text-gray-900 mt-1">{threatAssessment.tide.waveHeight}</p>
                                <p className="text-[10px] text-slate-500">{threatAssessment.tide.waveDirection}</p>
                              </div>
                              <div className="text-center">
                                <Wind className="w-4 h-4 text-purple-500 mx-auto" />
                                <p className="text-sm font-semibold text-gray-900 mt-1">{threatAssessment.tide.swell}</p>
                                <p className="text-[10px] text-slate-500">{threatAssessment.tide.swellPeriod}</p>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-center py-4 text-slate-400 text-sm">
                        Weather data unavailable
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Right Column - Hazard Type & Description */}
            <div className="space-y-5">

              {/* Threat Assessment Card */}
              {threatAssessment && location && (() => {
                const threatLevel = threatAssessment.levelName?.toUpperCase() || 'NO THREAT';
                const isHighThreat = threatLevel.includes('HIGH') || threatLevel.includes('SEVERE') || threatLevel.includes('WARNING');
                const isMediumThreat = threatLevel.includes('MEDIUM') || threatLevel.includes('ALERT');
                const bgColor = isHighThreat ? 'bg-gradient-to-br from-red-500 to-red-600' : isMediumThreat ? 'bg-gradient-to-br from-orange-500 to-orange-600' : 'bg-gradient-to-br from-emerald-500 to-emerald-600';
                const ThreatIcon = isHighThreat ? ShieldAlert : isMediumThreat ? AlertTriangle : ShieldCheck;

                return (
                  <div className={`${bgColor} rounded-2xl p-5 text-white shadow-lg overflow-hidden relative`}>
                    {/* Background Pattern */}
                    <div className="absolute inset-0 opacity-10">
                      <div className="absolute top-0 right-0 w-32 h-32 bg-white rounded-full -translate-y-1/2 translate-x-1/2" />
                      <div className="absolute bottom-0 left-0 w-24 h-24 bg-white rounded-full translate-y-1/2 -translate-x-1/2" />
                    </div>

                    <div className="relative">
                      {/* Header */}
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
                            <ThreatIcon className="w-5 h-5" />
                          </div>
                          <div>
                            <p className="text-xs opacity-80 uppercase tracking-wide">Threat Assessment</p>
                            <p className="text-lg font-semibold">{threatAssessment.levelName?.replace(/_/g, ' ') || 'NO THREAT'}</p>
                          </div>
                        </div>
                        <span className="text-sm bg-white/20 px-3 py-1 rounded-full backdrop-blur-sm">{threatAssessment.confidence}%</span>
                      </div>

                      {/* Hazard Status Grid */}
                      <div className="grid grid-cols-5 gap-2">
                        {[
                          { key: 'tsunami', label: 'Tsunami', icon: Waves },
                          { key: 'cyclone', label: 'Cyclone', icon: CloudRain },
                          { key: 'highWaves', label: 'Waves', icon: Waves },
                          { key: 'flood', label: 'Flood', icon: Droplets },
                          { key: 'ripCurrent', label: 'Rip', icon: Wind }
                        ].map(({ key, label, icon: Icon }) => {
                          const status = getHazardStatus(threatAssessment.hazards?.[key]);
                          return (
                            <div key={key} className="text-center bg-white/10 rounded-xl py-2 px-1 backdrop-blur-sm">
                              <Icon className="w-4 h-4 mx-auto mb-1 opacity-90" />
                              <p className="text-[10px] font-medium truncate">{label}</p>
                              <div className="flex items-center justify-center gap-1 mt-1">
                                <span className={`w-2 h-2 ${status.color} rounded-full`}></span>
                                <span className="text-[9px] opacity-80">{status.label}</span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                );
              })()}

              {/* Hazard Type Selection Card */}
              <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
                <div className="p-4 sm:p-5">
                  <label className="flex items-center gap-2 text-base font-semibold text-gray-900">
                    <AlertTriangle className="w-5 h-5 text-[#0d4a6f]" />
                    What did you see? <span className="text-red-500">*</span>
                  </label>
                  <p className="text-sm text-slate-500 mt-0.5 mb-4">Select the type of hazard you encountered</p>

                  {/* Natural Hazards */}
                  <div className="mb-4">
                    <p className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-2">Natural Hazards</p>
                    <div className="flex flex-wrap gap-2">
                      {NATURAL_HAZARDS.map((hazard) => {
                        const Icon = hazard.icon;
                        const isSelected = selectedHazard?.id === hazard.id;
                        return (
                          <button
                            key={hazard.id}
                            type="button"
                            onClick={() => setSelectedHazard(hazard)}
                            className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-base font-medium transition-all border-2 ${
                              isSelected
                                ? 'bg-[#0d4a6f] text-white border-[#0d4a6f] shadow-lg shadow-[#0d4a6f]/20'
                                : 'bg-white text-slate-700 border-slate-200 hover:border-[#1a6b9a] hover:bg-slate-50'
                            }`}
                          >
                            <Icon className="w-4 h-4" />
                            {hazard.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Human-Made Hazards */}
                  <div>
                    <p className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-2">Human-Made Hazards</p>
                    <div className="flex flex-wrap gap-2">
                      {HUMAN_MADE_HAZARDS.map((hazard) => {
                        const Icon = hazard.icon;
                        const isSelected = selectedHazard?.id === hazard.id;
                        return (
                          <button
                            key={hazard.id}
                            type="button"
                            onClick={() => setSelectedHazard(hazard)}
                            className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-base font-medium transition-all border-2 ${
                              isSelected
                                ? 'bg-[#0d4a6f] text-white border-[#0d4a6f] shadow-lg shadow-[#0d4a6f]/20'
                                : 'bg-white text-slate-700 border-slate-200 hover:border-[#1a6b9a] hover:bg-slate-50'
                            }`}
                          >
                            <Icon className="w-4 h-4" />
                            {hazard.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                  {/* <button
                    type="button"
                    onClick={openCameraModal}
                    className="flex items-center justify-center space-x-2 px-8 py-3 bg-blue-600 hover:bg-blue-700 active:scale-[0.98] text-white font-semibold rounded-xl transition-all shadow-sm"
                  >
                    <Camera className="w-5 h-5" />
                    <span>Open Camera</span>
                  </button> */}
                </div>
              </div>

              {/* Description Card */}
              <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
                <div className="p-4 sm:p-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="flex items-center gap-2 text-base font-semibold text-gray-900">
                        <FileText className="w-5 h-5 text-[#0d4a6f]" />
                        Additional Details <span className="text-slate-400 font-normal"></span>
                      </label>
                      <p className="text-sm text-slate-500 mt-0.5">Describe the hazard using text or voice</p>
                    </div>
                    {/* Voice Input in Header */}
                    <InlineVoiceInput
                      value={description}
                      onChange={setDescription}
                      disabled={isSubmitting}
                      onListeningChange={setIsVoiceListening}
                      onTranscriptChange={setVoiceTranscript}
                    />
                  </div>

                  {/* Live Transcript - shown below header when listening */}
                  {isVoiceListening && voiceTranscript && (
                    <div className="mt-3 px-3 py-2 bg-red-50 rounded-lg border border-red-100">
                      <p className="text-sm text-slate-600 italic">"{voiceTranscript}"</p>
                    </div>
                  )}

                  {/* Description Textarea */}
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Describe the hazard in detail - what you saw, how severe it looks, any immediate dangers..."
                    rows={4}
                    className={`w-full px-4 py-3 border-2 border-slate-200 focus:border-[#0d4a6f] rounded-xl text-base text-gray-900 placeholder-slate-400 focus:outline-none focus:ring-0 resize-none transition-colors ${isVoiceListening && voiceTranscript ? 'mt-3' : 'mt-4'}`}
                  />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => router.back()}
                  className="flex-1 py-3.5 bg-white text-slate-700 font-semibold rounded-xl border-2 border-slate-200 hover:bg-slate-50 hover:border-slate-300 transition-all text-base"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || !capturedImage || !selectedHazard}
                  className="flex-[2] py-3.5 bg-[#0d4a6f] hover:bg-[#083a57] text-white font-semibold rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-base shadow-lg shadow-[#0d4a6f]/20"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Submitting...
                    </>
                  ) : (
                    <>
                      <Check className="w-4 h-4" />
                      Submit Report
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </form>
      </div>

      {/* Camera Modal - Higher z-index to appear above PageHeader (z-9999) and BottomNav (z-50) */}
      {showCameraModal && (
        <div className="fixed inset-0 z-[99999] bg-black">
          {!showCapturePreview ? (
            <div className="relative w-full h-full">
              <div className="absolute top-0 left-0 right-0 z-10 bg-gradient-to-b from-black/70 to-transparent">
                <div className="flex items-center justify-between p-4 safe-area-top">
                  <button onClick={closeCameraModal} className="w-11 h-11 bg-white/10 hover:bg-white/20 rounded-full flex items-center justify-center backdrop-blur-md transition-colors">
                    <X className="w-5 h-5 text-white" />
                  </button>
                  <h2 className="text-white font-semibold text-lg">Take Photo</h2>
                  <button onClick={switchCamera} className="w-11 h-11 bg-white/10 hover:bg-white/20 rounded-full flex items-center justify-center backdrop-blur-md transition-colors">
                    <RotateCcw className="w-5 h-5 text-white" />
                  </button>
                </div>
              </div>
              {isCameraLoading ? (
                <div className="w-full h-full flex flex-col items-center justify-center">
                  <Loader2 className="w-12 h-12 text-white animate-spin mb-4" />
                  <p className="text-white text-base">Starting camera...</p>
                </div>
              ) : (
                <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
              )}
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent py-10 safe-area-bottom">
                <div className="flex justify-center">
                  <button
                    onClick={capturePhoto}
                    disabled={!isCameraActive}
                    className="w-20 h-20 bg-white rounded-full flex items-center justify-center shadow-2xl hover:scale-105 active:scale-95 transition-transform disabled:opacity-50"
                  >
                    <div className="w-16 h-16 bg-white border-4 border-slate-900 rounded-full" />
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="relative w-full h-full">
              <div className="absolute top-0 left-0 right-0 z-10 bg-gradient-to-b from-black/70 to-transparent">
                <div className="flex items-center justify-between p-4 safe-area-top">
                  <button onClick={closeCameraModal} className="w-11 h-11 bg-white/10 hover:bg-white/20 rounded-full flex items-center justify-center backdrop-blur-md transition-colors">
                    <X className="w-5 h-5 text-white" />
                  </button>
                  <h2 className="text-white font-semibold text-lg">Preview</h2>
                  <div className="w-11 h-11" />
                </div>
              </div>
              <img src={previewImage?.url} alt="Preview" className="w-full h-full object-contain bg-black" />
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent py-8 px-6 safe-area-bottom">
                <div className="flex justify-center gap-4 max-w-sm mx-auto">
                  <button
                    onClick={retakePhoto}
                    className="flex-1 flex items-center justify-center gap-2 px-6 py-4 bg-white/10 hover:bg-white/20 border-2 border-white text-white font-semibold rounded-xl backdrop-blur-md transition-all"
                  >
                    <RotateCcw className="w-5 h-5" /> Retake
                  </button>
                  <button
                    onClick={usePhoto}
                    className="flex-1 flex items-center justify-center gap-2 px-6 py-4 bg-[#0d4a6f] hover:bg-[#083a57] text-white font-semibold rounded-xl transition-all shadow-lg"
                  >
                    <Check className="w-5 h-5" /> Use Photo
                  </button>
                </div>
              </div>
            </div>
          )}
          <canvas ref={canvasRef} className="hidden" />
        </div>
      )}
    </div>
  );
}

export default function ReportHazardPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <ReportHazardContent />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
