#!/bin/bash
# Sets up a legacy SSH service on onode for the N810 only.
# Port 22 (ubuntu login) is left unchanged.
# Run from the laptop:  ssh onode 'bash -s' < onode-legacy-setup.sh
set -e

# 1. Dedicated user, key login only
sudo id n810 >/dev/null 2>&1 || sudo useradd -m -s /bin/bash n810
sudo install -d -m 700 -o n810 -g n810 /home/n810/.ssh
sudo install -m 600 -o n810 -g n810 /dev/null /home/n810/.ssh/authorized_keys

# 2. Legacy sshd config: port 2222, n810 only, SHA-1 algorithms added
sudo tee /etc/ssh/sshd_config.legacy >/dev/null <<'CFG'
Port 2222
HostKey /etc/ssh/ssh_host_rsa_key
HostKey /etc/ssh/ssh_host_ed25519_key
PidFile /run/sshd-legacy.pid
AllowUsers n810
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
UsePAM yes
X11Forwarding no
KexAlgorithms +diffie-hellman-group14-sha1
HostKeyAlgorithms +ssh-rsa
PubkeyAcceptedAlgorithms +ssh-rsa
Subsystem sftp /usr/lib/openssh/sftp-server
CFG
sudo /usr/sbin/sshd -t -f /etc/ssh/sshd_config.legacy
echo "config OK"

# 3. Separate systemd service (ssh.service is untouched)
sudo tee /etc/systemd/system/ssh-legacy.service >/dev/null <<'UNIT'
[Unit]
Description=Legacy OpenSSH on port 2222 (N810 only)
After=network.target

[Service]
ExecStartPre=/usr/bin/mkdir -p /run/sshd
ExecStart=/usr/sbin/sshd -D -f /etc/ssh/sshd_config.legacy
Restart=on-failure

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now ssh-legacy.service
sleep 2
systemctl is-active ssh-legacy.service
sudo ss -ltnp | grep ':2222' || echo "not listening yet"

# 4. Host firewall: allow 2222 before the REJECT rule, and save it
sudo iptables -C INPUT -p tcp -m state --state NEW -m tcp --dport 2222 -j ACCEPT 2>/dev/null || \
  sudo iptables -I INPUT 5 -p tcp -m state --state NEW -m tcp --dport 2222 -j ACCEPT
sudo netfilter-persistent save
sudo iptables -S INPUT

echo "Done. Next: open TCP 2222 in the OCI security list, then add the N810 key to /home/n810/.ssh/authorized_keys."
