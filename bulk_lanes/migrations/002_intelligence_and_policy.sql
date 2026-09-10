CREATE TABLE IF NOT EXISTS route_cooldowns (
    route_id TEXT PRIMARY KEY,
    cooldown_until REAL NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS route_evaluations (
    eval_id TEXT PRIMARY KEY,
    task_name TEXT NOT NULL,
    route_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    total_samples INTEGER NOT NULL,
    schema_pass_count INTEGER NOT NULL,
    grounding_pass_count INTEGER NOT NULL,
    correct_count INTEGER,
    error_count INTEGER NOT NULL,
    rate_limit_count INTEGER NOT NULL,
    avg_latency_seconds REAL NOT NULL,
    composite_score REAL NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_route_evals_task ON route_evaluations(task_name, route_id);
