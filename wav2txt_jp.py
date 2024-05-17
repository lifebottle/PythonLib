import os
import torch
import torchaudio
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import json

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

# Root directory containing the subfolders
root_directory = "Logo"

# Function to extract the numerical part of the filename
def extract_number(filename):
    return int(''.join(filter(str.isdigit, filename)))

# Function to transcribe audio
def transcribe_audio(audio_path):
    try:
        transcription = transcribe(audio_path)
        print(f"{audio_path}: {transcription}")
    except Exception as e:
        transcription = f"Error: {e}"
        print(f"{audio_path}: {transcription}")
    return transcription

# If there are no subfolders, process files in the root directory directly
if not any(os.path.isdir(os.path.join(root_directory, subdir)) for subdir in os.listdir(root_directory)):
    subdir_path = root_directory
    subfolders = [""]
else:
    subfolders = [subdir for subdir in os.listdir(root_directory) if os.path.isdir(os.path.join(root_directory, subdir))]

for subdir in subfolders:
    subdir_path = os.path.join(root_directory, subdir)
    results = {}
    i = 1

    # Iterate over .wav files in the current directory
    for filename in os.listdir(subdir_path):
        if filename.endswith(".wav"):
            audio_path = os.path.join(subdir_path, filename)
            # Transcribe the audio
            transcription = transcribe_audio(audio_path)

            # Store the result text in the dictionary
            results[filename] = transcription

            print("Transcribed {} ({}/{})".format(filename, i, len(os.listdir(subdir_path))))
            i += 1

    # Sort the results by filename numerically
    sorted_results = {k: results[k] for k in sorted(results, key=extract_number)}

    # Output JSON file path for the current directory
    if subdir == "":
        output_file = os.path.join(root_directory + ".json")
    else:
        output_file = os.path.join(root_directory, f"{subdir}.json")

    # Write the sorted results to a JSON file with non-ASCII characters preserved
    with open(output_file, "w", encoding="utf-8") as json_file:
        json.dump(sorted_results, json_file, indent=4, ensure_ascii=False)

    print("Transcription results saved to", output_file)
    
