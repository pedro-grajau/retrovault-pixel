ALTER TABLE sessions ADD COLUMN expired_at TIMESTAMPTZ;
ALTER TABLE sessions ADD COLUMN cleaned_at TIMESTAMPTZ;
ALTER TABLE offers ADD COLUMN active BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE offers ADD COLUMN release_kind TEXT NOT NULL DEFAULT 'uncertain';
ALTER TABLE orders ADD COLUMN origin TEXT NOT NULL DEFAULT 'legacy';
CREATE TABLE conversations (
 id TEXT PRIMARY KEY, session_id TEXT UNIQUE NOT NULL REFERENCES sessions(id),
 started_at TIMESTAMPTZ NOT NULL DEFAULT now(), partial BOOLEAN NOT NULL DEFAULT false
);
CREATE TABLE conversation_messages (
 id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(id),
 role TEXT NOT NULL CHECK(role IN ('user','assistant')), content TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('received','responded','failed','legacy')),
 created_at TIMESTAMPTZ, sequence BIGSERIAL UNIQUE NOT NULL
);
CREATE TABLE journey_events (
 id TEXT PRIMARY KEY, conversation_id TEXT REFERENCES conversations(id),
 session_id TEXT NOT NULL REFERENCES sessions(id), message_id TEXT REFERENCES conversation_messages(id),
 type TEXT NOT NULL, origin TEXT NOT NULL, status TEXT NOT NULL,
 offer_id BIGINT REFERENCES offers(id), order_id TEXT REFERENCES orders(id),
 data JSONB NOT NULL DEFAULT '{}', created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE admin_sessions (token_hash TEXT PRIMARY KEY, expires_at TIMESTAMPTZ NOT NULL);
CREATE TABLE admin_attempts (key TEXT PRIMARY KEY, count INTEGER NOT NULL, window_at TIMESTAMPTZ NOT NULL);
CREATE INDEX orders_created ON orders(created_at);
CREATE INDEX conversation_started ON conversations(started_at);
CREATE INDEX message_conversation ON conversation_messages(conversation_id,sequence);
CREATE INDEX event_conversation ON journey_events(conversation_id,created_at);
INSERT INTO conversations(id,session_id,started_at,partial)
 SELECT 'legacy:'||id,id,created_at,true FROM sessions WHERE jsonb_array_length(messages)>0;
INSERT INTO conversation_messages(id,conversation_id,role,content,status,created_at)
 SELECT 'legacy:'||s.id||':'||m.ordinality,'legacy:'||s.id,m.value->>'role',m.value->>'content','legacy',NULL
 FROM sessions s CROSS JOIN LATERAL jsonb_array_elements(s.messages) WITH ORDINALITY m(value,ordinality)
 WHERE jsonb_array_length(s.messages)>0 ORDER BY s.created_at,m.ordinality;
