CREATE TABLE games (
 id BIGINT PRIMARY KEY, title TEXT NOT NULL, summary TEXT NOT NULL DEFAULT '',
 cover TEXT, genres JSONB NOT NULL DEFAULT '[]', updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE platforms (slug TEXT PRIMARY KEY, igdb_id BIGINT UNIQUE NOT NULL, name TEXT NOT NULL);
CREATE TABLE offers (
 id BIGSERIAL PRIMARY KEY, game_id BIGINT NOT NULL REFERENCES games(id),
 platform TEXT NOT NULL REFERENCES platforms(slug), sale_price INTEGER NOT NULL CHECK(sale_price>0),
 rental_price INTEGER NOT NULL CHECK(rental_price>0), UNIQUE(game_id,platform)
);
CREATE TABLE demo_links (offer_id BIGINT PRIMARY KEY REFERENCES offers(id), provider TEXT NOT NULL, url TEXT NOT NULL, embed_url TEXT);
CREATE TABLE sessions (
 id TEXT PRIMARY KEY, customer TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 last_seen TIMESTAMPTZ NOT NULL DEFAULT now(), version INTEGER NOT NULL DEFAULT 0,
 chat_count INTEGER NOT NULL DEFAULT 0, chat_window TIMESTAMPTZ NOT NULL DEFAULT now(),
 last_manual TIMESTAMPTZ, messages JSONB NOT NULL DEFAULT '[]', chat_busy_until TIMESTAMPTZ,
 chat_lease TEXT
);
CREATE TABLE sale_stock (
 session_id TEXT REFERENCES sessions(id) ON DELETE CASCADE, offer_id BIGINT REFERENCES offers(id),
 quantity INTEGER NOT NULL CHECK(quantity>=0), PRIMARY KEY(session_id,offer_id)
);
CREATE TABLE rental_copies (
 id BIGSERIAL PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
 offer_id BIGINT NOT NULL REFERENCES offers(id), available BOOLEAN NOT NULL DEFAULT true
);
CREATE TABLE carts (
 session_id TEXT REFERENCES sessions(id) ON DELETE CASCADE, offer_id BIGINT REFERENCES offers(id),
 mode TEXT NOT NULL CHECK(mode IN ('sale','rental')), quantity INTEGER NOT NULL CHECK(quantity BETWEEN 1 AND 10),
 PRIMARY KEY(session_id,offer_id,mode)
);
CREATE TABLE checkouts (
 id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
 version INTEGER NOT NULL, summary JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 consumed BOOLEAN NOT NULL DEFAULT false
);
CREATE TABLE orders (
 id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
 checkout_id TEXT UNIQUE REFERENCES checkouts(id), actor TEXT NOT NULL CHECK(actor IN ('visitor','simulation')),
 items JSONB NOT NULL, total INTEGER NOT NULL CHECK(total>=0), created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE rentals (
 id TEXT PRIMARY KEY, order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
 copy_id BIGINT NOT NULL REFERENCES rental_copies(id), due_at TIMESTAMPTZ NOT NULL, returned_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX one_active_rental ON rentals(copy_id) WHERE returned_at IS NULL;
CREATE TABLE batches (
 id TEXT NOT NULL, session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
 events JSONB NOT NULL DEFAULT '[]', created_at TIMESTAMPTZ NOT NULL DEFAULT now(), PRIMARY KEY(session_id,id)
);
CREATE TABLE import_runs (
 id TEXT PRIMARY KEY, started_at TIMESTAMPTZ NOT NULL DEFAULT now(), finished_at TIMESTAMPTZ,
 status TEXT NOT NULL, added INTEGER NOT NULL DEFAULT 0, error TEXT
);
CREATE INDEX active_sessions ON sessions(last_seen);
CREATE INDEX offers_platform ON offers(platform);
