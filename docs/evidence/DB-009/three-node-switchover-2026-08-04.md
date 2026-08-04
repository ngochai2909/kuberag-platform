# DB-009 Controlled switchover — 2026-08-04

- Action: `kubectl cnpg promote kuberag-pg kuberag-pg-2 -n data`
- Started ~2026-08-04T08:48:33Z
- New primary: kuberag-pg-2 on kuberag-worker-observability
- Former primary kuberag-pg-1 became standby, later destroyed and
  recreated on kuberag-worker-application after postgresql-final.
- Warm RAG after switchover: HTTP 200 (~28.8s)

## Post-final topology
NAME           READY   STATUS    RESTARTS   AGE     IP           NODE                           NOMINATED NODE   READINESS GATES
kuberag-pg-1   1/1     Running   0          4m27s   10.52.3.20   kuberag-worker-application     <none>           <none>
kuberag-pg-2   1/1     Running   0          72s     10.52.0.20   kuberag-worker-observability   <none>           <none>

Cluster Summary
Name                     data/kuberag-pg
System ID:               7667486598156607507
PostgreSQL Image:        ghcr.io/cloudnative-pg/postgresql:18.4-standard-trixie@sha256:c94c6b0db7bc90c4d89cc0950fbb22907aa55df0e948cbc112adb87846660974
Primary instance:        kuberag-pg-2
Primary promotion time:  2026-08-04 08:48:37 +0000 UTC (10m24s)
Status:                  Cluster in healthy state 
Instances:               2
Ready instances:         2
Size:                    465M
Current Write LSN:       4/1A00AD90 (Timeline: 2 - WAL File: 00000002000000040000001A)

Continuous Backup not configured

Streaming Replication status
Replication Slots Enabled
Name          Sent LSN    Write LSN   Flush LSN   Replay LSN  Write Lag  Flush Lag  Replay Lag  State      Sync State  Sync Priority  Replication Slot
----          --------    ---------   ---------   ----------  ---------  ---------  ----------  -----      ----------  -------------  ----------------
kuberag-pg-1  4/1A00AD90  4/1A00AD90  4/1A00AD90  4/1A00AD90  00:00:00   00:00:00   00:00:00    streaming  async       0              active

Instances status
Name          Current LSN  Replication role  Status  QoS        Manager Version  Node
----          -----------  ----------------  ------  ---        ---------------  ----
kuberag-pg-2  4/1A00AD90   Primary           OK      Burstable  1.30.0           kuberag-worker-observability
kuberag-pg-1  4/1A00AD90   Standby (async)   OK      Burstable  1.30.0           kuberag-worker-application

