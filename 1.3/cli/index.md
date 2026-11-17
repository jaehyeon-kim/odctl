# CLI Reference

This page holds the output of `odctl --help` and of `odctl <command> --help`, captured when the site was built.

## odctl

```text
Usage: odctl [OPTIONS] COMMAND [ARGS]...

 odctl: run an open data stack on your machine, with its services already
 connected, from one command.

 Commands list the profiles, start and stop them with Docker Compose, and show
 what is running.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --install-completion          Install completion for the current shell.      │
│ --show-completion             Show completion for the current shell, to copy │
│                               it or customize the installation.              │
│ --help                        Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Global Options ─────────────────────────────────────────────────────────────╮
│ --verbose                    Enable debug-level logging across all commands. │
│ --workspace  -w      <path>  Path to the odctl workspace directory (default: │
│                              ./.odctl).                                      │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Inspection & Info ──────────────────────────────────────────────────────────╮
│ list      List all available profiles and their capabilities.                │
│ explain   Explain the details, services, images, and dependencies of a       │
│           profile.                                                           │
│ ps        List Docker containers managed by the Open Data Stack.             │
│ info      Show the installed odctl version and whether Docker is reachable.  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Workspace ──────────────────────────────────────────────────────────────────╮
│ init      Initialize a local .odctl workspace for custom configurations.     │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Cluster Lifecycle ──────────────────────────────────────────────────────────╮
│ pull      Pre-fetch Docker images without starting the containers.           │
│ up        Launch Open Data profiles.                                         │
│ down      Stop and remove profile containers and networks.                   │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Management ─────────────────────────────────────────────────────────────────╮
│ logs      Fetch the logs of containers managed by specific profiles.         │
│ restart   Restart one or more specific profiles.                             │
│ recreate  Replace one or more profiles' containers, applying compose file    │
│           changes.                                                           │
╰──────────────────────────────────────────────────────────────────────────────╯

 Examples:

   # View all profiles and exposed ports

   $ odctl list -d


   # See exactly what the kafka-lite profile provisions

   $ odctl explain kafka-lite


   # Launch specific profiles and their dependencies

   $ odctl up flink-lite kafka-lite spark-lite


   # Complete teardown and wipe all data

   $ odctl down --all --volumes
```

## odctl list

```text
Usage: odctl list [OPTIONS]

 List all available profiles and their capabilities.

 A profile is a specific capability or technology (for example, `kafka-lite`,
 `spark-lite`, `airflow`)
 provided by the Open Data Stack. This command lists them alongside their
 parent stack.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --details  -d        Inspect docker-compose files to show exact services and │
│                      exposed host ports.                                     │
│ --help               Show this message and exit.                             │
╰──────────────────────────────────────────────────────────────────────────────╯

 Examples:

   # View all basic profiles

   $ odctl list


   # View profiles, underlying services, and ports

   $ odctl list -d
```

## odctl explain

```text
Usage: odctl explain [OPTIONS] {profile}

 Explain the details, services, images, and dependencies of a profile.

 Displays a detailed breakdown of what a profile provisions, its container
 images,
 exposed host ports, and any prerequisite profiles it depends on.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    profile      <str>  The target profile to inspect (for example,         │
│                          'airflow', 'kafka-lite').                           │
│                          [required]                                          │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯

 Examples:

   # See what the Spark profile provisions

   $ odctl explain spark-lite
```

## odctl init

```text
Usage: odctl init [OPTIONS]

 Initialize a local .odctl workspace for custom configurations.

 Copies the bundled docker-compose files, configs, and `.env` template into a
 local `./.odctl/` directory. You can then edit these files directly to
 customize the stack.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --force  -f        Wipe out the existing workspace and recreate it from      │
│                    scratch.                                                  │
│ --yes    -y        Answer yes to the confirmation prompt, for scripts and    │
│                    CI.                                                       │
│ --help             Show this message and exit.                               │
╰──────────────────────────────────────────────────────────────────────────────╯

 Examples:

   # Initialize a new workspace in ./.odctl/

   $ odctl init


   # Recreate workspace, overwriting any local changes

   $ odctl init --force


   # The same, without the prompt, as in a script

   $ odctl init --force --yes
```

## odctl pull

```text
Usage: odctl pull [OPTIONS] [profiles]...

 Pre-fetch Docker images without starting the containers.

 Useful for downloading heavy images (like Spark, Flink, Kafka) ahead of time,
 or for fetching a tag that changed in the registry before launching.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   profiles      <str>  Specific profiles to pull images for.                 │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --all   -a        Pull images for ALL available profiles in the registry.    │
│ --help            Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯

 Examples:

   # Pre-fetch images for all profiles

   $ odctl pull --all


   # Pre-fetch images just for Flink and Kafka

   $ odctl pull flink-lite kafka-lite
```

## odctl up

```text
Usage: odctl up [OPTIONS] {profiles}...

 Launch Open Data profiles.

 Resolves dependencies for the requested profiles and brings up the required
 Docker Compose stacks in the correct topological order.

 Refuses to start if the images for the resolved TAG are not published,
 naming the tag rather than leaving Docker to report a missing manifest.
 Warns about any service whose declared profile belongs to another compose
 file, since the planner will never start it.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    profiles      <str>  One or more profiles to launch (for example,       │
│                           'ch-lite', 'kafka-lite').                          │
│                           [required]                                         │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --dry-run          Preview the execution plan without actually starting      │
│                    anything.                                                 │
│ --pull             Pull the images again before starting, to fetch a tag     │
│                    that changed in the registry.                             │
│ --help             Show this message and exit.                               │
╰──────────────────────────────────────────────────────────────────────────────╯

 Examples:

   # Launch Clickhouse, Flink, and their dependencies

   $ odctl up ch-lite flink-lite


   # Preview what would be launched for Airflow

   $ odctl up airflow --dry-run


   # Pull the images again before launching

   $ odctl up kafka-lite --pull
```

## odctl down

```text
Usage: odctl down [OPTIONS] [profiles]...

 Stop and remove profile containers and networks.

 Tears down the requested profiles. Data kept inside a container is removed
 with it.
 Unnamed volumes stay on disk, unused.
 Use --volumes to also remove the volumes, such as the shared jar volume.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   profiles      <str>  Specific profiles to stop.                            │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --all      -a        Stop ALL running profiles.                              │
│ --volumes  -v        Also remove named volumes, including the shared jar     │
│                      volume once no other profile uses it.                   │
│ --dry-run            Preview the teardown plan without actually stopping     │
│                      anything.                                               │
│ --yes      -y        Answer yes to the confirmation prompt, for scripts and  │
│                      CI.                                                     │
│ --help               Show this message and exit.                             │
╰──────────────────────────────────────────────────────────────────────────────╯

 Examples:

   # Stop specific profile(s)

   $ odctl down kafka-lite


   # Stop all running profiles

   $ odctl down --all


   # Complete teardown and wipe all data

   $ odctl down --all -v


   # The same, without the prompt, as in a script

   $ odctl down --all -v --yes
```

## odctl ps

```text
Usage: odctl ps [OPTIONS] [profiles]...

 List Docker containers managed by the Open Data Stack.

 Filters out system containers and only shows those belonging to requested
 profiles.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   profiles      <str>  Specific profiles to inspect.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --all   -a        Show all containers managed by odctl.                      │
│ --help            Show this message and exit.                                │
╰──────────────────────────────────────────────────────────────────────────────╯

 Examples:

   # Show all running containers managed by odctl

   $ odctl ps --all


   # Show containers just for specific profiles

   $ odctl ps kafka-lite spark-lite
```

## odctl info

```text
Usage: odctl info [OPTIONS]

 Show the installed odctl version and whether Docker is reachable.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## odctl logs

```text
Usage: odctl logs [OPTIONS] {profiles}...

 Fetch the logs of containers managed by specific profiles.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    profiles      <str>  Profiles to fetch logs for. [required]             │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --service     -s      <str>  Filter to a specific compose service (Use       │
│                              'odctl ps' to find names).                      │
│ --follow      -f             Follow log output in real-time.                 │
│ --tail        -n      <str>  Number of lines to show from the end of the     │
│                              logs.                                           │
│                              [default: all]                                  │
│ --timestamps  -t             Show timestamps.                                │
│ --since               <str>  Show logs since timestamp or relative (for      │
│                              example '42m').                                 │
│ --until               <str>  Show logs before a timestamp or relative.       │
│ --help                       Show this message and exit.                     │
╰──────────────────────────────────────────────────────────────────────────────╯

 Examples:

   # Tail the last 50 lines of all Flink containers and follow live

   $ odctl logs flink-lite -n 50 -f


   # View logs strictly for the JobManager service

   $ odctl logs flink-lite -s jobmanager


   # Show logs with timestamps for the last 10 minutes

   $ odctl logs kafka-lite --since 10m -t
```

## odctl restart

```text
Usage: odctl restart [OPTIONS] {profiles}...

 Restart one or more specific profiles.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    profiles      <str>  Profiles to restart. [required]                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## odctl recreate

```text
Usage: odctl recreate [OPTIONS] {profiles}...

 Replace one or more profiles' containers, applying compose file changes.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    profiles      <str>  Profiles to recreate. [required]                   │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --pull          Pull images before recreating.                               │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```
