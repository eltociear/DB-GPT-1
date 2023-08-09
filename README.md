# DB-GPT
Welcome to the DB-GPT code repository! Our framework is based on LLM and designed to facilitate database tasks. 

## Setup

```shell
conda create -n LMDB python=3.11	 	
conda activate LMDB
while read requirement; do pip install $requirement; done < requirements.txt
```

## Modules

The description of files included in each module is shown below (click corresponding links to view detailed instructions).


| Module              | Description                                                  |
| ------------------- | ------------------------------------------------------------ |
| [DB-Bot](./diagnosis) | Diagnosing root causes of database anomalies under the [agentverse](https://github.com/OpenBMB/AgentVerse) framework.        |
| [query_rewrite](./optimization/query_rewrite) | LLM for query rewrite.        |
| [index_tuning](./optimization/index_tuning) | LLM for index tuning.        |


## Contributing
Please leave your comments in the Issues if you would like to get involved or contribute!
