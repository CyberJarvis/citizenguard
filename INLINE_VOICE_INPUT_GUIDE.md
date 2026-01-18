# Inline Voice Input - Simple Integration Guide

## Overview

Users can now **speak in their regional language** directly while filling the description field. The voice input is seamlessly integrated - users can either type OR click a mic button to speak.

## How It Works

### User Experience:

1. **Go to Report Hazard page** (`/report-hazard`)
2. **Scroll to Description field**
3. **See language selector and Record button above the textarea**
4. **Choose language** (Hindi, Tamil, Bengali, etc.)
5. **Click "Record"** → Speak your description
6. **Click "Stop"** → Audio transcribed automatically
7. **Transcription appears in the description field!**
8. **Edit if needed** or **add more** by typing or recording again

### Simple Flow:

```
Description Field
├── [Language Selector ▼] [🎤 Record]
├── ⬇ (User speaks)
├── ⬇ (Transcription)
└── [Textarea with transcribed text]
```

## Quick Setup

### 1. Install Backend Dependencies

```bash
cd backend
pip install transformers torch torchaudio onnx onnxruntime
```

### 2. Start Backend

```bash
python main.py
```

### 3. Start Frontend

```bash
cd frontend
npm run dev
```

### 4. Test!

1. Open http://localhost:3000/report-hazard
2. Select language (e.g., Hindi)
3. Click "Record" button
4. Speak: "समुद्र में बहुत ऊंची लहरें हैं"
5. Click Stop
6. See transcription appear in description!

## Features

✅ **22 Indian Languages** - Hindi, Bengali, Tamil, Telugu, Marathi, Malayalam, Gujarati, Kannada, Odia, Punjabi, Assamese, and more

✅ **Seamless Integration** - Voice input button right above description field

✅ **Type OR Speak** - Users choose what's comfortable

✅ **Smart Append** - Multiple recordings append to existing text

✅ **Real-time Feedback** - Recording timer, transcription status

✅ **Error Handling** - Clear messages for mic permissions, no speech detected, etc.

## UI Components

### Language Selector
- Dropdown showing all 22 languages
- Popular coastal languages highlighted
- Native script display (हिन्दी, தமிழ், বাংলা)

### Record Button
- Click to start recording
- Shows timer while recording
- Click again to stop and transcribe

### Status Indicators
- 🔴 "Recording in Hindi..." (red banner)
- ⏳ "Transcribing Hindi..." (blue banner)
- ✓ "Transcribed successfully!" (toast notification)

## Code Example

### Using InlineVoiceInput Component

```jsx
import InlineVoiceInput from '@/components/InlineVoiceInput';

function MyForm() {
  const [description, setDescription] = useState('');

  return (
    <div>
      {/* Voice Input Controls */}
      <InlineVoiceInput
        value={description}
        onChange={setDescription}
      />

      {/* Description Textarea */}
      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Type or speak..."
        rows={6}
      />
    </div>
  );
}
```

## API Endpoint

The component uses the backend transcription API:

```
POST /api/v1/transcribe
- audio: file (WebM audio)
- language: string (e.g., 'hi', 'ta', 'bn')
- decode_strategy: 'ctc' (fast)

Response:
{
  "transcription": "transcribed text",
  "language": "Hindi",
  "language_code": "hi"
}
```

## Supported Languages

| Code | Language | Native Name |
|------|----------|-------------|
| `hi` | Hindi | हिन्दी |
| `bn` | Bengali | বাংলা |
| `te` | Telugu | తెలుగు |
| `ta` | Tamil | தமிழ் |
| `mr` | Marathi | मराठी |
| `ml` | Malayalam | മലയാളം |
| `gu` | Gujarati | ગુજરાતી |
| `kn` | Kannada | ಕನ್ನಡ |
| `or` | Odia | ଓଡ଼ିଆ |
| `pa` | Punjabi | ਪੰਜਾਬੀ |
| + 13 more languages |

## Performance

- **Recording:** Instant start
- **Transcription:** 1-10 seconds (depending on CPU/GPU)
- **Model Size:** 600MB (downloads once, cached)

## Browser Requirements

- **Chrome/Edge:** ✅ Full support
- **Firefox:** ✅ Full support
- **Safari:** ✅ Full support (macOS/iOS)
- **Requirement:** HTTPS (for mic access in production)

## Troubleshooting

### Mic Permission Denied
**Fix:** Allow microphone access in browser settings

### No Speech Detected
**Fix:**
- Speak louder/clearer
- Check microphone is working
- Try a longer recording (>2 seconds)

### Wrong Language Transcribed
**Fix:** Ensure correct language is selected before recording

### Slow Transcription
**Fix:**
- First transcription downloads model (~600MB)
- Subsequent transcriptions are faster
- Use GPU for 5x speed boost

## Example Usage

### Scenario: Fisherman Reporting High Waves

1. **Language:** Selects "Tamil" (தமிழ்)
2. **Records:** "கடலில் பெரிய அலைகள் உள்ளன. மீனவர்களுக்கு மிகவும் ஆபத்தானது."
3. **Result:** Description field shows:
   ```
   கடலில் பெரிய அலைகள் உள்ளன. மீனவர்களுக்கு மிகவும் ஆபத்தானது.
   ```
4. **Edits:** User can type additional details or record more

## Technical Details

### Component Location
- Frontend: `frontend/components/InlineVoiceInput.js`
- Backend: `backend/app/api/v1/transcription.py`
- Service: `backend/app/services/voice_transcription.py`

### Dependencies
- **Frontend:** React, axios, lucide-react, react-hot-toast
- **Backend:** FastAPI, transformers, torch, torchaudio

### Model
- **Name:** ai4bharat/indic-conformer-600m-multilingual
- **Parameters:** 600M
- **Provider:** AI4Bharat (IIT Madras)
- **License:** MIT

## Benefits for Coastal Users

1. **Language Accessibility** - Speak in native language
2. **Literacy Support** - No need to type in English
3. **Speed** - Faster than typing on mobile
4. **Accuracy** - AI-powered transcription
5. **Ease of Use** - Simple click-record-stop flow

## Next Steps

1. Test with different languages
2. Try multiple recordings (appends text)
3. Combine typing + voice input
4. Deploy to production with HTTPS

---

**Simple. Fast. Multilingual. 🎤✨**
