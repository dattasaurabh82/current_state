#!/bin/bash

mkdir -p $(HOME)/.config/systemd/user/

# TODO: 
# 1. Dynamically Replace hardcoded path of Working Dir in full-cycle-btn.service to where the project is located: <PROJECT DIR ABS PATH>
# 2. Dynamically Replace hardcoded path of Working Dir in music-player.service to where the project is located: <PROJECT DIR ABS PATH>
# 3. Dynamically Replace hardcoded path of Working Dir in process-monitor-web.service to where the project is located: <PROJECT DIR ABS PATH>  
# 4. Dynamically Replace hardcoded path of 'alias' in process-monitor-web to where the project is located: <PROJECT DIR ABS PATH>
# 5. Below, Dynamically Replace hardcoded paths form $(HOME)/current_state/services/... to <PROJECT DIR ABS PATH>/services/...
cp $(HOME)/current_state/services/full-cycle-btn.service $(HOME)/.config/systemd/user/
cp $(HOME)/current_state/services/music-player.service $(HOME)/.config/systemd/user/
cp $(HOME)/current_state/services/process-monitor-web.service $(HOME)/.config/systemd/user/

ls -la $(HOME)/.config/systemd/user/

systemctl --user daemon-reload
systemctl --user enable full-cycle-btn.service
systemctl --user enable music-player.service
systemctl --user enable process-monitor-web.service

systemctl --user start full-cycle-btn.service
systemctl --user start music-player.service
systemctl --user start process-monitor-web.service

# -----------
# Nginx setup
# -----------
chmod o+x $(HOME)
sudo cp $(HOME)/current_state/services/process-monitor-web /etc/nginx/sites-available/ # ToDo: Replace hardcoded paths form $(HOME)/current_state/services/... to <PROJECT DIR ABS PATH>/services/...

sudo ln -s /etc/nginx/sites-available/process-monitor-web /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default site
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
sudo systemctl enable nginx
sudo systemctl start nginx


# TODO:
# Show all 4 status (success or failure) in a nice TUI 