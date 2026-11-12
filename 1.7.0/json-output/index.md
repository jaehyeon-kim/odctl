# JSON Output

`odctl list`, `odctl explain`, `odctl ps` and `odctl info` print one JSON document with `--json`, for scripts and AI assistants. The `list`, `explain`, `ps` and `info` tools of the [MCP server](https://jaehyeon.me/odctl/latest/guides/mcp-server/index.md) return the same documents. This page holds the JSON Schema of each document, captured when the site was built. A JSON Schema lists the keys of a document, the type of each value and which keys are always present. Standard output holds only the JSON document. Warnings and errors go to standard error. A usage error, such as an unknown option, exits with code 2. Any other failure exits with code 1 and prints nothing on standard output. [What Stays Stable in 1.x](https://jaehyeon.me/odctl/latest/how-it-works/#what-stays-stable-in-1x) says which changes to these keys wait for 2.0.

## odctl list

`odctl list --json` prints an array with one object for each profile, sorted by profile name. Its schema:

```json
{
  "$defs": {
    "Port": {
      "properties": {
        "host": {
          "description": "The port on the host, a number.",
          "title": "Host",
          "type": "integer"
        },
        "container": {
          "description": "The port inside the container, a number.",
          "title": "Container",
          "type": "integer"
        },
        "protocol": {
          "default": "tcp",
          "description": "The transport protocol, `tcp` or `udp`, as Docker or the compose file gives it.",
          "title": "Protocol",
          "type": "string"
        }
      },
      "required": [
        "host",
        "container",
        "protocol"
      ],
      "title": "Port",
      "type": "object"
    },
    "ProfileInfo": {
      "properties": {
        "profile": {
          "description": "The profile name, which `odctl up` takes.",
          "title": "Profile",
          "type": "string"
        },
        "stack": {
          "description": "The stack the profile belongs to, such as `kafka` for `kafka-lite`. When the registry gives the stack a `parent` group, the value is that group instead, such as `infra` for `postgres`, `storage` and `catalog`.",
          "title": "Stack",
          "type": "string"
        },
        "description": {
          "description": "What the stack provides.",
          "title": "Description",
          "type": "string"
        },
        "compose_file": {
          "description": "The compose file that defines the profile's services.",
          "title": "Compose File",
          "type": "string"
        },
        "depends_on": {
          "description": "The profiles the registry lists as direct prerequisites, sorted by name. Empty when there are none.",
          "items": {
            "type": "string"
          },
          "title": "Depends On",
          "type": "array"
        },
        "starts": {
          "description": "Every profile `odctl up` starts for this one: the profile itself and all its prerequisites, sorted by name.",
          "items": {
            "type": "string"
          },
          "title": "Starts",
          "type": "array"
        },
        "services": {
          "description": "The services the profile starts, sorted by name.",
          "items": {
            "$ref": "#/$defs/ServiceInfo"
          },
          "title": "Services",
          "type": "array"
        }
      },
      "required": [
        "profile",
        "stack",
        "description",
        "compose_file",
        "depends_on",
        "starts",
        "services"
      ],
      "title": "ProfileInfo",
      "type": "object"
    },
    "ServiceInfo": {
      "properties": {
        "name": {
          "description": "The compose service name.",
          "title": "Name",
          "type": "string"
        },
        "image": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "The image as it will run, with `TAG` resolved. `null` when the compose file gives the service no `image`, as for a service that is built.",
          "title": "Image"
        },
        "ports": {
          "description": "The ports the service publishes on the host, sorted by host port. Compose variables are expanded first, as compose does. A port range is left out, and so is a port with no host part, which compose publishes on a random host port. Empty when the service publishes none.",
          "items": {
            "$ref": "#/$defs/Port"
          },
          "title": "Ports",
          "type": "array"
        }
      },
      "required": [
        "name",
        "image",
        "ports"
      ],
      "title": "ServiceInfo",
      "type": "object"
    }
  },
  "items": {
    "$ref": "#/$defs/ProfileInfo"
  },
  "type": "array"
}
```

## odctl explain

`odctl explain --json` prints one object for the profile you name. Its schema:

```json
{
  "$defs": {
    "Port": {
      "properties": {
        "host": {
          "description": "The port on the host, a number.",
          "title": "Host",
          "type": "integer"
        },
        "container": {
          "description": "The port inside the container, a number.",
          "title": "Container",
          "type": "integer"
        },
        "protocol": {
          "default": "tcp",
          "description": "The transport protocol, `tcp` or `udp`, as Docker or the compose file gives it.",
          "title": "Protocol",
          "type": "string"
        }
      },
      "required": [
        "host",
        "container",
        "protocol"
      ],
      "title": "Port",
      "type": "object"
    },
    "ServiceInfo": {
      "properties": {
        "name": {
          "description": "The compose service name.",
          "title": "Name",
          "type": "string"
        },
        "image": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "The image as it will run, with `TAG` resolved. `null` when the compose file gives the service no `image`, as for a service that is built.",
          "title": "Image"
        },
        "ports": {
          "description": "The ports the service publishes on the host, sorted by host port. Compose variables are expanded first, as compose does. A port range is left out, and so is a port with no host part, which compose publishes on a random host port. Empty when the service publishes none.",
          "items": {
            "$ref": "#/$defs/Port"
          },
          "title": "Ports",
          "type": "array"
        }
      },
      "required": [
        "name",
        "image",
        "ports"
      ],
      "title": "ServiceInfo",
      "type": "object"
    }
  },
  "properties": {
    "profile": {
      "description": "The profile name, which `odctl up` takes.",
      "title": "Profile",
      "type": "string"
    },
    "stack": {
      "description": "The stack the profile belongs to, such as `kafka` for `kafka-lite`. When the registry gives the stack a `parent` group, the value is that group instead, such as `infra` for `postgres`, `storage` and `catalog`.",
      "title": "Stack",
      "type": "string"
    },
    "description": {
      "description": "What the stack provides.",
      "title": "Description",
      "type": "string"
    },
    "compose_file": {
      "description": "The compose file that defines the profile's services.",
      "title": "Compose File",
      "type": "string"
    },
    "depends_on": {
      "description": "The profiles the registry lists as direct prerequisites, sorted by name. Empty when there are none.",
      "items": {
        "type": "string"
      },
      "title": "Depends On",
      "type": "array"
    },
    "starts": {
      "description": "Every profile `odctl up` starts for this one: the profile itself and all its prerequisites, sorted by name.",
      "items": {
        "type": "string"
      },
      "title": "Starts",
      "type": "array"
    },
    "services": {
      "description": "The services the profile starts, sorted by name.",
      "items": {
        "$ref": "#/$defs/ServiceInfo"
      },
      "title": "Services",
      "type": "array"
    },
    "usage": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "The text that says how to reach the profile's services. `null` when the registry has none for this profile.",
      "title": "Usage"
    },
    "role": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "What the profile's stack does in a data platform. `null` when the registry gives none.",
      "title": "Role"
    },
    "volumes": {
      "description": "The named volumes the profile's services mount, sorted by name. Bind mounts are left out, and so are volumes the compose file declares as `external`, so `odctl-shared-deps` appears only for the `deps` profile. Empty when there are none.",
      "items": {
        "type": "string"
      },
      "title": "Volumes",
      "type": "array"
    }
  },
  "required": [
    "profile",
    "stack",
    "description",
    "compose_file",
    "depends_on",
    "starts",
    "services",
    "usage",
    "role",
    "volumes"
  ],
  "title": "ProfileDetails",
  "type": "object"
}
```

## odctl ps

`odctl ps --json` prints one object with the active profiles and the matching containers. Its schema:

```json
{
  "$defs": {
    "ContainerInfo": {
      "properties": {
        "name": {
          "description": "The container name.",
          "title": "Name",
          "type": "string"
        },
        "service": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "The compose service. `null` when the container has no compose service label.",
          "title": "Service"
        },
        "state": {
          "description": "The state as Docker reports it, for example `running` or `exited`.",
          "title": "State",
          "type": "string"
        },
        "health": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "The health status as Docker reports it, for example `healthy`. `null` when the container has no health check.",
          "title": "Health"
        },
        "ports": {
          "description": "The ports published on the host, sorted by host port, then container port and protocol. Empty when the container publishes none.",
          "items": {
            "$ref": "#/$defs/Port"
          },
          "title": "Ports",
          "type": "array"
        }
      },
      "required": [
        "name",
        "service",
        "state",
        "health",
        "ports"
      ],
      "title": "ContainerInfo",
      "type": "object"
    },
    "Port": {
      "properties": {
        "host": {
          "description": "The port on the host, a number.",
          "title": "Host",
          "type": "integer"
        },
        "container": {
          "description": "The port inside the container, a number.",
          "title": "Container",
          "type": "integer"
        },
        "protocol": {
          "default": "tcp",
          "description": "The transport protocol, `tcp` or `udp`, as Docker or the compose file gives it.",
          "title": "Protocol",
          "type": "string"
        }
      },
      "required": [
        "host",
        "container",
        "protocol"
      ],
      "title": "Port",
      "type": "object"
    }
  },
  "properties": {
    "active_profiles": {
      "description": "The profiles whose services are all running, sorted. Only the profiles the command names are considered, with their prerequisites in the same compose file, such as `postgres` and `storage` for `catalog`. With `--all`, every profile is considered. `deps` is never listed. A profile whose services are a strict subset of another listed profile's is left out, so `spark-lite` is not listed beside `spark-full`. Empty when no profile is fully running.",
      "items": {
        "type": "string"
      },
      "title": "Active Profiles",
      "type": "array"
    },
    "containers": {
      "description": "The matching containers, sorted by name. Empty when none match.",
      "items": {
        "$ref": "#/$defs/ContainerInfo"
      },
      "title": "Containers",
      "type": "array"
    }
  },
  "required": [
    "active_profiles",
    "containers"
  ],
  "title": "PsReport",
  "type": "object"
}
```

## odctl info

`odctl info --json` prints one object with the CLI version, the image tag, the workspace, Docker and odctl's own images. Its schema:

```json
{
  "$defs": {
    "DockerInfo": {
      "properties": {
        "reachable": {
          "description": "Whether the daemon answers.",
          "title": "Reachable",
          "type": "boolean"
        }
      },
      "required": [
        "reachable"
      ],
      "title": "DockerInfo",
      "type": "object"
    },
    "ImageInfo": {
      "properties": {
        "reference": {
          "description": "The full image reference, with its tag.",
          "title": "Reference",
          "type": "string"
        },
        "local": {
          "description": "Whether the image is already on the Docker host. `false` when Docker is not reachable.",
          "title": "Local",
          "type": "boolean"
        }
      },
      "required": [
        "reference",
        "local"
      ],
      "title": "ImageInfo",
      "type": "object"
    },
    "WorkspaceInfo": {
      "properties": {
        "path": {
          "description": "The workspace path, an absolute path.",
          "title": "Path",
          "type": "string"
        },
        "exists": {
          "description": "Whether the folder exists. When it does not, odctl reads the files bundled with the CLI.",
          "title": "Exists",
          "type": "boolean"
        },
        "stale_tag": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "The workspace's `TAG` when it differs from the CLI version and no `TAG` is set in the shell. Otherwise `null`.",
          "title": "Stale Tag"
        }
      },
      "required": [
        "path",
        "exists",
        "stale_tag"
      ],
      "title": "WorkspaceInfo",
      "type": "object"
    }
  },
  "properties": {
    "cli_version": {
      "description": "The installed odctl version.",
      "title": "Cli Version",
      "type": "string"
    },
    "tag": {
      "description": "`TAG` as Docker Compose resolves it.",
      "title": "Tag",
      "type": "string"
    },
    "workspace": {
      "$ref": "#/$defs/WorkspaceInfo",
      "description": "The workspace folder."
    },
    "docker": {
      "$ref": "#/$defs/DockerInfo",
      "description": "The Docker daemon."
    },
    "images": {
      "description": "odctl's own images at `tag` for every profile, sorted by reference.",
      "items": {
        "$ref": "#/$defs/ImageInfo"
      },
      "title": "Images",
      "type": "array"
    }
  },
  "required": [
    "cli_version",
    "tag",
    "workspace",
    "docker",
    "images"
  ],
  "title": "Info",
  "type": "object"
}
```
