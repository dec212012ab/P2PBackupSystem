
rm -rf ~/.eth redist/geth ~/.backup_manifest
rm ../contracts/*.sc
python prereq.py --skip_golang --skip_ipfs --skip_ipfs_cluster_service --skip_ipfs_cluster_ctl --geth_generate_genesis_block --geth_generate_bootstrap_record --geth_generate_static_node_list --force
cd ..
#python init_geth.py
#cd install