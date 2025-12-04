from typing import Optional, Tuple, List, Dict, Union
from .deepgram_transcription import transcribe_audio as deepgram_transcribe
from .assemblyai_transcription import transcribe_audio as assemblyai_transcribe
from .gemini_transcription import transcribe_audio as gemini_transcribe
from .soniox_async import transcribe_audio as soniox_transcribe

# Soniox supported languages (ISO codes)
SONIOX_SUPPORTED_LANGUAGES = {
    'af', 'sq', 'ar', 'az', 'eu', 'be', 'bn', 'bs', 'bg', 'ca', 'zh', 'hr', 'cs', 'da', 
    'nl', 'en', 'et', 'fi', 'fr', 'gl', 'de', 'el', 'gu', 'he', 'hi', 'hu', 'id', 'it', 
    'ja', 'kn', 'kk', 'ko', 'lv', 'lt', 'mk', 'ms', 'ml', 'mr', 'no', 'fa', 'pl', 'pt', 
    'pa', 'ro', 'ru', 'sr', 'sk', 'sl', 'es', 'sw', 'sv', 'tl', 'ta', 'te', 'th', 'tr', 
    'uk', 'ur', 'vi', 'cy'
}

async def transcribe_audio(audio_path: str, language: str = 'auto') -> Tuple[Optional[str], Optional[List[Dict]], Optional[str], Optional[str]]:
    # Determine if we should use Soniox based on language support
    use_soniox = False
    
    if language.lower() in ['auto', '']:
        # For auto-detect, use Soniox
        use_soniox = True
        language_hints = ["en"]
    elif language.lower() in SONIOX_SUPPORTED_LANGUAGES:
        # Language is supported by Soniox
        use_soniox = True
        language_hints = [language, "en"]
        
        language_hints = list(dict.fromkeys(language_hints))
    
    if use_soniox:
        # Try Soniox first
        try:
            result = await soniox_transcribe(audio_url=audio_path, language_hints=language_hints)
            # Check if there's an error in the result (error is the 3rd element)
            if result and result[2] is None:
                return result
            # If there's an error, fall through to try other services
        except Exception as e:
            # If Soniox fails with an exception, fall through to try other services
            pass
    
    # Failback to Deepgram
    try:
        result = await deepgram_transcribe(audio_path, language)
        # Check if there's an error in the result
        if result and result[2] is None:
            return result
    except Exception as e:
        # If Deepgram fails, fall through to try AssemblyAI
        pass
    
    # Final failback to AssemblyAI
    return await assemblyai_transcribe(audio_path, model='best')
