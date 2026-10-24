# Troubleshooting

## Containers Exit or Docker Runs Out of Memory

Each service has a memory limit, listed on its [profile page](profiles/index.md). The limits of everything you start add up, and Docker needs that much memory available. Give Docker the memory that [Getting Started](getting-started.md#requirements) names, start fewer profiles at once, or choose a lite profile over a full one. To lower a limit, edit `mem_limit` in the compose file in `.odctl` and run `odctl recreate <profile>`, as [How It Works](how-it-works.md#examples) shows for SeaweedFS.

## Uploads Fail with HTTP 500 and Seaweed Exited with Code 137

`seaweed` reached its memory limit while it buffered a large upload, and the kernel killed it. The client sees HTTP 500 and every profile that uses S3 loses its storage until the container starts again. `docker inspect seaweed --format '{{.State.OOMKilled}}'` prints `true` after such a kill. A model or file of several hundred MB can reach the limit. Raise `mem_limit` and `GOMEMLIMIT` together, as [How It Works](how-it-works.md#examples) shows for 2 GB. A workspace made by a release before `GOMEMLIMIT` was added lacks it until you run `odctl init --force`, which [Start Again](how-it-works.md#start-again) describes.

## A Port Is Already in Use

Every service publishes fixed host ports, listed on its profile page. If another program holds one, `odctl up` fails to start that service. Stop the other program, or change the host side of the port mapping in `.odctl/compose-*.yml` and run `odctl recreate <profile>`, as [How It Works](how-it-works.md#examples) shows for Trino. Containers still reach each other on their internal ports, so only clients on your host need the new port.

## Use 127.0.0.1, Not localhost

Host addresses in `odctl explain` and on these pages use `127.0.0.1`. With IPv6 enabled in Docker, `localhost` can resolve to a service's IPv6 address, and services that listen on IPv4 only reset the connection. `localhost` works when Docker's IPv6 is off.

## No Published Image for a TAG

`odctl up` checks the images odctl builds before it starts anything. If the registry says an image for the resolved `TAG` does not exist, it stops with `No published image for TAG=...` and lists the missing images. An image already on your machine passes without a registry call. If the registry cannot be reached, odctl starts anyway and Docker reports what it finds.

The usual causes are a CLI version whose images are not published yet, or a `TAG` in `.odctl/.env` that you changed by hand. Set `TAG` to a published version in `.odctl/.env`, or install a CLI version whose images exist.

## Workspace TAG Differs from the CLI Version

After you upgrade the CLI, every command except `odctl init` warns that `.odctl/.env` sets an older `TAG`. The workspace keeps the old profiles, images and compose files until you run `odctl init --force`. [Start Again](how-it-works.md#start-again) says what that command removes.

## A Service Is Up but Does Not Work

`odctl logs <profile>` shows the logs of a profile's containers. Add `-s <service>` for one service, or `-f` to follow them. `odctl ps --all` shows every container odctl manages and its state.

## Older Messages Are Missing

The Kafka brokers delete old messages, so a consumer that starts from the beginning of a topic sees only what is left. [Keep Messages Longer](guides/kafka.md#keep-messages-longer) gives the limits, shows how to read them and shows how to set `retention.ms` and `retention.bytes` to `-1` on a topic that must keep everything.
