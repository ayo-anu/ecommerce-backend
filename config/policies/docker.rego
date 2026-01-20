
package docker

import future.keywords.contains
import future.keywords.if
import future.keywords.in

deny[msg] {
    input[i].Cmd == "run"
    val := input[i].Value[_]
    contains(lower(val), "--privileged")
    msg := sprintf("Line %d: Privileged mode is not allowed for security reasons", [i])
}

deny[msg] {
    not user_defined
    msg := "Dockerfile must specify a non-root USER (e.g., USER appuser)"
}

user_defined {
    input[_].Cmd == "user"
    input[_].Value[_] != "root"
    input[_].Value[_] != "0"
}

deny[msg] {
    not healthcheck_defined
    msg := "Dockerfile must include a HEALTHCHECK instruction for container monitoring"
}

healthcheck_defined {
    input[_].Cmd == "healthcheck"
}

deny[msg] {
    input[i].Cmd == "from"
    val := input[i].Value[_]
    contains(val, ":latest")
    msg := sprintf("Line %d: Using 'latest' tag is not allowed - use specific versions (e.g., :3.11-slim)", [i])
}

deny[msg] {
    input[i].Cmd == "from"
    val := input[i].Value[_]
    not contains(val, ":")
    not contains(val, "@sha256:")
    msg := sprintf("Line %d: Base image '%s' must specify an explicit tag or digest", [i, val])
}

deny[msg] {
    input[i].Cmd == "from"
    val := input[i].Value[_]
    image_parts := split(val, ":")
    image_name := image_parts[0]
    not approved_image(image_name)
    msg := sprintf("Line %d: Base image '%s' is not approved. Approved images: python:3.11-slim*, nginx:*-alpine*, postgres:*-alpine*, redis:*-alpine*", [i, image_name])
}

approved_image(image) {
    startswith(image, "python:3.11-slim")
}

approved_image(image) {
    startswith(image, "python:3.11-alpine")
}

approved_image(image) {
    startswith(image, "nginx:")
    contains(image, "alpine")
}

approved_image(image) {
    startswith(image, "postgres:")
    contains(image, "alpine")
}

approved_image(image) {
    startswith(image, "redis:")
    contains(image, "alpine")
}

approved_image(image) {
    startswith(image, "hashicorp/vault:")
}

approved_image(image) {
    image == "scratch"
}


warn[msg] {
    input[i].Cmd == "run"
    val := input[i].Value[_]
    contains(lower(val), "pip install")
    not contains(val, "==")
    not contains(val, "-r")
    msg := sprintf("Line %d: Consider pinning pip package versions with '==' for reproducibility", [i])
}

warn[msg] {
    input[i].Cmd == "copy"
    not has_chown_flag(input[i])
    msg := sprintf("Line %d: Consider using --chown flag with COPY for proper file ownership", [i])
}

has_chown_flag(instruction) {
    instruction.Flags[_] == "--chown"
}

warn[msg] {
    input[i].Cmd == "run"
    val := input[i].Value[_]
    contains(lower(val), "curl")
    not contains(lower(val), "rm")
    msg := sprintf("Line %d: Consider cleaning up downloaded files after use", [i])
}

warn[msg] {
    not expose_defined
    msg := "Consider adding EXPOSE directive to document which ports the container listens on"
}

expose_defined {
    input[_].Cmd == "expose"
}


lower(s) = output {
    output := lower(s)
}
