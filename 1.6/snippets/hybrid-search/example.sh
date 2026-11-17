#!/usr/bin/env bash
# Starts postgres and runs a vector query and a BM25 query in the vector
# database, on tables it creates again on every run.
set -euo pipefail

odctl up postgres

docker exec -i postgres psql -U user -d vector -v ON_ERROR_STOP=1 <<'SQL'
DROP TABLE IF EXISTS demo_items, demo_docs;

CREATE TABLE demo_items (id bigserial primary key, embedding vector(3));
INSERT INTO demo_items (embedding) VALUES ('[1,0,0]'), ('[0,1,0]'), ('[0.9,0.1,0]');
CREATE INDEX demo_items_hnsw ON demo_items USING hnsw (embedding vector_l2_ops);
SELECT id FROM demo_items ORDER BY embedding <-> '[1,0,0]' LIMIT 1;

CREATE TABLE demo_docs (id int primary key, content text);
INSERT INTO demo_docs VALUES
  (1, 'PostgreSQL is a powerful database system'),
  (2, 'BM25 is an effective ranking function'),
  (3, 'Full text search with custom scoring');
CREATE INDEX demo_docs_bm25 ON demo_docs USING bm25(content) WITH (text_config='english');
SELECT id FROM demo_docs ORDER BY content <@> 'ranking function' LIMIT 1;
SQL
