"""Operator-only Google Cloud speech synthesis. Audio is returned, never stored."""
import os


def synthesize(text: str) -> bytes:
    from google.cloud import texttospeech

    if not 1 <= len(text) <= 2000:
        raise ValueError('Speech text must be between 1 and 2000 characters')
    client = texttospeech.TextToSpeechClient()
    response = client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=text),
        voice=texttospeech.VoiceSelectionParams(
            language_code='en-US', name=os.getenv('NEUROMESH_VOICE_NAME', 'en-US-Neural2-J')),
        audio_config=texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.LINEAR16),
    )
    return response.audio_content
