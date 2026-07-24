# INF-003 Ansible install evidence

The first `make k3s-install` / `ansible-playbook` run reached the k3s installer but the upstream GitHub binary download failed. Recovery was completed interactively by downloading and checksum-verifying the pinned `v1.35.5+k3s1` binary, configuring the systemd service with Traefik disabled, and applying node labels after the API became ready.

This is recovery evidence, not a passing `INF-003` Ansible recap. The playbook was then updated to download the pinned binary directly with a SHA-256 checksum before configuring the service. `INF-003` and `INF-004` remain pending until clean and second Ansible runs are captured. Runtime cluster evidence is under `K8S-001` through `K8S-005`.
