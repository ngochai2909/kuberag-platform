# DB-002 Primary/replica on two workers — 2026-08-04

NAME           READY   STATUS    RESTARTS   AGE     IP           NODE                           NOMINATED NODE   READINESS GATES
kuberag-pg-1   1/1     Running   0          4m30s   10.52.3.20   kuberag-worker-application     <none>           <none>
kuberag-pg-2   1/1     Running   0          75s     10.52.0.20   kuberag-worker-observability   <none>           <none>

Affinity excludes server (all-in-one):
{
    "requiredDuringSchedulingIgnoredDuringExecution": {
        "nodeSelectorTerms": [
            {
                "matchExpressions": [
                    {
                        "key": "kuberag.io/role",
                        "operator": "In",
                        "values": [
                            "observability",
                            "application"
                        ]
                    }
                ]
            }
        ]
    }
}
