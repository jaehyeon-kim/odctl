# valkey-ttl-check

Answer sheet of the case `valkey-ttl-check`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A10 (a check that cannot fail), A3 (address or login from the wrong side, or guessed), A8 (stack setting assumed).

## Records

- planning `odctl/release/1.2.0/review-batch1.md:11` (R1 1): a check that could not fail (A10).
- planning `architecting-analytics/review-labs.md:39` (HIGH 1): host names and logins that do not exist (A3).
- planning `architecting-analytics/validation-live-stack.md:147`: a service's access setting assumed (A8).

## Right answer

- From the host: `127.0.0.1:6379`, user `user`, password `password` (`registry.yml:165-167`; `docs/guides/valkey.md:15-17`).
- The `default` user is off (`compose-store.yml:106-109`; `docs/guides/valkey.md:24`), so the client passes both: `valkey.Valkey(host="127.0.0.1", port=6379, username="user", password="password")` (valkey-io/valkey-py tag `v6.1.1`, `valkey/client.py:172-212`, which has `username` and `password`), or `valkey.from_url("valkey://user:password@127.0.0.1:6379")` (`valkey/connection.py:978`). With a password alone the client sends `AUTH <password>`, which logs in as `default` (valkey.io, AUTH), and that user is off.
- `TTL` answers `-2` when the key does not exist and `-1` when it has no expiry (valkey.io, TTL). The check exits 0 only when the answer is above 0 and at most 1800 (0 is also accepted: the key expires within the second); it exits 1 for `-2`, `-1`, a larger value and any error, including a refused connection.
- A check with only an upper bound (`ttl <= 1800`) passes for `-1` and `-2`, so it cannot fail when the key is missing or never expires.

## Wrong answers seen or expected

- A10: `ttl <= 1800` alone, `ttl != 0`, `exists` alone, or an error caught and turned into exit 0.
- A3: `valkey:6379` from the laptop; a login other than `user` / `password`.
- A8: a client with a password and no user name, or no login at all, stated to work.
