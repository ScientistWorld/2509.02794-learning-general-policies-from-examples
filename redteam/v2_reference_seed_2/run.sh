#!/bin/bash
set -euo pipefail
cd /home/user
python -m redteam.audit_v2.harness v2_reference_seed_2
