#!/bin/bash
# -------------------------------------------------------------------
# robot_setup.sh - Complete TurtleBot network configuration assistant
# -------------------------------------------------------------------
set -e

echo "============================================"
echo " TurtleBot Network Configuration Assistant"
echo "============================================"

# ---------- 1. Install dependencies ----------
echo "[*] Installing dependencies..."

if ! command -v python3 &> /dev/null; then
    echo "Python3 is required but not found. Please install it first."
    exit 1
fi

if ! command -v pip3 &> /dev/null; then
    echo "pip3 not found, installing..."
    sudo apt-get update
    sudo apt-get install -y python3-pip
fi

sudo apt-get install -y sshpass
pip3 install --user ipscan

# ---------- 2. Detect local IP (used by both robot and local bashrc) ----------
LOCAL_IP=$(hostname -I | awk '{print $1}')
if [ -z "$LOCAL_IP" ]; then
    echo "Failed to detect local IP. Please check your network."
    exit 1
fi
echo "[*] Local IP detected: $LOCAL_IP"

# ---------- 3. Write Python script to temp file and execute ----------
echo "[*] Running the robot selection & SSH configuration..."

TMPPY=$(mktemp /tmp/robotsetup_XXXXXX.py)
cat > "$TMPPY" <<PYEOF
from ipscan import ping_range
import socket, os, subprocess, glob

user = 'ubuntu'
password = 'turtlebot'
local_ip = '$LOCAL_IP'          # use the IP detected by bash script

def ensure_ssh_key():
    """Check if any SSH private key exists. If not, generate one without a passphrase."""
    ssh_dir = os.path.expanduser("~/.ssh")
    key_candidates = glob.glob(os.path.join(ssh_dir, "id_*"))
    private_keys = [k for k in key_candidates if not k.endswith(".pub") and os.path.isfile(k)]
    if private_keys:
        print(f"SSH key(s) found: {', '.join(private_keys)}")
        return True
    print("No SSH key found. Generating new ED25519 key pair without passphrase...")
    os.system('ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519 -q')
    print("New SSH key generated at ~/.ssh/id_ed25519")
    return True

def check_ssh_simple(host, port=22, timeout=2):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def get_available_hosts():
    online_hosts = ping_range("192.168.1.1", "192.168.1.254", show_progress=False)
    ssh_hosts = []
    for host in online_hosts:
        if check_ssh_simple(host):
            ssh_hosts.append(host)
    return ssh_hosts

def print_hosts():
    hosts = get_available_hosts()
    if hosts:
        hosts_numbered = {idx+1: h for idx, h in enumerate(hosts)}
        print("Select host to configure: ")
        print("\n".join([f"({num}) {ip}" for num, ip in hosts_numbered.items()]))
        return hosts_numbered
    else:
        print('No hosts for configuration')
        return {}

def config_device(host, user, password):
    # Remove old host keys for this IP (to avoid mismatch errors)
    os.system(f'ssh-keygen -R {host} 2>/dev/null')
    # Copy the SSH key, accepting new host keys automatically
    cmd_copy_id = (
        f'sshpass -p "{password}" '
        f'ssh-copy-id -o StrictHostKeyChecking=accept-new '
        f'{user}@{host}'
    )
    print(f"Copying SSH key to {host} ...")
    os.system(cmd_copy_id)

    # Robot side: ROS_MASTER_URI points to local PC, ROS_HOSTNAME is robot's IP
    ros_master_uri = f"export ROS_MASTER_URI=http://{local_ip}:11311"
    ros_hostname   = f"export ROS_HOSTNAME={host}"

    # Remote .bashrc update
    remove_lines = (
        f"sed -i '/ROS_MASTER_URI/d' ~/.bashrc; "
        f"sed -i '/ROS_HOSTNAME/d' ~/.bashrc"
    )
    append_lines = (
        f"echo '{ros_master_uri}' >> ~/.bashrc; "
        f"echo '{ros_hostname}' >> ~/.bashrc"
    )
    remote_cmd = f"{remove_lines}; {append_lines}"
    ssh_cmd = f'sshpass -p "{password}" ssh {user}@{host} "{remote_cmd}"'
    print(f"Configuring ROS environment on {host} ...")
    os.system(ssh_cmd)

def update_local_alias(host_ip):
    bashrc_path = os.path.expanduser("~/.bashrc")
    new_alias_line = f"alias srob='ssh ubuntu@{host_ip}'\n"
    try:
        with open(bashrc_path, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = []
    lines = [line for line in lines if not line.strip().startswith("alias srob=")]
    lines.append(new_alias_line)
    with open(bashrc_path, "w") as f:
        f.writelines(lines)
    print(f"Local alias 'srob' updated -> ssh ubuntu@{host_ip}")

# ==================== MAIN ====================
if __name__ == "__main__":
    ensure_ssh_key()
    h = print_hosts()
    if h:
        number = int(input('Input number: '))
        chosen_ip = h[number]
        config_device(chosen_ip, user=user, password=password)
        update_local_alias(chosen_ip)
        print("Robot configuration complete.")
PYEOF

python3 "$TMPPY"
rm "$TMPPY"

# ---------- 4. Add static ROS environment variables to local .bashrc ----------
echo "[*] Adding ROS environment variables (with fixed local IP $LOCAL_IP) to your local ~/.bashrc..."

BASHRC="$HOME/.bashrc"

# Remove any previous ROS_MASTER_URI, ROS_HOSTNAME, and MAIN_HOST lines
sed -i '/export ROS_MASTER_URI=/d' "$BASHRC"
sed -i '/export ROS_HOSTNAME=/d' "$BASHRC"
sed -i '/^MAIN_HOST=/d' "$BASHRC"

# Add new static entries with the detected local IP
echo "# ROS environment (set by robot_setup.sh)" >> "$BASHRC"
echo "export ROS_MASTER_URI=http://$LOCAL_IP:11311" >> "$BASHRC"
echo "export ROS_HOSTNAME=$LOCAL_IP" >> "$BASHRC"
echo "export TURTLEBOT3_MODEL=waffle_pi" >> "$BASHRC"

# Add useful aliases (avoid duplicates)
add_if_missing() {
    local line="$1"
    if ! grep -qF "$line" "$BASHRC"; then
        echo "$line" >> "$BASHRC"
        echo "   Added: $line"
    else
        echo "   Already present: $line"
    fi
}

add_if_missing "alias rcr='roscore'"
add_if_missing "alias slam='roslaunch turtlebot3_slam turtlebot3_slam.launch slam_methods:=gmapping'"
add_if_missing "alias nav='roslaunch turtlebot3_navigation move_base.launch'"

# ---------- 5. Done ----------
echo ""
echo "============================================"
echo " Setup complete!"
echo "============================================"
echo " Local IP used: $LOCAL_IP"
echo " ROS_MASTER_URI and ROS_HOSTNAME have been written to ~/.bashrc"
echo " To apply all changes now, run:"
echo "   source ~/.bashrc"
echo " Then connect to your robot with:"
echo "   srob"
echo "============================================"