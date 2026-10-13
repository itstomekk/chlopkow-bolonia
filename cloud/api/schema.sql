-- chlopkow-api D1 schema. One row per finished run of any game.
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  game TEXT NOT NULL,
  device TEXT NOT NULL,            -- random id from the player's browser (localStorage); player = device + name
  name TEXT NOT NULL,
  char TEXT NOT NULL DEFAULT '',
  score REAL NOT NULL,
  trace TEXT NOT NULL DEFAULT '',  -- JSON array of checkpoint values (game-specific), used for the average CPU
  proof TEXT NOT NULL DEFAULT '{}',
  mode TEXT NOT NULL DEFAULT '',   -- e.g. solo / local4
  created INTEGER NOT NULL,        -- ms since epoch
  ip TEXT NOT NULL,                -- salted hash prefix, never the raw IP
  client TEXT NOT NULL DEFAULT '',
  version INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_runs_game_score ON runs (game, score);
CREATE INDEX IF NOT EXISTS idx_runs_game_created ON runs (game, created);
CREATE INDEX IF NOT EXISTS idx_runs_game_player ON runs (game, device, name);
CREATE INDEX IF NOT EXISTS idx_runs_ip_created ON runs (ip, created);
