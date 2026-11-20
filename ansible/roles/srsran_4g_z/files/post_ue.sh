#!/bin/bash
echo "Add DNS and Default Route"

sudo ip netns exec ue1 bash -c "echo 'nameserver 8.8.8.8' > /etc/resolv.conf"
sudo ip netns exec ue1 ip route add default via 10.45.0.1 dev tun_srsue
