# Voice Transcription Feature - IndicConformer Integration

## Overview

The voice transcription feature enables users to speak in any of 22 Indian regional languages and automatically transcribe their speech to text using AI. This is powered by **IndicConformer**, a state-of-the-art multilingual ASR (Automatic Speech Recognition) model from AI4Bharat.

## Supported Languages

The system supports all 22 officially recognized Indian languages:

| Language | Code | Native Name |
|----------|------|-------------|
| Hindi | `hi` | हिन्दी |
| Bengali | `bn` | বাংলা |
| Telugu | `te` | తెలుగు |
| Marathi | `mr` | मराठी |
| Tamil | `ta` | தமிழ் |
| Urdu | `ur` | اردو |
| Gujarati | `gu` | ગુજરાતી |
| Kannada | `kn` | ಕನ್ನಡ |
| Malayalam | `ml` | മലയാളം |
| Odia | `or` | ଓଡ଼ିଆ |
| Punjabi | `pa` | ਪੰਜਾਬੀ |
| Assamese | `as` | অসমীয়া |
| Maithili | `mai` | मैथिली |
| Bodo | `brx` | बड़ो |
| Santali | `sat` | ᱥᱟᱱᱛᱟᱲᱤ |
| Konkani | `kok` | कोंकणी |
| Dogri | `doi` | डोगरी |
| Kashmiri | `ks` | कॉशुर |
| Nepali | `ne` | नेपाली |
| Sindhi | `sd` | سنڌي |
| Manipuri | `mni` | মৈতৈলোন্ |
| Sanskrit | `sa` | संस्कृतम् |
| English | `en` | English |

## Architecture

### Backend Components

1. **Voice Transcription Service** (`backend/app/services/voice_transcription.py`)
   - Loads IndicConformer model from HuggingFace
   - Handles audio preprocessing (mono conversion, 16kHz resampling)
   - Supports GPU acceleration (CUDA) when available
   - Implements lazy loading for efficient resource usage

2. **API Endpoint** (`backend/app/api/v1/transcription.py`)
   - `POST /api/v1/transcribe` - Transcribe audio to text
   - `GET /api/v1/transcribe/languages` - Get supported languages
   - `GET /api/v1/transcribe/health` - Health check

### Frontend Components

1. **VoiceInput Component** (`frontend/components/VoiceInput.js`)
   - Language selector with 22 Indian languages
   - Audio recording with browser MediaRecorder API
   - Real-time transcription via backend API
   - Auto-fill description field with transcription

2. **Integration** (`frontend/app/report-hazard/page.js`)
   - Embedded in hazard reporting form
   - Seamless user experience
   - Error handling and loading states

## Installation & Setup

### Backend Setup

1. **Install Dependencies**

```bash
cd backend
pip install -r requirements.txt
```

This will install:
- `transformers>=4.36.0` - HuggingFace Transformers library
- `torch>=2.1.0` - PyTorch deep learning framework
- `torchaudio>=2.1.0` - Audio processing library
- `onnx>=1.15.0` - ONNX runtime support
- `onnxruntime>=1.16.0` - Optimized inference

2. **GPU Support (Optional but Recommended)**

For faster transcription, install CUDA-enabled PyTorch:

```bash
# For CUDA 11.8
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118

# For CUDA 12.1
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

3. **Model Download**

The model will be automatically downloaded from HuggingFace on first use (~600MB).

To pre-download:

```python
from transformers import AutoModel
model = AutoModel.from_pretrained(
    "ai4bharat/indic-conformer-600m-multilingual",
    trust_remote_code=True
)
```

4. **Start Backend**

```bash
python main.py
```

The transcription endpoint will be available at:
- `http://localhost:8000/api/v1/transcribe`
- API docs: `http://localhost:8000/docs`

### Frontend Setup

1. **Install Dependencies**

```bash
cd frontend
npm install
```

2. **Configure API URL**

Create or update `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

3. **Start Frontend**

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

## Usage

### For Users

1. **Navigate to Hazard Reporting**
   - Go to `/report-hazard` page
   - Fill in hazard details (photo, location, type)

2. **Use Voice Input**
   - Select your regional language from dropdown
   - Click "Start Voice Recording"
   - Speak clearly in your selected language
   - Click "Stop Recording"
   - Wait for automatic transcription
   - Transcribed text will appear in Description field

3. **Edit and Submit**
   - Review and edit the transcribed text if needed
   - Complete the form and submit

### For Developers

#### Using the API Directly

**Transcribe Audio:**

```bash
curl -X POST "http://localhost:8000/api/v1/transcribe" \
  -H "Content-Type: multipart/form-data" \
  -F "audio=@recording.wav" \
  -F "language=hi" \
  -F "decode_strategy=ctc"
```

**Response:**

```json
{
  "transcription": "यह एक परीक्षण संदेश है",
  "language": "Hindi",
  "language_code": "hi",
  "decode_strategy": "ctc",
  "success": true
}
```

**Get Supported Languages:**

```bash
curl "http://localhost:8000/api/v1/transcribe/languages"
```

#### Using in React Components

```jsx
import VoiceInput from '@/components/VoiceInput';

function MyForm() {
  const [description, setDescription] = useState('');

  return (
    <VoiceInput
      description={description}
      onDescriptionChange={setDescription}
      onTranscription={(text, langCode) => {
        console.log('Transcribed:', text, 'in', langCode);
      }}
    />
  );
}
```

## Performance Considerations

### Model Performance

- **Model Size:** ~600MB
- **Transcription Speed:**
  - CPU: ~5-10 seconds per 30-second audio
  - GPU (CUDA): ~1-2 seconds per 30-second audio

### Optimization Tips

1. **Use GPU Acceleration**
   - Install CUDA-enabled PyTorch
   - Verify GPU usage: Check logs for "Model loaded on GPU"

2. **Decode Strategy**
   - `ctc` - Faster, good for real-time use
   - `rnnt` - More accurate, slightly slower

3. **Audio Quality**
   - Record in quiet environment
   - Use good quality microphone
   - Avoid background noise

4. **Caching**
   - Model is loaded once and kept in memory
   - Subsequent transcriptions are faster

## Troubleshooting

### Model Loading Issues

**Problem:** `Failed to load IndicConformer model`

**Solutions:**
1. Check internet connection (model downloads from HuggingFace)
2. Verify sufficient disk space (~1GB)
3. Check Python version (requires 3.8+)
4. Install missing dependencies: `pip install transformers torch torchaudio`

### Transcription Errors

**Problem:** `Failed to transcribe audio`

**Solutions:**
1. Check audio format (WAV, MP3, WebM supported)
2. Verify audio file is not corrupted
3. Ensure audio is at least 1 second long
4. Check microphone permissions in browser

### GPU Not Detected

**Problem:** Model running on CPU despite having GPU

**Solutions:**
1. Install CUDA toolkit (11.8 or 12.1)
2. Reinstall PyTorch with CUDA support
3. Verify CUDA installation: `python -c "import torch; print(torch.cuda.is_available())"`

### Browser Compatibility

**Problem:** Voice recording not working

**Solutions:**
1. Use modern browser (Chrome, Edge, Firefox, Safari)
2. Enable microphone permissions
3. Use HTTPS (required for microphone access in production)

## API Reference

### POST /api/v1/transcribe

Transcribe audio to text using IndicConformer.

**Request:**
- `audio` (file, required): Audio file (WAV, MP3, WebM, etc.)
- `language` (string, optional): Language code (default: 'hi')
- `decode_strategy` (string, optional): 'ctc' or 'rnnt' (default: 'ctc')

**Response:**
```json
{
  "transcription": "string",
  "language": "string",
  "language_code": "string",
  "decode_strategy": "string",
  "success": true
}
```

**Status Codes:**
- `200` - Success
- `400` - Invalid request (bad audio format, unsupported language)
- `503` - Service unavailable (model not loaded)
- `500` - Internal server error

### GET /api/v1/transcribe/languages

Get list of supported languages.

**Response:**
```json
{
  "languages": {
    "hi": "Hindi",
    "bn": "Bengali",
    ...
  },
  "count": 23
}
```

### GET /api/v1/transcribe/health

Health check for transcription service.

**Response:**
```json
{
  "status": "healthy",
  "model": "ai4bharat/indic-conformer-600m-multilingual",
  "model_loaded": true,
  "supported_languages": 23,
  "decode_strategies": ["ctc", "rnnt"]
}
```

## Security Considerations

1. **File Upload Limits**
   - Max file size: 10MB
   - Allowed formats: WAV, MP3, WebM, OGG, FLAC, M4A

2. **Rate Limiting**
   - Transcription endpoint is rate-limited
   - Configurable via `RATE_LIMIT_*` settings

3. **Input Validation**
   - Audio files are validated before processing
   - Language codes are validated against whitelist

4. **Error Handling**
   - Errors are logged but not exposed to users
   - Generic error messages in production

## Future Enhancements

1. **Real-time Streaming**
   - WebSocket-based streaming transcription
   - Live transcription as user speaks

2. **Language Auto-detection**
   - Automatically detect spoken language
   - No need to manually select language

3. **Offline Support**
   - Client-side transcription using WASM
   - PWA support for offline usage

4. **Custom Vocabulary**
   - Add domain-specific terms (marine, fishing, coastal)
   - Improve accuracy for hazard-related terms

5. **Speaker Diarization**
   - Identify multiple speakers
   - Useful for group reporting

## Credits

- **IndicConformer Model:** AI4Bharat (IIT Madras)
- **HuggingFace:** Model hosting and Transformers library
- **PyTorch:** Deep learning framework

## License

This feature uses the IndicConformer model which is released under the MIT License.

## Support

For issues or questions:
1. Check documentation above
2. Review API logs in backend console
3. Check browser console for frontend errors
4. Open issue on GitHub repository

---

**Last Updated:** January 2025
**Version:** 1.0.0
