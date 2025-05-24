#!/bin/bash

echo "🔧 Inizializzo variabili ambiente..."
source ~/.bashrc
source ~/.profile  # se presente

echo "🗂️ Avvio HDFS (start-dfs.sh)..."
$HADOOP_HOME/sbin/start-dfs.sh

echo "🚀 Avvio Ray (nodo HEAD)..."
ray start --head --node-ip-address=192.168.100.10 --port=6379

echo "✅ MASTER pronto. HDFS e Ray HEAD attivi."
