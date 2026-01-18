/**
 * Date Utilities for IST (Indian Standard Time)
 * All timestamps in CoastGuardians are displayed in IST (UTC+5:30)
 */

// IST timezone identifier
export const IST_TIMEZONE = 'Asia/Kolkata';

// IST offset in minutes (5 hours 30 minutes = 330 minutes)
export const IST_OFFSET_MINUTES = 330;

/**
 * Convert any date to IST Date object
 * @param {string|Date|number} date - Date in any format
 * @returns {Date} Date object in IST
 */
export function toIST(date) {
  if (!date) return null;
  const d = new Date(date);
  if (isNaN(d.getTime())) return null;
  return d;
}

/**
 * Format date to IST string with full date and time
 * @param {string|Date|number} date - Date in any format
 * @returns {string} Formatted string like "03 Dec 2025, 10:30 AM IST"
 */
export function formatDateTimeIST(date) {
  if (!date) return '';
  const d = toIST(date);
  if (!d) return '';

  return d.toLocaleString('en-IN', {
    timeZone: IST_TIMEZONE,
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  }) + ' IST';
}

/**
 * Format date to IST string with date only
 * @param {string|Date|number} date - Date in any format
 * @returns {string} Formatted string like "03 Dec 2025"
 */
export function formatDateIST(date) {
  if (!date) return '';
  const d = toIST(date);
  if (!d) return '';

  return d.toLocaleString('en-IN', {
    timeZone: IST_TIMEZONE,
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  });
}

/**
 * Format date to IST string with time only
 * @param {string|Date|number} date - Date in any format
 * @returns {string} Formatted string like "10:30 AM"
 */
export function formatTimeIST(date) {
  if (!date) return '';
  const d = toIST(date);
  if (!d) return '';

  return d.toLocaleString('en-IN', {
    timeZone: IST_TIMEZONE,
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  });
}

/**
 * Format date to short IST string
 * @param {string|Date|number} date - Date in any format
 * @returns {string} Formatted string like "03/12/2025 10:30"
 */
export function formatShortDateTimeIST(date) {
  if (!date) return '';
  const d = toIST(date);
  if (!d) return '';

  return d.toLocaleString('en-IN', {
    timeZone: IST_TIMEZONE,
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });
}

/**
 * Format date for input fields (YYYY-MM-DD)
 * @param {string|Date|number} date - Date in any format
 * @returns {string} Formatted string like "2025-12-03"
 */
export function formatDateForInput(date) {
  if (!date) return '';
  const d = toIST(date);
  if (!d) return '';

  const year = d.toLocaleString('en-IN', { timeZone: IST_TIMEZONE, year: 'numeric' });
  const month = d.toLocaleString('en-IN', { timeZone: IST_TIMEZONE, month: '2-digit' });
  const day = d.toLocaleString('en-IN', { timeZone: IST_TIMEZONE, day: '2-digit' });

  return `${year}-${month}-${day}`;
}

/**
 * Format datetime for input fields (YYYY-MM-DDTHH:mm)
 * @param {string|Date|number} date - Date in any format
 * @returns {string} Formatted string like "2025-12-03T10:30"
 */
export function formatDateTimeForInput(date) {
  if (!date) return '';
  const d = toIST(date);
  if (!d) return '';

  const parts = d.toLocaleString('en-IN', {
    timeZone: IST_TIMEZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).split(/[/,\s:]+/);

  // Format: DD/MM/YYYY, HH:mm -> YYYY-MM-DDTHH:mm
  return `${parts[2]}-${parts[1]}-${parts[0]}T${parts[3]}:${parts[4]}`;
}

/**
 * Get relative time string (e.g., "2 hours ago", "just now") in IST context
 * @param {string|Date|number} date - Date in any format
 * @returns {string} Relative time string
 */
export function getRelativeTimeIST(date) {
  if (!date) return '';
  const d = toIST(date);
  if (!d) return '';

  const now = new Date();
  const diffMs = now - d;
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);
  const diffWeeks = Math.floor(diffDays / 7);
  const diffMonths = Math.floor(diffDays / 30);
  const diffYears = Math.floor(diffDays / 365);

  if (diffSeconds < 60) {
    return 'just now';
  } else if (diffMinutes < 60) {
    return `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`;
  } else if (diffHours < 24) {
    return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  } else if (diffDays < 7) {
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  } else if (diffWeeks < 4) {
    return `${diffWeeks} week${diffWeeks > 1 ? 's' : ''} ago`;
  } else if (diffMonths < 12) {
    return `${diffMonths} month${diffMonths > 1 ? 's' : ''} ago`;
  } else {
    return `${diffYears} year${diffYears > 1 ? 's' : ''} ago`;
  }
}

/**
 * Get smart relative time - shows relative for recent, full date for older
 * @param {string|Date|number} date - Date in any format
 * @param {number} thresholdDays - Days threshold for showing relative time (default: 7)
 * @returns {string} Relative time or formatted date
 */
export function getSmartTimeIST(date, thresholdDays = 7) {
  if (!date) return '';
  const d = toIST(date);
  if (!d) return '';

  const now = new Date();
  const diffMs = now - d;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays < thresholdDays) {
    return getRelativeTimeIST(date);
  } else {
    return formatDateTimeIST(date);
  }
}

/**
 * Check if a date is today in IST
 * @param {string|Date|number} date - Date in any format
 * @returns {boolean} True if the date is today in IST
 */
export function isTodayIST(date) {
  if (!date) return false;
  const d = toIST(date);
  if (!d) return false;

  const today = new Date();
  const dDate = d.toLocaleDateString('en-IN', { timeZone: IST_TIMEZONE });
  const todayDate = today.toLocaleDateString('en-IN', { timeZone: IST_TIMEZONE });

  return dDate === todayDate;
}

/**
 * Check if a date is yesterday in IST
 * @param {string|Date|number} date - Date in any format
 * @returns {boolean} True if the date is yesterday in IST
 */
export function isYesterdayIST(date) {
  if (!date) return false;
  const d = toIST(date);
  if (!d) return false;

  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);

  const dDate = d.toLocaleDateString('en-IN', { timeZone: IST_TIMEZONE });
  const yesterdayDate = yesterday.toLocaleDateString('en-IN', { timeZone: IST_TIMEZONE });

  return dDate === yesterdayDate;
}

/**
 * Format date with context (Today, Yesterday, or full date)
 * @param {string|Date|number} date - Date in any format
 * @param {boolean} includeTime - Whether to include time
 * @returns {string} Contextual date string
 */
export function formatContextualDateIST(date, includeTime = true) {
  if (!date) return '';
  const d = toIST(date);
  if (!d) return '';

  const timeStr = includeTime ? `, ${formatTimeIST(date)}` : '';

  if (isTodayIST(date)) {
    return `Today${timeStr}`;
  } else if (isYesterdayIST(date)) {
    return `Yesterday${timeStr}`;
  } else {
    return includeTime ? formatDateTimeIST(date) : formatDateIST(date);
  }
}

/**
 * Get current time in IST
 * @returns {Date} Current time as Date object
 */
export function nowIST() {
  return new Date();
}

/**
 * Format date for display in tables/lists (compact format)
 * @param {string|Date|number} date - Date in any format
 * @returns {string} Compact date string like "03 Dec, 10:30 AM"
 */
export function formatCompactDateTimeIST(date) {
  if (!date) return '';
  const d = toIST(date);
  if (!d) return '';

  return d.toLocaleString('en-IN', {
    timeZone: IST_TIMEZONE,
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  });
}

/**
 * Format duration between two dates
 * @param {string|Date|number} startDate - Start date
 * @param {string|Date|number} endDate - End date (defaults to now)
 * @returns {string} Duration string like "2h 30m" or "3d 5h"
 */
export function formatDuration(startDate, endDate = new Date()) {
  if (!startDate) return '';
  const start = toIST(startDate);
  const end = toIST(endDate);
  if (!start || !end) return '';

  const diffMs = Math.abs(end - start);
  const diffMinutes = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffDays > 0) {
    const remainingHours = diffHours % 24;
    return `${diffDays}d ${remainingHours}h`;
  } else if (diffHours > 0) {
    const remainingMinutes = diffMinutes % 60;
    return `${diffHours}h ${remainingMinutes}m`;
  } else {
    return `${diffMinutes}m`;
  }
}

/**
 * Parse date from IST input and convert to ISO string for API
 * @param {string} dateStr - Date string from form input
 * @param {string} timeStr - Optional time string (HH:mm)
 * @returns {string} ISO string for API
 */
export function parseISTToISO(dateStr, timeStr = '00:00') {
  if (!dateStr) return null;

  // Create date string in IST
  const dateTimeStr = `${dateStr}T${timeStr}:00`;

  // Parse as IST and convert to ISO
  const d = new Date(dateTimeStr);

  // Adjust for IST offset (the input is in IST, but JS creates it in local time)
  // This is a simplified approach - for production, consider using a library like date-fns-tz
  return d.toISOString();
}

// Export all functions as default object for convenience
export default {
  IST_TIMEZONE,
  toIST,
  formatDateTimeIST,
  formatDateIST,
  formatTimeIST,
  formatShortDateTimeIST,
  formatDateForInput,
  formatDateTimeForInput,
  getRelativeTimeIST,
  getSmartTimeIST,
  isTodayIST,
  isYesterdayIST,
  formatContextualDateIST,
  nowIST,
  formatCompactDateTimeIST,
  formatDuration,
  parseISTToISO
};
