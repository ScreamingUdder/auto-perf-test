# auto-perf-test

To use this:
- Set up Mantid developer environment
- Install pip and then required python packages by doing `pip install -r requirements.txt`
- This repository uses git submodules, do `git submodule init` then `git submodule update`
- To run as a systemd service:
  - Edit the path and environment variables in `auto-perf-test.service`
  - Put `auto-perf-test.service` in your systemd directory, usually `/etc/systemd/system`
  - Enable the service to start at boot with `systemctl enable auto-perf-test`
  - Start the service with `systemctl start auto-perf-test`
- Alternatively, to launch manually you can edit then run `run_autotest.sh`
