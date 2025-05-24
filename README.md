# ProgettoBigData
# Sistema Distribuito di Retrieval-Augmented Generation (RAG) per Documenti Scientifici

## Introduzione

Questo progetto ha l’obiettivo di costruire un sistema distribuito in grado di effettuare **Retrieval-Augmented Generation (RAG)** su un ampio insieme di documenti scientifici. L’intero sistema è stato implementato e testato in un cluster composto da due macchine virtuali (una master e una worker), configurate per lavorare in modo cooperativo tramite strumenti di elaborazione e memorizzazione distribuita.

Il progetto si articola in più fasi, a partire dalla gestione e preprocessamento di un dataset scientifico di grandi dimensioni, fino all’indicizzazione semantica dei documenti tramite embeddings e alla generazione contestualizzata delle risposte tramite modello linguistico. In fase finale, il sistema è anche in grado di valutare automaticamente la qualità delle risposte generate attraverso l'uso di un 'LLM as a Judge'.

## Dataset

Il dataset utilizzato è stato scaricato da Kaggle al seguente link:  
[https://www.kaggle.com/datasets/Cornell-University/arxiv](https://www.kaggle.com/datasets/Cornell-University/arxiv)

Si tratta del dump completo del database arXiv, fornito dalla Cornell University, in formato JSON e con una dimensione di circa **4,5 GB**. Ogni elemento del dataset rappresenta un articolo scientifico pubblicato su arXiv.org e contiene diversi metadati:
- `id`: identificativo dell'articolo su arXiv;
- `title`: titolo;
- `abstract`: riassunto;
- `authors`: lista degli autori;
- `categories`: insieme delle categorie arXiv associate;
- `update_date`: ultima data di aggiornamento.

Il dataset è stato inizialmente **caricato all'interno di HDFS**, per poter essere gestito tramite strumenti di elaborazione distribuita. 

## Preprocessing tramite Apache Spark su HDFS
Inizialmente, il dataset originale è stato prima **filtrato** per selezionare solamente gli articoli appartenenti alla categoria `cs.AI` (Artificial Intelligence).
Il dataset filtrato è stato poi preprocessato utilizzando **Apache Spark**, con l'obiettivo di:
- ripulire i testi rimuovendo caratteri indesiderati e formattazioni non necessarie;
- normalizzare il contenuto degli abstract;
- suddividere ciascun abstract in uno o più **chunk** testuali coerenti, pronti per la successiva elaborazione semantica;
- estrazione dei metadati (come ID dell’articolo, titolo, e categoria) che saranno utilizzati in fase di risposta per arricchire il contesto.

Il risultato è un file JSON contenente i chunk di testo associati agli articoli `cs.AI` e con i relativi metadati, già pronti per la fase di embedding.

## Calcolo Distribuito degli Embedding con Ray tramite modello SentenceTransformers

Una volta ottenuti i chunk, è stata avviata la fase di calcolo degli **embedding vettoriali** mediante l’uso del framework **Ray**, che consente l’elaborazione distribuita e parallela su più nodi del cluster. Per la generazione degli embedding è stato utilizzato il modello `all-MiniLM-L6-v2` fornito dalla libreria **SentenceTransformers**, in grado di produrre rappresentazioni numeriche semanticamente significative dei testi.

## Indicizzazione embeddings in Qdrant (Vector Database)

Il file risultante contenente tutti gli embedding e i relativi metadati è stato caricato all’interno di **Qdrant**, un **vector database** ottimizzato per il retrieval semantico. Qdrant è stato configurato in modalità distribuita e utilizza l’algoritmo **HNSW (Hierarchical Navigable Small World)** per indicizzare i vettori e permettere il recupero efficiente dei documenti semanticamente più rilevanti rispetto a una query.

## Generazione delle Risposte con LLM puro e LLM + RAG

Una volta indicizzati i documenti, è stato realizzato uno script che implementa il comportamento completo del sistema RAG: a partire da una **domanda in linguaggio naturale** inserita dall’utente, il sistema effettua il retrieval dei documenti più rilevanti tramite Qdrant, ed elabora una risposta **contestualizzata** utilizzando il modello linguistico **phi-4**, eseguito tramite API esterne.

Viene inoltre generata una seconda risposta "pura", ottenuta da phi-4 **senza l’uso di documenti di contesto**, al fine di permettere un confronto tra i due approcci.

## Valutazione Automatica delle Risposte (LLM as a Judge)

Come fase finale, il sistema integra un modulo di **valutazione automatica** delle risposte, basato sul paradigma *LLM-as-a-Judge*. Viene utilizzato il modello linguistico **LLaMA 3**, accessibile tramite le **API gratuite di OpenRouter**, per confrontare le due risposte (quella "pura" e quella RAG) secondo criteri quali:
- completezza,
- accuratezza,
- coerenza,
- aderenza al contesto.

L'obiettivo di questa parte finale è fornire un sistema oggettivo di **valutazione della qualità** delle risposte generate, simulando il comportamento di un giudice umano.

---
