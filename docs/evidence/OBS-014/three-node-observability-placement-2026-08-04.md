# Three-node observability placement — 2026-08-04

Fresh redeploy onto `kuberag-worker-observability` via
`scripts/gcp-three-node-observability-migrate.sh`.
Short-retention telemetry PVCs were recreated (history reset).
PostgreSQL and application workloads were not modified.

## Pods
NAME                                                     READY   STATUS    RESTARTS   AGE     IP           NODE                           NOMINATED NODE   READINESS GATES
alertmanager-kuberag-monitoring-kube-pr-alertmanager-0   2/2     Running   0          2m52s   10.52.0.10   kuberag-worker-observability   <none>           <none>
kuberag-loki-0                                           2/2     Running   0          2m43s   10.52.0.17   kuberag-worker-observability   <none>           <none>
kuberag-monitoring-grafana-5b9c469444-qp4d4              3/3     Running   0          3m1s    10.52.0.9    kuberag-worker-observability   <none>           <none>
kuberag-monitoring-kube-pr-operator-8db69cf4c-xj558      1/1     Running   0          3m1s    10.52.0.6    kuberag-worker-observability   <none>           <none>
kuberag-monitoring-kube-state-metrics-7b7fb9cbc6-knzzq   1/1     Running   0          3m1s    10.52.0.8    kuberag-worker-observability   <none>           <none>
kuberag-otel-collector-6f8946d486-rwpwd                  1/1     Running   0          2m30s   10.52.0.16   kuberag-worker-observability   <none>           <none>
kuberag-pyroscope-0                                      1/1     Running   0          2m34s   10.52.0.19   kuberag-worker-observability   <none>           <none>
kuberag-tempo-0                                          1/1     Running   0          2m40s   10.52.0.18   kuberag-worker-observability   <none>           <none>
prometheus-kuberag-monitoring-kube-pr-prometheus-0       2/2     Running   0          2m51s   10.52.0.12   kuberag-worker-observability   <none>           <none>

## PVCs
NAME                                                                                                     STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE     VOLUMEMODE
data-kuberag-pyroscope-0                                                                                 Bound    pvc-612ff2aa-de5e-4441-a378-114473d09d97   5Gi        RWO            local-path     <unset>                 2m34s   Filesystem
kuberag-monitoring-grafana                                                                               Bound    pvc-748c4e87-47d3-44e2-a9f0-d8bb6470d992   2Gi        RWO            local-path     <unset>                 3m2s    Filesystem
prometheus-kuberag-monitoring-kube-pr-prometheus-db-prometheus-kuberag-monitoring-kube-pr-prometheus-0   Bound    pvc-8c84b671-abcc-49cc-ae5e-7abf86498a5f   10Gi       RWO            local-path     <unset>                 2m51s   Filesystem
storage-kuberag-loki-0                                                                                   Bound    pvc-34251382-a953-4a20-ac6a-116c3e956dc1   5Gi        RWO            local-path     <unset>                 2m43s   Filesystem
storage-kuberag-tempo-0                                                                                  Bound    pvc-556a7848-b278-43ee-acff-4c4a9df42eae   5Gi        RWO            local-path     <unset>                 2m40s   Filesystem

## Node resources
Allocated resources:
  (Total limits may be over 100 percent, i.e., overcommitted.)
  Resource           Requests      Limits
  --------           --------      ------
  cpu                1300m (65%)   4800m (240%)
  memory             2368Mi (29%)  5632Mi (70%)
  ephemeral-storage  0 (0%)        0 (0%)
  hugepages-1Gi      0 (0%)        0 (0%)
  hugepages-2Mi      0 (0%)        0 (0%)
Events:
