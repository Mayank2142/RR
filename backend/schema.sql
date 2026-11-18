-- Optional PostgreSQL persistence schema. Derived API snapshots need no database.
-- Raw ball-by-ball data stays in the immutable pack; avoid duplicating it here.
CREATE TABLE IF NOT EXISTS analysis_run (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  version TEXT NOT NULL,
  data_cutoff DATE NOT NULL,
  source_manifest JSONB NOT NULL,
  assumptions JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS player (
  source_player_id BIGINT PRIMARY KEY,
  display_name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS player_rating (
  run_id BIGINT NOT NULL REFERENCES analysis_run(id),
  source_player_id BIGINT NOT NULL REFERENCES player(source_player_id),
  discipline TEXT NOT NULL CHECK (discipline IN ('bat','bowl')),
  rank INTEGER NOT NULL CHECK (rank > 0),
  score NUMERIC(8,4) NOT NULL CHECK (score BETWEEN 0 AND 100),
  evidence JSONB NOT NULL,
  PRIMARY KEY(run_id, source_player_id, discipline),
  UNIQUE(run_id, discipline, rank)
);
