# services/key_service.py
import os
import base64
import logging
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from config import settings

logger = logging.getLogger(__name__)

# サーバー共通の秘密鍵からFernet用32バイト暗号鍵を誘導生成（環境変数の変更にも一定の安定性を持たせるため静的ソルトを使用）
_secret = getattr(settings, "SECRET_KEY", None) or os.getenv("SECRET_KEY", "manual_creator_default_secret_key_change_in_prod")
_kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=b"manual_creator_static_salt_v1",
    iterations=100000,
)
_fernet_key = base64.urlsafe_b64encode(_kdf.derive(_secret.encode('utf-8')))
_cipher_suite = Fernet(_fernet_key)

import json

class KeyService:
    @staticmethod
    def encrypt_api_key(api_key: str) -> str:
        """APIキーをFernetで暗号化してHttpOnly Cookie保存用トークン文字列を生成"""
        if not api_key:
            return ""
        return _cipher_suite.encrypt(api_key.strip().encode('utf-8')).decode('utf-8')

    @staticmethod
    def decrypt_api_key(encrypted_token: str) -> Optional[str]:
        """HttpOnly Cookieに格納された暗号化トークンを復号して元のAPIキーを抽出"""
        if not encrypted_token:
            return None
        try:
            return _cipher_suite.decrypt(encrypted_token.encode('utf-8')).decode('utf-8')
        except Exception as e:
            logger.warning(f"Failed to decrypt API key token: {e}")
            return None

    @staticmethod
    def encrypt_data(data: dict) -> str:
        """辞書/JSONオブジェクト構造全体をFernetで暗号化して文字列化"""
        if not data:
            return ""
        json_str = json.dumps(data, ensure_ascii=False)
        return _cipher_suite.encrypt(json_str.encode('utf-8')).decode('utf-8')

    @staticmethod
    def decrypt_data(encrypted_token: str) -> Optional[dict]:
        """暗号化トークンを復号して辞書/JSONオブジェクト構造を復元"""
        if not encrypted_token:
            return None
        try:
            decrypted_str = _cipher_suite.decrypt(encrypted_token.encode('utf-8')).decode('utf-8')
            return json.loads(decrypted_str)
        except Exception as e:
            # 旧バージョンの単一文字列キー形式である場合の互換処理
            try:
                single_key = _cipher_suite.decrypt(encrypted_token.encode('utf-8')).decode('utf-8')
                if single_key and not single_key.startswith("{"):
                    return {
                        "active_id": "legacy_default_id",
                        "keys": [{
                            "id": "legacy_default_id",
                            "label": "標準登録キー",
                            "api_key": single_key
                        }]
                    }
            except:
                pass
            logger.warning(f"Failed to decrypt storage data token: {e}")
            return None

    @staticmethod
    def mask_api_key(api_key: str) -> str:
        """フロントエンド確認表示用マスク化 (例: AIzaSy...4aX9) 生キーの漏洩を防止"""
        if not api_key:
            return ""
        clean = api_key.strip()
        if len(clean) <= 10:
            return f"{clean[:2]}***{clean[-2:]}"
        return f"{clean[:6]}...{clean[-4:]}"

