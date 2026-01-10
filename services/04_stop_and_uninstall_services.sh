#!/bin/bash

systemctl --user stop full-cycle-btn.service
systemctl --user stop music-player.service
systemctl --user stop process-monitor-web.service

systemctl --user disable full-cycle-btn.service
systemctl --user disable music-player.service
systemctl --user disable process-monitor-web.service

systemctl --user daemon-reload

# TODO: 
# Dynamically Replace hardcoded paths form $(HOME)/current_state/services/... to <PROJECT DIR ABS PATH>/services/...
rm $(HOME)/.config/systemd/user/full-cycle-btn.service
rm $(HOME)/.config/systemd/user/music-player.service
rm $(HOME)/.config/systemd/user/process-monitor-web.service

ls -la $(HOME)/.config/systemd/user/


# -----------
# Nginx setup
# -----------
sudo systemctl stop nginx
sudo systemctl disable nginx


# TODO:
# Show all 4 status (success or failure) in a nice TUI 