# Troubleshooting

## Containers exit or Docker runs out of memory

Each service has a memory limit, listed on its [profile page](https://jaehyeon.me/odctl/latest/profiles/index.md). The limits of everything you start add up, and Docker needs that much memory available. Give Docker 8 to 16 GB, start fewer profiles at once, or choose a lite profile over a full one. To lower a limit, edit `mem_limit` in the compose file in `.odctl` and run `odctl recreate <profile>`.

## Uploads fail with HTTP 500 and seaweed exited with code 137

`seaweed` reached its memory limit while it buffered a large upload, and the kernel killed it. The client sees HTTP 500 and every profile that uses S3 loses its storage until the container starts again. `docker inspect seaweed --format '{{.State.OOMKilled}}'` prints `true` after such a kill. odctl sets `GOMEMLIMIT` in `compose-infra.yml` to three quarters of `mem_limit`, so SeaweedFS collects garbage more often as it nears the limit; a workspace made by an earlier release lacks it until `odctl init --force`. A model or file of several hundred MB can still reach the limit. Raise `mem_limit` and `GOMEMLIMIT` together, as [How it works](https://jaehyeon.me/odctl/latest/how-it-works/#examples) shows for 2 GB, and run `odctl recreate storage`.

## A port is already in use

Every service publishes fixed host ports, listed on its profile page. If another program holds one, `odctl up` fails to start that service. Stop the other program, or change the host side of the port mapping in `.odctl/compose-*.yml` and run `odctl recreate <profile>`. Containers still reach each other on their internal ports, so only clients on your host need the new port.

## Use 127.0.0.1, not localhost

Host addresses in `odctl explain` and on these pages use `127.0.0.1`. With IPv6 enabled in Docker, `localhost` can resolve to a service's IPv6 address, and services that listen on IPv4 only reset the connection. `localhost` works when Docker's IPv6 is off.

## No published image for a TAG

`odctl up` checks the images odctl builds before it starts anything. If the registry says an image for the resolved `TAG` does not exist, it stops with `No published image for TAG=...` and lists the missing images. An image already on your machine passes without a registry call. If the registry cannot be reached, odctl starts anyway and Docker reports what it finds.

The usual causes are a CLI version whose images are not published yet, or a `TAG` in `.odctl/.env` that you changed by hand. Set `TAG` to a published version in `.odctl/.env`, or install a CLI version whose images exist.

## Workspace TAG differs from the CLI version

After you upgrade the CLI, every command except `odctl init` warns that `.odctl/.env` sets an older `TAG`. The workspace keeps the old profiles, images and compose files until you run `odctl init --force`, which also resets your edits.

## A service is up but does not work

`odctl logs <profile>` shows the logs of a profile's containers. Add `-s <service>` for one service, or `-f` to follow them. `odctl ps --all` shows every container odctl manages and its state.

## Older messages are missing

The Kafka brokers delete messages after one day, or when a partition passes 500 MB. A consumer that starts from the beginning of a topic sees only what is left. [Keep messages longer](https://jaehyeon.me/odctl/latest/guides/kafka/#keep-messages-longer) shows how to read these limits and how to set `retention.ms` and `retention.bytes` to `-1` on a topic that must keep everything.
