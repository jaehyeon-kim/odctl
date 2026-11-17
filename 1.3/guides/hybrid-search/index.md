# Hybrid Search in PostgreSQL

odctl's PostgreSQL image adds pgvector for vector search and pg_textsearch for BM25 keyword ranking. Vector search finds the rows whose embeddings are nearest to a query embedding. BM25 is a ranking function that scores a text by how often it holds the query's words, weighted by how rare each word is. Both extensions are created in the `vector` database. Hybrid search runs both queries and combines their rankings, which your application or a final SQL query does. The end-to-end tests run the SQL below on every release.

This guide builds on [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/index.md).

| Endpoint                              | Address                                            |
| ------------------------------------- | -------------------------------------------------- |
| PostgreSQL from the host              | `127.0.0.1:5432`, user `user`, password `password` |
| PostgreSQL inside the `odctl` network | `postgres:5432`                                    |
| Database with both extensions         | `vector`                                           |

Start the profile and open `psql` in the container:

```bash
odctl up postgres
docker exec -it postgres psql -U user -d vector
```

## Vector Similarity with pgvector

This creates a table of three-dimensional vectors with an HNSW index and returns the row nearest to `[1,0,0]`:

```sql
CREATE TABLE items (id bigserial primary key, embedding vector(3));
INSERT INTO items (embedding) VALUES ('[1,0,0]'), ('[0,1,0]'), ('[0.9,0.1,0]');
CREATE INDEX items_hnsw ON items USING hnsw (embedding vector_l2_ops);

SELECT id FROM items ORDER BY embedding <-> '[1,0,0]' LIMIT 1;
```

`<->` is the Euclidean distance, so the nearest row comes first, and the query returns id `1`. The index is an HNSW index: HNSW (hierarchical navigable small world) is a graph of the vectors in layers, which finds near neighbours without comparing the query with every row.

## Keyword Ranking with pg_textsearch

This creates a table of three texts with a BM25 index and returns the best match for `ranking function`:

```sql
CREATE TABLE docs (id int primary key, content text);
INSERT INTO docs VALUES
  (1, 'PostgreSQL is a powerful database system'),
  (2, 'BM25 is an effective ranking function'),
  (3, 'Full text search with custom scoring');
CREATE INDEX docs_bm25 ON docs USING bm25(content) WITH (text_config='english');

SELECT id FROM docs ORDER BY content <@> 'ranking function' LIMIT 1;
```

Ordering by `content <@> 'query'` puts the best BM25 match first, so the query returns id `2`. pg_textsearch works only when PostgreSQL preloads it, and odctl's compose file sets `shared_preload_libraries` to do that.

`psql` shows each query's result:

To use the extensions in another database, run `CREATE EXTENSION vector;` or `CREATE EXTENSION pg_textsearch;` there.

## From Another Container

Inside the [`odctl` network](https://jaehyeon.me/odctl/latest/how-it-works/#how-you-reach-a-service), connect to `postgres:5432` with the same user and password, for example `postgresql://user:password@postgres:5432/vector`.

## Runnable Example

Save this file as `example.sh` and run it with `bash example.sh` in the folder that holds your `.odctl` workspace. It runs both queries on tables named `demo_items` and `demo_docs`, which it drops and creates again on every run:

```bash
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
```

It prints the statements' results, with id `1` from the vector query and id `2` from the BM25 query. The BM25 index build also prints `NOTICE` lines.
