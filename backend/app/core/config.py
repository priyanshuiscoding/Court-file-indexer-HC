from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Court File Indexer Backend"
    APP_ENV: str = "local"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "change-me"

    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "court_indexer"
    POSTGRES_USER: str = "court_user"
    POSTGRES_PASSWORD: str = "court_pass"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "court_documents"
    EMBEDDING_VECTOR_SIZE: int = 1024
    QDRANT_TOP_K: int = 8
    CHAT_CONTEXT_TOP_K: int = 6
    CHAT_SUMMARY_CONTEXT_TOP_K: int = 12
    CHAT_MAX_HISTORY: int = 12
    CHAT_GENERATION_TIMEOUT_SECONDS: int = 45
    CHAT_REQUEST_TIMEOUT_SECONDS: int = 70

    STORAGE_ROOT: str = "./storage"
    PDF_STORAGE_DIR: str = "./storage/pdfs"
    RENDER_STORAGE_DIR: str = "./storage/rendered"
    OCR_STORAGE_DIR: str = "./storage/ocr"
    EXPORT_STORAGE_DIR: str = "./storage/exports"
    LOG_STORAGE_DIR: str = "./storage/logs"
    MAPPING_SHEET_PATH: str = "./storage/config/document_mapping.xlsx"
    MAPPING_SHEET_NAME: str = "Sheet1"
    MAPPING_REFRESH_SECONDS: int = 60

    DEFAULT_INDEX_SCAN_START: int = 1
    DEFAULT_INDEX_SCAN_END: int = 10
    DEFAULT_BATCH_CHUNK_SIZE: int = 10
    DEFAULT_QUEUE_NAME: str = "index_queue"
    TASK_HEARTBEAT_SECONDS: int = 30
    STUCK_TASK_SECONDS: int = 900

    OCR_ENGINE: str = "paddle"
    OCR_LANGUAGES: str = "en,hi"
    OCR_USE_ANGLE_CLS: bool = True
    OCR_RENDER_DPI: int = 220
    OCR_RENDER_FORMAT: str = "png"
    INDEX_MIN_CANDIDATE_SCORE: float = 2.0
    INDEX_CONTINUATION_MIN_SCORE: float = 1.2
    ENABLE_HINDI_FALLBACK: bool = True
    ENABLE_CONTENT_GENERATED_INDEX_FALLBACK: bool = True
    TESSERACT_CMD: str = "tesseract"

    USE_VLM_FALLBACK: bool = True
    ENABLE_CHAT: bool = True
    ENABLE_QDRANT: bool = True

    LOCAL_EMBEDDING_MODEL: str = "BAAI/bge-m3"
    LOCAL_RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"
    LOCAL_CHAT_MODEL: str = "Qwen/Qwen2.5-3B-Instruct"
    LOCAL_VLM_MODEL: str = "Qwen/Qwen2.5-VL-7B-Instruct"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_CHAT_MODEL: str = "qwen2.5:7b-instruct"

    EXTERNAL_FETCH_ENABLED: bool = False
    EXTERNAL_FETCH_URL: str = ""
    EXTERNAL_FETCH_API_KEY: str = ""
    EXTERNAL_FETCH_TIMEOUT_SECONDS: int = 60
    EXTERNAL_FETCH_BATCH_SIZE: int = 10
    EXTERNAL_FETCH_SOURCE_SYSTEM: str = "external_api"

    HC_MYSQL_HOST: str = ""
    HC_MYSQL_PORT: int = 3306
    HC_MYSQL_DB: str = "Digitization"
    HC_MYSQL_USER: str = ""
    HC_MYSQL_PASSWORD: str = ""
    HC_MYSQL_TABLE: str = "mp_indexing_batch"
    HC_MOUNT_ROOT: str = "/mnt/hitachi_disk1/JBP/SCANNING/scaned_clean_final"
    HC_IMPORT_ORDER: str = "ASC"
    HC_IMPORT_SCAN_MULTIPLIER: int = 5
    HC_IMPORT_MAX_SCAN: int = 500
    HC_PDF_RESOLVE_RECURSIVE: bool = True
    HC_PDF_RESOLVE_MAX_DEPTH: int = 3
    HC_IMPORT_LIMIT: int = 10
    HC_SOURCE_SYSTEM: str = "high_court_mysql"
    HC_MYSQL_MARK_COMPLETE_ENABLED: bool = False
    HC_MYSQL_COMPLETE_FIELD: str = "completed"
    HC_MYSQL_INDEX_DATE_FIELD: str = "indexing_com_date"
    HC_SCHEDULER_ENABLED: bool = False
    HC_SCHEDULER_IMPORT_EVERY_SECONDS: int = 300
    HC_SCHEDULER_IMPORT_LIMIT: int = 10
    HC_SCHEDULER_SYNC_STATUS_EVERY_SECONDS: int = 120
    HC_SCHEDULER_MARK_COMPLETE_ENABLED: bool = False
    HC_SCHEDULER_MARK_COMPLETE_EVERY_SECONDS: int = 300
    HC_SCHEDULER_MARK_COMPLETE_LIMIT: int = 50
    CLIENT_API_KEY: str = ""
    ENABLE_CLIENT_API_AUTH: bool = True

    @property
    def sqlalchemy_database_uri(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def qdrant_url(self) -> str:
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
