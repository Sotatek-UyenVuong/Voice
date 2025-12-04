import os
import asyncio
import argparse
from typing import Optional
import aiohttp
from dotenv import load_dotenv

load_dotenv()

SONIOX_API_BASE_URL = "https://api.soniox.com"


# Get Soniox STT config.
def get_config(
    audio_url: Optional[str], 
    file_id: Optional[str], 
    translation: Optional[str],
    language_hints: Optional[list[str]] = None
) -> dict:
    config = {
        # Select the model to use.
        # See: soniox.com/docs/stt/models
        "model": "stt-async-v3",
        #
        # Set language hints when possible to significantly improve accuracy.
        # See: soniox.com/docs/stt/concepts/language-hints
        "language_hints": language_hints if language_hints is not None else ["en", "es"],
        #
        # Enable language identification. Each token will include a "language" field.
        # See: soniox.com/docs/stt/concepts/language-identification
        "enable_language_identification": True,
        #
        # Enable speaker diarization. Each token will include a "speaker" field.
        # See: soniox.com/docs/stt/concepts/speaker-diarization
        "enable_speaker_diarization": True,
        #
        # Set context to help the model understand your domain, recognize important terms,
        # and apply custom vocabulary and translation preferences.
        # See: soniox.com/docs/stt/concepts/context
        # "context": {
        #     "general": [
        #         {"key": "domain", "value": "Healthcare"},
        #         {"key": "topic", "value": "Diabetes management consultation"},
        #         {"key": "doctor", "value": "Dr. Martha Smith"},
        #         {"key": "patient", "value": "Mr. David Miller"},
        #         {"key": "organization", "value": "St John's Hospital"},
        #     ],
        #     "text": "Mr. David Miller visited his healthcare provider last month for a routine follow-up related to diabetes care. The clinician reviewed his recent test results, noted improved glucose levels, and adjusted his medication schedule accordingly. They also discussed meal planning strategies and scheduled the next check-up for early spring.",
        #     "terms": [
        #         "Celebrex",
        #         "Zyrtec",
        #         "Xanax",
        #         "Prilosec",
        #         "Amoxicillin Clavulanate Potassium",
        #     ],
        #     "translation_terms": [
        #         {"source": "Mr. Smith", "target": "Sr. Smith"},
        #         {"source": "St John's", "target": "St John's"},
        #         {"source": "stroke", "target": "ictus"},
        #     ],
        # },
        #
        # Optional identifier to track this request (client-defined).
        # See: https://soniox.com/docs/stt/api-reference/transcriptions/create_transcription#request
        "client_reference_id": "MyReferenceId",
    }
    
    # Audio source (only one can be specified):
    # - Public URL of the audio file.
    # - File ID of a previously uploaded file
    # See: https://soniox.com/docs/stt/api-reference/transcriptions/create_transcription#request
    # IMPORTANT: Only add the field that has a value, not both
    if audio_url is not None:
        config["audio_url"] = audio_url
    elif file_id is not None:
        config["file_id"] = file_id

    # Webhook.
    # You can set a webhook to get notified when the transcription finishes or fails.
    # See: https://soniox.com/docs/stt/api-reference/transcriptions/create_transcription#request

    # Translation options.
    # See: soniox.com/docs/stt/rt/real-time-translation#translation-modes
    if translation == "none":
        pass
    elif translation == "one_way":
        # Translates all languages into the target language.
        config["translation"] = {
            "type": "one_way",
            "target_language": "es",
        }
    elif translation == "two_way":
        # Translates from language_a to language_b and back from language_b to language_a.
        config["translation"] = {
            "type": "two_way",
            "language_a": "en",
            "language_b": "es",
        }
    else:
        raise ValueError(f"Unsupported translation: {translation}")

    return config


async def upload_audio(session: aiohttp.ClientSession, audio_path: str) -> str:
    print("Starting file upload...")
    with open(audio_path, "rb") as f:
        data = aiohttp.FormData()
        data.add_field("file", f, filename=os.path.basename(audio_path))
        async with session.post(f"{SONIOX_API_BASE_URL}/v1/files", data=data) as response:
            result = await response.json()
            file_id = result["id"]
            print(f"File ID: {file_id}")
            return file_id


async def create_transcription(session: aiohttp.ClientSession, config: dict) -> str:
    print("Creating transcription...")
    print(f"Config being sent: {config}")
    try:
        async with session.post(
            f"{SONIOX_API_BASE_URL}/v1/transcriptions",
            json=config,
        ) as response:
            # 201 Created is a success response, only log errors (>= 400)
            if response.status >= 400:
                error_text = await response.text()
                print(f"Error response status: {response.status}")
                print(f"Error response body: {error_text}")
            response.raise_for_status()
            result = await response.json()
            transcription_id = result["id"]
            print(f"Transcription ID: {transcription_id}")
            return transcription_id
    except Exception as e:
        print("error here:", e)
        raise


async def wait_until_completed(session: aiohttp.ClientSession, transcription_id: str) -> None:
    print("Waiting for transcription...")
    while True:
        async with session.get(f"{SONIOX_API_BASE_URL}/v1/transcriptions/{transcription_id}") as response:
            response.raise_for_status()
            data = await response.json()
            if data["status"] == "completed":
                return
            elif data["status"] == "error":
                raise Exception(f"Error: {data.get('error_message', 'Unknown error')}")
        await asyncio.sleep(1)


async def get_transcription(session: aiohttp.ClientSession, transcription_id: str) -> dict:
    async with session.get(
        f"{SONIOX_API_BASE_URL}/v1/transcriptions/{transcription_id}/transcript"
    ) as response:
        response.raise_for_status()
        return await response.json()


async def delete_transcription(session: aiohttp.ClientSession, transcription_id: str) -> None:
    async with session.delete(f"{SONIOX_API_BASE_URL}/v1/transcriptions/{transcription_id}") as response:
        response.raise_for_status()


async def delete_file(session: aiohttp.ClientSession, file_id: str) -> None:
    async with session.delete(f"{SONIOX_API_BASE_URL}/v1/files/{file_id}") as response:
        response.raise_for_status()


async def delete_all_files(session: aiohttp.ClientSession) -> None:
    files: list[dict] = []
    cursor: str = ""

    while True:
        print("Getting files...")
        async with session.get(f"{SONIOX_API_BASE_URL}/v1/files?cursor={cursor}") as response:
            response.raise_for_status()
            res_json = await response.json()
            files.extend(res_json["files"])
            cursor = res_json["next_page_cursor"]
            if cursor is None:
                break

    total = len(files)
    if total == 0:
        print("No files to delete.")
        return

    print(f"Deleting {total} files...")
    for idx, file in enumerate(files):
        file_id = file["id"]
        print(f"Deleting file: {file_id} ({idx + 1}/{total})")
        await delete_file(session, file_id)


async def delete_all_transcriptions(session: aiohttp.ClientSession) -> None:
    transcriptions: list[dict] = []
    cursor: str = ""

    while True:
        print("Getting transcriptions...")
        async with session.get(f"{SONIOX_API_BASE_URL}/v1/transcriptions?cursor={cursor}") as response:
            response.raise_for_status()
            res_json = await response.json()
            for transcription in res_json["transcriptions"]:
                status = transcription["status"]
                # Delete only transcriptions with completed or error status.
                if status in ("completed", "error"):
                    transcriptions.append(transcription)
            cursor = res_json["next_page_cursor"]
            if cursor is None:
                break

    total = len(transcriptions)
    if total == 0:
        print("No transcriptions to delete.")
        return

    print(f"Deleting {total} transcriptions...")
    for idx, transcription in enumerate(transcriptions):
        transcription_id = transcription["id"]
        print(f"Deleting transcription: {transcription_id} ({idx + 1}/{total})")
        await delete_transcription(session, transcription_id)


# Convert tokens into a readable transcript.
def render_tokens(final_tokens: list[dict]) -> str:
    text_parts: list[str] = []
    current_speaker: Optional[str] = None
    current_language: Optional[str] = None

    # Process all tokens in order.
    for token in final_tokens:
        text = token["text"]
        speaker = token.get("speaker")
        language = token.get("language")
        is_translation = token.get("translation_status") == "translation"

        # Speaker changed -> add a speaker tag.
        if speaker is not None and speaker != current_speaker:
            if current_speaker is not None:
                text_parts.append("\n\n")
            current_speaker = speaker
            current_language = None  # Reset language on speaker changes.
            text_parts.append(f"Speaker {current_speaker}:")

        # Language changed -> add a language or translation tag.
        if language is not None and language != current_language:
            current_language = language
            prefix = "[Translation] " if is_translation else ""
            text_parts.append(f"\n{prefix}[{current_language}] ")
            text = text.lstrip()

        text_parts.append(text)

    return "".join(text_parts)


async def transcribe_audio(
    audio_url: Optional[str],
    audio_path: Optional[str] = None,
    translation: str = "none",
    language_hints: Optional[list[str]] = None,
) -> tuple[Optional[str], Optional[list[dict]], Optional[str], Optional[str]]:
    # Get API key from environment
    api_key = os.environ.get("SONIOX_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing SONIOX_API_KEY.\n"
            "1. Get your API key at https://console.soniox.com\n"
            "2. Run: export SONIOX_API_KEY=<YOUR_API_KEY>"
        )
    
    # Create an authenticated session
    headers = {"Authorization": f"Bearer {api_key}"}
    
    async with aiohttp.ClientSession(headers=headers) as session:
        if audio_url is not None:
            # Public URL of the audio file to transcribe.
            assert audio_path is None
            file_id = None
        elif audio_path is not None:
            # Local file to be uploaded to obtain file id.
            assert audio_url is None
            file_id = await upload_audio(session, audio_path)
        else:
            raise ValueError("Missing audio: audio_url or audio_path must be specified.")

        config = get_config(audio_url, file_id, translation, language_hints)

        transcription_id = await create_transcription(session, config)

        await wait_until_completed(session, transcription_id)

        result = await get_transcription(session, transcription_id)

        text = render_tokens(result["tokens"])

        # Process tokens into sentences with timing information
        sentences = []
        current_sentence_tokens = []
        current_speaker = None
        
        tokens = result.get("tokens", [])
        
        for token in tokens:
            token_text = token.get("text", "")
            speaker = token.get("speaker")
            start_ms = token.get("start_ms")
            end_ms = token.get("end_ms")
            
            # Skip tokens without timing information
            if start_ms is None or end_ms is None:
                continue
            
            # If speaker changed or we don't have a current speaker, start potential new sentence
            if speaker != current_speaker:
                # Save previous sentence if exists
                if current_sentence_tokens:
                    sentence_text = "".join([t["text"] for t in current_sentence_tokens]).strip()
                    if sentence_text:
                        first_token = current_sentence_tokens[0]
                        last_token = current_sentence_tokens[-1]
                        start = first_token["start_ms"] / 1000.0  # Convert to seconds
                        end = last_token["end_ms"] / 1000.0
                        
                        sentences.append({
                            "text": sentence_text,
                            "start": start,
                            "end": end,
                            "speaker": f"Speaker {current_speaker}" if current_speaker is not None else "Speaker 0",
                            "duration": end - start
                        })
                
                current_sentence_tokens = []
                current_speaker = speaker
            
            # Add token to current sentence
            current_sentence_tokens.append({
                "text": token_text,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "speaker": speaker
            })
            
            # Check if sentence ends (based on punctuation)
            if token_text.rstrip().endswith((".", "!", "?", "。", "！", "？")):
                sentence_text = "".join([t["text"] for t in current_sentence_tokens]).strip()
                if sentence_text:
                    first_token = current_sentence_tokens[0]
                    last_token = current_sentence_tokens[-1]
                    start = first_token["start_ms"] / 1000.0  # Convert to seconds
                    end = last_token["end_ms"] / 1000.0
                    
                    sentences.append({
                        "text": sentence_text,
                        "start": start,
                        "end": end,
                        "speaker": f"Speaker {current_speaker}" if current_speaker is not None else "Speaker 0",
                        "duration": end - start
                    })
                
                current_sentence_tokens = []
        
        # Add any remaining tokens as final sentence
        if current_sentence_tokens:
            sentence_text = "".join([t["text"] for t in current_sentence_tokens]).strip()
            if sentence_text:
                first_token = current_sentence_tokens[0]
                last_token = current_sentence_tokens[-1]
                start = first_token["start_ms"] / 1000.0
                end = last_token["end_ms"] / 1000.0
                
                sentences.append({
                    "text": sentence_text,
                    "start": start,
                    "end": end,
                    "speaker": f"Speaker {current_speaker}" if current_speaker is not None else "Speaker 0",
                    "duration": end - start
                })

        await delete_transcription(session, transcription_id)

        if file_id is not None:
            await delete_file(session, file_id)
        
        # Extract full transcript text from sentences
        if sentences and len(sentences) > 0:
            transcript_text = ""
            
            for sentence in sentences:
                start = sentence["start"]
                text = sentence["text"]
                speaker = sentence.get("speaker", "1")
                
                # Format timestamp
                hours = int(start // 3600)
                minutes = int((start % 3600) // 60)
                seconds = int(start % 60)
                
                if hours > 0:
                    timestamp = f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"
                else:
                    timestamp = f"[{minutes:02d}:{seconds:02d}]"
                
                # Format speaker label
                if isinstance(speaker, (int, str)) and str(speaker).isdigit():
                    speaker_label = f"Speaker {speaker}"
                else:
                    speaker_label = speaker
                

                transcript_text += f"{timestamp} {text}\n"

            
            transcript_text = transcript_text.strip()
            return transcript_text, sentences, None, audio_url
        else:
            return None, None, "audio has no content", audio_url


async def main():
    # Example usage
    audio_url = "https://pub-661d733d32f14d8684c7617d2f2e3372.r2.dev/audio/6847e1136bd67c40dc827779/vqv-jfnt-qww_vqv-jfnt-qww-aabb5b4b.wav"
    
    # Simple call with just audio_url
    sentences = await transcribe_audio(audio_url)
    print(sentences)
    
    # Or with custom language hints
    # sentences = await transcribe_audio(audio_url, language_hints=["vi", "en"])
    # print(sentences)


if __name__ == "__main__":
    asyncio.run(main())
