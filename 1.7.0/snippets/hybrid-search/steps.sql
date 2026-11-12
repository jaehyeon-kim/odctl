-- SQL from docs/guides/hybrid-search.md, run by .github/scripts/smoke.sh in the
-- vector database.

-- --8<-- [start:vector]
CREATE TABLE items (id bigserial primary key, embedding vector(3));
INSERT INTO items (embedding) VALUES ('[1,0,0]'), ('[0,1,0]'), ('[0.9,0.1,0]');
CREATE INDEX items_hnsw ON items USING hnsw (embedding vector_l2_ops);

SELECT id FROM items ORDER BY embedding <-> '[1,0,0]' LIMIT 1;
-- --8<-- [end:vector]

-- --8<-- [start:bm25]
CREATE TABLE docs (id int primary key, content text);
INSERT INTO docs VALUES
  (1, 'PostgreSQL is a powerful database system'),
  (2, 'BM25 is an effective ranking function'),
  (3, 'Full text search with custom scoring');
CREATE INDEX docs_bm25 ON docs USING bm25(content) WITH (text_config='english');

SELECT id FROM docs ORDER BY content <@> 'ranking function' LIMIT 1;
-- --8<-- [end:bm25]
