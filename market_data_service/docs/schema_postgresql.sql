BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001

CREATE TABLE symbols (
    id SERIAL NOT NULL,
    symbol_l18 VARCHAR(100) NOT NULL,
    ins_code VARCHAR(40),
    isin VARCHAR(40),
    symbol_name VARCHAR(500),
    market VARCHAR(100),
    sector VARCHAR(500),
    is_active BOOLEAN NOT NULL,
    raw JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (symbol_l18)
);

CREATE INDEX ix_symbols_ins_code ON symbols (ins_code);

CREATE TABLE indices (
    id SERIAL NOT NULL,
    index_type INTEGER NOT NULL,
    name VARCHAR(200) NOT NULL,
    state VARCHAR(100),
    PRIMARY KEY (id),
    UNIQUE (index_type, name)
);

CREATE TABLE raw_responses (
    id BIGSERIAL NOT NULL,
    endpoint VARCHAR(40) NOT NULL,
    params JSONB NOT NULL,
    payload JSONB NOT NULL,
    fetched_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id)
);

CREATE INDEX ix_raw_responses_endpoint ON raw_responses (endpoint);

CREATE TABLE sync_runs (
    id BIGSERIAL NOT NULL,
    endpoint VARCHAR(40),
    params JSONB,
    status VARCHAR(30) NOT NULL,
    accepted INTEGER,
    rejected INTEGER,
    error_kind VARCHAR(100),
    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id)
);

CREATE TABLE sync_errors (
    id BIGSERIAL NOT NULL,
    run_id BIGINT,
    raw_id BIGINT,
    endpoint VARCHAR(40),
    error_kind TEXT NOT NULL,
    raw JSONB,
    recorded_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id),
    FOREIGN KEY(run_id) REFERENCES sync_runs (id),
    FOREIGN KEY(raw_id) REFERENCES raw_responses (id)
);

CREATE TABLE price_history (
    id BIGSERIAL NOT NULL,
    natural_key VARCHAR(64) NOT NULL,
    symbol_id INTEGER,
    date_shamsi VARCHAR(10),
    date_basis VARCHAR(20) NOT NULL,
    time_shamsi VARCHAR(8) NOT NULL,
    raw_id BIGINT NOT NULL,
    raw JSONB NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    trade_count BIGINT,
    volume BIGINT,
    value NUMERIC(30, 6),
    price_min NUMERIC(30, 6),
    price_max NUMERIC(30, 6),
    price_yesterday NUMERIC(30, 6),
    price_first NUMERIC(30, 6),
    price_last NUMERIC(30, 6),
    price_last_change NUMERIC(30, 6),
    price_last_change_pct NUMERIC(30, 6),
    price_close NUMERIC(30, 6),
    price_close_change NUMERIC(30, 6),
    price_close_change_pct NUMERIC(30, 6),
    PRIMARY KEY (id),
    UNIQUE (natural_key),
    FOREIGN KEY(symbol_id) REFERENCES symbols (id),
    FOREIGN KEY(raw_id) REFERENCES raw_responses (id)
);

CREATE INDEX ix_price_history_symbol_id ON price_history (symbol_id);

CREATE INDEX ix_price_history_symbol_date ON price_history (symbol_id, date_shamsi);

CREATE TABLE client_type_history (
    id BIGSERIAL NOT NULL,
    natural_key VARCHAR(64) NOT NULL,
    symbol_id INTEGER,
    date_shamsi VARCHAR(10),
    date_basis VARCHAR(20) NOT NULL,
    time_shamsi VARCHAR(8) NOT NULL,
    raw_id BIGINT NOT NULL,
    raw JSONB NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    buy_real_count BIGINT,
    buy_real_volume BIGINT,
    buy_real_value NUMERIC(30, 6),
    buy_legal_count BIGINT,
    buy_legal_volume BIGINT,
    buy_legal_value NUMERIC(30, 6),
    sell_real_count BIGINT,
    sell_real_volume BIGINT,
    sell_real_value NUMERIC(30, 6),
    sell_legal_count BIGINT,
    sell_legal_volume BIGINT,
    sell_legal_value NUMERIC(30, 6),
    PRIMARY KEY (id),
    UNIQUE (natural_key),
    FOREIGN KEY(symbol_id) REFERENCES symbols (id),
    FOREIGN KEY(raw_id) REFERENCES raw_responses (id)
);

CREATE INDEX ix_client_type_history_symbol_id ON client_type_history (symbol_id);

CREATE INDEX ix_client_type_history_symbol_date ON client_type_history (symbol_id, date_shamsi);

CREATE TABLE candlesticks (
    id BIGSERIAL NOT NULL,
    natural_key VARCHAR(64) NOT NULL,
    symbol_id INTEGER,
    date_shamsi VARCHAR(10),
    date_basis VARCHAR(20) NOT NULL,
    time_shamsi VARCHAR(8) NOT NULL,
    raw_id BIGINT NOT NULL,
    raw JSONB NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    candle_type INTEGER NOT NULL,
    open NUMERIC(30, 6),
    high NUMERIC(30, 6),
    low NUMERIC(30, 6),
    close NUMERIC(30, 6),
    volume BIGINT,
    PRIMARY KEY (id),
    UNIQUE (natural_key),
    FOREIGN KEY(symbol_id) REFERENCES symbols (id),
    FOREIGN KEY(raw_id) REFERENCES raw_responses (id)
);

CREATE INDEX ix_candlesticks_symbol_id ON candlesticks (symbol_id);

CREATE INDEX ix_candlesticks_symbol_date ON candlesticks (symbol_id, date_shamsi);

CREATE TABLE transactions (
    id BIGSERIAL NOT NULL,
    natural_key VARCHAR(64) NOT NULL,
    symbol_id INTEGER,
    date_shamsi VARCHAR(10),
    date_basis VARCHAR(20) NOT NULL,
    time_shamsi VARCHAR(8) NOT NULL,
    raw_id BIGINT NOT NULL,
    raw JSONB NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    row_num BIGINT NOT NULL,
    canceled BOOLEAN NOT NULL,
    price NUMERIC(30, 6),
    volume BIGINT,
    PRIMARY KEY (id),
    UNIQUE (natural_key),
    FOREIGN KEY(symbol_id) REFERENCES symbols (id),
    FOREIGN KEY(raw_id) REFERENCES raw_responses (id)
);

CREATE INDEX ix_transactions_symbol_date ON transactions (symbol_id, date_shamsi);

CREATE INDEX ix_transactions_symbol_id ON transactions (symbol_id);

CREATE TABLE shareholders (
    id BIGSERIAL NOT NULL,
    natural_key VARCHAR(64) NOT NULL,
    symbol_id INTEGER,
    date_shamsi VARCHAR(10),
    date_basis VARCHAR(20) NOT NULL,
    time_shamsi VARCHAR(8) NOT NULL,
    raw_id BIGINT NOT NULL,
    raw JSONB NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    shareholder_name TEXT NOT NULL,
    percentage NUMERIC(30, 6),
    change NUMERIC(30, 6),
    volume BIGINT,
    PRIMARY KEY (id),
    UNIQUE (natural_key),
    FOREIGN KEY(symbol_id) REFERENCES symbols (id),
    FOREIGN KEY(raw_id) REFERENCES raw_responses (id)
);

CREATE INDEX ix_shareholders_symbol_date ON shareholders (symbol_id, date_shamsi);

CREATE INDEX ix_shareholders_symbol_id ON shareholders (symbol_id);

CREATE TABLE symbol_snapshots (
    id BIGSERIAL NOT NULL,
    natural_key VARCHAR(64) NOT NULL,
    symbol_id INTEGER,
    date_shamsi VARCHAR(10),
    date_basis VARCHAR(20) NOT NULL,
    time_shamsi VARCHAR(8) NOT NULL,
    raw_id BIGINT NOT NULL,
    raw JSONB NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    price_last NUMERIC(30, 6),
    price_close NUMERIC(30, 6),
    value NUMERIC(30, 6),
    volume BIGINT,
    PRIMARY KEY (id),
    UNIQUE (natural_key),
    FOREIGN KEY(symbol_id) REFERENCES symbols (id),
    FOREIGN KEY(raw_id) REFERENCES raw_responses (id)
);

CREATE INDEX ix_symbol_snapshots_symbol_id ON symbol_snapshots (symbol_id);

CREATE INDEX ix_symbol_snapshots_symbol_date ON symbol_snapshots (symbol_id, date_shamsi);

CREATE TABLE etf_nav (
    id BIGSERIAL NOT NULL,
    natural_key VARCHAR(64) NOT NULL,
    symbol_id INTEGER,
    date_shamsi VARCHAR(10),
    date_basis VARCHAR(20) NOT NULL,
    time_shamsi VARCHAR(8) NOT NULL,
    raw_id BIGINT NOT NULL,
    raw JSONB NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    nav_issue NUMERIC(30, 6),
    nav_value NUMERIC(30, 6),
    PRIMARY KEY (id),
    UNIQUE (natural_key),
    FOREIGN KEY(symbol_id) REFERENCES symbols (id),
    FOREIGN KEY(raw_id) REFERENCES raw_responses (id)
);

CREATE INDEX ix_etf_nav_symbol_id ON etf_nav (symbol_id);

CREATE INDEX ix_etf_nav_symbol_date ON etf_nav (symbol_id, date_shamsi);

CREATE TABLE index_values (
    id BIGSERIAL NOT NULL,
    natural_key VARCHAR(64) NOT NULL,
    symbol_id INTEGER,
    date_shamsi VARCHAR(10),
    date_basis VARCHAR(20) NOT NULL,
    time_shamsi VARCHAR(8) NOT NULL,
    raw_id BIGINT NOT NULL,
    raw JSONB NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    index_id INTEGER NOT NULL,
    value NUMERIC(30, 6),
    change_value NUMERIC(30, 6),
    change_percent NUMERIC(30, 6),
    min_value NUMERIC(30, 6),
    max_value NUMERIC(30, 6),
    equal_weight NUMERIC(30, 6),
    equal_weight_change NUMERIC(30, 6),
    PRIMARY KEY (id),
    UNIQUE (natural_key),
    FOREIGN KEY(symbol_id) REFERENCES symbols (id),
    FOREIGN KEY(raw_id) REFERENCES raw_responses (id),
    FOREIGN KEY(index_id) REFERENCES indices (id)
);

CREATE INDEX ix_index_values_symbol_date ON index_values (symbol_id, date_shamsi);

CREATE INDEX ix_index_values_symbol_id ON index_values (symbol_id);

CREATE TABLE tse_options (
    id BIGSERIAL NOT NULL,
    natural_key VARCHAR(64) NOT NULL,
    symbol_id INTEGER,
    date_shamsi VARCHAR(10),
    date_basis VARCHAR(20) NOT NULL,
    time_shamsi VARCHAR(8) NOT NULL,
    raw_id BIGINT NOT NULL,
    raw JSONB NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    contract_name TEXT,
    underlying VARCHAR(100),
    option_type VARCHAR(10),
    expiry_date VARCHAR(10),
    strike_price NUMERIC(30, 6),
    last_price NUMERIC(30, 6),
    volume BIGINT,
    open_interest BIGINT,
    PRIMARY KEY (id),
    UNIQUE (natural_key),
    FOREIGN KEY(symbol_id) REFERENCES symbols (id),
    FOREIGN KEY(raw_id) REFERENCES raw_responses (id)
);

CREATE INDEX ix_tse_options_symbol_id ON tse_options (symbol_id);

CREATE INDEX ix_tse_options_symbol_date ON tse_options (symbol_id, date_shamsi);

CREATE TABLE codal_announcements (
    id BIGSERIAL NOT NULL,
    natural_key VARCHAR(64) NOT NULL,
    symbol_id INTEGER,
    date_shamsi VARCHAR(10),
    date_basis VARCHAR(20) NOT NULL,
    time_shamsi VARCHAR(8) NOT NULL,
    raw_id BIGINT NOT NULL,
    raw JSONB NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    summary TEXT,
    PRIMARY KEY (id),
    UNIQUE (natural_key),
    FOREIGN KEY(symbol_id) REFERENCES symbols (id),
    FOREIGN KEY(raw_id) REFERENCES raw_responses (id)
);

CREATE INDEX ix_codal_announcements_symbol_id ON codal_announcements (symbol_id);

CREATE INDEX ix_codal_announcements_symbol_date ON codal_announcements (symbol_id, date_shamsi);

CREATE TABLE ime_futures (
    id BIGSERIAL NOT NULL,
    natural_key VARCHAR(64) NOT NULL,
    symbol_id INTEGER,
    date_shamsi VARCHAR(10),
    date_basis VARCHAR(20) NOT NULL,
    time_shamsi VARCHAR(8) NOT NULL,
    raw_id BIGINT NOT NULL,
    raw JSONB NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    contract_code VARCHAR(200),
    contract_name TEXT,
    underlying TEXT,
    option_type VARCHAR(10),
    expiry_date VARCHAR(10),
    offer_code VARCHAR(100),
    currency VARCHAR(40),
    unit VARCHAR(100),
    value_unit VARCHAR(100),
    strike_price NUMERIC(30, 6),
    last_price NUMERIC(30, 6),
    nav NUMERIC(30, 6),
    volume NUMERIC(30, 6),
    value NUMERIC(30, 6),
    open_interest BIGINT,
    PRIMARY KEY (id),
    UNIQUE (natural_key),
    FOREIGN KEY(symbol_id) REFERENCES symbols (id),
    FOREIGN KEY(raw_id) REFERENCES raw_responses (id)
);

CREATE INDEX ix_ime_futures_symbol_id ON ime_futures (symbol_id);

CREATE INDEX ix_ime_futures_symbol_date ON ime_futures (symbol_id, date_shamsi);

CREATE TABLE ime_options (
    id BIGSERIAL NOT NULL,
    natural_key VARCHAR(64) NOT NULL,
    symbol_id INTEGER,
    date_shamsi VARCHAR(10),
    date_basis VARCHAR(20) NOT NULL,
    time_shamsi VARCHAR(8) NOT NULL,
    raw_id BIGINT NOT NULL,
    raw JSONB NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    contract_code VARCHAR(200),
    contract_name TEXT,
    underlying TEXT,
    option_type VARCHAR(10),
    expiry_date VARCHAR(10),
    offer_code VARCHAR(100),
    currency VARCHAR(40),
    unit VARCHAR(100),
    value_unit VARCHAR(100),
    strike_price NUMERIC(30, 6),
    last_price NUMERIC(30, 6),
    nav NUMERIC(30, 6),
    volume NUMERIC(30, 6),
    value NUMERIC(30, 6),
    open_interest BIGINT,
    PRIMARY KEY (id),
    UNIQUE (natural_key),
    FOREIGN KEY(symbol_id) REFERENCES symbols (id),
    FOREIGN KEY(raw_id) REFERENCES raw_responses (id)
);

CREATE INDEX ix_ime_options_symbol_id ON ime_options (symbol_id);

CREATE INDEX ix_ime_options_symbol_date ON ime_options (symbol_id, date_shamsi);

CREATE TABLE ime_certificates (
    id BIGSERIAL NOT NULL,
    natural_key VARCHAR(64) NOT NULL,
    symbol_id INTEGER,
    date_shamsi VARCHAR(10),
    date_basis VARCHAR(20) NOT NULL,
    time_shamsi VARCHAR(8) NOT NULL,
    raw_id BIGINT NOT NULL,
    raw JSONB NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    contract_code VARCHAR(200),
    contract_name TEXT,
    underlying TEXT,
    option_type VARCHAR(10),
    expiry_date VARCHAR(10),
    offer_code VARCHAR(100),
    currency VARCHAR(40),
    unit VARCHAR(100),
    value_unit VARCHAR(100),
    strike_price NUMERIC(30, 6),
    last_price NUMERIC(30, 6),
    nav NUMERIC(30, 6),
    volume NUMERIC(30, 6),
    value NUMERIC(30, 6),
    open_interest BIGINT,
    PRIMARY KEY (id),
    UNIQUE (natural_key),
    FOREIGN KEY(symbol_id) REFERENCES symbols (id),
    FOREIGN KEY(raw_id) REFERENCES raw_responses (id)
);

CREATE INDEX ix_ime_certificates_symbol_date ON ime_certificates (symbol_id, date_shamsi);

CREATE INDEX ix_ime_certificates_symbol_id ON ime_certificates (symbol_id);

CREATE TABLE ime_funds (
    id BIGSERIAL NOT NULL,
    natural_key VARCHAR(64) NOT NULL,
    symbol_id INTEGER,
    date_shamsi VARCHAR(10),
    date_basis VARCHAR(20) NOT NULL,
    time_shamsi VARCHAR(8) NOT NULL,
    raw_id BIGINT NOT NULL,
    raw JSONB NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    contract_code VARCHAR(200),
    contract_name TEXT,
    underlying TEXT,
    option_type VARCHAR(10),
    expiry_date VARCHAR(10),
    offer_code VARCHAR(100),
    currency VARCHAR(40),
    unit VARCHAR(100),
    value_unit VARCHAR(100),
    strike_price NUMERIC(30, 6),
    last_price NUMERIC(30, 6),
    nav NUMERIC(30, 6),
    volume NUMERIC(30, 6),
    value NUMERIC(30, 6),
    open_interest BIGINT,
    PRIMARY KEY (id),
    UNIQUE (natural_key),
    FOREIGN KEY(symbol_id) REFERENCES symbols (id),
    FOREIGN KEY(raw_id) REFERENCES raw_responses (id)
);

CREATE INDEX ix_ime_funds_symbol_date ON ime_funds (symbol_id, date_shamsi);

CREATE INDEX ix_ime_funds_symbol_id ON ime_funds (symbol_id);

CREATE TABLE ime_physical (
    id BIGSERIAL NOT NULL,
    natural_key VARCHAR(64) NOT NULL,
    symbol_id INTEGER,
    date_shamsi VARCHAR(10),
    date_basis VARCHAR(20) NOT NULL,
    time_shamsi VARCHAR(8) NOT NULL,
    raw_id BIGINT NOT NULL,
    raw JSONB NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    contract_code VARCHAR(200),
    contract_name TEXT,
    underlying TEXT,
    option_type VARCHAR(10),
    expiry_date VARCHAR(10),
    offer_code VARCHAR(100),
    currency VARCHAR(40),
    unit VARCHAR(100),
    value_unit VARCHAR(100),
    strike_price NUMERIC(30, 6),
    last_price NUMERIC(30, 6),
    nav NUMERIC(30, 6),
    volume NUMERIC(30, 6),
    value NUMERIC(30, 6),
    open_interest BIGINT,
    PRIMARY KEY (id),
    UNIQUE (natural_key),
    FOREIGN KEY(symbol_id) REFERENCES symbols (id),
    FOREIGN KEY(raw_id) REFERENCES raw_responses (id)
);

CREATE INDEX ix_ime_physical_symbol_id ON ime_physical (symbol_id);

CREATE INDEX ix_ime_physical_symbol_date ON ime_physical (symbol_id, date_shamsi);

CREATE TABLE commodities (
    id BIGSERIAL NOT NULL,
    natural_key VARCHAR(64) NOT NULL,
    symbol_id INTEGER,
    date_shamsi VARCHAR(10),
    date_basis VARCHAR(20) NOT NULL,
    time_shamsi VARCHAR(8) NOT NULL,
    raw_id BIGINT NOT NULL,
    raw JSONB NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    commodity_symbol VARCHAR(60) NOT NULL,
    commodity_name VARCHAR(200),
    unit VARCHAR(100),
    price NUMERIC(30, 6),
    change_value NUMERIC(30, 6),
    change_percent NUMERIC(30, 6),
    PRIMARY KEY (id),
    UNIQUE (natural_key),
    FOREIGN KEY(symbol_id) REFERENCES symbols (id),
    FOREIGN KEY(raw_id) REFERENCES raw_responses (id)
);

CREATE INDEX ix_commodities_symbol_date ON commodities (symbol_id, date_shamsi);

CREATE INDEX ix_commodities_symbol_id ON commodities (symbol_id);

INSERT INTO alembic_version (version_num) VALUES ('0001') RETURNING alembic_version.version_num;

-- Running upgrade 0001 -> 0002

ALTER TABLE price_history ADD COLUMN source VARCHAR(40) DEFAULT 'brsapi' NOT NULL;

ALTER TABLE client_type_history ADD COLUMN source VARCHAR(40) DEFAULT 'brsapi' NOT NULL;

ALTER TABLE candlesticks ADD COLUMN source VARCHAR(40) DEFAULT 'brsapi' NOT NULL;

ALTER TABLE transactions ADD COLUMN source VARCHAR(40) DEFAULT 'brsapi' NOT NULL;

ALTER TABLE shareholders ADD COLUMN source VARCHAR(40) DEFAULT 'brsapi' NOT NULL;

ALTER TABLE symbol_snapshots ADD COLUMN source VARCHAR(40) DEFAULT 'brsapi' NOT NULL;

ALTER TABLE etf_nav ADD COLUMN source VARCHAR(40) DEFAULT 'brsapi' NOT NULL;

ALTER TABLE index_values ADD COLUMN source VARCHAR(40) DEFAULT 'brsapi' NOT NULL;

ALTER TABLE tse_options ADD COLUMN source VARCHAR(40) DEFAULT 'brsapi' NOT NULL;

ALTER TABLE codal_announcements ADD COLUMN source VARCHAR(40) DEFAULT 'brsapi' NOT NULL;

ALTER TABLE ime_futures ADD COLUMN source VARCHAR(40) DEFAULT 'brsapi' NOT NULL;

ALTER TABLE ime_options ADD COLUMN source VARCHAR(40) DEFAULT 'brsapi' NOT NULL;

ALTER TABLE ime_certificates ADD COLUMN source VARCHAR(40) DEFAULT 'brsapi' NOT NULL;

ALTER TABLE ime_funds ADD COLUMN source VARCHAR(40) DEFAULT 'brsapi' NOT NULL;

ALTER TABLE ime_physical ADD COLUMN source VARCHAR(40) DEFAULT 'brsapi' NOT NULL;

ALTER TABLE commodities ADD COLUMN source VARCHAR(40) DEFAULT 'brsapi' NOT NULL;

ALTER TABLE raw_responses ADD COLUMN source VARCHAR(40) DEFAULT 'brsapi' NOT NULL;

CREATE TABLE provider_requests (
    id BIGSERIAL NOT NULL,
    source VARCHAR(40) NOT NULL,
    endpoint VARCHAR(200) NOT NULL,
    params JSONB NOT NULL,
    status VARCHAR(40) NOT NULL,
    http_status INTEGER,
    origin VARCHAR(255),
    format VARCHAR(20),
    source_hash VARCHAR(64),
    payload JSONB,
    error_kind VARCHAR(100),
    accepted INTEGER,
    rejected INTEGER,
    fetched_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id)
);

CREATE INDEX ix_provider_requests_endpoint ON provider_requests (endpoint);

CREATE TABLE market_observations (
    id BIGSERIAL NOT NULL,
    natural_key VARCHAR(64) NOT NULL,
    request_id BIGINT NOT NULL,
    source VARCHAR(40) NOT NULL,
    endpoint VARCHAR(200) NOT NULL,
    instrument_code VARCHAR(40),
    symbol VARCHAR(100),
    date_shamsi VARCHAR(10),
    time_shamsi VARCHAR(8) NOT NULL,
    data_class VARCHAR(20) NOT NULL,
    quality JSONB NOT NULL,
    raw JSONB NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id),
    UNIQUE (natural_key),
    FOREIGN KEY(request_id) REFERENCES provider_requests (id)
);

CREATE INDEX ix_market_observations_instrument_code ON market_observations (instrument_code);

CREATE INDEX ix_market_observations_date_shamsi ON market_observations (date_shamsi);

UPDATE alembic_version SET version_num='0002' WHERE alembic_version.version_num = '0001';

COMMIT;
