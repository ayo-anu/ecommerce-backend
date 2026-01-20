
package compose

import future.keywords.contains
import future.keywords.if
import future.keywords.in

deny[msg] {
    service := input.services[name]
    not service.deploy.resources.limits
    not excluded_from_resource_limits(name)
    msg := sprintf("Service '%s' must have resource limits (deploy.resources.limits) defined", [name])
}

deny[msg] {
    service := input.services[name]
    service.deploy.resources.limits
    not service.deploy.resources.limits.memory
    not excluded_from_resource_limits(name)
    msg := sprintf("Service '%s' must have memory limit defined", [name])
}

deny[msg] {
    service := input.services[name]
    service.deploy.resources.limits
    not service.deploy.resources.limits.cpus
    not excluded_from_resource_limits(name)
    msg := sprintf("Service '%s' must have CPU limit defined", [name])
}

deny[msg] {
    service := input.services[name]
    not service.healthcheck
    not excluded_from_healthcheck(name)
    msg := sprintf("Service '%s' must have a healthcheck configured", [name])
}

deny[msg] {
    service := input.services[name]
    not service.restart
    not excluded_from_restart_policy(name)
    msg := sprintf("Service '%s' must have a restart policy (e.g., 'always', 'unless-stopped')", [name])
}

deny[msg] {
    service := input.services[name]
    service.privileged == true
    msg := sprintf("Service '%s' cannot run in privileged mode - this is a security risk", [name])
}

deny[msg] {
    service := input.services[name]
    not service.security_opt
    not excluded_from_security_opt(name)
    msg := sprintf("Service '%s' must have security_opt set (e.g., 'no-new-privileges:true')", [name])
}

deny[msg] {
    service := input.services[name]
    not service.logging
    not excluded_from_logging(name)
    msg := sprintf("Service '%s' must have logging configured for audit trails", [name])
}

deny[msg] {
    service := input.services[name]
    service.network_mode == "host"
    msg := sprintf("Service '%s' cannot use host network mode - use bridge networking instead", [name])
}

deny[msg] {
    service := input.services[name]
    image := service.image
    contains(image, ":latest")
    msg := sprintf("Service '%s' uses ':latest' tag - use specific version tags instead", [name])
}

deny[msg] {
    service := input.services[name]
    volume := service.volumes[_]
    is_string(volume)
    sensitive_mount := ["/", "/etc", "/usr", "/bin", "/sbin", "/boot", "/sys"]
    host_path := split(volume, ":")[0]
    sensitive_mount[_] == host_path
    msg := sprintf("Service '%s' attempts to mount sensitive host path '%s' - this is not allowed", [name, host_path])
}


warn[msg] {
    service := input.services[name]
    not service.read_only
    not excluded_from_readonly(name)
    msg := sprintf("Service '%s' should consider using read_only root filesystem for added security", [name])
}

warn[msg] {
    service := input.services[name]
    not service.user
    not excluded_from_user_spec(name)
    msg := sprintf("Service '%s' should specify a non-root user (e.g., user: '1000:1000')", [name])
}

warn[msg] {
    service := input.services[name]
    service.cap_add
    caps := concat(", ", service.cap_add)
    msg := sprintf("Service '%s' adds capabilities [%s] - ensure this is necessary", [name, caps])
}

warn[msg] {
    service := input.services[name]
    count(service.ports) > 0
    not is_public_service(name)
    msg := sprintf("Service '%s' exposes ports - ensure this is intended for production", [name])
}

warn[msg] {
    service := input.services[name]
    env := service.environment[_]
    is_string(env)
    contains(lower(env), "password")
    msg := sprintf("Service '%s' may have password in environment - consider using Docker secrets instead", [name])
}

warn[msg] {
    service := input.services[name]
    env := service.environment[_]
    is_string(env)
    contains(lower(env), "secret")
    not contains(lower(env), "secret_id")
    msg := sprintf("Service '%s' may have secret in environment - consider using Docker secrets or Vault", [name])
}


excluded_from_resource_limits(name) {
    name == "localstack"
}

excluded_from_resource_limits(name) {
    name == "mailhog"
}

excluded_from_healthcheck(name) {
    name == "postgres"
}

excluded_from_healthcheck(name) {
    name == "postgres_ai"
}

excluded_from_healthcheck(name) {
    name == "redis"
}

excluded_from_healthcheck(name) {
    name == "redis_cache"
}

excluded_from_healthcheck(name) {
    name == "pgbouncer"
}

excluded_from_healthcheck(name) {
    name == "prometheus"
}

excluded_from_healthcheck(name) {
    name == "grafana"
}

excluded_from_restart_policy(name) {
    startswith(name, "test_")
}

excluded_from_restart_policy(name) {
    startswith(name, "migrate_")
}

excluded_from_security_opt(name) {
    name == "vault"
}

excluded_from_logging(name) {
    name == "localstack"
}

excluded_from_logging(name) {
    name == "mailhog"
}

excluded_from_readonly(name) {
    name == "postgres"
}

excluded_from_readonly(name) {
    name == "postgres_ai"
}

excluded_from_readonly(name) {
    name == "redis"
}

excluded_from_readonly(name) {
    name == "redis_cache"
}

excluded_from_readonly(name) {
    name == "vault"
}

excluded_from_user_spec(name) {
    name == "postgres"
}

excluded_from_user_spec(name) {
    name == "postgres_ai"
}

excluded_from_user_spec(name) {
    name == "redis"
}

excluded_from_user_spec(name) {
    name == "redis_cache"
}

excluded_from_user_spec(name) {
    name == "nginx"
}

is_public_service(name) {
    name == "nginx"
}

is_public_service(name) {
    name == "api-gateway"
}

is_string(x) {
    is_string(x)
}

lower(s) = output {
    output := lower(s)
}
