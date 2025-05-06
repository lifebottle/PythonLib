'''
Before you run this, make sure these are installed:
pip install torch
pip install torchaudio
pip install gradio
pip install transformers

You also need the following in your PATH environment variable: https://www.ffmpeg.org/download.html
ffmpeg
ffprobe

Finally, when you first run this, it'll download the openai/whisper-medium model, which is about 3GB.
'''

import torch
import torchaudio
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import gradio as gr

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
WHISPER_SAMPLE_RATE = 16000

processor = WhisperProcessor.from_pretrained("openai/whisper-medium")
model = WhisperForConditionalGeneration.from_pretrained(
    "openai/whisper-medium"
).to(DEVICE)


def preprocess_audio(audio_path: str) -> torch.Tensor:
    audio, sample_rate = torchaudio.load(audio_path)
    # Resample if necessary
    if sample_rate != WHISPER_SAMPLE_RATE:
        resampler = torchaudio.transforms.Resample(
            orig_freq=sample_rate, new_freq=WHISPER_SAMPLE_RATE
        )
        audio = resampler(audio)
    # Convert to mono
    if audio.shape[0] > 1:
        audio = torch.mean(audio, dim=0)
    return audio.squeeze()


def transcribe(audio_path: str) -> str:
    audio_input = preprocess_audio(audio_path)
    input_features = processor(
        audio_input,
        sampling_rate=WHISPER_SAMPLE_RATE,
        return_tensors="pt",
        language="japanese",
    ).input_features.to(DEVICE)

    predicted_ids = model.generate(input_features)
    transcription = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
    return transcription


iface = gr.Interface(
    fn=transcribe,
    inputs=gr.Audio(type="filepath"),
    outputs="text",
    title="OpenAI Whisper - Speech Recognition",
)
iface.launch()
