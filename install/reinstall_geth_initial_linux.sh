
rm -rf ~/.eth redist/geth ~/.backup_manifest
python3 prereq.py --skip_golang --skip_ipfs --skip_ipfs_cluster_service --skip_ipfs_cluster_ctl --geth_generate_genesis_block --geth_generate_bootstrap_record --geth_generate_static_node_list --force
cd ..
#python3 init_geth.py
#cd install