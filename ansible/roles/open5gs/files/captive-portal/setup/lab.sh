#!/usr/bin/env bash

set -e

LAN_IF="enp8s0"
WAN_IF="wlp9s0"
BR_IF="br0"
NS="testns"
VETH_HOST="veth-host"
VETH_CLIENT="veth-client"
#SUBNET="192.168.50.0/24"
SUBNET="172.16.0.0/16"
#GW_IP="192.168.50.1"
GW_IP="172.16.0.1"

DHCP_CONF="/etc/dhcp/dhcpd.conf"
DHCP_DEFAULT="/etc/default/isc-dhcp-server"

function setup_network() {
    echo "[+] Creating bridge"
    ip link add $BR_IF type bridge || true
    ip link set $BR_IF up

    echo "[+] Attaching $LAN_IF to bridge"
    ip link set $LAN_IF master $BR_IF

    echo "[+] Assigning IP to bridge"
    ip addr flush dev $LAN_IF || true
    ip addr add $GW_IP/16 dev $BR_IF

    echo "[+] Creating veth pair"
    ip link add $VETH_HOST type veth peer name $VETH_CLIENT || true

    echo "[+] Attaching veth-host to bridge"
    ip link set $VETH_HOST master $BR_IF
    ip link set $VETH_HOST up

    echo "[+] Creating namespace"
    ip netns add $NS || true
    ip link set $VETH_CLIENT netns $NS

    echo "[+] Bringing up namespace interfaces"
    ip netns exec $NS ip link set lo up
    ip netns exec $NS ip link set $VETH_CLIENT up
}

function setup_dhcp() {
    echo "[+] Configuring DHCP server"

    cat > $DHCP_CONF <<EOF
default-lease-time 6000;
max-lease-time 72000;

subnet 172.16.0.0 netmask 255.255.0.0 {
  range 172.16.0.100 172.16.0.200;
  option routers 172.16.0.1;
  option domain-name-servers 8.8.8.8;
}
EOF

    sed -i "s/^INTERFACESv4=.*/INTERFACESv4=\"$BR_IF\"/" $DHCP_DEFAULT || true

    systemctl restart isc-dhcp-server
}

function setup_nat() {
    echo "[+] Enabling IP forwarding"
    sysctl -w net.ipv4.ip_forward=1

    echo "[+] Configuring iptables NAT"
    iptables -t nat -A POSTROUTING -o $WAN_IF -j MASQUERADE
    iptables -A FORWARD -i $BR_IF -o $WAN_IF -j ACCEPT
    iptables -A FORWARD -i $WAN_IF -o $BR_IF -m state --state RELATED,ESTABLISHED -j ACCEPT
}

function get_dhcp() {
    echo "[+] Requesting DHCP lease inside namespace"
    ip netns exec $NS dhclient $VETH_CLIENT
}

function test_connectivity() {
    echo "[+] Checking IP"
    ip netns exec $NS ip addr show $VETH_CLIENT

    echo "[+] Pinging gateway"
    ip netns exec $NS ping -c 2 $GW_IP

    echo "[+] Pinging internet"
    ip netns exec $NS ping -c 2 8.8.8.8

    echo "[+] Testing DNS"
    ip netns exec $NS ping -c 2 google.com
}

function teardown() {
    echo "[+] Stopping DHCP"
    systemctl stop isc-dhcp-server || true

    echo "[+] Removing iptables rules"
    iptables -t nat -D POSTROUTING -o $WAN_IF -j MASQUERADE || true
    iptables -D FORWARD -i $BR_IF -o $WAN_IF -j ACCEPT || true
    iptables -D FORWARD -i $WAN_IF -o $BR_IF -m state --state RELATED,ESTABLISHED -j ACCEPT || true

    echo "[+] Deleting namespace"
    ip netns delete $NS || true

    echo "[+] Deleting veth"
    ip link delete $VETH_HOST || true

    echo "[+] Removing bridge"
    ip link set $LAN_IF nomaster || true
    ip link delete $BR_IF || true

    echo "[+] Cleaning IP"
    ip addr flush dev $LAN_IF || true
}

case "$1" in
    up)
        setup_network
        setup_dhcp
        setup_nat
        get_dhcp
        ;;
    test)
        test_connectivity
        ;;
    down)
        teardown
        ;;
    *)
        echo "Usage: $0 {up|test|down}"
        exit 1
        ;;
esac
