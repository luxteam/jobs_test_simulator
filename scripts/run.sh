#!/bin/bash
TESTS_FILTER="$1"
RETRIES=${2:-2}
python3.9 -m pip install --user -r ../jobs_launcher/install/requirements.txt

python3.9 ../jobs_launcher/executeTests.py --test_filter $TESTS_FILTER --file_filter none --tests_root ../jobs --work_root ../Work/Results --work_dir Simulator --cmd_variables Tool "/home/$(eval whoami)/svlsimulator/simulator" ResPath "$CIS_TOOLS/../TestResources/simulator" retries $RETRIES
