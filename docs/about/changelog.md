# Changelog

Each release, newest first: what changed, then under Upgrading what to change in commands, workspaces or clients that use the previous release. Releases up to 1.0.2 are described on [GitHub Releases](https://github.com/jaehyeon-kim/odctl/releases).

## Version 1.1.0

Every service is now reachable from your machine only, and the docs have a [Roadmap](roadmap.md) and a [Changelog](changelog.md).

- Every published port binds to `127.0.0.1`, on macOS, Linux and WSL2, so other machines on your network cannot reach the services. [How you reach a service](../how-it-works.md#how-you-reach-a-service) says how to open a port when you need to.
- Kafka no longer publishes ports 29092, 29093 and 29094, which were listeners for a minikube cluster.
- An odctl skill and `llms.txt` help an AI assistant choose a profile and reach its services. See [Use it with an AI assistant](../getting-started.md#use-it-with-an-ai-assistant).
- Eight guides show in a diagram how data moves between their services, and [How it works](../how-it-works.md) shows what `odctl up` checks and the order it starts services in. The end-to-end tests run every command the guides show.
- The tables of `odctl ps` and `odctl explain` draw straight right borders on rows with port mappings.
- `odctl down --help` says what `--volumes` removes.

### Upgrading

- To reach a service from another machine, run `odctl init`, remove `127.0.0.1:` from the service's port line in `.odctl/compose-*.yml`, and run `odctl recreate <profile>`.
- A Kafka client in minikube cannot use `host.minikube.internal:29092` any more. Add a listener for it to the Kafka service in `.odctl/compose-kafka.yml`.
- A workspace made by `odctl init` with an earlier release keeps its old compose files, which publish on all interfaces and include port 29092. Run `odctl init --force` to copy the new files; it replaces your edits.
