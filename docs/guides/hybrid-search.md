# Hybrid search in PostgreSQL

odctl's PostgreSQL image adds pgvector for vector search and pg_textsearch for BM25 keyword ranking. Both extensions are created in the `vector` database. Hybrid search runs both queries and combines their rankings, which your application or a final SQL query does. The SQL below comes from the end-to-end tests.

```bash
odctl up postgres
docker exec -it postgres psql -U user -d vector
```

## Vector similarity with pgvector

```sql
CREATE TABLE items (id bigserial primary key, embedding vector(3));
INSERT INTO items (embedding) VALUES ('[1,0,0]'), ('[0,1,0]'), ('[0.9,0.1,0]');
CREATE INDEX items_hnsw ON items USING hnsw (embedding vector_l2_ops);

SELECT id FROM items ORDER BY embedding <-> '[1,0,0]' LIMIT 1;
```

`<->` is the Euclidean distance, so the nearest row comes first.

## Keyword ranking with pg_textsearch

```sql
CREATE TABLE docs (id int primary key, content text);
INSERT INTO docs VALUES
  (1, 'PostgreSQL is a powerful database system'),
  (2, 'BM25 is an effective ranking function'),
  (3, 'Full text search with custom scoring');
CREATE INDEX docs_bm25 ON docs USING bm25(content) WITH (text_config='english');

SELECT id FROM docs ORDER BY content <@> 'ranking function' LIMIT 1;
```

Ordering by `content <@> 'query'` puts the best BM25 match first. pg_textsearch works only when PostgreSQL preloads it, and odctl's compose file sets `shared_preload_libraries` to do that.

To use the extensions in another database, run `CREATE EXTENSION vector;` or `CREATE EXTENSION pg_textsearch;` there. From the host, connect to `127.0.0.1:5432` as `user` with password `password`.
