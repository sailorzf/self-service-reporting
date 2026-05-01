from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "mysql+pymysql://root:password@localhost:3306/report_db"
    dashscope_api_key: str = ""
    dashscope_model: str = "qwen-plus"
    max_joins: int = 3
    sql_timeout: int = 5
    max_result_rows: int = 1000

    class Config:
        env_file = ".env"

settings = Settings()
