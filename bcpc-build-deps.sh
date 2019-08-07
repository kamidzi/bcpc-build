# Build dependencies for bcpc-build

set -e

# Virtualbox
# vbox_ver=6.0
# ## add repositories
# wget -q https://www.virtualbox.org/download/oracle_vbox_2016.asc -O- |\
#   sudo apt-key add -
# wget -q https://www.virtualbox.org/download/oracle_vbox.asc -O- |\
#   sudo apt-key add -
# url='https://download.virtualbox.org/virtualbox/debian'
# read _ codename <<< "$(lsb_release -c)"
# sudo apt-add-repository --yes -u "deb $url $codename contrib"
# ## download && install
# sudo apt install -y "virtualbox-${vbox_ver}"

# Best to to stick with OS distributor's version of virtualbox, otherwise will
# have issues with python bindings; i.e., missing VBoxPython{minor}_{major}m.so
# which has _correct_ symbols.
sudo apt install -y virtualbox sqlite3 vagrant
