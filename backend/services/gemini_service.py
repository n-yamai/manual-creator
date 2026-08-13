import time
import json
import logging
from typing import Dict, Any, List, Optional
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

def parse_gemini_error(e: Exception) -> str:
    """
    Parses Exception objects raised by Gemini API / google-genai / HTTP requests
    and returns a user-friendly, descriptive Japanese error message.
    """
    error_str = str(e)
    error_type = type(e).__name__

    # 1. 認証エラー・APIキー無効 (401, 403, PermissionDenied, Unauthenticated)
    if any(k in error_str for k in ["401", "403", "API_KEY_INVALID", "API key not valid", "PermissionDenied", "Unauthenticated", "UNAUTHENTICATED", "PERMISSION_DENIED"]):
        return "【認証エラー】Gemini APIキーが無効であるか、アクセス権限がありません。GEMINI_API_KEYの設定をご確認ください。"

    # 2. クォータ制限・利用制限・クレジット不足 (429, ResourceExhausted, QuotaExceeded)
    if any(k in error_str for k in ["429", "RESOURCE_EXHAUSTED", "QuotaExceeded", "quota", "Rate limit", "rate_limit"]):
        return "【利用制限/クレジット不足】Gemini APIの利用制限（レートリミットまたはクォータ制限・クレジット不足）に達しました。時間をおくか、APIの利用契約・課金設定をご確認ください。"

    # 3. リソース不在・モデル名エラー (404, NotFound)
    if any(k in error_str for k in ["404", "NOT_FOUND", "NotFound", "model not found"]):
        return "【モデル/リソース不在エラー】指定されたAIモデルが見つかりません。有効なGeminiモデルが選択されているかご確認ください。"

    # 4. リクエスト不正 (400, InvalidArgument)
    if any(k in error_str for k in ["400", "INVALID_ARGUMENT", "InvalidArgument"]):
        return f"【リクエスト不正エラー】送信されたデータまたはパラメーターが不正です。動画フォーマットや指示文をご確認ください。（詳細: {error_str}）"

    # 5. Gemini API サーバーエラー (500, 502, 503, 504, ServerError, ServiceUnavailable)
    if any(k in error_str for k in ["500", "502", "503", "504", "INTERNAL", "UNAVAILABLE", "ServiceUnavailable", "InternalServerError"]):
        return "【Gemini APIサーバーエラー】Google Gemini APIサーバー側で一時的な障害が発生しています。しばらく時間を置いてから再度お試しください。"

    # 6. 通信・ネットワークエラー (ConnectError, TimeoutError, ConnectionRefused, DNS)
    if any(k in error_type for k in ["Connect", "Timeout", "Network", "Connection"]) or any(k in error_str for k in ["connection", "timeout", "timed out", "NameResolutionError"]):
        return "【通信エラー】Gemini APIサーバーとの通信に失敗しました。サーバーのネットワーク接続やプロキシ設定をご確認ください。"

    # 7. その他の例外
    return f"【Gemini APIエラー】AI処理中にエラーが発生しました（{error_type}: {error_str}）"


PREDEFINED_MODELS = [
    {
        "id": "gemini-3.5-flash",
        "name": "Gemini 3.5 Flash",
        "badge": "推奨 (標準)",
        "badgeClass": "badge-recommended",
        "description": "高速かつバランスの取れた標準モデル。画像・音声の高品質なステップ解析を行います。"
    },
    {
        "id": "gemini-3.6-flash",
        "name": "Gemini 3.6 Flash",
        "badge": "最新 Flash",
        "badgeClass": "badge-new",
        "description": "最新フラグシップ Flash モデル。高度で精度の高い理解能力を備えます。"
    },
    {
        "id": "gemini-3.5-flash-lite",
        "name": "Gemini 3.5 Flash Lite",
        "badge": "超高速",
        "badgeClass": "badge-lite",
        "description": "処理スピード最優先の軽量モデル。迅速にドラフト作成したい場合に最適です。"
    },
    {
        "id": "gemini-3-pro-preview",
        "name": "Gemini 3 Pro Preview",
        "badge": "高精度 Pro",
        "badgeClass": "badge-pro",
        "description": "深い推論と複雑な手順解析が可能な最高精度 Pro モデル。"
    },
    {
        "id": "gemini-2.5-pro",
        "name": "Gemini 2.5 Pro",
        "badge": "Pro 安定版",
        "badgeClass": "badge-pro",
        "description": "安定性に優れた Pro グレードモデル。"
    }
]

class GeminiService:
    def get_client(self, api_key: Optional[str] = None) -> genai.Client:
        """指定されたAPIキー、または設定/環境変数のフォールバックキーを使用して Client インスタンスを生成"""
        target_key = api_key.strip() if (api_key and api_key.strip()) else settings.GEMINI_API_KEY
        if not target_key:
            raise RuntimeError("Gemini APIキーが設定されていません。画面上部の設定モーダルからAPIキーを設定してください。")
        return genai.Client(api_key=target_key)

    def get_available_models(self, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """ListModels 連携により利用可能なモデルを取得し、厳選モデルリストと突合して available: bool を設定"""
        fetched_ids = set()
        try:
            client = self.get_client(api_key)
            all_models = client.models.list()
            for model in all_models:
                actions = getattr(model, "supported_actions", []) or []
                if "generateContent" in actions:
                    raw_name = getattr(model, "name", "")
                    model_id = raw_name.replace("models/", "") if raw_name.startswith("models/") else raw_name
                    if model_id:
                        fetched_ids.add(model_id)
        except Exception as e:
            logger.warning(f"ListModels failed: {e}")

        result_models = []
        for model_def in PREDEFINED_MODELS:
            item = dict(model_def)
            item["available"] = item["id"] in fetched_ids
            result_models.append(item)

        return result_models

    def generate_manual_from_video(self, video_path: str, user_instruction: str = None, model_name: str = "gemini-3.5-flash", api_key: Optional[str] = None) -> ManualGenerationResult:
        """
        Uploads a video to Gemini API, analyzes it, and generates a structured manual
        with Markdown content and recommended keyframe timestamps using the specified model and user API key.
        """
        logger.info(f"Uploading video {video_path} to Gemini (Model: {model_name})...")
        client = self.get_client(api_key)

        # Upload video file to Gemini
        try:
            video_file = client.files.upload(file=video_path)
            logger.info(f"Video uploaded. File name: {video_file.name}. Waiting for processing...")
        except Exception as e:
            detailed_msg = parse_gemini_error(e)
            logger.error(f"Failed to upload video to Gemini: {detailed_msg}")
            raise RuntimeError(detailed_msg) from e
        
        # Wait for file processing to complete
        while video_file.state.name == "PROCESSING":
            time.sleep(5)
            try:
                video_file = client.files.get(name=video_file.name)
            except Exception as e:
                detailed_msg = parse_gemini_error(e)
                logger.error(f"Failed during file processing status check: {detailed_msg}")
                raise RuntimeError(detailed_msg) from e
            
        if video_file.state.name == "FAILED":
            raise RuntimeError("【Gemini動画解析エラー】アップロードされた動画のエンコード解析に失敗しました。動画ファイルが破損していないかご確認ください。")
            
        logger.info("Video processing complete. Starting generation...")

        # Build prompt (Forcing Japanese language output)
        prompt = (
            "【言語制約 - 最優先指示】\n"
            "生成する手順書のタイトル、本文、手順の説明、キーフレームの解説を含むすべての出力テキストは、必ず自然で読みやすい「日本語」で記述・作成してください。"
            "動画内の音声や字幕が他言語であっても、生成するマニュアルのテキストはすべて日本語で記述する必要があります。\n\n"
            "【指示内容】\n"
            "提供された動画ファイルの映像と音声を詳細に解析し、業務・操作トレーニング用のプロフェッショナルなステップバイステップ手順書（Markdown形式）を作成してください。"
            "出力は指定された JSON スキーマに従ってください。\n\n"
            "【各フィールドの要求仕様】:\n"
            "1. title: 手順書の明確で分かりやすい日本語タイトル。\n"
            "2. content: Markdown形式で記述された手順書本文（全テキスト日本語）。\n"
            "   - 論理的なセクション（例: 概要・準備物、操作手順、注意点・Tipsなど）に分類してください。\n"
            "   - 各ステップについて、何を行うべきか具体的な操作方法を日本語で詳細に記述してください。\n"
            "   - 重要ステップには必ず画像プレースホルダー `![image](IMAGE_INDEX)` を埋め込んでください。"
            "IMAGE_INDEX は `keyframes` 配列のインデックス（0開始の数値）に対応させます。"
            "例えば 3 つのキーフレームがある場合、本文の該当するステップの位置に `![image](0)`, `![image](1)`, `![image](2)` を配置してください。その他の外部URLは使用しないでください。\n"
            "3. keyframes: 手順のキーとなる瞬間（秒単位のタイムスタンプと、その場面の日本語による短い解説文）のリスト。\n"
        )
        
        if user_instruction:
            prompt += f"\n【追加のユーザー指示】:\n{user_instruction}\n（※ユーザー指示が含まれる場合も、必ず最終出力テキストはすべて日本語で記述してください。）\n"

        target_model = model_name if model_name else "gemini-3.5-flash"

        try:
            # Request specified Gemini Model
            response = client.models.generate_content(
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
                client.files.delete(name=video_file.name)
            except Exception as e:
                logger.warning(f"Failed to delete Gemini temp file: {e}")

            # Parse JSON result
            result_json = json.loads(response.text)
            return ManualGenerationResult(**result_json)

        except Exception as e:
            detailed_msg = parse_gemini_error(e)
            logger.error(f"Error calling Gemini API: {detailed_msg}")
            # Ensure cleanup
            try:
                client.files.delete(name=video_file.name)
            except:
                pass
            raise RuntimeError(detailed_msg) from e

    def refine_manual_content(self, current_content: str, instruction: str, model_name: str = "gemini-3.5-flash", api_key: Optional[str] = None) -> str:
        """
        Refines and rewrites the current manual Markdown content based on user prompt instructions using user API key.
        """
        target_model = model_name if model_name else "gemini-3.5-flash"
        logger.info(f"Refining manual content using Gemini (Model: {target_model})...")
        client = self.get_client(api_key)

        prompt = (
            "あなたはプロフェッショナルなテクニカルライターおよびマニュアル編集の専門家です。\n"
            "提供された【現在のマニュアル本文(Markdown)】を、【ユーザーからの修正指示】に従って正確に再構成・修正してください。\n\n"
            "【厳格な遵守事項】:\n"
            "1. すべてのテキストは必ず自然な「日本語」で記述してください。\n"
            "2. 修正後のMarkdownテキストのみを出力してください。挨拶文、解説文、```markdown などのコードブロック囲みは含めないでください。\n"
            "3. 本文中に埋め込まれている画像タグ（例: `![alt](url)`）や重要な構造を保持しながら、ユーザー指定の修正・追加を行ってください。\n"
            "4. 誤字脱字の修正および専門用語の分かりやすい日本語表現への統一を行ってください。\n\n"
            f"【現在のマニュアル本文】:\n{current_content}\n\n"
            f"【ユーザーからの修正指示】:\n{instruction}\n"
        )

        try:
            response = client.models.generate_content(
                model=target_model,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    temperature=0.3,
                )
            )

            text = response.text.strip()
            # Clean code block markdown wrapper if model included it
            if text.startswith("```markdown"):
                text = text[11:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]

            return text.strip()

        except Exception as e:
            detailed_msg = parse_gemini_error(e)
            logger.error(f"Error calling Gemini API for content refinement: {detailed_msg}")
            raise RuntimeError(detailed_msg) from e



