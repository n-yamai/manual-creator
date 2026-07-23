import cv2
import os
from config import settings


class VideoService:
    @staticmethod
    def extract_frame(video_path: str, timestamp: float, output_filename: str) -> str:
        """
        Extracts a frame from the video at the given timestamp (in seconds)
        and saves it as an image.
        If the timestamp exceeds video duration or fails, automatically clamps/fallbacks to valid frames.
        Returns the relative path of the saved image.
        """
        # Ensure target directory exists
        images_dir = os.path.join(settings.MEDIA_DIR, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        output_path = os.path.join(images_dir, output_filename)
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 0:
            fps = 30.0  # Fallback
            
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames > 0:
            duration = total_frames / fps
        else:
            duration = 99999.0

        # Clamp timestamp if it exceeds video duration
        target_timestamp = max(0.0, timestamp)
        if total_frames > 0 and target_timestamp >= duration:
            # If timestamp exceeds, use duration minus 1 second
            target_timestamp = max(0.0, duration - 1.0)
            
        target_frame = int(target_timestamp * fps)
        if total_frames > 0:
            target_frame = min(target_frame, max(0, total_frames - 2))

        # Try seeking by frame number
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        success, frame = cap.read()
        
        # Fallback 1: Try millisecond position
        if not success:
            cap.set(cv2.CAP_PROP_POS_MSEC, target_timestamp * 1000)
            success, frame = cap.read()

        # Fallback 2: Search backwards for a valid frame near the end
        if not success and total_frames > 0:
            search_frames = [
                max(0, total_frames - 5),
                max(0, total_frames - 10),
                max(0, total_frames - 30),
                0
            ]
            for f_idx in search_frames:
                cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
                success, frame = cap.read()
                if success:
                    break

        if not success:
            cap.release()
            raise ValueError(f"Could not extract any valid frame from {video_path}")
            
        # Save the frame
        cv2.imwrite(output_path, frame)
        cap.release()
        
        # Return the relative path from the media directory
        return os.path.join("images", output_filename)
