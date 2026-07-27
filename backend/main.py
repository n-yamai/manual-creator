import os
import shutil
import uuid
import re
from datetime import datetime

from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from urllib.parse import quote


from config import settings
from database import engine, Base, get_db
from models import Manual, ManualImage
from schemas import (
    ManualResponse, ManualDetailResponse, ManualUpdate, 
    ManualCreate, ManualImageResponse, ExtractFrameRequest,
    ManualRefineRequest, ManualRefineResponse
)


from services.video_service import VideoService
from services.gemini_service import GeminiService
from services.pdf_service import PDFService


# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Manual Creator API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure media directories exist
os.makedirs(os.path.join(settings.MEDIA_DIR, "videos"), exist_ok=True)
os.makedirs(os.path.join(settings.MEDIA_DIR, "images"), exist_ok=True)
os.makedirs(os.path.join(settings.MEDIA_DIR, "pdfs"), exist_ok=True)

# Serve static media files
app.mount("/api/media", StaticFiles(directory=settings.MEDIA_DIR), name="media")

gemini_service = GeminiService()

@app.get("/api/manuals", response_model=List[ManualResponse])
def list_manuals(db: Session = Depends(get_db)):
    """Returns a list of all manuals."""
    return db.query(Manual).order_by(Manual.created_at.desc()).all()

@app.get("/api/manuals/{manual_id}", response_model=ManualDetailResponse)
def get_manual(manual_id: int, db: Session = Depends(get_db)):
    """Returns details of a specific manual, including its images."""
    manual = db.query(Manual).filter(Manual.id == manual_id).first()
    if not manual:
        raise HTTPException(status_code=404, detail="Manual not found")
    return manual

@app.post("/api/manuals", response_model=ManualResponse)
def create_manual(manual: ManualCreate, db: Session = Depends(get_db)):
    """Creates a new manual (empty or with preliminary content)."""
    db_manual = Manual(title=manual.title, content=manual.content, video_path=manual.video_path)
    db.add(db_manual)
    db.commit()
    db.refresh(db_manual)
    return db_manual

@app.put("/api/manuals/{manual_id}", response_model=ManualResponse)
def update_manual(manual_id: int, manual_update: ManualUpdate, db: Session = Depends(get_db)):
    """Updates manual content (Markdown or Title)."""
    db_manual = db.query(Manual).filter(Manual.id == manual_id).first()
    if not db_manual:
        raise HTTPException(status_code=404, detail="Manual not found")
    
    if manual_update.title is not None:
        db_manual.title = manual_update.title
    if manual_update.content is not None:
        db_manual.content = manual_update.content
        
    db_manual.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_manual)
    return db_manual

@app.delete("/api/manuals/{manual_id}")
def delete_manual(manual_id: int, db: Session = Depends(get_db)):
    """Deletes a manual, its images, and associated local media files."""
    db_manual = db.query(Manual).filter(Manual.id == manual_id).first()
    if not db_manual:
        raise HTTPException(status_code=404, detail="Manual not found")
    
    # Remove files from local filesystem
    if db_manual.video_path and os.path.exists(db_manual.video_path):
        try:
            os.remove(db_manual.video_path)
        except Exception as e:
            print(f"Error removing video file: {e}")

    for img in db_manual.images:
        abs_img_path = os.path.join(settings.MEDIA_DIR, img.image_path)
        if os.path.exists(abs_img_path):
            try:
                os.remove(abs_img_path)
            except Exception as e:
                print(f"Error removing image file: {e}")

    db.delete(db_manual)
    db.commit()
    return {"message": "Manual successfully deleted"}

@app.post("/api/manuals/upload", response_model=ManualDetailResponse)
async def upload_and_generate_manual(
    file: UploadFile = File(...),
    prompt_instruction: Optional[str] = Form(None),
    model_name: Optional[str] = Form("gemini-3.5-flash"),
    db: Session = Depends(get_db)
):
    """
    Uploads a video, calls Gemini API to extract manual content, 
    cuts recommended frames, and saves everything.
    """
    # 1. Save video file to disk
    file_ext = os.path.splitext(file.filename)[1]
    unique_id = str(uuid.uuid4())
    video_filename = f"{unique_id}{file_ext}"
    video_save_path = os.path.join(settings.MEDIA_DIR, "videos", video_filename)
    
    try:
        with open(video_save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save video: {str(e)}")

    # 2. Process with Gemini API
    try:
        selected_model = model_name if model_name else "gemini-3.5-flash"
        gen_result = gemini_service.generate_manual_from_video(
            video_path=video_save_path,
            user_instruction=prompt_instruction,
            model_name=selected_model
        )

    except Exception as e:
        # Cleanup video if generation fails
        if os.path.exists(video_save_path):
            os.remove(video_save_path)
        raise HTTPException(status_code=500, detail=f"AI Generation failed: {str(e)}")

    # 3. Create Manual in Database
    db_manual = Manual(
        title=gen_result.title,
        content="",  # will populate after extracting image paths
        video_path=video_save_path
    )
    db.add(db_manual)
    db.commit()
    db.refresh(db_manual)

    # 4. Extract screenshots for each recommended keyframe and save to DB
    extracted_image_urls = {}
    
    for i, keyframe in enumerate(gen_result.keyframes):
        img_filename = f"manual_{db_manual.id}_{i}_{unique_id[:8]}.png"
        try:
            rel_image_path = VideoService.extract_frame(
                video_path=video_save_path,
                timestamp=keyframe.timestamp,
                output_filename=img_filename
            )
            
            # Save ManualImage to database
            db_image = ManualImage(
                manual_id=db_manual.id,
                image_path=rel_image_path,
                timestamp=keyframe.timestamp,
                description=keyframe.description
            )
            db.add(db_image)
            
            # The relative URL for image serving
            extracted_image_urls[i] = f"/api/media/{rel_image_path}"

            
        except Exception as e:
            print(f"Failed to extract frame at {keyframe.timestamp}s: {e}")

    db.commit() # Save images

    # 5. Replace placeholders in markdown with actual image links (e.g. ![image](0), ![step 1](0))
    final_content = gen_result.content
    for i, keyframe in enumerate(gen_result.keyframes):
        pattern = re.compile(rf'!\s*\[([^\]]*)\]\s*\(\s*{i}\s*\)')
        if i in extracted_image_urls:
            url = extracted_image_urls[i]
            desc = keyframe.description or "静止画"
            final_content = pattern.sub(f'![{desc}]({url})', final_content)
        else:
            final_content = pattern.sub(f'*([静止画抽出失敗 ({keyframe.timestamp:.1f}s)])*', final_content)

    # Update manual with final markdown content
    db_manual.content = final_content
    db.commit()
    db.refresh(db_manual)

    return db_manual


# Export APIs
@app.get("/api/manuals/{manual_id}/pdf")
def export_pdf(manual_id: int, db: Session = Depends(get_db)):
    """Generates and downloads the PDF version of the manual."""
    manual = db.query(Manual).filter(Manual.id == manual_id).first()
    if not manual:
        raise HTTPException(status_code=404, detail="Manual not found")
        
    created_at_str = manual.created_at.strftime("%Y-%m-%d %H:%M")
    pdf_filename = f"manual_{manual_id}.pdf"
    pdf_path = os.path.join(settings.MEDIA_DIR, "pdfs", pdf_filename)
    
    PDFService.generate_pdf(
        title=manual.title,
        markdown_content=manual.content or "",
        created_at_str=created_at_str,
        output_path=pdf_path
    )

    # Use URL encoded filename for Content-Disposition to support Japanese filenames
    encoded_filename = quote(manual.title.replace(' ', '_'))
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}.pdf"}
    )

@app.get("/api/manuals/{manual_id}/html")
def export_html(manual_id: int, db: Session = Depends(get_db)):
    """Generates and downloads the HTML version of the manual."""
    manual = db.query(Manual).filter(Manual.id == manual_id).first()
    if not manual:
        raise HTTPException(status_code=404, detail="Manual not found")
        
    created_at_str = manual.created_at.strftime("%Y-%m-%d %H:%M")
    html_content = PDFService.generate_html(
        title=manual.title,
        markdown_content=manual.content or "",
        created_at_str=created_at_str
    )
    
    encoded_filename = quote(manual.title.replace(' ', '_'))
    return Response(
        content=html_content,
        media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}.html"}
    )

@app.get("/api/manuals/{manual_id}/markdown")
def export_markdown(manual_id: int, db: Session = Depends(get_db)):
    """Downloads the raw Markdown content of the manual."""
    manual = db.query(Manual).filter(Manual.id == manual_id).first()
    if not manual:
        raise HTTPException(status_code=404, detail="Manual not found")
        
    encoded_filename = quote(manual.title.replace(' ', '_'))
    return Response(
        content=manual.content or "",
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}.md"}
    )

@app.post("/api/manuals/{manual_id}/extract-frame", response_model=ManualImageResponse)
def extract_frame_custom(
    manual_id: int, 
    req: ExtractFrameRequest, 
    db: Session = Depends(get_db)
):
    """Extracts a frame at user-specified timestamp and attaches it to the manual."""
    manual = db.query(Manual).filter(Manual.id == manual_id).first()
    if not manual or not manual.video_path:
        raise HTTPException(status_code=404, detail="Manual or associated video not found")
        
    if not os.path.exists(manual.video_path):
        raise HTTPException(status_code=404, detail="Video file missing on server")

    unique_id = str(uuid.uuid4())[:8]
    img_filename = f"manual_{manual.id}_user_{unique_id}.png"
    
    try:
        rel_image_path = VideoService.extract_frame(
            video_path=manual.video_path,
            timestamp=req.timestamp,
            output_filename=img_filename
        )
        
        description = req.description or f"静止画 ({req.timestamp:.1f}秒)"
        db_image = ManualImage(
            manual_id=manual.id,
            image_path=rel_image_path,
            timestamp=req.timestamp,
            description=description
        )
        db.add(db_image)
        db.commit()
        db.refresh(db_image)
        return db_image
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract frame: {str(e)}")

@app.delete("/api/manuals/{manual_id}/images/{image_id}")
def delete_manual_image(manual_id: int, image_id: int, db: Session = Depends(get_db)):
    """Deletes a specific extracted image from manual and disk."""
    image = db.query(ManualImage).filter(
        ManualImage.id == image_id, 
        ManualImage.manual_id == manual_id
    ).first()
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
        
    abs_img_path = os.path.join(settings.MEDIA_DIR, image.image_path)
    if os.path.exists(abs_img_path):
        try:
            os.remove(abs_img_path)
        except Exception as e:
            print(f"Error removing image file: {e}")

    db.delete(image)
    db.commit()
    return {"message": "Image deleted successfully"}

@app.post("/api/manuals/{manual_id}/images/{image_id}/update", response_model=ManualImageResponse)
async def update_manual_image(
    manual_id: int, 
    image_id: int, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    """
    Updates an existing manual image file with an edited image version.
    """
    image = db.query(ManualImage).filter(
        ManualImage.id == image_id, 
        ManualImage.manual_id == manual_id
    ).first()
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
        
    abs_img_path = os.path.join(settings.MEDIA_DIR, image.image_path)
    
    try:
        with open(abs_img_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update image file: {str(e)}")

    db.commit()
    db.refresh(image)
    return image

@app.post("/api/manuals/{manual_id}/refine", response_model=ManualRefineResponse)
def refine_manual(
    manual_id: int, 
    req: ManualRefineRequest, 
    db: Session = Depends(get_db)
):
    """
    Uses Gemini API to refine and rewrite manual markdown content according to user prompt instructions.
    """
    manual = db.query(Manual).filter(Manual.id == manual_id).first()
    if not manual:
        raise HTTPException(status_code=404, detail="Manual not found")

    content_to_refine = req.current_content if req.current_content else (manual.content or "")
    if not content_to_refine.strip():
        raise HTTPException(status_code=400, detail="Content to refine is empty")

    try:
        refined_content = gemini_service.refine_manual_content(
            current_content=content_to_refine,
            instruction=req.instruction,
            model_name=req.model_name or "gemini-3.5-flash"
        )
        return ManualRefineResponse(refined_content=refined_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Refinement failed: {str(e)}")




