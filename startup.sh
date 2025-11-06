pkill -f "hedge/hedge_mode_lighter.py"

rm -rf perp-dex-tools

unzip perp-dex-tools.zip

source lumao_env/bin/activate

cd perp-dex-tools

nohup /home/admin/myproject/lumao_env/bin/python /home/admin/myproject/perp-dex-tools/hedge/hedge_mode_lighter.py &