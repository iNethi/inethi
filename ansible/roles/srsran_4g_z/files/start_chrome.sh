#!/bin/bash
echo "Start Chrome"

sudo xhost +local:root
sudo ip netns exec ue1 google-chrome --no-sandbox http://www.radiusdesk.com
