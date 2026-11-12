from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    brs_api_key: SecretStr = SecretStr('')
    database_url: str = 'postgresql+psycopg://market:market@localhost:5432/market'
    admin_token: SecretStr = SecretStr('')
    read_token: SecretStr = SecretStr('')
    data_provider: str = 'tsetmc'
    brs_fallback_enabled: bool = False
    tsetmc_base_urls: str = 'https://cdn.tsetmc.com,https://cdn10.tsetmc.com'
    tsetmc_proxy_url: SecretStr = SecretStr('')
    request_interval: float = Field(1.0, ge=0)
    request_timeout: float = Field(30, gt=0)
    max_retries: int = Field(3, ge=0, le=8)
    max_retry_wait: float = Field(120, gt=0)
    codal_max_pages: int = Field(100, ge=1)
    selected_symbols: str = ''
    nav_symbols: str = 'اهرم,عیار'
    market_types: str = '1,2,3,4,5'
    log_path: str = 'logs/market.jsonl'

    def symbols(self) -> list[str]:
        return [s.strip() for s in self.selected_symbols.split(',') if s.strip()]
