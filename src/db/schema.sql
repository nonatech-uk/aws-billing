CREATE TABLE IF NOT EXISTS account (
  account_id         text PRIMARY KEY,
  slug               text NOT NULL UNIQUE,
  name               text NOT NULL,
  billing            text NOT NULL CHECK (billing IN ('org','separate')),
  monthly_budget_usd numeric(10,2),
  created_at         timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS monthly_cost (
  account_id  text NOT NULL REFERENCES account(account_id),
  month       date NOT NULL,
  gross_usd   numeric(12,4) NOT NULL,
  net_usd     numeric(12,4) NOT NULL,
  fetched_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (account_id, month)
);

CREATE TABLE IF NOT EXISTS service_cost (
  account_id  text NOT NULL,
  month       date NOT NULL,
  service     text NOT NULL,
  cost_usd    numeric(12,4) NOT NULL,
  PRIMARY KEY (account_id, month, service),
  FOREIGN KEY (account_id, month) REFERENCES monthly_cost(account_id, month) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sync_run (
  id          bigserial PRIMARY KEY,
  started_at  timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  status      text NOT NULL DEFAULT 'running',
  error       text
);

CREATE INDEX IF NOT EXISTS idx_monthly_cost_month ON monthly_cost(month);

ALTER TABLE service_cost ADD COLUMN IF NOT EXISTS usage_qty numeric(14,4);
ALTER TABLE service_cost ADD COLUMN IF NOT EXISTS usage_unit text;
