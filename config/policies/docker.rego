# OPA policy: Dockerfile security.

package docker

import future.keywords.contains
import future.keywords.if
import future.keywords.in

# Deny privileged containers
deny[msg] {
    input[i].Cmd == "run"
    val := input[i].Value[_]
    contains(lower(val), "--privileged")
    msg := sprintf("Line %d: Privileged mode is not allowed for security reasons", [i])
}

# Deny root user - require USER directive
deny[msg] {
    not user_defined
    msg := "Dockerfile must specify a non-root USER (e.g., USER appuser)"
}

user_defined {
    input[_].Cmd == "user"
    input[_].Value[_] != "root"
    input[_].Value[_] != "0"
}

# Require health check
deny[msg] {
    not healthcheck_defined
    msg := "Dockerfile must include a HEALTHCHECK instruction for container monitoring"
}

healthcheck_defined {
    input[_].Cmd == "healthcheck"
}

# Deny latest tag
deny[msg] {
    input[i].Cmd == "from"
    val := input[i].Value[_]
    contains(val, ":latest")
    msg := sprintf("Line %d: Using 'latest' tag is not allowed - use specific versions (e.g., :3.11-slim)", [i])
}

# Deny images without tags
deny[msg] {
    input[i].Cmd == "from"
    val := input[i].Value[_]
    not contains(val, ":")
    not contains(val, "@sha256:")
    msg := sprintf("Line %d: Base image '%s' must specify an explicit tag or digest", [i, val])
}

# Require approved base images
deny[msg] {
    input[i].Cmd == "from"
    val := input[i].Value[_]
    # Extract image name (before @ or :)
    image_parts := split(val, ":")
    image_name := image_parts[0]
    not approved_image(image_name)
    msg := sprintf("Line %d: Base image '%s' is not approved. Approved images: python:3.11-slim*, nginx:*-alpine*, postgres:*-alpine*, redis:*-alpine*", [i, image_name])
}

# Approved base images list
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
    # Allow scratch for minimal images
    image == "scratch"
}

# ==============================================================================
# WARN RULES - Advisory warnings
# ==============================================================================

# Warn about unpinned pip packages
warn[msg] {
    input[i].Cmd == "run"
    val := input[i].Value[_]
    contains(lower(val), "pip install")
    not contains(val, "==")
    not contains(val, "-r")  # Requirements file is OK
    msg := sprintf("Line %d: Consider pinning pip package versions with '==' for reproducibility", [i])
}

# Warn if COPY doesn't set ownership
warn[msg] {
    input[i].Cmd == "copy"
    not has_chown_flag(input[i])
    msg := sprintf("Line %d: Consider using --chown flag with COPY for proper file ownership", [i])
}

has_chown_flag(instruction) {
    instruction.Flags[_] == "--chown"
}

# Warn about curl/wget without cleanup
warn[msg] {
    input[i].Cmd == "run"
    val := input[i].Value[_]
    contains(lower(val), "curl")
    not contains(lower(val), "rm")
    msg := sprintf("Line %d: Consider cleaning up downloaded files after use", [i])
}

# Warn about missing EXPOSE
warn[msg] {
    not expose_defined
    msg := "Consider adding EXPOSE directive to document which ports the container listens on"
}

expose_defined {
    input[_].Cmd == "expose"
}

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

lower(s) = output {
    output := lower(s)
}
