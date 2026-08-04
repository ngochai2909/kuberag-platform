# DB-008 Replication healthy — 2026-08-04

 application_name | client_addr |   state   | sync_state |   replay_lag    
------------------+-------------+-----------+------------+-----------------
 kuberag-pg-1     | 10.52.3.20  | streaming | async      | 00:00:00.002695
(1 row)


Streaming Replication status
Replication Slots Enabled
Name          Sent LSN    Write LSN   Flush LSN   Replay LSN  Write Lag  Flush Lag  Replay Lag  State      Sync State  Sync Priority  Replication Slot
----          --------    ---------   ---------   ----------  ---------  ---------  ----------  -----      ----------  -------------  ----------------
kuberag-pg-1  4/1A00B6F0  4/1A00B6F0  4/1A00B6F0  4/1A00B6F0  00:00:00   00:00:00   00:00:00    streaming  async       0              active

Instances status
