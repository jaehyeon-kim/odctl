# Troubleshooting

## Containers exit or Docker runs out of memory

Each service has a memory limit, listed on its [profile page](profiles/index.md). The limits of everything you start add up, and Docker needs that much memory available. Give Docker 8 to 16 GB, start fewer profiles at once, or choose a lite profile over a full one. To lower a limit, edit `mem_limit` in the compose file in `.odctl` and run `odctl recreate <profile>`.

## A port is already in use

Every service publishes fixed host ports, listed on its profile page. If another program holds one, `odctl up` fails to start that service. Stop the other program, or change the host side of the port mapping in `.odctl/compose-*.yml` and run `odctl recreate <profile>`. Containers still reach each other on their internal ports, so only clients on your host need the new port.

## Use 127.0.0.1, not localhost

Host addresses in `odctl explain` and on these pages use `127.0.0.1`. With IPv6 enabled in Docker, `localhost` can resolve to a service's IPv6 address, and services that listen on IPv4 only reset the connection. `localhost` works when Docker's IPv6 is off.

## No published image for a TAG

`odctl up` checks the images odctl builds before it starts anything. If the registry says an image for the resolved `TAG` does not exist, it stops with `No published image for TAG=...` and lists the missing images. An image already on your machine passes without a registry call. If the registry cannot be reached, odctl starts anyway and Docker reports what it finds.

The usual causes are a CLI version whose images are not published yet, or a `TAG` in `.odctl/.env` that you changed by hand. Set `TAG` to a published version in `.odctl/.env`, or install a CLI version whose images exist.

## Workspace TAG differs from the CLI version

After you upgrade the CLI, every command except `odctl init` warns that `.odctl/.env` sets an older `TAG`. The workspace keeps the old profiles, images and compose files until you run `odctl init --force`, which also resets your edits.

## After an upgrade, a connector or job runs an old version

The shared jar volume, `odctl-shared-deps`, keeps jars from earlier odctl versions. An upgrade adds the new jars beside the old ones, and a service can load the old one. For example, after upgrading to 1.0.0, Kafka Connect loaded Debezium 3.5.1 instead of 3.7.0. Remove the volume, and the next `odctl up` fills it again with only the current jars:

```bash
odctl down --all --volumes
odctl up <profiles>
```

`odctl down` removes your data anyway, so removing the volume costs only the time to copy the jars again. [Issue #126](https://github.com/jaehyeon-kim/odctl/issues/126) tracks the fix.

Without a workspace, odctl runs its own images tagged `latest`, and Docker does not pull an image it already has. An older `latest` from before the upgrade then keeps running. Run `odctl init` to use images tagged with the CLI version, or add `--pull` to `odctl up` to fetch `latest` again. [Issue #127](https://github.com/jaehyeon-kim/odctl/issues/127) tracks this.

## A service is up but does not work

`odctl logs <profile>` shows the logs of a profile's containers. Add `-s <service>` for one service, or `-f` to follow them. `odctl ps --all` shows every container odctl manages and its state.
