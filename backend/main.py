import os
import shutil
import uuid
import re
from datetime import datetime

from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy.orm import Session
from urllib.parse import quote


from config import settings
from database import engine, Base, get_db, run_migrations
from models import Manual, ManualImage
from schemas import (
    ManualResponse, ManualDetailResponse, ManualUpdate, 
    ManualCreate, ManualImageResponse, ExtractFrameRequest,
    ManualRefineRequest, ManualRefineResponse,
    ApiKeySetRequest, ApiKeyStatusResponse, AiModelResponse,
    ApiKeyAddRequest, ApiKeySelectRequest, ApiKeyItemResponse, ApiKeysStatusResponse
)



from services.video_service import VideoService
from services.gemini_service import GeminiService
from services.pdf_service import PDFService
from services.key_service import KeyService



# Create database tables & run migrations for existing DB compatibility
Base.metadata.create_all(bind=engine)
run_migrations()

app = FastAPI(title="Manual Creator API")

# Setup CORS
# withCredentials: true（認証情報の送信）を行う場合、Access-Control-Allow-Origin にワイルドカード "*" は使用できません。
# CORS_ORIGINS 環境変数が未指定の場合は、全HTTP/HTTPSオリジンからの接続に対しリクエスト元のOriginを返す allow_origin_regex を適用します。
cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]

if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https?://.*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Ensure media directories exist
os.makedirs(os.path.join(settings.MEDIA_DIR, "videos"), exist_ok=True)
os.makedirs(os.path.join(settings.MEDIA_DIR, "images"), exist_ok=True)
os.makedirs(os.path.join(settings.MEDIA_DIR, "pdfs"), exist_ok=True)

@app.get("/api/media/videos/{filename}")
def stream_video(filename: str, request: Request):
    """
    Serves video files with HTTP Range Requests support (206 Partial Content)
    enabling smooth timeline seeking in HTML5 video players across all browsers.
    """
    video_path = os.path.join(settings.MEDIA_DIR, "videos", filename)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")

    file_size = os.path.getsize(video_path)
    range_header = request.headers.get("range")

    if not range_header:
        def full_file_iterator():
            with open(video_path, "rb") as f:
                while chunk := f.read(1024 * 1024):
                    yield chunk

        return StreamingResponse(
            full_file_iterator(),
            media_type="video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
            }
        )

    try:
        units, range_str = range_header.split("=")
        if units.strip() != "bytes":
            raise ValueError()

        start_str, end_str = range_str.split("-")
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1

        if start >= file_size or end >= file_size or start > end:
            raise ValueError()

    except ValueError:
        return Response(
            status_code=416,
            headers={
                "Content-Range": f"bytes */{file_size}",
                "Accept-Ranges": "bytes"
            }
        )

    chunk_size = (end - start) + 1

    def range_stream_iterator():
        with open(video_path, "rb") as f:
            f.seek(start)
            bytes_left = chunk_size
            while bytes_left > 0:
                read_size = min(1024 * 1024, bytes_left)
                data = f.read(read_size)
                if not data:
                    break
                bytes_left -= len(data)
                yield data

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_size),
        "Content-Type": "video/mp4",
    }

    return StreamingResponse(
        range_stream_iterator(),
        status_code=206,
        headers=headers,
        media_type="video/mp4"
    )

# Serve static media files
app.mount("/api/media", StaticFiles(directory=settings.MEDIA_DIR), name="media")

gemini_service = GeminiService()

COOKIE_KEY_NAME = "gemini_user_api_keys"

def get_storage_data_from_cookie(request: Request) -> dict:
    """HttpOnly Cookieから暗号化データを復号して取得"""
    encrypted_token = request.cookies.get(COOKIE_KEY_NAME)
    if not encrypted_token:
        # 旧形式の単一キーCookieの互換チェック
        legacy_token = request.cookies.get("gemini_user_api_key")
        if legacy_token:
            encrypted_token = legacy_token
    
    if encrypted_token:
        data = KeyService.decrypt_data(encrypted_token)
        if data and isinstance(data, dict):
            return data
    return {"active_id": None, "keys": []}

def save_storage_data_to_cookie(response: Response, storage_data: dict) -> str:
    """辞書データを暗号化して HttpOnly Cookie に保存"""
    encrypted_token = KeyService.encrypt_data(storage_data)
    response.set_cookie(
        key=COOKIE_KEY_NAME,
        value=encrypted_token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 90
    )
    return encrypted_token

def get_current_api_key(request: Request) -> Optional[str]:
    """現在アクティブなAPIキーの文字列を取得"""
    storage = get_storage_data_from_cookie(request)
    active_id = storage.get("active_id")
    keys = storage.get("keys", [])

    if active_id and keys:
        for k in keys:
            if k.get("id") == active_id:
                return k.get("api_key")
    
    # active_id が未指定でキーが存在する場合は先頭を使用
    if keys:
        return keys[0].get("api_key")

    return None

@app.get("/api/settings/api-keys", response_model=ApiKeysStatusResponse)
def get_api_keys_status(request: Request):
    """登録済みAPIキーの一覧およびアクティブキー情報を取得"""
    storage = get_storage_data_from_cookie(request)
    active_id = storage.get("active_id")
    keys_data = storage.get("keys", [])

    items: List[ApiKeyItemResponse] = []
    active_label = None

    for k in keys_data:
        kid = k.get("id", "")
        label = k.get("label", "登録キー")
        raw_key = k.get("api_key", "")
        is_active = (kid == active_id) if active_id else False

        if is_active:
            active_label = label

        items.append(ApiKeyItemResponse(
            id=kid,
            label=label,
            masked_key=KeyService.mask_api_key(raw_key),
            is_active=is_active
        ))

    # もし active_id がなく、キーが存在する場合は先頭をアクティブ扱いにする
    if items and not any(i.is_active for i in items):
        items[0].is_active = True
        active_id = items[0].id
        active_label = items[0].label

    fallback_key = settings.GEMINI_API_KEY
    using_fallback = len(items) == 0 and bool(fallback_key and fallback_key.strip())
    fallback_masked = KeyService.mask_api_key(fallback_key) if fallback_key else None

    return ApiKeysStatusResponse(
        active_id=active_id,
        active_label=active_label,
        keys=items,
        using_fallback=using_fallback,
        fallback_masked_key=fallback_masked
    )

@app.post("/api/settings/api-keys")
def add_api_key(req: ApiKeyAddRequest, request: Request, response: Response):
    """新しいAPIキーの接続テストを行い、ラベル付きで追加＆アクティブに設定"""
    clean_key = req.api_key.strip()
    clean_label = req.label.strip() if req.label and req.label.strip() else "APIキー"

    if not clean_key:
        raise HTTPException(status_code=400, detail="APIキーを入力してください。")

    # 1. 接続テスト
    try:
        gemini_service.get_available_models(api_key=clean_key)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"APIキーの接続テストに失敗しました: {str(e)}")

    # 2. 既存ストレージの読み込み
    storage = get_storage_data_from_cookie(request)
    keys = storage.get("keys", [])

    new_id = f"key_{uuid.uuid4().hex[:8]}"
    new_item = {
        "id": new_id,
        "label": clean_label,
        "api_key": clean_key
    }
    keys.append(new_item)
    storage["keys"] = keys
    storage["active_id"] = new_id  # 新規追加したキーを自動的にアクティブ化

    save_storage_data_to_cookie(response, storage)
    return {"message": f"APIキー「{clean_label}」を追加し、有効化しました。", "id": new_id}

@app.put("/api/settings/api-keys/active")
def select_active_api_key(req: ApiKeySelectRequest, request: Request, response: Response):
    """指定されたIDのAPIキーをアクティブに切り替え"""
    storage = get_storage_data_from_cookie(request)
    keys = storage.get("keys", [])

    target_item = next((k for k in keys if k.get("id") == req.id), None)
    if not target_item:
        raise HTTPException(status_code=404, detail="指定されたAPIキーが見つかりません。")

    storage["active_id"] = req.id
    save_storage_data_to_cookie(response, storage)
    return {"message": f"使用するAPIキーを「{target_item.get('label')}」に切り替えました。"}

@app.delete("/api/settings/api-keys/{key_id}")
def delete_api_key_item(key_id: str, request: Request, response: Response):
    """指定されたIDのAPIキーを削除"""
    storage = get_storage_data_from_cookie(request)
    keys = storage.get("keys", [])

    filtered_keys = [k for k in keys if k.get("id") != key_id]
    if len(filtered_keys) == len(keys):
        raise HTTPException(status_code=404, detail="指定されたAPIキーが見つかりません。")

    storage["keys"] = filtered_keys

    # もし削除したキーがアクティブだった場合、残っている先頭のキーをアクティブ化
    if storage.get("active_id") == key_id:
        if filtered_keys:
            storage["active_id"] = filtered_keys[0].get("id")
        else:
            storage["active_id"] = None

    save_storage_data_to_cookie(response, storage)
    return {"message": "APIキーを削除しました。"}

# 互換性用単一キー用エンドポイント
@app.get("/api/settings/api-key", response_model=ApiKeyStatusResponse)
def get_api_key_status(request: Request):
    user_key = get_current_api_key(request)
    if user_key:
        return ApiKeyStatusResponse(is_set=True, masked_key=KeyService.mask_api_key(user_key), using_fallback=False)
    fallback_key = settings.GEMINI_API_KEY
    if fallback_key and fallback_key.strip():
        return ApiKeyStatusResponse(is_set=False, masked_key=KeyService.mask_api_key(fallback_key), using_fallback=True)
    return ApiKeyStatusResponse(is_set=False, masked_key=None, using_fallback=False)

@app.get("/api/models", response_model=List[AiModelResponse])
def get_available_models(request: Request):
    """厳選モデルリストと Gemini ListModels 取得結果を突合して利用可能一覧を返却"""
    user_key = get_current_api_key(request)
    return gemini_service.get_available_models(api_key=user_key)

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
    request: Request,
    file: UploadFile = File(...),
    prompt_instruction: Optional[str] = Form(None),
    model_name: Optional[str] = Form("gemini-3.5-flash"),
    db: Session = Depends(get_db)
):
    """
    Uploads a video, calls Gemini API to extract manual content, 
    cuts recommended frames, and saves everything.
    """
    user_api_key = get_current_api_key(request)

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
            model_name=selected_model,
            api_key=user_api_key
        )

    except Exception as e:
        # Cleanup video if generation fails
        if os.path.exists(video_save_path):
            os.remove(video_save_path)
        raise HTTPException(status_code=500, detail=str(e))



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
            description=description,
            image_type="extracted"
        )
        db.add(db_image)
        db.commit()
        db.refresh(db_image)
        return db_image
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract frame: {str(e)}")

@app.post("/api/manuals/{manual_id}/upload-image", response_model=ManualImageResponse)
async def upload_custom_image(
    manual_id: int,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Uploads an arbitrary custom image file and attaches it to the manual."""
    manual = db.query(Manual).filter(Manual.id == manual_id).first()
    if not manual:
        raise HTTPException(status_code=404, detail="Manual not found")

    file_ext = os.path.splitext(file.filename)[1] if file.filename else ".png"
    if not file_ext:
        file_ext = ".png"

    unique_id = str(uuid.uuid4())[:8]
    img_filename = f"manual_{manual_id}_custom_{unique_id}{file_ext}"
    rel_image_path = f"images/{img_filename}"
    abs_image_save_path = os.path.join(settings.MEDIA_DIR, "images", img_filename)

    try:
        with open(abs_image_save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save custom image: {str(e)}")

    img_desc = description or (file.filename if file.filename else "追加画像")
    
    db_image = ManualImage(
        manual_id=manual.id,
        image_path=rel_image_path,
        timestamp=None,
        description=img_desc,
        image_type="uploaded"
    )
    db.add(db_image)
    db.commit()
    db.refresh(db_image)
    return db_image

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
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Uses Gemini API to refine and rewrite manual markdown content according to user prompt instructions.
    """
    user_api_key = get_current_api_key(request)

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
            model_name=req.model_name or "gemini-3.5-flash",
            api_key=user_api_key
        )
        return ManualRefineResponse(refined_content=refined_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))






