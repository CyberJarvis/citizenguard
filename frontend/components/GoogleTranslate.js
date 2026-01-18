'use client';

import { useEffect, useState, useRef } from 'react';
import { Globe, Check } from 'lucide-react';

const LANGUAGES = [
  { code: 'en', name: 'English', native: 'English' },
  { code: 'hi', name: 'Hindi', native: 'हिंदी' },
  { code: 'ta', name: 'Tamil', native: 'தமிழ்' },
  { code: 'te', name: 'Telugu', native: 'తెలుగు' },
  { code: 'kn', name: 'Kannada', native: 'ಕನ್ನಡ' },
  { code: 'ml', name: 'Malayalam', native: 'മലയാളം' },
  { code: 'bn', name: 'Bengali', native: 'বাংলা' },
  { code: 'gu', name: 'Gujarati', native: 'ગુજરાતી' },
  { code: 'mr', name: 'Marathi', native: 'मराठी' },
  { code: 'pa', name: 'Punjabi', native: 'ਪੰਜਾਬੀ' },
  { code: 'or', name: 'Odia', native: 'ଓଡ଼ିଆ' },
];

export default function GoogleTranslate({ fixed = false, variant = 'header' }) {
  const [isOpen, setIsOpen] = useState(false);
  const [currentLang, setCurrentLang] = useState('en');
  const dropdownRef = useRef(null);

  useEffect(() => {
    // Add Google Translate script
    const addScript = () => {
      const script = document.createElement('script');
      script.src = '//translate.google.com/translate_a/element.js?cb=googleTranslateElementInit';
      script.async = true;
      document.body.appendChild(script);
    };

    // Initialize Google Translate (hidden)
    window.googleTranslateElementInit = () => {
      if (window.google && window.google.translate) {
        new window.google.translate.TranslateElement(
          {
            pageLanguage: 'en',
            includedLanguages: 'en,hi,ta,te,kn,ml,bn,gu,mr,pa,or',
            layout: window.google.translate.TranslateElement.InlineLayout.SIMPLE,
            autoDisplay: false,
          },
          'google_translate_element'
        );
      }
    };

    // Check if script already exists
    if (!document.querySelector('script[src*="translate.google.com"]')) {
      addScript();
    } else if (window.google && window.google.translate) {
      window.googleTranslateElementInit();
    }

    // Close dropdown on outside click
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      delete window.googleTranslateElementInit;
    };
  }, []);

  // Function to trigger Google Translate
  const changeLanguage = (langCode) => {
    setCurrentLang(langCode);
    setIsOpen(false);

    // Find and trigger Google Translate
    const googleFrame = document.querySelector('.goog-te-menu-frame');
    if (googleFrame) {
      const frameDoc = googleFrame.contentDocument || googleFrame.contentWindow.document;
      const langLinks = frameDoc.querySelectorAll('.goog-te-menu2-item span.text');

      langLinks.forEach((link) => {
        const langName = LANGUAGES.find(l => l.code === langCode)?.name;
        if (link.textContent === langName) {
          link.click();
        }
      });
    } else {
      // Alternative: Use cookie method
      const domain = window.location.hostname;
      document.cookie = `googtrans=/en/${langCode}; path=/; domain=${domain}`;
      document.cookie = `googtrans=/en/${langCode}; path=/`;

      // Reload to apply translation
      if (langCode !== 'en') {
        window.location.reload();
      } else {
        // Reset to English
        document.cookie = 'googtrans=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        window.location.reload();
      }
    }
  };

  // Detect browser language and map to supported language
  const detectBrowserLanguage = () => {
    // Get browser language (e.g., 'hi-IN', 'ta-IN', 'en-US', 'en')
    const browserLang = navigator.language || navigator.userLanguage || 'en';
    
    // Extract base language code (e.g., 'hi' from 'hi-IN')
    const baseLang = browserLang.split('-')[0].toLowerCase();
    
    // Map browser language to our supported languages
    const languageMap = {
      'en': 'en',
      'hi': 'hi',
      'ta': 'ta',
      'te': 'te',
      'kn': 'kn',
      'ml': 'ml',
      'bn': 'bn',
      'gu': 'gu',
      'mr': 'mr',
      'pa': 'pa',
      'or': 'or',
    };
    
    // Return mapped language or default to English
    return languageMap[baseLang] || 'en';
  };

  // Check current language from cookie on mount and auto-detect if needed
  useEffect(() => {
    // Check if user has a saved language preference
    const match = document.cookie.match(/googtrans=\/en\/(\w+)/);
    
    if (match && match[1]) {
      // User has a saved preference, use it
      setCurrentLang(match[1]);
    } else {
      // No saved preference - auto-detect browser language
      const detectedLang = detectBrowserLanguage();
      
      // Only auto-select if it's not English (to avoid unnecessary reload)
      if (detectedLang !== 'en') {
        // Set the language state
        setCurrentLang(detectedLang);
        
        // Auto-apply the language after a short delay to ensure Google Translate is ready
        const autoSelectTimer = setTimeout(() => {
          // Use cookie method to set language
          const domain = window.location.hostname;
          document.cookie = `googtrans=/en/${detectedLang}; path=/; domain=${domain}`;
          document.cookie = `googtrans=/en/${detectedLang}; path=/`;
          
          // Reload to apply translation
          window.location.reload();
        }, 500);
        
        return () => clearTimeout(autoSelectTimer);
      } else {
        // Default to English
        setCurrentLang('en');
      }
    }
  }, []);

  const currentLangData = LANGUAGES.find(l => l.code === currentLang) || LANGUAGES[0];

  // Sidebar variant - dark icon for light sidebar (used in PageHeader)
  if (variant === 'sidebar') {
    return (
      <div className="relative" ref={dropdownRef}>
        <div id="google_translate_element" style={{ display: 'none' }} />
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-8 h-8 flex items-center justify-center hover:bg-gray-100 rounded-lg transition-colors"
          title={`Language: ${currentLangData.name}`}
        >
          <Globe className="w-[26px] h-[26px] text-gray-600" />
        </button>

        {isOpen && (
          <div className="absolute top-full right-0 mt-2 bg-white rounded-xl shadow-xl border border-gray-200 min-w-[200px] z-[200] overflow-hidden">
            <div className="px-3 py-2 border-b border-gray-100 bg-gray-50">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Select Language</p>
            </div>
            <div className="max-h-[280px] overflow-y-auto">
              {LANGUAGES.map((lang) => (
                <button
                  key={lang.code}
                  onClick={() => changeLanguage(lang.code)}
                  className={`w-full text-left px-3 py-2 text-sm flex items-center gap-2 hover:bg-gray-50 ${currentLang === lang.code ? 'bg-[#e8f4fc] text-[#0d4a6f] font-medium' : 'text-gray-700'}`}
                >
                  <span className="flex-1">{lang.native}</span>
                  <span className="text-xs text-gray-400">{lang.name}</span>
                  {currentLang === lang.code && <Check className="w-4 h-4 text-[#0d4a6f]" />}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Icon-only button style for header integration (white icons)
  if (variant === 'header') {
    return (
      <div className="relative" ref={dropdownRef}>
        {/* Hidden Google Translate Element */}
        <div id="google_translate_element" style={{ display: 'none' }} />

        {/* Custom Globe Icon Button - White for blue header */}
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-8 h-8 flex items-center justify-center hover:bg-white/20 rounded-lg transition-colors"
          title={`Language: ${currentLangData.name}`}
        >
          <Globe className="w-[26px] h-[26px] text-white" />
        </button>

        {/* Custom Dropdown */}
        {isOpen && (
          <div className="absolute top-full right-0 mt-2 w-48 bg-white rounded-xl shadow-2xl border border-gray-100 overflow-hidden" style={{ zIndex: 10001 }}>
            <div className="px-3 py-2 border-b border-gray-100 bg-gray-50">
              <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">Select Language</p>
            </div>
            <div className="max-h-[250px] overflow-y-auto">
              {LANGUAGES.map((lang) => (
                <button
                  key={lang.code}
                  onClick={() => changeLanguage(lang.code)}
                  className={`w-full text-left px-3 py-2 text-sm flex items-center gap-2 hover:bg-gray-50 transition-colors ${
                    currentLang === lang.code ? 'bg-[#e8f4fc] text-[#0d4a6f] font-medium' : 'text-gray-700'
                  }`}
                >
                  <span className="flex-1">{lang.native}</span>
                  <span className="text-[10px] text-gray-400">{lang.name}</span>
                  {currentLang === lang.code && (
                    <Check className="w-3.5 h-3.5 text-[#0d4a6f]" />
                  )}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Compact variant for other pages (fixed position)
  return (
    <div className={`relative ${fixed ? 'google-translate-fixed' : ''}`} ref={dropdownRef}>
      <div id="google_translate_element" style={{ display: 'none' }} />

      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 bg-white rounded-xl shadow-lg border border-gray-200 hover:shadow-xl transition-all"
      >
        <Globe className="w-4 h-4 text-[#0d4a6f]" />
        <span className="text-sm font-medium text-gray-700">{currentLangData.native}</span>
      </button>

      {isOpen && (
        <div className="language-dropdown" style={{ top: 'auto', bottom: 'calc(100% + 8px)' }}>
          <div className="px-4 py-2 border-b border-gray-100">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Select Language</p>
          </div>
          <div className="max-h-[250px] overflow-y-auto">
            {LANGUAGES.map((lang) => (
              <button
                key={lang.code}
                onClick={() => changeLanguage(lang.code)}
                className={`language-dropdown-item w-full text-left ${currentLang === lang.code ? 'active' : ''}`}
              >
                <span className="flex-1">{lang.native}</span>
                <span className="text-xs text-gray-400">{lang.name}</span>
                {currentLang === lang.code && (
                  <Check className="w-4 h-4 text-[#0d4a6f]" />
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
