CREATE TABLE IF NOT EXISTS numbers (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    phone TEXT NOT NULL,
    risk_score NUMERIC(5, 2),
    risk_level TEXT,
    campaign_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT numbers_risk_score_check
        CHECK (risk_score IS NULL OR risk_score BETWEEN 0 AND 100),
    CONSTRAINT numbers_risk_level_check
        CHECK (risk_level IS NULL OR risk_level IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT numbers_phone_unique UNIQUE (phone)
);

CREATE TABLE IF NOT EXISTS campaigns (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    risk_score NUMERIC(5, 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT campaigns_risk_score_check
        CHECK (risk_score IS NULL OR risk_score BETWEEN 0 AND 100)
);

CREATE TABLE IF NOT EXISTS reports (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    number_id BIGINT NOT NULL,
    category TEXT NOT NULL,
    subcategories JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT reports_subcategories_array_check
        CHECK (jsonb_typeof(subcategories) = 'array'),
    CONSTRAINT reports_number_id_fkey
        FOREIGN KEY (number_id) REFERENCES numbers (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS campaign_numbers (
    campaign_id BIGINT NOT NULL,
    number_id BIGINT NOT NULL,
    similarity_score NUMERIC(5, 2),
    CONSTRAINT campaign_numbers_pkey PRIMARY KEY (campaign_id, number_id),
    CONSTRAINT campaign_numbers_similarity_score_check
        CHECK (similarity_score IS NULL OR similarity_score BETWEEN 0 AND 100),
    CONSTRAINT campaign_numbers_campaign_id_fkey
        FOREIGN KEY (campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE,
    CONSTRAINT campaign_numbers_number_id_fkey
        FOREIGN KEY (number_id) REFERENCES numbers (id) ON DELETE CASCADE
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'numbers_campaign_id_fkey'
          AND conrelid = 'numbers'::regclass
    ) THEN
        ALTER TABLE numbers
            ADD CONSTRAINT numbers_campaign_id_fkey
            FOREIGN KEY (campaign_id) REFERENCES campaigns (id) ON DELETE SET NULL;
    END IF;
END
$$;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS numbers_set_updated_at ON numbers;

CREATE TRIGGER numbers_set_updated_at
BEFORE UPDATE ON numbers
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS reports_number_id_idx
    ON reports (number_id);

CREATE INDEX IF NOT EXISTS campaign_numbers_number_id_idx
    ON campaign_numbers (number_id);

CREATE INDEX IF NOT EXISTS numbers_campaign_id_idx
    ON numbers (campaign_id);

CREATE INDEX IF NOT EXISTS numbers_risk_level_idx
    ON numbers (risk_level);

CREATE INDEX IF NOT EXISTS reports_category_idx
    ON reports (category);

CREATE INDEX IF NOT EXISTS campaign_numbers_similarity_score_idx
    ON campaign_numbers (similarity_score);
