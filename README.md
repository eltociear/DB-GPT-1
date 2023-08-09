# DB-GPT
Welcome to the DB-GPT code repository! Our framework is designed to facilitate database tasks with LLMs. 

## Setup

```shell
conda create -n LMDB python=3.11	 	
conda activate LMDB
while read requirement; do pip install $requirement; done < requirements.txt
```

## Modules

The description of each component (click links to view detailed instructions).


| Module              | Description                                                  |
| ------------------- | ------------------------------------------------------------ |
| [DB-Bot](./diagnosis) | Diagnosing anomalies under the [agentverse](https://github.com/OpenBMB/AgentVerse) framework.        |
| [query_rewrite](./optimization/query_rewrite) | LLM for query rewrite.        |
| [index_tuning](./optimization/index_tuning) | LLM for index tuning.        |


## Contributing
Please leave your comments in the Issues if you would like to get involved or contribute!
