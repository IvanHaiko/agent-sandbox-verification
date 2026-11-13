ALTER TABLE games
ADD COLUMN IF NOT EXISTS steam_store_updated_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS steam_store_success BOOLEAN,
ADD COLUMN IF NOT EXISTS steam_store_last_error TEXT;
