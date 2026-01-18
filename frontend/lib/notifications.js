/**
 * Browser Push Notifications and Sound Alerts for MultiHazard System
 */

// Track shown notifications to avoid duplicates
const shownNotifications = new Set();

// Alert level configuration
const ALERT_SOUNDS = {
  5: { duration: 1000, frequency: 880, repeat: 3 }, // CRITICAL - urgent high pitch
  4: { duration: 500, frequency: 660, repeat: 2 },  // WARNING - medium pitch
};

/**
 * Request notification permission from user
 */
export const requestNotificationPermission = async () => {
  if (!('Notification' in window)) {
    console.log('Browser does not support notifications');
    return false;
  }

  if (Notification.permission === 'granted') {
    return true;
  }

  if (Notification.permission !== 'denied') {
    const permission = await Notification.requestPermission();
    return permission === 'granted';
  }

  return false;
};

/**
 * Check if notifications are enabled
 */
export const isNotificationEnabled = () => {
  return 'Notification' in window && Notification.permission === 'granted';
};

/**
 * Play alert sound using Web Audio API
 */
export const playAlertSound = (alertLevel) => {
  if (alertLevel < 4) return; // Only play for WARNING and CRITICAL

  try {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const config = ALERT_SOUNDS[alertLevel] || ALERT_SOUNDS[4];

    const playBeep = (delay) => {
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      oscillator.frequency.value = config.frequency;
      oscillator.type = 'sine';

      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime + delay);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + delay + config.duration / 1000);

      oscillator.start(audioContext.currentTime + delay);
      oscillator.stop(audioContext.currentTime + delay + config.duration / 1000);
    };

    // Play beeps with spacing
    for (let i = 0; i < config.repeat; i++) {
      playBeep(i * (config.duration + 200) / 1000);
    }
  } catch (error) {
    console.error('Failed to play alert sound:', error);
  }
};

/**
 * Show browser notification for hazard alert
 */
export const showHazardNotification = async (hazard, location, options = {}) => {
  // Create unique ID for this notification
  const notificationId = `${hazard.alert_id || hazard.hazard_type}-${location.location_id || location.name}`;

  // Skip if already shown recently
  if (shownNotifications.has(notificationId)) {
    return false;
  }

  // Request permission if needed
  const hasPermission = await requestNotificationPermission();
  if (!hasPermission) {
    console.log('Notification permission not granted');
    return false;
  }

  // Build notification content
  const alertLevel = hazard.alert_level || 4;
  const levelName = alertLevel === 5 ? 'CRITICAL' : 'WARNING';
  const hazardType = hazard.hazard_type?.replace('_', ' ').toUpperCase() || 'HAZARD';
  const locationName = location.location_name || location.name || 'Unknown Location';

  const title = `${levelName} ALERT - ${locationName}`;
  const body = buildNotificationBody(hazard, location);
  const icon = alertLevel === 5 ? '/icons/alert-critical.png' : '/icons/alert-warning.png';

  try {
    const notification = new Notification(title, {
      body,
      icon,
      badge: '/icons/badge.png',
      tag: notificationId,
      requireInteraction: alertLevel === 5, // Keep CRITICAL alerts visible
      vibrate: alertLevel === 5 ? [200, 100, 200, 100, 200] : [200, 100, 200],
      data: {
        hazard,
        location,
        url: options.url || `/map?location=${location.location_id}`
      }
    });

    // Handle notification click
    notification.onclick = (event) => {
      event.preventDefault();
      window.focus();
      if (notification.data.url) {
        window.location.href = notification.data.url;
      }
      if (options.onLocationSelect) {
        options.onLocationSelect(location);
      }
      notification.close();
    };

    // Mark as shown
    shownNotifications.add(notificationId);

    // Clear from set after 5 minutes to allow re-notification
    setTimeout(() => {
      shownNotifications.delete(notificationId);
    }, 5 * 60 * 1000);

    // Play sound if enabled
    if (options.playSound !== false) {
      playAlertSound(alertLevel);
    }

    return true;
  } catch (error) {
    console.error('Failed to show notification:', error);
    return false;
  }
};

/**
 * Build notification body text
 */
const buildNotificationBody = (hazard, location) => {
  const parts = [];

  // Hazard type
  const hazardType = hazard.hazard_type?.replace('_', ' ') || 'Unknown hazard';
  parts.push(hazardType.charAt(0).toUpperCase() + hazardType.slice(1) + ' detected');

  // Confidence if available
  if (hazard.confidence) {
    parts.push(`${(hazard.confidence * 100).toFixed(0)}% confidence`);
  }

  // First recommendation
  if (hazard.recommendations && hazard.recommendations.length > 0) {
    parts.push(hazard.recommendations[0]);
  }

  return parts.join('. ');
};

/**
 * Check for new critical alerts and notify
 * Compare with previous alerts to detect new ones
 */
export const checkAndNotifyNewAlerts = (currentAlerts, previousAlerts, locations, options = {}) => {
  if (!currentAlerts || !Array.isArray(currentAlerts)) return;

  const previousIds = new Set(previousAlerts?.map(a => a.alert_id) || []);

  currentAlerts.forEach(alert => {
    // Only notify for new WARNING (4) and CRITICAL (5) alerts
    if (alert.alert_level >= 4 && !previousIds.has(alert.alert_id)) {
      // Find location info
      const location = locations?.find(l =>
        l.location_id === alert.location_id ||
        l.name === alert.location_name
      ) || { location_name: alert.location_name, location_id: alert.location_id };

      showHazardNotification(alert, location, options);
    }
  });
};

/**
 * Clear all shown notification tracking
 */
export const clearNotificationHistory = () => {
  shownNotifications.clear();
};

/**
 * Get notification permission status
 */
export const getNotificationStatus = () => {
  if (!('Notification' in window)) {
    return 'unsupported';
  }
  return Notification.permission;
};
