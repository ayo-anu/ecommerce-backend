FROM alpine:3.18

RUN apk add --no-cache \
    pgbouncer \
    postgresql-client \
    ca-certificates

RUN mkdir -p /etc/pgbouncer /var/log/pgbouncer /var/run/pgbouncer && \
    chown -R postgres:postgres /etc/pgbouncer /var/log/pgbouncer /var/run/pgbouncer

COPY pgbouncer.ini /etc/pgbouncer/pgbouncer.ini
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh && \
    chown postgres:postgres /etc/pgbouncer/pgbouncer.ini

EXPOSE 6432

USER postgres

ENTRYPOINT ["/entrypoint.sh"]
CMD ["pgbouncer", "/etc/pgbouncer/pgbouncer.ini"]
