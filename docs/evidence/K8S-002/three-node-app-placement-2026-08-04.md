# Three-node application placement — 2026-08-04

Verified after `make gcp-three-node-apps-apply` plus CPU-request packing
patches for the 2 vCPU application worker.

## Nodes
NAME                           STATUS   ROLES           AGE    VERSION        INTERNAL-IP   EXTERNAL-IP   OS-IMAGE             KERNEL-VERSION    CONTAINER-RUNTIME         LABELS
kuberag-server                 Ready    control-plane   7d5h   v1.35.5+k3s1   10.42.0.2     <none>        Ubuntu 24.04.4 LTS   6.17.0-1021-gcp   containerd://2.2.3-k3s1   beta.kubernetes.io/arch=amd64,beta.kubernetes.io/instance-type=k3s,beta.kubernetes.io/os=linux,kuberag.io/role=all-in-one,kuberag.io/topology=single-node,kubernetes.io/arch=amd64,kubernetes.io/hostname=kuberag-server,kubernetes.io/os=linux,node-role.kubernetes.io/control-plane=true,node.kubernetes.io/instance-type=k3s
kuberag-worker-application     Ready    <none>          86m    v1.35.5+k3s1   10.42.0.4     <none>        Ubuntu 24.04.4 LTS   6.17.0-1021-gcp   containerd://2.2.3-k3s1   beta.kubernetes.io/arch=amd64,beta.kubernetes.io/instance-type=k3s,beta.kubernetes.io/os=linux,kuberag.io/role=application,kuberag.io/topology=three-node,kubernetes.io/arch=amd64,kubernetes.io/hostname=kuberag-worker-application,kubernetes.io/os=linux,node.kubernetes.io/instance-type=k3s
kuberag-worker-observability   Ready    <none>          86m    v1.35.5+k3s1   10.42.0.3     <none>        Ubuntu 24.04.4 LTS   6.17.0-1021-gcp   containerd://2.2.3-k3s1   beta.kubernetes.io/arch=amd64,beta.kubernetes.io/instance-type=k3s,beta.kubernetes.io/os=linux,kuberag.io/role=observability,kuberag.io/topology=three-node,kubernetes.io/arch=amd64,kubernetes.io/hostname=kuberag-worker-observability,kubernetes.io/os=linux,node.kubernetes.io/instance-type=k3s

## Application pods
NAME                                   READY   STATUS      RESTARTS   AGE     IP           NODE                         NOMINATED NODE   READINESS GATES
kuberag-llm-674d5fc765-ldk6b           1/1     Running     0          2m56s   10.52.3.14   kuberag-worker-application   <none>           <none>
kuberag-llm-model-warm-vfnwp           0/1     Completed   0          60m     <none>       kuberag-worker-application   <none>           <none>
kuberag-pss-smoke-59bc599cd9-4bww6     1/1     Running     0          24h     10.52.1.11   kuberag-server               <none>           <none>
kuberag-rag-api-76bc559c7-xnjs9        1/1     Running     0          2m52s   10.52.3.15   kuberag-worker-application   <none>           <none>
kuberag-rag-api-embedding-warm-qczf7   0/1     Completed   0          60m     10.52.3.9    kuberag-worker-application   <none>           <none>
kuberag-web-5b44666bfc-w8dvg           1/1     Running     0          4m56s   10.52.3.10   kuberag-worker-application   <none>           <none>

## Prefect pods
NAME                                   READY   STATUS      RESTARTS   AGE     IP           NODE                         NOMINATED NODE   READINESS GATES
kuberag-ingestion-failure-test-ps5hk   0/1     Error       0          21h     10.52.1.50   kuberag-server               <none>           <none>
kuberag-prefect-embedding-warm-r7lb4   0/1     Completed   0          60m     10.52.3.8    kuberag-worker-application   <none>           <none>
prefect-server-5d6b9696bd-4zhw2        1/1     Running     0          4m47s   10.52.3.11   kuberag-worker-application   <none>           <none>
prefect-worker-7bcdb885-69s7p          1/1     Running     0          2m50s   10.52.3.16   kuberag-worker-application   <none>           <none>

## PostgreSQL (unchanged this phase)
NAME           READY   STATUS    RESTARTS   AGE   IP           NODE                           NOMINATED NODE   READINESS GATES
kuberag-pg-1   1/1     Running   0          71m   10.52.1.51   kuberag-server                 <none>           <none>
kuberag-pg-2   1/1     Running   0          74m   10.52.0.5    kuberag-worker-observability   <none>           <none>
NAME         AGE   INSTANCES   READY   STATUS                     PRIMARY
kuberag-pg   7d    2           2       Cluster in healthy state   kuberag-pg-1

## Application worker allocated resources
Allocated resources:
  (Total limits may be over 100 percent, i.e., overcommitted.)
  Resource           Requests      Limits
  --------           --------      ------
  cpu                1250m (62%)   9250m (462%)
  memory             5952Mi (74%)  14464Mi (182%)
  ephemeral-storage  0 (0%)        0 (0%)
  hugepages-1Gi      0 (0%)        0 (0%)
  hugepages-2Mi      0 (0%)        0 (0%)
Events:

## Envoy smoke
hostname: kuberag-pss-smoke-59bc599cd9-4bww6
frontend: 200

## Warm RAG query (redacted body preview only)
{
  "http": 200,
  "request_id": "0b771e4d-9fb2-461e-b0d1-ca89f77f85d4",
  "trace_id": "b5a649042aa2b8af61beb4e2994e7bf2",
  "sources": 3,
  "retrieval_ms": 78.55,
  "generation_ms": 7188.07,
  "total_ms": 7267.26,
  "answer_len": 229,
  "first_source_title": "Google tri\u1ec3n khai AI Agent cho ng\u01b0\u1eddi d\u00f9ng Vi\u1ec7t Nam"
}

## Notes

- First cold query returned HTTP 504 at the FastAPI 45s bound while E5 loaded.
- Warm query succeeded in ~7.6s through Envoy.
- Overlay CPU requests lowered so LLM+RAG+Prefect fit the 2 vCPU worker;
  limits remain higher for burst.
