
rm -rf ~/.eth ~/.backup_manifest
python prereq.py --skip_golang --skip_ipfs --skip_ipfs_cluster_service --skip_ipfs_cluster_ctl --genesis_block_file redist/geth/genesis.json --geth_generate_bootstrap_record --geth_generate_static_node_list --force
cd ..
#python init_geth_secondary.py
#cd install