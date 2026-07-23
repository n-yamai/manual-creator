import time
import json
import logging
from typing import Dict, Any, List
from pydantic import BaseModel
from google import genai
from google.genai import types
from config import settings


logger = logging.getLogger(__name__)

class KeyframeInfo(BaseModel):
    timestamp: float
    description: str

class ManualGenerationResult(BaseModel):
    title: str
    content: str
    keyframes: List[KeyframeInfo]

class GeminiService:
    def __init__(self):
        # APIキーが空の場合は、環境変数から読み込む
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            logger.warning("GEMINI_API_KEY is not set. Gemini API calls will fail.")
        self.client = genai.Client(api_key=api_key)

    def generate_manual_from_video(self, video_path: str, user_instruction: str = None, model_name: str = "gemini-3.5-flash") -> ManualGenerationResult:
        """
        Uploads a video to Gemini API, analyzes it, and generates a structured manual
        with Markdown content and recommended keyframe timestamps using the specified model.
        """
        logger.info(f"Uploading video {video_path} to Gemini (Model: {model_name})...")
        
        # Upload video file to Gemini
        video_file = self.client.files.upload(file=video_path)
        logger.info(f"Video uploaded. File name: {video_file.name}. Waiting for processing...")
        
        # Wait for file processing to complete
        while video_file.state.name == "PROCESSING":
            time.sleep(5)
            video_file = self.client.files.get(name=video_file.name)
            
        if video_file.state.name == "FAILED":
            raise Exception("Gemini video processing failed.")
            
        logger.info("Video processing complete. Starting generation...")

        # Build prompt
        prompt = (
            "Analyze the audio and video content of the provided video file. "
            "Generate a highly professional, detailed step-by-step training/operation manual. "
            "The output must follow the specified JSON schema.\n\n"
            "Requirements for the fields:\n"
            "1. title: A clear, descriptive title for the manual.\n"
            "2. content: The full body of the manual written in Markdown format. "
            "Divide the manual into logical sections (e.g., Preparation, Steps, Tips). "
            "For each key step, describe what is happening in detail. "
            "You MUST embed images at key steps by using the placeholder format `![image](IMAGE_INDEX)` "
            "where IMAGE_INDEX corresponds to the index of the keyframe in the `keyframes` list (0-indexed). "
            "For example, if you list 3 keyframes, use `![image](0)`, `![image](1)`, and `![image](2)` in the Markdown text "
            "at the exact positions where those images should visually explain the step. Do NOT use other image URLs.\n"
            "3. keyframes: A list of key moments (timestamp in seconds, and brief description) that visually capture the core steps "
            "described in the manual, which will be extracted as screenshots.\n"
        )
        
        if user_instruction:
            prompt += f"\nAdditional User Instructions: {user_instruction}\n"

        target_model = model_name if model_name else "gemini-3.5-flash"

        try:
            # Request specified Gemini Model
            response = self.client.models.generate_content(
                model=target_model,
                contents=[video_file, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ManualGenerationResult,
                    temperature=0.2,
                )
            )

            
            # Delete file from Gemini after analysis to be clean
            try:
                self.client.files.delete(name=video_file.name)
            except Exception as e:
                logger.warning(f"Failed to delete Gemini temp file: {e}")

            # Parse JSON result
            result_json = json.loads(response.text)
            return ManualGenerationResult(**result_json)

        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            # Ensure cleanup
            try:
                self.client.files.delete(name=video_file.name)
            except:
                pass
            raise e
