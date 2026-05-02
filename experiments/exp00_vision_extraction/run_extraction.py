import json
import os
import sys
import base64
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import argparse
import requests

from PIL import Image
import google.generativeai as genai
from openai import OpenAI

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


class VisionExtractor:
    def __init__(self, dataset_path: str = "manifests/dataset.jsonl", prompt_version: str = "v1"):
        self.dataset_path = dataset_path
        self.prompt_version = prompt_version
        self.base_dir = Path(__file__).parent
        self.project_root = self.base_dir.parent.parent  # luckyttoba/
        self.prompts = {}
        self._load_prompts()

    def _load_prompts(self):
        """Load prompts for each model (prompt_version에 따라 파일 선택)"""
        models = ["gemini"]
        for model in models:
            prompt_path = self.base_dir / "prompts" / f"extraction_{self.prompt_version}_{model}.txt"
            if prompt_path.exists():
                with open(prompt_path, "r", encoding="utf-8") as f:
                    self.prompts[model] = f.read()
            else:
                print(f"Warning: Prompt file not found: {prompt_path}")

    def load_image_as_base64(self, image_path: str) -> str:
        """Load image and convert to base64"""
        full_path = self.project_root / image_path
        if not full_path.exists():
            raise FileNotFoundError(f"Image not found: {full_path}")

        with open(full_path, "rb") as f:
            return base64.standard_b64encode(f.read()).decode("utf-8")

    def get_image_media_type(self, image_path: str) -> str:
        """Determine media type from file extension"""
        ext = Path(image_path).suffix.lower()
        media_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp"
        }
        return media_types.get(ext, "image/jpeg")

    def extract_with_gemini(self, image_paths: List[str], run_num: int) -> Dict[str, Any]:
        """Extract product info using Gemini API with multiple images"""
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not set in .env")

            genai.configure(api_key=api_key)

            prompt = self.prompts.get("gemini", "")

            # Build parts with all images
            parts = [{"text": prompt}]
            for image_path in image_paths:
                image_base64 = self.load_image_as_base64(image_path)
                media_type = self.get_image_media_type(image_path)
                parts.append({
                    "inline_data": {
                        "mime_type": media_type,
                        "data": image_base64
                    }
                })

            # Use REST API directly
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={api_key}"

            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [
                    {
                        "parts": parts
                    }
                ]
            }

            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()

            result_data = response.json()
            response_text = result_data["candidates"][0]["content"]["parts"][0]["text"].strip()

            # Extract JSON if it's wrapped in markdown code blocks
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "")
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "")

            result = json.loads(response_text)
            return result

        except Exception as e:
            print(f"Error with Gemini extraction: {e}")
            return None

    def extract_with_gpt(self, image_path: str, run_num: int) -> Dict[str, Any]:
        """Extract product info using OpenAI GPT-4V API"""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set in .env")

            client = OpenAI(api_key=api_key)

            image_base64 = self.load_image_as_base64(image_path)
            media_type = self.get_image_media_type(image_path)

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{image_base64}"
                                },
                            },
                            {
                                "type": "text",
                                "text": self.prompts.get("gpt", "")
                            }
                        ],
                    }
                ],
            )

            # Parse JSON from response
            response_text = response.choices[0].message.content.strip()
            # Extract JSON if it's wrapped in markdown code blocks
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "")
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "")

            result = json.loads(response_text)
            return result

        except Exception as e:
            print(f"Error with GPT extraction: {e}")
            return None

    def get_next_run_number(self, model: str, image_id: str) -> int:
        """Get the next run number for a model-image combination"""
        results_dir = self.base_dir / "results" / f"{model}_{self.prompt_version}"
        results_dir.mkdir(parents=True, exist_ok=True)

        # Check for existing files matching pattern
        existing_files = list(results_dir.glob(f"{image_id}_*.jsonl"))
        if not existing_files:
            return 1

        # Extract run numbers and get the max
        run_numbers = []
        for f in existing_files:
            try:
                num = int(f.stem.split("_")[-1])
                run_numbers.append(num)
            except ValueError:
                pass

        return max(run_numbers) + 1 if run_numbers else 1

    def save_result(self, model: str, image_id: str, run: int, result: Dict[str, Any], timestamp: str):
        """Save extraction result to JSONL file (버전별 폴더)"""
        results_dir = self.base_dir / "results" / f"{model}_{self.prompt_version}"
        results_dir.mkdir(parents=True, exist_ok=True)

        # Ensure run number is two digits
        result_file = results_dir / f"{image_id}_{run:02d}.jsonl"

        output = {
            "run": run,
            "model": model,
            "image_id": image_id,
            "timestamp": timestamp,
            "result": result
        }

        # Append to file (or create if doesn't exist)
        with open(result_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(output, ensure_ascii=False) + "\n")

        print(f"[OK] Saved {model} result: {result_file}")

    def load_dataset(self) -> list:
        """Load dataset from JSONL file"""
        dataset_path = self.base_dir / self.dataset_path
        if not dataset_path.exists():
            print(f"Error: Dataset file not found: {dataset_path}")
            print("Please create the dataset.jsonl file first with entries like:")
            print('{"id": "product_001", "images": ["images/product_001/01.png"]}')
            return []

        dataset = []
        with open(dataset_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    dataset.append(json.loads(line))
        return dataset

    def run_extraction(self, models: List[str], image_indices: Optional[List[int]] = None):
        """Run extraction for specified models"""
        dataset = self.load_dataset()
        if not dataset:
            return

        # Validate models
        valid_models = ["gemini", "gpt"]
        models = [m for m in models if m in valid_models]
        if not models:
            print(f"Error: No valid models specified. Choose from: {valid_models}")
            return

        timestamp = datetime.utcnow().isoformat() + "Z"

        # Process each item in dataset
        for idx, item in enumerate(dataset):
            if image_indices and idx not in image_indices:
                continue

            image_id = item["id"]
            images = item["images"]

            print(f"\n[*] Processing: {image_id}")
            print(f"   Images: {images}")

            for model in models:
                print(f"  [*] Extracting with {model.upper()}...", end=" ", flush=True)

                run_num = self.get_next_run_number(model, image_id)

                if model == "gemini":
                    result = self.extract_with_gemini(images, run_num)
                elif model == "gpt":
                    # For GPT, process first image only (multi-image support can be added later)
                    result = self.extract_with_gpt(images[0], run_num)
                else:
                    result = None

                if result:
                    self.save_result(model, image_id, run_num, result, timestamp)
                    print("Done")
                else:
                    print("Failed")


def main():
    parser = argparse.ArgumentParser(
        description="Extract product information from shopping screenshots using Vision LLMs"
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=["gemini"],
        choices=["gemini", "gpt"],
        help="Models to use for extraction (default: gemini)"
    )
    parser.add_argument(
        "--prompt-version",
        default="v1",
        choices=["v1", "v2", "v3"],
        help="Prompt version: v1 / v2 / v3 (GT 양식 1:1 일치)"
    )
    parser.add_argument(
        "--indices",
        nargs="+",
        type=int,
        help="Dataset indices to process (0-based, e.g., 0 2 3)"
    )
    parser.add_argument(
        "--dataset",
        default="manifests/dataset.jsonl",
        help="Path to dataset.jsonl file"
    )

    args = parser.parse_args()

    extractor = VisionExtractor(dataset_path=args.dataset, prompt_version=args.prompt_version)
    extractor.run_extraction(models=args.models, image_indices=args.indices)


if __name__ == "__main__":
    main()
